# Enterprise Hardening Checklist (Bangladesh + Global)

## Security
- Enforce 2FA for all admin users (django-otp + two-factor already enabled)
- IP allowlist for /admin/ and /account/
- Rotate SECRET_KEY on deploys; never fallback in production
- Set CSRF_TRUSTED_ORIGINS for all public domains
- Enforce HTTPS via proxy headers on Render

## Payments
- Enable provider webhooks with HMAC signatures
- Reconcile payments nightly (missing/duplicate transactions)
- Store transaction metadata for dispute/refund

## Orders
- Allowed status transitions enforced
- Stock updates in transaction with row locks
- Refunds update payment + order status

## Messaging
- SMS/WhatsApp templates managed in admin
- Provider fallback (SMS if WhatsApp fails)

## Observability
- Sentry enabled in production
- Structured logs to stdout
- Uptime monitor configured (UptimeRobot/BetterStack)

## Backups & Data Ops
- Daily DB dumps to S3
- Monthly restore test
- GDPR export/delete workflow

## Performance
- Redis cache in production
- CDN for static/media
- Celery workers for email/notifications

## Compliance
- Consent tracking + data retention policy
- Data deletion SLA
