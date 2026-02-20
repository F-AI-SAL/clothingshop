from ..models import MessagingConfig, ManualNotificationLog, MessageTemplate


def _render_template(template, order, extra=None):
    data = {
        "order_id": order.id,
        "status": order.get_status_display(),
        "total": order.total,
        "tracking_id": getattr(order.shipments.order_by("-created_at").first(), "tracking_id", "") if hasattr(order, "shipments") else "",
    }
    if extra:
        data.update(extra)
    content = template
    for key, value in data.items():
        content = content.replace(f"{{{key}}}", str(value))
    return content


def send_sms(order, message=None):
    config = MessagingConfig.objects.first()
    if not config or not config.sms_provider or not config.sms_api_key:
        return False

    if not message:
        template = MessageTemplate.objects.filter(channel="sms", event="order_status_updated", is_active=True).first()
        if template:
            message = _render_template(template.body, order)
        else:
            message = f"Order #{order.id} status: {order.get_status_display()}"

    # TODO: call real SMS gateway
    ManualNotificationLog.objects.create(order=order, channel="sms", message=message, status="queued")
    return True


def send_whatsapp(order, template_name, variables=None):
    config = MessagingConfig.objects.first()
    if not config or not config.whatsapp_provider or not config.whatsapp_api_key:
        return False

    template = MessageTemplate.objects.filter(channel="whatsapp", event=template_name, is_active=True).first()
    message = template_name
    if template:
        message = _render_template(template.body, order, variables)

    # TODO: call real WhatsApp provider
    ManualNotificationLog.objects.create(order=order, channel="whatsapp", message=message, status="queued")
    return True
