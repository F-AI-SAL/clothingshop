class RedxClient:
    def __init__(self, *, base_url, access_token):
        self.base_url = base_url
        self.access_token = access_token

    def create_shipment(self, payload):
        raise NotImplementedError

    def track(self, tracking_id):
        raise NotImplementedError
