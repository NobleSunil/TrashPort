from django.contrib.auth import login as django_login
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .serializers import FirebaseTokenVerifySerializer
from .utils import verify_firebase_id_token
from django.contrib.auth import get_user_model

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_token_view(request):
    """
    API View to verify a Firebase ID token and authenticate or create the local user.
    """
    serializer = FirebaseTokenVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    token = serializer.validated_data["token"]
    role = serializer.validated_data.get("role", User.Roles.CITIZEN)
    passed_name = serializer.validated_data.get("name")
    password = serializer.validated_data.get("password")

    decoded = verify_firebase_id_token(token)
    uid = decoded.get("uid")
    email = decoded.get("email", "").strip().lower()

    user = User.objects.filter(firebase_uid=uid).first()
    if not user and email:
        user = User.objects.filter(email__iexact=email).first()
        if user:
            user.firebase_uid = uid
            if password:
                user.set_password(password)
            user.save()

    if not user:
        display_name = passed_name or decoded.get("name") or (email.split("@")[0].capitalize() if email else "User")
        user = User.objects.create_user(
            email=email or f"{uid}@trashport.local",
            name=display_name,
            role=role,
        )
        user.firebase_uid = uid
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    return Response({
        "status": "success",
        "user": {
            "id": user.pk,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "firebase_uid": user.firebase_uid,
        },
        "redirect_url": "/dashboard/"
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Returns current user's profile and firebase details."""
    user = request.user
    return Response({
        "id": user.pk,
        "email": user.email,
        "name": user.name,
        "role": getattr(user, "role", "CITIZEN"),
        "wallet_points": getattr(user, "wallet_points", 0),
        "firebase_uid": getattr(user, "firebase_uid", None),
    })
