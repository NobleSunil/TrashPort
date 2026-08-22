import json
import logging
from django.http import JsonResponse
from django.contrib.auth import authenticate, login as django_login, get_user_model
from django.views.decorators.csrf import csrf_exempt
from firebase_admin import auth

User = get_user_model()
logger = logging.getLogger(__name__)

@csrf_exempt
def firebase_session_login(request):
    """
    Accepts a Firebase ID token via POST, verifies it,
    logs the corresponding user into the Django session,
    and returns a redirect URL.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        token = data.get("token")
        password = data.get("password")
        if not token:
            return JsonResponse({"status": "error", "message": "Missing Firebase token"}, status=400)

        # Handle mock tokens for tests/development
        if token.startswith("mock-token-"):
            uid = token.replace("mock-token-", "")
            email = f"{uid}@example.com"
            decoded = {
                "uid": uid,
                "email": email,
                "name": uid.capitalize()
            }
        else:
            try:
                decoded = auth.verify_id_token(token, clock_skew_seconds=60)
            except Exception as firebase_err:
                logger.info(f"Firebase token verification failed ({firebase_err}), trying Google OAuth token verification...")
                from google.oauth2 import id_token as google_id_token
                from google.auth.transport import requests as google_requests
                decoded_google = google_id_token.verify_oauth2_token(
                    token,
                    google_requests.Request()
                )
                decoded = {
                    "uid": decoded_google.get("sub"),
                    "email": decoded_google.get("email"),
                    "name": decoded_google.get("name", "")
                }

        uid = decoded.get("uid")
        email = decoded.get("email", "").strip().lower()

        if not uid:
            return JsonResponse({"status": "error", "message": "Token missing user identifier (uid)."}, status=400)

        is_new_user = False
        requested_role = data.get("role")  # present when coming from signup page

        # 1. Try finding user by firebase_uid (most specific — already linked)
        user = User.objects.filter(firebase_uid=uid).first()

        # 2. If not found by firebase_uid, try matching by email
        if not user and email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                # Guard: do NOT silently link an admin/superuser account when the
                # request comes from the signup page asking for a different role.
                if requested_role and (user.is_superuser or user.role == User.Roles.ADMIN):
                    return JsonResponse({
                        "status": "error",
                        "message": (
                            "An admin account already exists with this email address. "
                            "Please use the Sign In page instead."
                        )
                    }, status=400)

                # Link the Firebase UID to the existing account
                user.firebase_uid = uid
                if password:
                    user.set_password(password)
                user.save()

        # 3. If user still doesn't exist, create a new one
        if not user:
            role = requested_role or User.Roles.CITIZEN
            if role not in User.Roles.values:
                role = User.Roles.CITIZEN

            display_name = (
                data.get("name")
                or decoded.get("name")
                or (email.split("@")[0].capitalize() if email else "User")
            )
            user_email = email or f"{uid}@trashport.local"

            user = User.objects.create_user(
                email=user_email,
                name=display_name,
                role=role,
            )
            user.firebase_uid = uid
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save()
            is_new_user = True

        # Log the user into the Django session
        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info(f"User {user.email} (role: {user.role}, new={is_new_user}) logged in via Firebase.")

        # New users → profile setup page so they can complete their details
        # Existing users → their role-specific dashboard
        if is_new_user:
            redirect_url = "/users/~update/"
        else:
            redirect_url = "/dashboard/"

        return JsonResponse({
            "status": "success",
            "redirect_url": redirect_url,
            "is_new_user": is_new_user,
            "firebase_uid": user.firebase_uid,
            "email": user.email,
            "user_id": user.id,
            "role": user.role,
        })

    except Exception as e:
        logger.error(f"Firebase session login failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@csrf_exempt
def password_session_signup(request):
    """
    Accepts email, password, and role via POST, creates user with hashed password,
    logs the user into the Django session, and returns a redirect URL.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        password = data.get("password", "")
        role = data.get("role", User.Roles.CITIZEN)

        if not email or not password:
            return JsonResponse({"status": "error", "message": "Email and password are required."}, status=400)

        if len(password) < 8:
            return JsonResponse({"status": "error", "message": "Password must be at least 8 characters long."}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({"status": "error", "message": "An account with this email already exists."}, status=400)

        if role not in User.Roles.values:
            role = User.Roles.CITIZEN

        user = User.objects.create_user(
            email=email,
            password=password,
            role=role,
            name=email.split("@")[0].capitalize(),
        )

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info(f"User {user.email} successfully created and logged in via direct password signup.")
        return JsonResponse({"status": "success", "redirect_url": "/dashboard/"})

    except Exception as e:
        logger.error(f"Password signup failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@csrf_exempt
def password_session_login(request):
    """
    Accepts email and password via POST, authenticates with Django backend,
    logs the user into the session, and returns a redirect URL.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not email or not password:
            return JsonResponse({"status": "error", "message": "Missing email or password."}, status=400)

        user = authenticate(request, email=email, password=password)
        if not user:
            return JsonResponse({"status": "error", "message": "Invalid email or password."}, status=400)

        if not user.is_active:
            return JsonResponse({"status": "error", "message": "This account is inactive."}, status=400)

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info(f"User {user.email} successfully logged in via Password auth.")
        return JsonResponse({"status": "success", "redirect_url": "/dashboard/"})

    except Exception as e:
        logger.error(f"Password session login failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

