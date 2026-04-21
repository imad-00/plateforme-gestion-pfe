from datetime import timedelta
from pathlib import Path

import environ

ROOT_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = ROOT_DIR.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_S3=(bool, True),
    MINIO_USE_SSL=(bool, False),
    API_PAGE_SIZE=(int, 10),
    API_MAX_PAGE_SIZE=(int, 100),
    SIMPLE_JWT_ACCESS_MINUTES=(int, 15),
    SIMPLE_JWT_REFRESH_DAYS=(int, 7),
)

for env_path in (ROOT_DIR / ".env", REPO_DIR / ".env"):
    if env_path.exists():
        environ.Env.read_env(str(env_path))
        break

# Core runtime configuration comes from environment variables / backend/.env
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
DATABASE_URL = env("DATABASE_URL")
REDIS_URL = env("REDIS_URL")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "storages",
    "apps.accounts",
    "apps.academics",
    "apps.campaigns",
    "apps.topics",
    "apps.teams",
    "apps.assignments",
    "apps.projects",
    "apps.deliverables",
    "apps.defenses",
    "apps.archives",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = ROOT_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = ROOT_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.MatriculeOrEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.accounts.permissions.IsAuthenticatedAndActiveAccount",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE"),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("SIMPLE_JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("SIMPLE_JWT_REFRESH_DAYS")),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "PFE Management API",
    "DESCRIPTION": "Authentication and identity foundations.",
    "VERSION": "0.2.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

USE_S3 = env.bool("USE_S3")
if USE_S3:
    MINIO_USE_SSL = env.bool("MINIO_USE_SSL")
    protocol = "https" if MINIO_USE_SSL else "http"

    AWS_ACCESS_KEY_ID = env("MINIO_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = env("MINIO_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = env("MINIO_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("MINIO_REGION")
    AWS_S3_ENDPOINT_URL = f"{protocol}://{env('MINIO_ENDPOINT')}"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

DEFAULT_PAGE_SIZE = env.int("API_PAGE_SIZE")
MAX_PAGE_SIZE = env.int("API_MAX_PAGE_SIZE")
