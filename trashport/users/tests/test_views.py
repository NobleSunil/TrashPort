from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from trashport.users.forms import UserAdminChangeForm
from trashport.users.tests.factories import UserFactory
from trashport.users.views import UserRedirectView
from trashport.users.views import UserUpdateView
from trashport.users.views import user_detail_view

if TYPE_CHECKING:
    from django.test import RequestFactory

    from trashport.users.models import User

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request
        assert view.get_success_url() == "/users/profile/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserAdminChangeForm()
        form.cleaned_data = {}
        form.instance = user
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == [_("Information successfully updated")]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request
        assert view.get_redirect_url() == "/users/profile/"


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = UserFactory.create()
        response = user_detail_view(request, pk=user.pk)

        assert response.status_code == HTTPStatus.OK

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, pk=user.pk)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"


class TestPasswordResetAndEmailViews:
    def test_password_reset_page_loads(self, client):
        response = client.get(reverse("account_reset_password"))
        assert response.status_code == HTTPStatus.OK
        assert "Forgot Password?" in response.content.decode()

    def test_password_reset_submission_sends_email(self, client, user: User):
        response = client.post(
            reverse("account_reset_password"),
            data={"email": user.email},
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK
        assert "Check Your Email" in response.content.decode()

    def test_login_page_loads_with_forgot_password_link(self, client):
        response = client.get(reverse("account_login"))
        assert response.status_code == HTTPStatus.OK
        assert reverse("account_reset_password") in response.content.decode()

    def test_signup_page_loads_clean_form(self, client):
        response = client.get(reverse("account_signup"))
        assert response.status_code == HTTPStatus.OK
        assert "Create Account" in response.content.decode()
