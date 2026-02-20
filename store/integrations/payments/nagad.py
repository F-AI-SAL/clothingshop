import json
import urllib.request


class NagadClient:
    def __init__(self, *, base_url, merchant_id, merchant_private_key, token_url=None, verify_url=None, refund_url=None, access_token=None):
        self.base_url = base_url
        self.merchant_id = merchant_id
        self.merchant_private_key = merchant_private_key
        self.token_url = token_url
        self.verify_url = verify_url
        self.refund_url = refund_url
        self.access_token = access_token

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def fetch_access_token(self):
        if not self.token_url:
            raise NotImplementedError("token_url not configured")
        payload = json.dumps({
            "merchantId": self.merchant_id,
            "privateKey": self.merchant_private_key,
        }).encode("utf-8")
        req = urllib.request.Request(self.token_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        token = data.get("access_token") or data.get("token")
        return token

    def verify_transaction(self, trx_id):
        if not self.verify_url:
            raise NotImplementedError("verify_url not configured")
        payload = json.dumps({"trxID": trx_id}).encode("utf-8")
        req = urllib.request.Request(self.verify_url, data=payload, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        status = str(data.get("status") or data.get("paymentStatus") or "").lower()
        return status in ("completed", "success", "paid")

    def refund(self, trx_id, amount, reason=""):
        if not self.refund_url:
            raise NotImplementedError("refund_url not configured")
        payload = json.dumps({"trxID": trx_id, "amount": str(amount), "reason": reason}).encode("utf-8")
        req = urllib.request.Request(self.refund_url, data=payload, headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        status = str(data.get("status") or "").lower()
        return status in ("completed", "success", "refunded")
