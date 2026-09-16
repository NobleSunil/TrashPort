"""
Server-side Google OAuth 2.0 flow for TrashPort.

Instead of a browser popup (which requires Authorized JavaScript Origins),
the server initiates the OAuth redirect and handles the callback.
This avoids ALL origin_mismatch errors entirely.

Required Google Cloud Console setting:
  Authorized redirect URIs → add:  http://localhost:8001/users/google/callback/
                                   http://127.0.0.1:8001/users/google/callback/
"""

import logging
import secrets

import requests
from django.contrib.auth import login as django_login
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from google_auth_oauthlib.flow import Flow

from trashport.users.models import User
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

# ─── Google OAuth 2.0 settings ────────────────────────────────────────────────
# These match your Firebase project's auto-created OAuth 2.0 Web Client.
from django.conf import settings

def _get_client_id(request=None) -> str:
    cid = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    if not cid:
        import os
        cid = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    return cid

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

def _get_redirect_uri(request) -> str:
    """Build the callback URI dynamically based on the current host, or use override if set."""
    override = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "") or os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    if override:
        uri = override.strip()
    else:
        uri = request.build_absolute_uri("/users/google/callback/")
        # For public domains (Cloudflare/EC2), always enforce https scheme
        host = request.get_host().split(":")[0].lower()
        if host not in ("localhost", "127.0.0.1", "0.0.0.0") and uri.startswith("http://"):
            uri = "https://" + uri[7:]
    logger.info(f"Google OAuth redirect_uri: {uri}")
    return uri


def _get_flow(request) -> Flow:
    """Create an OAuth flow using the Google client ID."""
    redirect_uri = _get_redirect_uri(request)
    client_config = {
        "web": {
            "client_id": _get_client_id(request),
            "client_secret": _get_client_secret(request),  # Use the actual client secret
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


@require_GET
def google_oauth_start(request):
    """
    Step 1: Redirect the user to Google's OAuth consent screen.
    Stores CSRF state and role in session.
    """
    role = request.GET.get("role", User.Roles.CITIZEN)
    state = secrets.token_urlsafe(32)

    flow = _get_flow(request)
    auth_url, _ = flow.authorization_url(
        state=state,
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )

    request.session["google_oauth_state"] = state
    request.session["google_oauth_role"] = role
    request.session["google_oauth_code_verifier"] = flow.code_verifier
    request.session.modified = True

    return redirect(auth_url)


@require_GET
def google_oauth_callback(request):
    """
    Step 2: Google redirects here after the user grants consent.
    Exchange the auth code for tokens, verify the ID token, create/login user.
    """
    error = request.GET.get("error")
    if error:
        logger.warning(f"Google OAuth error: {error}")
        return redirect(f"/accounts/signup/?google_error={error}")

    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("google_oauth_state")
    role = request.session.get("google_oauth_role", User.Roles.CITIZEN)
    code_verifier = request.session.get("google_oauth_code_verifier")

    if not code:
        return redirect("/accounts/signup/?google_error=no_code")

    if state != session_state:
        return redirect("/accounts/signup/?google_error=state_mismatch")

    # Exchange auth code for tokens using Google's token endpoint
    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": _get_client_id(request),
                "client_secret": _get_client_secret(request),
                "redirect_uri": _get_redirect_uri(request),
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
            timeout=10,
        )
        if token_response.status_code != 200:
            logger.error(f"Google Token Exchange Error: {token_response.status_code} - {token_response.text}")
        token_response.raise_for_status()
        token_data = token_response.json()
    except Exception as exc:
        logger.error(f"Token exchange failed: {exc}")
        return redirect("/accounts/signup/?google_error=token_exchange_failed")

    id_token_jwt = token_data.get("id_token")
    if not id_token_jwt:
        return redirect("/accounts/signup/?google_error=no_id_token")

    # Get user info from Google's userinfo endpoint
    access_token = token_data.get("access_token")
    try:
        userinfo_resp = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()
    except Exception as exc:
        logger.error(f"Userinfo fetch failed: {exc}")
        return redirect("/accounts/signup/?google_error=userinfo_failed")

    google_sub = userinfo.get("sub")       # Google's unique user ID
    email = userinfo.get("email", "").strip().lower()
    name = userinfo.get("name", "")
    email_verified = userinfo.get("email_verified", False)

    if not email or not email_verified:
        return redirect("/accounts/signup/?google_error=email_not_verified")

    # Try to verify with Firebase Admin SDK (links Google identity to Firebase)
    firebase_uid = None
    try:
        decoded = firebase_auth.verify_id_token(id_token_jwt, clock_skew_seconds=60)
        firebase_uid = decoded.get("uid")
    except Exception as fb_exc:
        logger.info(f"Firebase ID token verify skipped: {fb_exc}")
        # Use Google sub as fallback UID
        firebase_uid = f"google-{google_sub}"

    # Find or create user
    user = User.objects.filter(firebase_uid=firebase_uid).first()
    if not user and email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            user.firebase_uid = firebase_uid

    if not user:
        # New user — create them
        user = User.objects.create_user(
            email=email,
            name=name or email.split("@")[0].capitalize(),
            firebase_uid=firebase_uid,
            role=role,
        )
        user.set_unusable_password()
        logger.info(f"Created new user via Google OAuth: {email} (role={role})")

    if name and not user.name:
        user.name = name

    user.save()

    # Log into Django session
    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    logger.info(f"User {user.email} logged in via server-side Google OAuth.")

    # Clean up session
    request.session.pop("google_oauth_state", None)
    request.session.pop("google_oauth_role", None)
    request.session.pop("google_oauth_code_verifier", None)

    if not user.has_usable_password():
        from django.contrib import messages
        messages.info(
            request,
            "Welcome! Since you signed in with Google, you can set a account password now or do it later from your Edit Profile page."
        )

    return redirect("/dashboard/")


def _get_client_secret(request):
    """
    Retrieve the Google OAuth client secret from settings or env.
    The client secret is needed to exchange the auth code for tokens.
    """
    secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not secret:
        import os
        secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    return secret
