from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view
from .views import user_delete_view
from .views_firebase import firebase_session_login, password_session_login, password_session_signup
from .views_google_oauth import google_oauth_start, google_oauth_callback

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("~delete/", view=user_delete_view, name="delete"),
    path("firebase/login/", view=firebase_session_login, name="firebase_login"),
    path("password/login/", view=password_session_login, name="password_login"),
    path("password/signup/", view=password_session_signup, name="password_signup"),
    # Server-side Google OAuth (no popup, no origin_mismatch)
    path("google/login/", view=google_oauth_start, name="google_oauth_start"),
    path("google/callback/", view=google_oauth_callback, name="google_oauth_callback"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]
