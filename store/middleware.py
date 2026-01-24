from django.conf import settings
from django.http import HttpResponseForbidden


class AdminIPAllowlistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/") and settings.ADMIN_IP_ALLOWLIST:
            client_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            if not client_ip:
                client_ip = request.META.get("REMOTE_ADDR", "")
            if client_ip not in settings.ADMIN_IP_ALLOWLIST:
                return HttpResponseForbidden("Admin access restricted.")
        return self.get_response(request)
