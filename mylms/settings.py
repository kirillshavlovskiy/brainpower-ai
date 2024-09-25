"""
Django settings for LMS_project project.

Generated by 'django-admin startproject' using Django 4.2.10.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

load_dotenv()  # This loads the .env file

DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')


BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
DEPLOYED_COMPONENTS_URL = '/deployed/'
DEPLOYED_COMPONENTS_ROOT = '/home/ubuntu/brainpower-ai/deployed_apps/'


STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]



# Add the DEPLOYED_COMPONENTS_ROOT to STATICFILES_DIRS

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# Use the DJANGO_ENV variable to set different configurations
if DJANGO_ENV == 'production':
    DEBUG = False
    ALLOWED_HOSTS = ['13.60.82.196',
                     'brainpower-ai.net',
                     '.brainpower-ai.net',
                     'www.brainpower-ai.net',
                     'd1ruevvpet0k71.cloudfront.net',
                     'localhost',
                     '127.0.0.1',
                     ]
    # ... other production settings ...
elif DJANGO_ENV == 'development':
    DEBUG = True
    ALLOWED_HOSTS = ['*']
    # ... other development settings ...

# You can use DJANGO_ENV elsewhere in your settings as needed
print(f"Running in {DJANGO_ENV} mode")
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-r+zttm^2o4$y2n61xl&-vuul479zz0h)n8crl^lyj^tt=jt=e^'

# SECURITY WARNING: don't run with debug turned on in production!



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'courses',
    'corsheaders',
    'channels',
    'sandbox',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# Configure WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Ensure Django serves files from DEPLOYED_COMPONENTS_ROOT in development
if DJANGO_ENV == 'development':
    STATICFILES_DIRS.append(DEPLOYED_COMPONENTS_ROOT)

CORS_ALLOW_ALL_ORIGINS = True  # For development only. Set to False in production.

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://d1ruevvpet0k71.cloudfront.net",
    "https://13.60.82.196:8000",
    "http://brainpower-ai.net",
    "https://brainpower-ai.net",
    "http://*.brainpower-ai.net",
    "https://*.brainpower-ai.net"
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# Add this line to allow all headers
CORS_ALLOW_ALL_HEADERS = True



ROOT_URLCONF = 'mylms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'mylms.wsgi.application'
# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
ASGI_APPLICATION = 'mylms.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/



# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console'],
#             'level': 'INFO',
#         },
#         'your_app_name': {  # Replace with your app name
#             'handlers': ['console'],
#             'level': 'DEBUG',
#         },
#     },
# }