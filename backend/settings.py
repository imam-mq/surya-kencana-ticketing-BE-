from pathlib import Path
import os
from dotenv import load_dotenv

# variabe  file .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Mengambil kunci rahasia secara aman
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dummy-key-untuk-github')

DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".ngrok-free.dev", "*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # apps
    'accounts',
]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication', 
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = False

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.Pengguna'

# ===============================================
#  SESSION CONFIGURATION (UPDATED)
# ===============================================

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://jointured-ivana-unarrogantly.ngrok-free.dev",
]

CORS_ALLOW_CREDENTIALS = True



# KONFIGURASI MIDTRANS
MIDTRANS_MERCHANT_ID = os.getenv('MIDTRANS_MERCHANT_ID')
MIDTRANS_CLIENT_KEY = os.getenv('MIDTRANS_CLIENT_KEY')
MIDTRANS_SERVER_KEY = os.getenv('MIDTRANS_SERVER_KEY')

# testing sandbox
MIDTRANS_IS_PRODUCTION = os.getenv('MIDTRANS_IS_PRODUCTION', 'False') == 'True'

# Agar frontend bisa baca token CSRF dari cookie
CSRF_COOKIE_HTTPONLY = False 
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

# Nonaktifkan Secure jika masih tahap development (HTTP)
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

APPEND_SLASH = False

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
