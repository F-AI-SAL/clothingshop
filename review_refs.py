from pathlib import Path
files = ['config/settings.py','store/admin.py','store/middleware.py','store/views.py','store/context_processors.py']
keys = {
    'config/settings.py': ['PasswordChangeValidator', 'SECURE_SSL_REDIRECT', 'CONTENT_SECURITY_POLICY', 'ADMIN_IP_ALLOWLIST', 'LOGGING', 'LOGIN_URL'],
    'store/admin.py': ['quick_status_view', 'quick_actions', 'status_badge', 'anonymize_orders'],
    'store/middleware.py': ['class AdminIPAllowlistMiddleware'],
}
for path in files:
    lines = Path(path).read_text(encoding='utf-8', errors='ignore').splitlines()
    print(path)
    for i, line in enumerate(lines, 1):
        for k in keys.get(path, []):
            if k in line:
                print(f"  {i}: {line}")
    print()
