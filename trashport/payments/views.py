from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import PaymentTransaction, WalletHistory
from .serializers import (
    PaymentTransactionSerializer,
    CreatePaymentIntentSerializer,
    WalletHistorySerializer,
)
from .services import StripePaymentService


class PaymentTransactionListView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentTransaction.objects.filter(user=self.request.user)


class WalletHistoryListView(generics.ListAPIView):
    serializer_class = WalletHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WalletHistory.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_intent_view(request):
    serializer = CreatePaymentIntentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    result = StripePaymentService.create_payment_intent(
        user=request.user,
        amount=serializer.validated_data["amount"],
        currency=serializer.validated_data.get("currency", "USD"),
        description=serializer.validated_data.get("description", ""),
    )
    return Response(result, status=status.HTTP_201_CREATED)
