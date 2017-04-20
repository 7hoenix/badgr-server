import sys
import os

from mainsite import TOP_DIR
import logging


##
#
#  Important Stuff
#
##

INSTALLED_APPS = [
    # https://github.com/concentricsky/django-client-admin

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_object_actions',

    'badgeuser',

    'allauth',
    'allauth.account',
    'corsheaders',

    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_swagger',

    'django-ismigrated',
    'mainsite',
    'issuer',
    'composition',
    'verifier',
    'pathway',
    'recipient',
]

MIDDLEWARE_CLASSES = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_auth_lti.middleware.LTIAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'mainsite.middleware.MaintenanceMiddleware',
    'badgeuser.middleware.InactiveUserMiddleware',
    # 'mainsite.middleware.TrailingSlashMiddleware',
]

ROOT_URLCONF = 'mainsite.urls'

SECRET_KEY = '{{secret_key}}'
UNSUBSCRIBE_SECRET_KEY = 'kAYWM0YWI2MDj/FODBZjE0ZDI4N'

# Hosts/domain names that are valid for this site.
# "*" matches anything, ".example.com" matches example.com and all subdomains
ALLOWED_HOSTS = ['*', ]

##
#
#  Templates
#
##

TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

TEMPLATE_DIRS = [
    os.path.join(TOP_DIR, 'breakdown', 'templates'),
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.i18n',

    'mainsite.context_processors.extra_settings'
]



##
#
#  Static Files
#
##

HTTP_ORIGIN = "http://localhost:8000"

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATIC_ROOT = os.path.join(TOP_DIR, 'staticfiles')
STATIC_URL = HTTP_ORIGIN+'/static/'
STATICFILES_DIRS = [
    os.path.join(TOP_DIR, 'breakdown', 'static'),
]

##
#
#  User / Login / Auth
#
##

AUTH_USER_MODEL = 'badgeuser.BadgeUser'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/docs'

AUTHENTICATION_BACKENDS = [
    # Object permissions for issuing badges
    'rules.permissions.ObjectPermissionBackend',

    # Needed to login by username in Django admin, regardless of `allauth`
    "badgeuser.backends.CachedModelBackend",

    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",

]
ACCOUNT_ADAPTER = 'mainsite.account_adapter.BadgrAccountAdapter'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_FORMS = {
    'add_email': 'badgeuser.account_forms.AddEmailForm'
}
ACCOUNT_SIGNUP_FORM_CLASS = 'badgeuser.forms.BadgeUserCreationForm'


CORS_ORIGIN_ALLOW_ALL = True
CORS_URLS_REGEX = r'^.*$'
CORS_MODEL = 'mainsite.BadgrApp'


##
#
#  Media Files
#
##

MEDIA_ROOT = os.path.join(TOP_DIR, 'mediafiles')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = STATIC_URL+'admin/'

BADGR_UI_URL = 'https://badgr.io/'


##
#
#   Fixtures
#
##

FIXTURE_DIRS = [
    os.path.join(TOP_DIR, 'etc', 'fixtures'),
]


##
#
#  Logging
#
##

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': [],
            'class': 'django.utils.log.AdminEmailHandler'
        },

        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,

        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },

        # Badgr.Events emits all badge related activity
        'Badgr.Events': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        }

    },
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(module)s %(message)s'
        },
        'json': {
            '()': 'mainsite.formatters.JsonFormatter',
            'format': '%(asctime)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S%z',
        }
    },
}


##
#
#  Caching
#
##

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'KEY_PREFIX': 'badgr_',
        'VERSION': 10,
        'TIMEOUT': None,
    }
}

##
#
#  Maintenance Mode
#
##

MAINTENANCE_MODE = False
MAINTENANCE_URL = '/maintenance'


##
#
#  Sphinx Search
#
##

SPHINX_API_VERSION = 0x116  # Sphinx 0.9.9

##
#
# Testing
##
TEST_RUNNER = 'mainsite.testrunner.BadgrRunner'


##
#
#  REST Framework
#
##

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'mainsite.renderers.JSONLDRenderer',
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    )
}


##
#
#  Remote document fetcher (designed to be overridden in tests)
#
##

REMOTE_DOCUMENT_FETCHER = 'badgeanalysis.utils.get_document_direct'
LINKED_DATA_DOCUMENT_FETCHER = 'badgeanalysis.utils.custom_docloader'


##
#
#  Misc.
#
##

LTI_STORE_IN_SESSION = False

CAIROSVG_VERSION_SUFFIX = "2"

SITE_ID = 1

USE_I18N = False
USE_L10N = False
USE_TZ = True

BADGR_APP_ID = 1


##
#
# Markdownify
#
##

MARKDOWNIFY_WHITELIST_TAGS = [
    'a',
    'abbr',
    'acronym',
    'b',
    'blockquote',
    'em',
    'i',
    'li',
    'ol',
    'p',
    'strong',
    'ul'
]


##
#
#  artifact version
#
##


def determine_version():
    version_path = os.path.join(TOP_DIR, 'version.txt')
    if os.path.exists(version_path):
        with open(version_path, 'r') as version_file:
            return version_file.readline()
    import mainsite
    return mainsite.__version__

ARTIFACT_VERSION = determine_version()


##
#
#  Import settings_local.
#
##

try:
    from settings_local import *
except ImportError as e:
    import traceback
    traceback.print_exc()
    sys.stderr.write("no settings_local found, setting DEBUG=True...\n")
    DEBUG = True

