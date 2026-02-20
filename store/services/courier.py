from ..models import CourierProviderConfig, Shipment


def create_shipment_for_order(order):
    config = CourierProviderConfig.objects.filter(is_active=True).first()
    if not config:
        raise ValueError("No active courier provider configured.")

    # TODO: map order -> courier payload and call provider API
    shipment = Shipment.objects.create(
        order=order,
        courier_name=config.provider,
        merchant_id=config.api_key or config.client_id or "",
        status="created",
    )
    return shipment
