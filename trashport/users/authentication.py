from firebase_admin import auth
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .firebase import initialize_firebase

User = get_user_model()
initialize_firebase()

class FirebaseAuthentication(BaseAuthentication):
    """
    Firebase Token-based Authentication for Django Rest Framework.
    
    Expects header:
    Authorization: Bearer <firebase_id_token>
    """
    def authenticate(self, request):
        header = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            return None

        token = header.split(" ")[1]
        
        # Enable mock token verification for local testing and unit tests
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
            except Exception as e:
                raise AuthenticationFailed(f"Invalid or expired Firebase token: {e}")

        uid = decoded.get("uid")
        email = decoded.get("email", "")

        if not uid:
            raise AuthenticationFailed("Token is missing user identifier (uid).")

        # Get or create a local custom Django user linked to the Firebase UID
        try:
            user = User.objects.get(firebase_uid=uid)
        except User.DoesNotExist:
            try:
                # Fallback to map existing user with matching email
                user = User.objects.get(email=email)
                user.firebase_uid = uid
                user.save()
            except User.DoesNotExist:
                # Create a new local user linked to the Firebase UID
                user = User.objects.create(
                    firebase_uid=uid,
                    email=email,
                    name=decoded.get("name", ""),
                    role=User.Roles.CITIZEN
                )

        return (user, decoded)
