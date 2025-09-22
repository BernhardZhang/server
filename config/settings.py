import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',  # Add this for Token authentication
    'corsheaders',
    'cacheops',  # Django-cacheops
    # Custom apps in dependency order
    'apps.users',      # First - no dependencies
    'apps.projects',   # Second - depends on users
    'apps.voting',     # Third - depends on users and projects
    'apps.finance',    # Fourth - depends on users, projects, voting
    'apps.merit',      # Fifth - depends on users, projects, voting
    'apps.points',     # Sixth - depends on users, projects, voting
    'apps.tasks',      # Seventh - depends on users, projects
    'apps.analysis',   # Eighth - depends on users, projects, voting
    'apps.dashboard',  # Ninth - depends on users, projects, tasks
]

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

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='crewcut'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default='123456'),
        'HOST': config('DB_HOST', default='0.0.0.0'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

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

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

AUTH_USER_MODEL = 'users.User'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'config.middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Cacheops Configuration
CACHEOPS_REDIS = {
    'host': config('REDIS_HOST', default='127.0.0.1'),
    'port': config('REDIS_PORT', default=6379, cast=int),
    'db': config('REDIS_DB', default=1, cast=int),
    'socket_timeout': 3,
}

# Default cache timeout (in seconds)
CACHEOPS_DEFAULTS = {
    'timeout': 60 * 60,  # 1 hour
}

# Model-specific caching configuration
CACHEOPS = {
    # Cache all model operations for 1 hour
    'users.*': {'ops': 'all', 'timeout': 60 * 60},  # 1 hour
    'projects.*': {'ops': 'all', 'timeout': 60 * 60},
    'voting.*': {'ops': 'all', 'timeout': 30 * 60},  # 30 minutes for voting data
    'finance.*': {'ops': 'all', 'timeout': 60 * 60},
    'merit.*': {'ops': 'all', 'timeout': 60 * 60},
    'points.*': {'ops': 'all', 'timeout': 60 * 60},
    'tasks.*': {'ops': 'all', 'timeout': 30 * 60},   # 30 minutes for tasks
    'analysis.*': {'ops': 'all', 'timeout': 60 * 60},
    'dashboard.*': {'ops': 'all', 'timeout': 15 * 60}, # 15 minutes for dashboard
    
    # Cache auth models for longer
    'auth.*': {'ops': 'all', 'timeout': 60 * 60 * 24},  # 24 hours
}

# Enable cache debugging in development
CACHEOPS_DEGRADE_ON_FAILURE = True
