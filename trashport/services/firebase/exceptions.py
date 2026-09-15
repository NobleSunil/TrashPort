from rest_framework.exceptions import APIException


class FirebaseAuthenticationError(APIException):
    status_code = 401
    default_detail = "Invalid or expired Firebase authentication token."
    default_code = "firebase_authentication_failed"


class FirebaseUserNotFoundError(APIException):
    status_code = 404
    default_detail = "Firebase user not found."
    default_code = "firebase_user_not_found"


class FirebaseConfigurationError(Exception):
    """Raised when Firebase credentials or configuration are invalid."""
    pass
