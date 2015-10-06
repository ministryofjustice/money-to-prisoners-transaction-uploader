import os

SFTP_HOST = os.environ.get('SFTP_HOST', '')
SFTP_USER = os.environ.get('SFTP_USER', '')
SFTP_PRIVATE_KEY = os.environ.get('SFTP_PRIVATE_KEY', '~/.ssh/id_rsa')
SFTP_DIR = os.environ.get('SFTP_DIR', '')
ACCOUNT_CODE = os.environ.get('ACCOUNT_CODE', '')

API_USERNAME = os.environ.get('API_USERNAME', 'transaction-uploader')
API_PASSWORD = os.environ.get('API_PASSWORD', 'notthepassword')

API_CLIENT_ID = os.environ.get('API_CLIENT_ID', 'bank-admin')
API_CLIENT_SECRET = os.environ.get('API_CLIENT_SECRET', 'bank-admin')
API_URL = os.environ.get('API_URL', 'http://localhost:8000')

DS_LAST_DATE_FILE = os.environ.get('DS_LAST_DATE_FILE', '/tmp/ds_last_date')
DS_NEW_FILES_DIR = os.environ.get('DS_NEW_FILES_DIR', '/tmp/ds_new_files')
