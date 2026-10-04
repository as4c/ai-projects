"""Slim Django settings for the swipe-to-talk voice-avatars project."""

from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    VOICE_BOT_PORT=(int, 7860),
    VOICE_FREE_INTERACTIONS=(int, 100),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-change-me-voice-avatars")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "voice_avatars.apps.VoiceAvatarsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "voice_avatars" / "static",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
CORS_ALLOW_HEADERS = list({*default_headers, "authorization", "x-voice-bot-key"})

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://localhost:8000")

# Voice avatars · swipe-to-talk
VOICE_BOT_URL = env(
    "VOICE_BOT_URL",
    default="http://localhost:7860/voice-agent/connect",
)
VOICE_BOT_AUTH_KEY = env("VOICE_BOT_AUTH_KEY", default="dev-bot-key")
VOICE_FREE_INTERACTIONS = env("VOICE_FREE_INTERACTIONS")
VOICE_DJANGO_URL = env("VOICE_DJANGO_URL", default="http://localhost:8000")
VOICE_BOT_PORT = env("VOICE_BOT_PORT")
VOICE_LLM_MODEL = env("VOICE_LLM_MODEL", default="google/gemini-2.5-flash")

OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", default="")
DEEPGRAM_API_KEY = env("DEEPGRAM_API_KEY", default="")
CARTESIA_API_KEY = env("CARTESIA_API_KEY", default="")

VOICE_TURN_URLS = env.list("VOICE_TURN_URLS", default=[])
VOICE_TURN_USERNAME = env("VOICE_TURN_USERNAME", default="")
VOICE_TURN_CREDENTIAL = env("VOICE_TURN_CREDENTIAL", default="")
