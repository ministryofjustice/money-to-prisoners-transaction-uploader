import os

# NB: only values listed here will be available as environment variables when the cron job runs
# ensure that the environment and setting names match

ENV = os.environ.get('ENV', 'local')
APP_GIT_COMMIT = os.environ.get('APP_GIT_COMMIT', '')
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

SFTP_HOST = os.environ.get('SFTP_HOST', '')
SFTP_USER = os.environ.get('SFTP_USER', '')
SFTP_PRIVATE_KEY = os.environ.get('SFTP_PRIVATE_KEY', '~/.ssh/id_rsa')
SFTP_DIR = os.environ.get('SFTP_DIR', '')
ACCOUNT_CODE = os.environ.get('ACCOUNT_CODE', '444444')

API_USERNAME = os.environ.get('API_USERNAME', 'bank-admin')
API_PASSWORD = os.environ.get('API_PASSWORD', 'bank-admin')

API_CLIENT_ID = os.environ.get('API_CLIENT_ID', 'bank-admin')
API_CLIENT_SECRET = os.environ.get('API_CLIENT_SECRET', 'bank-admin')
API_URL = os.environ.get('API_URL', 'http://localhost:8000')

DS_NEW_FILES_DIR = os.environ.get('DS_NEW_FILES_DIR', '/tmp/ds_new_files')
