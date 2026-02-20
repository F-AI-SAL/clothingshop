import json
import hmac
import hashlib

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from ..models import PaymentWebhookEvent, PaymentProviderConfig
from ..services.payments import mark_payment_verified, mark_payment_refunded


def _verify_signature(provider, request):
    config = PaymentProviderConfig.objects.filter(provider=provider).first()
    if not config or not config.webhook_secret:
        return True
    header_name = config.signature_header or "X-Signature"
    signature = request.headers.get(header_name)
    timestamp, sig_value = _parse_signature(signature, config.signature_format)
    if not sig_value:
        return False

    payload = request.body
    if config.signature_payload == "t+raw" and timestamp:
        payload = f"{timestamp}.".encode("utf-8") + request.body

    digest = hmac.new(config.webhook_secret.encode("utf-8"), payload, hashlib.sha256).digest()
    if config.signature_format == "base64":
        import base64
        digest = base64.b64encode(digest).decode("utf-8")
    else:
        digest = digest.hex()

    return hmac.compare_digest(sig_value, digest)




def _parse_signature(header_value, signature_format):
    if not header_value:
        return None, None
    if signature_format == "t=,v1=":
        parts = {k: v for k, v in (p.split("=") for p in header_value.split(",") if "=" in p)}
        return parts.get("t"), parts.get("v1")
    return None, header_value


def _store_event(provider, event_id, payload):
    if PaymentWebhookEvent.objects.filter(event_id=event_id).exists():
        return False
    PaymentWebhookEvent.objects.create(provider=provider, event_id=event_id, payload=payload)
    return True




def _map_provider_status(provider, payload):
    if provider == "bkash":
        return str(payload.get("transactionStatus") or payload.get("status") or "").lower()
    if provider == "nagad":
        return str(payload.get("status") or payload.get("paymentStatus") or "").lower()
    return str(payload.get("status") or "").lower()


def _handle_status(payload, provider):
    status = _map_provider_status(provider, payload)
    reference_id = payload.get("trxID") or payload.get("transaction_id") or payload.get("reference_id")
    if status in ("success", "completed", "paid") and reference_id:
        mark_payment_verified(str(reference_id))
    if status in ("refunded",) and reference_id:
        mark_payment_refunded(str(reference_id))


@csrf_exempt
def bkash_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")
    if not _verify_signature("bkash", request):
        return HttpResponseBadRequest("Invalid signature")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    event_id = str(payload.get("event_id") or payload.get("trxID") or payload.get("transaction_id") or "")
    if not event_id:
        return HttpResponseBadRequest("Missing event_id")

    if not _store_event("bkash", event_id, payload):
        return JsonResponse({"status": "duplicate"})

    _handle_status(payload, "bkash")
    return JsonResponse({"status": "ok"})


@csrf_exempt
def nagad_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")
    if not _verify_signature("nagad", request):
        return HttpResponseBadRequest("Invalid signature")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    event_id = str(payload.get("event_id") or payload.get("trxID") or payload.get("transaction_id") or "")
    if not event_id:
        return HttpResponseBadRequest("Missing event_id")

    if not _store_event("nagad", event_id, payload):
        return JsonResponse({"status": "duplicate"})

    _handle_status(payload, "bkash")
    return JsonResponse({"status": "ok"})


@csrf_exempt
def bank_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")
    if not _verify_signature("bank", request):
        return HttpResponseBadRequest("Invalid signature")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    event_id = str(payload.get("event_id") or payload.get("reference_id") or "")
    if not event_id:
        return HttpResponseBadRequest("Missing event_id")

    if not _store_event("bank", event_id, payload):
        return JsonResponse({"status": "duplicate"})

    _handle_status(payload, "bkash")
    return JsonResponse({"status": "ok"})
