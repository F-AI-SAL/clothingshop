from django.conf import settings
from django.http import HttpResponseForbidden


class AdminIPAllowlistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        protect_admin = request.path.startswith("/admin/") or request.path.startswith("/account/")
        if protect_admin and settings.ADMIN_IP_ALLOWLIST:
            forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
            remote_addr = request.META.get("REMOTE_ADDR", "")
            if forwarded_for and remote_addr in settings.TRUSTED_PROXY_IPS:
                client_ip = forwarded_for.split(",")[0].strip()
            else:
                client_ip = remote_addr
            if client_ip not in settings.ADMIN_IP_ALLOWLIST:
                return HttpResponseForbidden("Admin access restricted.")
        return self.get_response(request)


from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        limits = getattr(settings, "RATE_LIMITS", {})
        allowlist = set(getattr(settings, "RATE_LIMIT_ALLOWLIST", []))
        if limits.get("enabled", False):
            path_limits = limits.get("paths", [])
            for rule in path_limits:
                if request.path.startswith(rule["path"]):
                    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
                    remote_addr = request.META.get("REMOTE_ADDR", "")
                    if forwarded_for and remote_addr in getattr(settings, "TRUSTED_PROXY_IPS", []):
                        client_ip = forwarded_for.split(",")[0].strip()
                    else:
                        client_ip = remote_addr
                    if client_ip in allowlist:
                        return self.get_response(request)

                    key = f"rl:{rule['path']}:{client_ip}"
                    window = int(rule.get("window", 60))
                    limit = int(rule.get("limit", 10))
                    now = timezone.now().timestamp()

                    data = cache.get(key)
                    if not data:
                        cache.set(key, {"count": 1, "start": now}, timeout=window)
                    else:
                        elapsed = now - data.get("start", now)
                        if elapsed > window:
                            cache.set(key, {"count": 1, "start": now}, timeout=window)
                        else:
                            data["count"] += 1
                            if data["count"] > limit:
                                return JsonResponse({"detail": "Rate limit exceeded."}, status=429)
                            cache.set(key, data, timeout=window)
                    break

        return self.get_response(request)
