import fileinput
import os
import pathlib
import random
import re
import string
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


def modify_settings(PROJECT_NAME):
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

    sec_middleware_pattern = re.compile("(\s*)'django.middleware.security.SecurityMiddleware.*")
    db_engine_pattern = re.compile("(\s*)'ENGINE'.*")
    db_name_pattern = re.compile("(\s*)'NAME':.*sqlite.*")
    base_settings = fileinput.input(base_settings_file_path, inplace=True, backup='.bak')
    for line in base_settings:
        if sec_middleware_pattern.match(line):
            print(line, end='')
            indent = sec_middleware_pattern.match(line).group(1)
            print(f"{indent}'whitenoise.middleware.WhiteNoiseMiddleware',")
        elif db_engine_pattern.match(line):
            indent = db_engine_pattern.match(line).group(1)
            print(f"{indent}'ENGINE': 'django.db.backends.postgresql_psycopg2',")
        elif db_name_pattern.match(line):
            indent = db_name_pattern.match(line).group(1)
            print(f"{indent}'NAME': '{PROJECT_NAME}_db',")
        else:
            print(line, end='')
    base_settings.close()


def add_heroku_files():
    procfile = open('Procfile', 'w')
    procfile.write('web: gunicorn config.wsgi --log-file -')
    procfile.close()

    runtime = open('runtime.txt', 'w')
    runtime.write('python-3.9.1')
    runtime.close()

    compress_script = '''
#!/usr/bin/env bash
set -eo pipefail
# Credit to nigma for this in the heroku-django-cookbook

indent() {
    RE="s/^/       /"
    [ $(uname) == "Darwin" ] && sed -l "$RE" || sed -u "$RE"
}

MANAGE_FILE=$(find . -maxdepth 3 -type f -name 'manage.py' | head -1)
MANAGE_FILE=${MANAGE_FILE:2}

echo "-----> Compressing static files"
python $MANAGE_FILE compress 2>&1 | indent

echo'''
    run_compress = open('run_compress', 'w')
    run_compress.write(compress_script)
    run_compress.close()


def initialise_git_repo():
    subprocess.run(['git', 'init'])
    ignore = '''
*.pyc
__pycache__/
*.swp
/static/
/media/
.env'''
    f = open('.gitignore', 'w')
    f.write(ignore)
    f.close()
    subprocess.run(['git', 'add', './'])
    subprocess.run(['git', 'commit', '-m', '"Initial commit"'])


def deploy_to_heroku():
    subprocess.run(['heroku', 'create'])
    subprocess.run(['git', 'push', 'heroku', 'master'])


def create_env_file():
    env_file_template='''
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=$key
DATABASE_URL=$url
'''
    template = string.Template(env_file_template)
    subs = {
        'url': get_db_url(),
        'key': generate_secret_key(),
    }
    s = template.substitute(subs)

    f = open('.env', 'w')
    f.write(s)
    f.close()


def get_db_url():
    result = subprocess.run(['heroku', 'config'], capture_output=True)
    decoded_result = result.stdout.decode()
    pattern = re.compile("DATABASE_URL: (.*)")
    lines = decoded_result.split('\n')
    for line in lines:
        if pattern.match(line):
            db_url = pattern.match(line).group(1)
    return db_url


def generate_secret_key(size=50, chars=string.ascii_uppercase + string.digits +
        string.ascii_lowercase):
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def push_heroku_config():
    if not is_heroku_config_installed():
        subprocess.run(['heroku', 'plugins:install', 'git://github.com/xavdid/heroku-config.git'])
    subprocess.run(['heroku', 'config:push'])


def is_heroku_config_installed():
    result = subprocess.run(['heroku', 'plugins'], capture_output=True)
    pattern = re.compile("heroku-config")
    return pattern.match(result.stdout.decode())


def migrate():
    subprocess.run(['heroku', 'run', 'python', 'manage.py', 'migrate'])


if __name__ == '__main__':
    PROJECT_NAME = input('What is the name of the new project? ')
    create_new_wagtail_project(PROJECT_NAME)
    modify_settings(PROJECT_NAME)
    add_heroku_files()
    initialise_git_repo()
    deploy_to_heroku()
    create_env_file()
    push_heroku_config()
    migrate()
    print('Your app should be ready for development')


