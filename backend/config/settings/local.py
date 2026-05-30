from .base import *  # noqa: F403,F401

DEBUG = env.bool("DEBUG", default=True)  # noqa: F405

# base.py already reads EMAIL_BACKEND from env (default: console). Override here
# only when EMAIL_FORCE_CONSOLE=1 — useful for offline dev where you don't want
# accidental real sends. Otherwise we honor .env so SMTP works as expected.
if env.bool("EMAIL_FORCE_CONSOLE", default=False):  # noqa: F405
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
