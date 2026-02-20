class SAParibahanClient:
    def __init__(self, *, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def create_shipment(self, payload):
        raise NotImplementedError

    def track(self, tracking_id):
        raise NotImplementedError
