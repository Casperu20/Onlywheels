from .base import *  # noqa: F403

DEBUG = False
AUTH_COOKIE_SECURE = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
PAYMENT_PROVIDER = "fake"
AI_STUDIO_PROVIDER = ""
AI_STUDIO_PRIVATE_BUCKET = ""
REPLICATE_API_TOKEN = ""
FAL_KEY = ""
STRIPE_SECRET_KEY = "sk_test_dummy"
STRIPE_WEBHOOK_SECRET = "whsec_test_secret"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
}
STORAGES = {
    **STORAGES,  # noqa: F405
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}
# Same as production, whatever DJANGO_DEBUG says in the local .env
CSP_ENABLED = True
if "csp.middleware.CSPMiddleware" not in MIDDLEWARE:  # noqa: F405
    MIDDLEWARE.append("csp.middleware.CSPMiddleware")  # noqa: F405
# Tests serve no static files; avoids WhiteNoise's "No directory at staticfiles/" warning.
MIDDLEWARE = [m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"]  # noqa: F405
