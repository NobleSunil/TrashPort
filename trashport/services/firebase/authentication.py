from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from .utils import verify_firebase_id_token
from .exceptions import FirebaseAuthenticationError

User = get_user_model()


class FirebaseTokenAuthentication(BaseAuthentication):
    """
    DRF Authentication class for Firebase ID Tokens passed via Authorization Header:
    Authorization: Bearer <firebase_id_token>
    """
    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]
        decoded_token = verify_firebase_id_token(token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email", "").strip().lower()

        if not uid:
            raise FirebaseAuthenticationError("Token missing user identifier (uid).")

        user = User.objects.filter(firebase_uid=uid).first()
        if not user and email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                user.firebase_uid = uid
                user.save()

        if not user:
            name = decoded_token.get("name") or (email.split("@")[0].capitalize() if email else "User")
            user = User.objects.create_user(
                email=email or f"{uid}@trashport.local",
                name=name,
                role=User.Roles.CITIZEN,
            )
            user.firebase_uid = uid
            user.set_unusable_password()
            user.save()

        return (user, decoded_token)
