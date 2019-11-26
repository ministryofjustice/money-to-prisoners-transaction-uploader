import os
from urllib.parse import urljoin

UPLOADER_DISABLED = os.environ.get('UPLOADER_DISABLED', '')

ENVIRONMENT = os.environ.get('ENV', 'local')
APP_BUILD_DATE = os.environ.get('APP_BUILD_DATE', '')
APP_BUILD_TAG = os.environ.get('APP_BUILD_TAG', '')
APP_GIT_COMMIT = os.environ.get('APP_GIT_COMMIT', '')

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')

SFTP_HOST = os.environ.get('SFTP_HOST', '')
SFTP_USER = os.environ.get('SFTP_USER', '')
SFTP_PRIVATE_KEY = os.environ.get('SFTP_PRIVATE_KEY', '~/.ssh/id_rsa')
SFTP_DIR = os.environ.get('SFTP_DIR', '')
ACCOUNT_CODE = os.environ.get('ACCOUNT_CODE', '444444')

UPLOAD_REQUEST_SIZE = int(os.environ.get('UPLOAD_REQUEST_SIZE', '1000'))

START_PAGE_URL = os.environ.get('START_PAGE_URL', 'https://www.gov.uk/send-prisoner-money')
CASHBOOK_URL = (
    f'https://{os.environ["PUBLIC_CASHBOOK_HOST"]}'
    if os.environ.get('PUBLIC_CASHBOOK_HOST')
    else 'http://localhost:8001'
)
BANK_ADMIN_URL = (
    f'https://{os.environ["PUBLIC_BANK_ADMIN_HOST"]}'
    if os.environ.get('PUBLIC_BANK_ADMIN_HOST')
    else 'http://localhost:8002'
)
NOMS_OPS_URL = (
    f'https://{os.environ["PUBLIC_NOMS_OPS_HOST"]}'
    if os.environ.get('PUBLIC_NOMS_OPS_HOST')
    else 'http://localhost:8003'
)
SEND_MONEY_URL = (
    f'https://{os.environ["PUBLIC_SEND_MONEY_HOST"]}'
    if os.environ.get('PUBLIC_SEND_MONEY_HOST')
    else 'http://localhost:8004'
)

API_USERNAME = os.environ.get('API_USERNAME', 'bank-admin')
API_PASSWORD = os.environ.get('API_PASSWORD', 'bank-admin')

API_CLIENT_ID = os.environ.get('API_CLIENT_ID', 'bank-admin')
API_CLIENT_SECRET = os.environ.get('API_CLIENT_SECRET', 'bank-admin')
API_URL = os.environ.get('API_URL', 'http://localhost:8000')
PUBLIC_STATIC_URL = urljoin(SEND_MONEY_URL, '/static/')

DS_NEW_FILES_DIR = os.environ.get('DS_NEW_FILES_DIR', '/tmp/ds_new_files')

NOMS_AGENCY_ACCOUNT_NUMBER = os.environ.get('NOMS_AGENCY_ACCOUNT_NUMBER', 'PPPPPPPP')
NOMS_AGENCY_SORT_CODE = os.environ.get('NOMS_AGENCY_SORT_CODE', 'XXXXXX')
WORLDPAY_SETTLEMENT_REFERENCE = os.environ.get('WORLDPAY_SETTLEMENT_REFERENCE', '.*GGGGGGGG.*([0-9]{4}).*')

if os.environ.get('IGNORE_LOCAL_SETTINGS', '') != 'True':
    try:
        from .local import *  # noqa
    except ImportError:
        pass
