from django.utils import timezone

from ..models import PaymentProviderConfig, PaymentTransaction


def mark_payment_verified(reference_id):
    txn = PaymentTransaction.objects.filter(reference_id=reference_id).first()
    if not txn:
        return None
    txn.status = "verified"
    txn.verified_at = timezone.now()
    txn.save(update_fields=["status", "verified_at"])

    order = txn.order
    if order.status == "pending":
        order.status = "accepted"
        order.save(update_fields=["status"])
    return txn


def mark_payment_refunded(reference_id):
    txn = PaymentTransaction.objects.filter(reference_id=reference_id).first()
    if not txn:
        return None
    txn.status = "refunded"
    txn.save(update_fields=["status"])

    order = txn.order
    if order.status != "refunded":
        order.status = "refunded"
        order.save(update_fields=["status"])
    return txn


from ..integrations.payments.bkash import BkashClient
from ..integrations.payments.nagad import NagadClient


def refresh_access_token(provider_config):
    if provider_config.provider == "bkash":
        client = BkashClient(
            base_url=provider_config.base_url,
            app_key=provider_config.app_key,
            app_secret=provider_config.app_secret,
            username=provider_config.username,
            password=provider_config.password,
            token_url=provider_config.token_url,
        )
        token = client.fetch_access_token()
    elif provider_config.provider == "nagad":
        client = NagadClient(
            base_url=provider_config.base_url,
            merchant_id=provider_config.merchant_id,
            merchant_private_key=provider_config.merchant_private_key,
            token_url=provider_config.token_url,
        )
        token = client.fetch_access_token()
    else:
        raise NotImplementedError("No token refresh for this provider")

    provider_config.access_token = token
    provider_config.save(update_fields=["access_token"])
    return token
