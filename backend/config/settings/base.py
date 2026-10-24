from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import environ
import structlog
from csp.constants import NONE, SELF, UNSAFE_EVAL, UNSAFE_INLINE

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    # unfold must be loaded before django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.simple_history",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # third party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "simple_history",
    "import_export",
    "csp",
    # local
    "apps.core",
    "apps.accounts",
    "apps.vehicles",
    "apps.fitment",
    "apps.catalog",
    "apps.inventory",
    "apps.reviews",
    "apps.pricing",
    "apps.cart",
    "apps.garages",
    "apps.appointments",
    "apps.orders",
    "apps.payments",
    "apps.notifications",
    # Phase 2 – structure only, not wired into the checkout yet
    "apps.shipping",
    "apps.invoicing",
    "apps.ai_studio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database (PostgreSQL only) ---------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth -------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
# Only Django's own login (the admin) uses this; Unfold's login form has no "next" field when opened directly.
LOGIN_REDIRECT_URL = "/admin/"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 60 * 60 * 2

GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")

# JWT stored in httpOnly cookies (web). Android will send the same token in the
# Authorization header instead (see apps/accounts/authentication.py).
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
AUTH_COOKIE_ACCESS = "ow_access"
AUTH_COOKIE_REFRESH = "ow_refresh"
AUTH_COOKIE_REFRESH_PATH = "/api/v1/auth/"
AUTH_COOKIE_SECURE = not DEBUG
AUTH_COOKIE_SAMESITE = "Lax"

# --- CORS / CSRF ------------------------------------------------------------
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[FRONTEND_URL])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[FRONTEND_URL])
# The SPA reads this cookie and sends it back in the X-CSRFToken header.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "apps.core.views.csrf_failure"

# --- REST framework / OpenAPI ----------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "300/min",
        "auth": "10/min",
        "checkout": "30/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "OnlyWheels API",
    "DESCRIPTION": "REST API for the OnlyWheels web and Android apps.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    # Stable enum names for the generated TypeScript client.
    "ENUM_NAME_OVERRIDES": {
        "OrderStatusEnum": "apps.orders.models.Order.Status",
        "AppointmentStatusEnum": "apps.appointments.models.Appointment.Status",
        "ReviewStatusEnum": "apps.reviews.models.Review.Status",
        "ProductTypeEnum": "apps.catalog.models.ProductType",
    },
}

# --- Celery -----------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="memory://")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = "Europe/Bucharest"

# --- Cache ------------------------------------------------------------------
CACHES = {
    "default": env.cache("CACHE_URL", default="locmemcache://"),
}

# --- Email ------------------------------------------------------------------
# Production: EMAIL_BACKEND=anymail.backends.resend.EmailBackend + RESEND_API_KEY
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="OnlyWheels <no-reply@onlywheels.local>")
ANYMAIL = {"RESEND_API_KEY": env("RESEND_API_KEY", default="")}

# --- i18n / time ------------------------------------------------------------
LANGUAGE_CODE = "ro"
LANGUAGES = [("ro", "Română"), ("en", "English")]
TIME_ZONE = "Europe/Bucharest"
USE_I18N = True
USE_TZ = True

# --- Static & media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Uploads go to S3-compatible storage (Cloudflare R2, AWS S3, MinIO) when a bucket is configured.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "endpoint_url": env("AWS_S3_ENDPOINT_URL", default=None),
            "access_key": env("AWS_ACCESS_KEY_ID", default=None),
            "secret_key": env("AWS_SECRET_ACCESS_KEY", default=None),
            "region_name": env("AWS_S3_REGION_NAME", default="auto"),
            "custom_domain": env("AWS_S3_CUSTOM_DOMAIN", default=None),
            "querystring_auth": False,
            "file_overwrite": False,
        },
    }

# --- Security headers: Content Security Policy (django-csp) ----------------
# Applies to HTML served by Django (admin, API docs). The SPA gets its CSP from frontend/public/_headers.
CSP_ENABLED = env.bool("CSP_ENABLED", default=not DEBUG)
if CSP_ENABLED:
    MIDDLEWARE.append("csp.middleware.CSPMiddleware")
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        # unfold (Alpine.js) needs eval; Swagger UI is loaded from jsDelivr
        "script-src": [SELF, UNSAFE_INLINE, UNSAFE_EVAL, "https://cdn.jsdelivr.net"],
        "style-src": [SELF, UNSAFE_INLINE, "https://cdn.jsdelivr.net"],
        "img-src": [SELF, "data:", "blob:", "https:"],
        "font-src": [SELF, "data:"],
        "connect-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],
    }
}

# --- Observability: Sentry + structured logs ------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
    )

LOG_FORMAT = env("LOG_FORMAT", default="console" if DEBUG else "json")  # json → Loki, Better Stack…
_LOG_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
]
_LOG_RENDERER = (
    [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
    if LOG_FORMAT == "json"
    else [structlog.dev.ConsoleRenderer(colors=False)]
)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [structlog.stdlib.ProcessorFormatter.remove_processors_meta, *_LOG_RENDERER],
            "foreign_pre_chain": _LOG_PROCESSORS,
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "structured"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}
structlog.configure(
    processors=[*_LOG_PROCESSORS, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# --- Admin (django-unfold) --------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "OnlyWheels Admin",
    "SITE_HEADER": "OnlyWheels",
}

# --- Business ---------------------------------------------------------------
CURRENCY = "RON"
VAT_RATE = Decimal(env("VAT_RATE", default="0.21"))
CART_MAX_QUANTITY = 20
SHIPPING_FLAT_RATE = Decimal(env("SHIPPING_FLAT_RATE", default="25.00"))
FREE_SHIPPING_THRESHOLD = Decimal(env("FREE_SHIPPING_THRESHOLD", default="1000.00"))
# Stock is held this long for unpaid orders. Stripe Checkout sessions last at least 30 min.
ORDER_RESERVATION_MINUTES = env.int("ORDER_RESERVATION_MINUTES", default=30)
APPOINTMENT_LEAD_HOURS = 24
APPOINTMENT_BOOKING_DAYS = 14

# --- Payments ---------------------------------------------------------------
# "fake" simulates payments in development (no account needed), "stripe" uses Stripe Checkout.
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", default="fake")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# --- Phase 2 placeholders ---------------------------------------------------
AI_STUDIO_PROVIDER = env("AI_STUDIO_PROVIDER", default="replicate")
AI_STUDIO_DAILY_QUOTA = env.int("AI_STUDIO_DAILY_QUOTA", default=5)
