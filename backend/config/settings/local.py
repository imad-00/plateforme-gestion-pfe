from .base import *  # noqa: F403,F401

DEBUG = env.bool("DEBUG", default=True)  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
