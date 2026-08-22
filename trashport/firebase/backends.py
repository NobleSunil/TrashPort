from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from .utils import verify_firebase_id_token

User = get_user_model()


class FirebaseAuthenticationBackend(BaseBackend):
    """
    Django Authentication Backend that authenticates using Firebase ID token.
    """
    def authenticate(self, request, firebase_token=None, **kwargs):
        if not firebase_token:
            return None

        try:
            decoded = verify_firebase_id_token(firebase_token)
            uid = decoded.get("uid")
            email = decoded.get("email", "").strip().lower()

            if not uid:
                return None

            user = User.objects.filter(firebase_uid=uid).first()
            if not user and email:
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    user.firebase_uid = uid
                    user.save()

            if not user:
                role = kwargs.get("role", User.Roles.CITIZEN)
                name = kwargs.get("name") or decoded.get("name") or (email.split("@")[0].capitalize() if email else "User")
                user = User.objects.create_user(
                    email=email or f"{uid}@trashport.local",
                    name=name,
                    role=role,
                )
                user.firebase_uid = uid
                user.set_unusable_password()
                user.save()

            return user if user.is_active else None
        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
