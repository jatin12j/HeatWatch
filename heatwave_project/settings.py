"""
Django settings for heatwave_project.

HeatWatch: Extreme Heatwave Early Warning and Human Thermal Stress Index System
"""

from pathlib import Path
from django.contrib.messages import constants as message_constants

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-heatwatch-dev-key-change-in-production-2024'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Allow sending origin as Referer to external tile servers (e.g. OpenStreetMap),
# because Django's default 'same-origin' strips Referer and causes 403 tile blocks.
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'warning',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'heatwave_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'heatwave_project.wsgi.application'


# Database - SQLite for simplicity (college project)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ──────────────────────────────────────────────
# Email - Console backend for college demo
# (prints emails to terminal instead of sending)
# ──────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ──────────────────────────────────────────────
# Messages (map Django error tag to Bootstrap danger)
# ──────────────────────────────────────────────
MESSAGE_TAGS = {
    message_constants.ERROR: 'danger',
}

# ──────────────────────────────────────────────
# Authentication URLs
# ──────────────────────────────────────────────
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'


# ──────────────────────────────────────────────
# Logging configuration
# ──────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'warning': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}


# ══════════════════════════════════════════════
# HeatWatch Configuration
# ══════════════════════════════════════════════

# Heatwave detection: minimum consecutive days with
# daily max Heat Index >= threshold
HEATWAVE_THRESHOLD_C = 39.0   # °C (Danger level)
HEATWAVE_MIN_DAYS = 3          # consecutive days

# Open-Meteo API (free, no key required)
OPEN_METEO_BASE_URL = 'https://api.open-meteo.com/v1/forecast'
