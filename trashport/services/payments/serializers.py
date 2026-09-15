from rest_framework import serializers
from .models import PaymentTransaction, WalletHistory


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")


class CreatePaymentIntentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default="USD", max_length=10)
    description = serializers.CharField(required=False, allow_blank=True)


class WalletHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletHistory
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at")
