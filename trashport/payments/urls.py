from django.urls import path
from .views import (
    PaymentTransactionListView,
    WalletHistoryListView,
    create_payment_intent_view,
)
from .webhooks import stripe_webhook

app_name = "payments"

urlpatterns = [
    path("history/", PaymentTransactionListView.as_view(), name="payment_history"),
    path("wallet/history/", WalletHistoryListView.as_view(), name="wallet_history"),
    path("intent/create/", create_payment_intent_view, name="create_intent"),
    path("webhook/stripe/", stripe_webhook, name="stripe_webhook"),
]
