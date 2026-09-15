import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import StripePaymentService

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    """
    Receives and processes asynchronous Stripe Webhook callbacks.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body)
        event_type = payload.get("type", "")

        if event_type == "payment_intent.succeeded":
            data_obj = payload.get("data", {}).get("object", {})
            txn_id = data_obj.get("id")
            if txn_id:
                StripePaymentService.complete_payment(txn_id)

        return JsonResponse({"status": "received"})
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return JsonResponse({"error": str(e)}, status=400)
