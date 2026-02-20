class WhatsappGateway:
    def __init__(self, *, provider, api_key, sender_id):
        self.provider = provider
        self.api_key = api_key
        self.sender_id = sender_id

    def send_template(self, phone, template_name, variables):
        raise NotImplementedError
