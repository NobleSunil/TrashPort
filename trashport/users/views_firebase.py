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
            decoded = auth.verify_id_token(token)

        uid = decoded.get("uid")
        email = decoded.get("email", "")

        if not uid:
            return JsonResponse({"status": "error", "message": "Token missing user identifier (uid)."}, status=400)

        # Get or create the local Django user
        try:
            user = User.objects.get(firebase_uid=uid)
        except User.DoesNotExist:
            try:
                # Fallback to map existing user by matching email
                user = User.objects.get(email=email)
                user.firebase_uid = uid
                user.save()
            except User.DoesNotExist:
                # Get role from request if provided (default to CITIZEN)
                role = data.get("role", User.Roles.CITIZEN)
                if role not in User.Roles.values:
                    role = User.Roles.CITIZEN

                user = User.objects.create(
                    firebase_uid=uid,
                    email=email,
                    name=decoded.get("name", ""),
                    role=role
                )

        # Log the user into the Django session
        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info(f"User {user.email} successfully logged in via Firebase session.")

        # Determine dashboard redirect URL based on role
        redirect_url = "/dashboard/"
        
        return JsonResponse({"status": "success", "redirect_url": redirect_url})

    except Exception as e:
        logger.error(f"Firebase session login failed: {e}")
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

