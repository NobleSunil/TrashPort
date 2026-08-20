from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view
from .views import user_delete_view
from .views_firebase import firebase_session_login, password_session_login

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("~delete/", view=user_delete_view, name="delete"),
    path("firebase/login/", view=firebase_session_login, name="firebase_login"),
    path("password/login/", view=password_session_login, name="password_login"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]
