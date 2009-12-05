# Django settings for chantal project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

import socket, os.path, sys

IS_TESTSERVER = len(sys.argv) >= 2
WITH_EPYDOC = 'epydoc' in sys.modules

import ConfigParser
credentials = ConfigParser.SafeConfigParser()
read_files = credentials.read(os.path.expanduser("~/chantal.auth" if IS_TESTSERVER or WITH_EPYDOC
                                                 else "/var/lib/chantal/chantal.auth"))
assert read_files, Exception("file with authentication data not found")
CREDENTIALS = dict(credentials.items("DEFAULT"))

ROOTDIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_FROM_EMAIL = "bronger@physik.rwth-aachen.de"
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMINS = (
    ('Torsten Bronger', 'bronger@physik.rwth-aachen.de'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'postgresql_psycopg2' # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'chantal'      # Or path to database file if using sqlite3.
DATABASE_USER = 'chantal'      # Not used with sqlite3.
DATABASE_PASSWORD = CREDENTIALS["postgresql_password"]    # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Rome'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de-de'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
DEFAULT_CHARSET = "utf-8"

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(ROOTDIR, 'media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media_admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = CREDENTIALS["salt"]

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'samples.middleware.chantal.LocaleMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'samples.middleware.chantal.ExceptionsMiddleware',
)
APPEND_SLASH = False

ROOT_URLCONF = 'chantal.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOTDIR, "templates")
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.markup',
    'samples',
)

CACHE_BACKEND = "file:///var/tmp/django_cache"

URL_PREFIX = "/" if IS_TESTSERVER else "/chantal/"

LOGIN_URL = URL_PREFIX + "login"
LOGIN_REDIRECT_URL = URL_PREFIX
if socket.gethostname() == "wilson":
    DOMAIN_NAME = "127.0.0.1:8000" if IS_TESTSERVER else "wilson.homeunix.com"
else:
    DOMAIN_NAME = "bob.ipv.kfa-juelich.de"

TEMPLATE_CONTEXT_PROCESSORS = ("django.core.context_processors.auth",
                               "django.core.context_processors.debug",
                               "django.core.context_processors.i18n",
                               "django.core.context_processors.media",
                               "samples.context_processors.default",
                               )

AUTH_PROFILE_MODULE = 'samples.userdetails'

LOCALES_DICT = {"en": "en_US.utf8", "de": "de_DE.utf8"}

# Absolute path to the directory that holds uploaded images for result
# processes.
UPLOADED_RESULT_IMAGES_ROOT = "/home/bronger/temp/chantal_images/" if IS_TESTSERVER else "/var/lib/chantal_images/"
THUMBNAIL_WIDTH = 400

import subprocess, re, time, glob
def _scan_version(package):
    dpgk = subprocess.Popen(["dpkg-query", "--show", package], stdout=subprocess.PIPE)
    match = re.match(re.escape(package)+r"\t(?P<version>.+?)-", dpgk.communicate()[0].strip())
    return match.group("version") if match else None
APACHE_VERSION = _scan_version("apache2")
APACHE_STARTUP_TIME = time.time() if IS_TESTSERVER or WITH_EPYDOC else os.stat("/var/run/apache2.pid")[9]
POSTGRESQL_VERSION = _scan_version("postgresql")
POSTGRESQL_STARTUP_TIME = os.stat(glob.glob("/var/run/postgresql/*-main.pid")[0])[9]
PYTHON_VERSION = _scan_version("python")
import matplotlib
MATPLOTLIB_VERSION = matplotlib.__version__
CHANTAL_REVNO = subprocess.Popen(["bzr", "revno", ROOTDIR], stdout=subprocess.PIPE).communicate()[0].strip()

# LDAP binding
AD_DNS_NAME = "localhost"
AD_LDAP_PORT = 389
AD_SEARCH_DN = "CN=Users,dc=example,dc=local"
# This is the NT4/Samba domain name
AD_NT4_DOMAIN = "example.local"
AD_SEARCH_FIELDS = ["mail", "givenName", "sn", "sAMAccountName"]
AD_LDAP_URL = "ldap://%s:%s" % (AD_DNS_NAME, AD_LDAP_PORT)
#AUTHENTICATION_BACKENDS = ("samples.auth.ActiveDirectoryBackend",)
