from django.urls import path
from .views import verify_token_view, me_view

app_name = "firebase"

urlpatterns = [
    path("verify/", verify_token_view, name="verify_token"),
    path("me/", me_view, name="me"),
]
