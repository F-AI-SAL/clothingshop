import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .integrations.payments.bkash import BkashClient
from .integrations.payments.nagad import NagadClient
from .integrations.payments.bank import BankManualVerifier
from .models import PaymentTransaction, PaymentProviderConfig, PaymentReconciliationReport
from .services.payments import mark_payment_verified, refresh_access_token
from django.core.mail import mail_admins


logger = logging.getLogger(__name__)


def _get_provider_config(provider):
    return PaymentProviderConfig.objects.filter(provider=provider).first()


def _verify_with_provider(txn):
    if txn.method == "bkash":
        config = _get_provider_config("bkash")
        if not config:
            return False
        if not config.access_token:
            refresh_access_token(config)
        client = BkashClient(
            base_url=config.base_url,
            app_key=config.app_key,
            app_secret=config.app_secret,
            username=config.username,
            password=config.password,
        )
        return client.verify_transaction(txn.reference_id)

    if txn.method == "nagad":
        config = _get_provider_config("nagad")
        if not config:
            return False
        if not config.access_token:
            refresh_access_token(config)
        client = NagadClient(
            base_url=config.base_url,
            merchant_id=config.merchant_id,
            merchant_private_key=config.merchant_private_key,
        )
        return client.verify_transaction(txn.reference_id)

    if txn.method == "bank":
        verifier = BankManualVerifier()
        return verifier.verify_reference(txn.reference_id)

    return False


@shared_task
def reconcile_payments():
    cutoff = timezone.now() - timedelta(days=1)
    pending = PaymentTransaction.objects.filter(status="pending", created_at__lte=cutoff)
    count = pending.count()
    reconciled = 0
    failed = 0
    details = []

    for txn in pending:
        if not txn.reference_id:
            continue
        try:
            verified = _verify_with_provider(txn)
        except NotImplementedError:
            logger.info("Provider verify not implemented for %s", txn.method)
            continue
        except Exception as exc:
            logger.exception("Reconcile failed for txn %s", txn.id)
            failed += 1
            details.append({"txn_id": txn.id, "error": str(exc)})
            continue

        if verified:
            mark_payment_verified(txn.reference_id)
            reconciled += 1
        else:
            details.append({"txn_id": txn.id, "verified": False})

    PaymentReconciliationReport.objects.create(
        total_pending=count,
        reconciled=reconciled,
        failed=failed,
        details=details,
    )

    try:
        mail_admins(
            subject="Payment Reconciliation Report",
            message=f"Pending: {count}\nReconciled: {reconciled}\nFailed: {failed}",
            fail_silently=True,
        )
    except Exception:
        logger.exception("Failed to email reconciliation report")

    logger.info("Reconciled %s/%s pending payments", reconciled, count)
    return reconciled
