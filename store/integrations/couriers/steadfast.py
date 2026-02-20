class SteadfastClient:
    def __init__(self, *, base_url, api_key, api_secret):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret

    def create_shipment(self, payload):
        raise NotImplementedError

    def track(self, tracking_id):
        raise NotImplementedError
