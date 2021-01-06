import fileinput
import os
import pathlib
import re
import subprocess

def create_new_wagtail_project(PROJECT_NAME):
    os.mkdir(PROJECT_NAME)

    os.chdir(PROJECT_NAME)

    PACKAGES = [
        'django',
        'wagtail',
        'psycopg2',
        'dj-database-url',
        'gunicorn',
        'whitenoise',
    ]

    for package in PACKAGES:
        exit_code = subprocess.call(f"pipenv install {package}", shell=True)

    exit_code = subprocess.run(['pipenv', 'run', 'wagtail', 'start', 'config', '.'])


def modify_settings():
    SETTINGS_DIR = pathlib.Path('config', 'settings')
    production_settings_content = '''
import os
import dj_database_url
from .base import *

env = os.environ.copy()

SECRET_KEY = env['SECRET_KEY']

DATABASES['default'] = dj_database_url.config()

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['*']

DEBUG = False

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
COMPRESS_OFFLINE = True
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
]
COMPRESS_CSS_HASHING_METHOD = 'content'

try:
    from .local import *
except ImportError:
    pass'''
    production_settings_file_path = pathlib.Path(SETTINGS_DIR, 'production.py')
    base_settings_file_path = pathlib.Path(SETTINGS_DIR, 'base.py')
    prod_settings = open(production_settings_file_path, 'w')
    prod_settings.write(production_settings_content)
    prod_settings.close()

    pattern = re.compile('.*django.middleware.security.SecurityMiddleware.*')
    base_settings = fileinput.input(base_settings_file_path, inplace=True, backup='.bak')
    for line in base_settings:
        if pattern.match(line):
            print(line, end='')
            print("    'whitenoise.middleware.WhiteNoiseMiddleware',")
        else:
            print(line, end='')
    base_settings.close()

if __name__ == '__main__':
    PROJECT_NAME = input('What is the name of the new project? ')
    create_new_wagtail_project(PROJECT_NAME)
    modify_settings()


