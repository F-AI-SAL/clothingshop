class PathaoClient:
    def __init__(self, *, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret

    def create_shipment(self, payload):
        raise NotImplementedError

    def track(self, tracking_id):
        raise NotImplementedError
