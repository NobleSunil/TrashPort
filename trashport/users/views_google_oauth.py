"""
Server-side Google OAuth 2.0 flow for TrashPort.

Instead of a browser popup (which requires Authorized JavaScript Origins),
the server initiates the OAuth redirect and handles the callback.
This avoids ALL origin_mismatch errors entirely.

Required Google Cloud Console setting:
  Authorized redirect URIs → add:  http://localhost:8001/users/google/callback/
                                   http://127.0.0.1:8001/users/google/callback/
"""

# ==============================================================================
# Standard and Third-Party Library Imports
# ==============================================================================
import logging
import os
import secrets

import requests
from django.conf import settings
from django.contrib.auth import login as django_login
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from firebase_admin import auth as firebase_auth
from google_auth_oauthlib.flow import Flow

from trashport.users.models import User

# Logger instance for tracking OAuth events, errors, and debug statements
logger = logging.getLogger(__name__)


# ==============================================================================
# Google OAuth 2.0 Helper Functions
# ==============================================================================

def _get_client_id(request=None) -> str:
    # Retrieve the Google OAuth Client ID from Django settings or environment variable
    cid = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    if not cid:
        cid = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    return cid


# Requested permissions from Google Account (Identity, Email address, and Basic Profile)
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _get_redirect_uri(request) -> str:
    """
    Build the callback URI dynamically based on the current host, or use override if set.
    Ensures that localhost/127.0.0.1 and production domains resolve to the correct URI.
    """
    # Check if a custom redirect URI is explicitly set in settings or .env
    override = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "") or os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    if override:
        uri = override.strip()
    else:
        # Construct absolute callback URL using the current request's host
        uri = request.build_absolute_uri("/users/google/callback/")
        # For public domains (Cloudflare/EC2/Production), enforce HTTPS scheme
        host = request.get_host().split(":")[0].lower()
        if host not in ("localhost", "127.0.0.1", "0.0.0.0") and uri.startswith("http://"):
            uri = "https://" + uri[7:]

    # Log redirect URI for verification and debugging
    logger.info(f"Google OAuth redirect_uri: {uri}")
    return uri


def _get_flow(request) -> Flow:
    """
    Create and configure the Google OAuth 2.0 Flow object using Client ID and Secret.
    This manages the PKCE challenge and OAuth URLs.
    """
    redirect_uri = _get_redirect_uri(request)
    # Define client configuration dictionary required by google_auth_oauthlib
    client_config = {
        "web": {
            "client_id": _get_client_id(request),
            "client_secret": _get_client_secret(request),  # Use the actual client secret
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    # Instantiate Flow instance from dictionary config
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


# ==============================================================================
# OAuth Flow - Step 1: Authorization Request
# ==============================================================================
@require_GET
def google_oauth_start(request):
    """
    Step 1: Redirect the user to Google's OAuth consent screen.
    - Captures the desired user role (CITIZEN or COLLECTOR)
    - Generates a secure CSRF state token and PKCE verifier
    - Stores state in the session to validate the callback
    """
    # Extract role parameter from query string (defaults to CITIZEN)
    role = request.GET.get("role", User.Roles.CITIZEN)
    # Generate cryptographic random token to prevent CSRF attacks
    state = secrets.token_urlsafe(32)

    # Initialize Google Flow and obtain authorization URL with PKCE
    flow = _get_flow(request)
    auth_url, _ = flow.authorization_url(
        state=state,
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )

    # Store state and PKCE verifier in the session for verification in Step 2
    request.session["google_oauth_state"] = state
    request.session["google_oauth_role"] = role
    request.session["google_oauth_code_verifier"] = flow.code_verifier
    request.session.modified = True

    # Redirect user browser to Google OAuth consent page
    return redirect(auth_url)


# ==============================================================================
# OAuth Flow - Step 2: Callback and Account Provisioning
# ==============================================================================
@require_GET
def google_oauth_callback(request):
    """
    Step 2: Google redirects here after the user grants consent.
    - Validates state to prevent CSRF attacks
    - Exchanges the authorization code for access and ID tokens
    - Fetches Google profile details (email, name, Google UID)
    - Finds or creates the User record with the selected role
    - Authenticates and logs the user into the Django session
    """
    # Check if Google returned an error query parameter
    error = request.GET.get("error")
    if error:
        logger.warning(f"Google OAuth error: {error}")
        return redirect(f"/accounts/signup/?google_error={error}")

    # Extract authorization code and returned state parameter
    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("google_oauth_state")
    role = request.session.get("google_oauth_role", User.Roles.CITIZEN)
    code_verifier = request.session.get("google_oauth_code_verifier")

    # Validate that authorization code is present
    if not code:
        return redirect("/accounts/signup/?google_error=no_code")

    # Validate CSRF state token against session value
    if state != session_state:
        return redirect("/accounts/signup/?google_error=state_mismatch")

    # Exchange authorization code for tokens using Google's token endpoint
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

    # Verify ID token is returned in response
    id_token_jwt = token_data.get("id_token")
    if not id_token_jwt:
        return redirect("/accounts/signup/?google_error=no_id_token")

    # Fetch user profile information from Google's UserInfo API endpoint
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

    # Parse profile attributes from UserInfo response
    google_sub = userinfo.get("sub")       # Google's unique user ID
    email = userinfo.get("email", "").strip().lower()
    name = userinfo.get("name", "")
    email_verified = userinfo.get("email_verified", False)

    # Reject accounts where the email has not been verified by Google
    if not email or not email_verified:
        return redirect("/accounts/signup/?google_error=email_not_verified")

    # Try to verify with Firebase Admin SDK (links Google identity to Firebase UID)
    firebase_uid = None
    try:
        decoded = firebase_auth.verify_id_token(id_token_jwt, clock_skew_seconds=60)
        firebase_uid = decoded.get("uid")
    except Exception as fb_exc:
        logger.info(f"Firebase ID token verify skipped: {fb_exc}")
        # Use Google unique subject identifier as fallback UID
        firebase_uid = f"google-{google_sub}"

    # Search for an existing user by Firebase UID or email address
    user = User.objects.filter(firebase_uid=firebase_uid).first()
    if not user and email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            user.firebase_uid = firebase_uid

    # If user does not exist in database, create a new record
    if not user:
        # New user — create them with selected role (Citizen / Collector)
        user = User.objects.create_user(
            email=email,
            name=name or email.split("@")[0].capitalize(),
            firebase_uid=firebase_uid,
            role=role,
        )
        # Google OAuth users authenticate via OAuth, not traditional passwords
        user.set_unusable_password()
        logger.info(f"Created new user via Google OAuth: {email} (role={role})")

    # Update name if user profile does not have one set
    if name and not user.name:
        user.name = name

    # Persist user changes to database
    user.save()

    # Authenticate and log the user into the Django session
    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    logger.info(f"User {user.email} logged in via server-side Google OAuth.")

    # Clean up temporary session tokens used during the OAuth handshake
    request.session.pop("google_oauth_state", None)
    request.session.pop("google_oauth_role", None)
    request.session.pop("google_oauth_code_verifier", None)

    # Inform user they can optionally configure a password for traditional login
    if not user.has_usable_password():
        from django.contrib import messages
        messages.info(
            request,
            "Welcome! Since you signed in with Google, you can set an account password now or do it later from your Edit Profile page."
        )

    # Redirect to the role dashboard
    return redirect("/dashboard/")


# ==============================================================================
# Helper Function: Retrieve Google Client Secret
# ==============================================================================
def _get_client_secret(request):
    """
    Retrieve the Google OAuth client secret from settings or environment variables.
    The client secret is required to exchange the authorization code for tokens.
    """
    secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not secret:
        secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    return secret
