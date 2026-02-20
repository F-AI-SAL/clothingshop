from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .models import MessageTemplate



DEFAULT_FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", "La Rosa <noreply@larosa.local>")
ADMIN_EMAILS = [email for _, email in getattr(settings, "ADMINS", []) if email]


def _safe_send(subject: str, body: str, recipients):
    if not recipients:
        return
    send_mail(subject, body, DEFAULT_FROM_EMAIL, recipients, fail_silently=True)


def _order_items_summary(order):
    lines = []
    for item in order.items.all():
        variant = []
        if item.color:
            variant.append(item.color)
        if item.size:
            variant.append(item.size)
        variant_desc = f" ({', '.join(variant)})" if variant else ""
        lines.append(f"- {item.product.title}{variant_desc} x{item.qty} @ PKR {item.price} = PKR {item.line_total}")
    return lines


def render_email_template(event, order):
    template = MessageTemplate.objects.filter(channel="email", event=event, is_active=True).first()
    if not template:
        return None, None
    subject = template.subject or f"Order #{order.id}"
    body = template.body
    body = body.replace("{order_id}", str(order.id))
    body = body.replace("{status}", order.get_status_display())
    body = body.replace("{total}", str(order.total))
    return subject, body


def send_order_created_notifications(order):
    subject, body = render_email_template("order_placed", order)
    if not subject:
        subject = f"Order #{order.id} received"
        body = f"Thanks for your order. Status: {order.get_status_display()}"
    email = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [order.email])
    if body and "<" in body and ">" in body:
        email.attach_alternative(body, "text/html")
    email.send(fail_silently=True)


def send_status_update_notification(order, previous_status=None):
    subject, body = render_email_template("order_status_updated", order)
    if not subject:
        subject = f"Order #{order.id} status update"
        body = f"Your order status is now {order.get_status_display()}"
    email = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [order.email])
    if body and "<" in body and ">" in body:
        email.attach_alternative(body, "text/html")
    email.send(fail_silently=True)
