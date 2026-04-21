"""
Configuration Django pour le portail éducatif IA.

Les valeurs sensibles (SECRET_KEY, identifiants de base de données, clé API)
sont lues depuis le fichier .env via python-decouple. Voir .env.example.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import AutoConfig, Csv

# Racine du projet Django (dossier backend/).
BASE_DIR = Path(__file__).resolve().parent.parent

# Racine du dépôt (contient .env, docs/, frontend/).
REPO_ROOT = BASE_DIR.parent

# Lecture du .env à la racine du dépôt. Si absent, les valeurs default sont utilisées.
config = AutoConfig(search_path=str(REPO_ROOT))


# --- Sécurité ---------------------------------------------------------------

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-change-me",
)
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)


# --- Applications -----------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]

LOCAL_APPS = [
    "utilisateurs",
    "contenu",
    "progression",
    "ia",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "portail.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portail.wsgi.application"


# --- Base de données -------------------------------------------------------
# SQLite par défaut (dev). Si DATABASE_URL est défini, on bascule sur la cible
# indiquée (typiquement PostgreSQL, conforme aux spécifications).

DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# --- Authentification ------------------------------------------------------

AUTH_USER_MODEL = "utilisateurs.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Django REST Framework -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# --- CORS ------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True


# --- IA / Claude -----------------------------------------------------------

ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL_GENERATION = config(
    "ANTHROPIC_MODEL_GENERATION",
    default="claude-sonnet-4-6",
)
ANTHROPIC_MODEL_QUESTIONS_LIBRES = config(
    "ANTHROPIC_MODEL_QUESTIONS_LIBRES",
    default="claude-haiku-4-5",
)
QUESTIONS_LIBRES_MAX_PAR_JOUR = config(
    "QUESTIONS_LIBRES_MAX_PAR_JOUR",
    default=5,
    cast=int,
)


# --- Internationalisation --------------------------------------------------

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True


# --- Fichiers statiques ----------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# --- Divers ----------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
