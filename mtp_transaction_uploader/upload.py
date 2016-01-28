from collections import namedtuple
from datetime import datetime
import logging
import os
import re
import shutil

from bankline_parser.data_services import parse
from bankline_parser.data_services.enums import TransactionCode
from pysftp import Connection
from slumber.exceptions import SlumberHttpBaseException

from . import settings
from .api_client import get_authenticated_connection

logger = logging.getLogger('mtp')

DATE_FORMAT = '%d%m%y'
SIZE_LIMIT_BYTES = 50 * 1000 * 1000  # 50MB

credit_ref_pattern = re.compile(
    '''
    ([A-Za-z][0-9]{4}[A-Za-z]{2}) # match the prisoner number
    .*?                           # skip until next digit
    ([0-9]{1,2})                  # match 1 or 2 digit day of month
    .*?                           # skip until next digit
    ([0-9]{1,2})                  # match 1 or 2 digit month
    .*?                           # skip until next digit
    ([0-9]{2,4})                  # match 2 or 4 digit year
    ''',
    re.X
)
file_pattern_str = (
    '''
    Y01A\.CARS\.\#D\.             # static file format
    %(code)s\.                    # our unique account code
    D(?P<date>[0-9]{6})           # date that file was generated (ddmmyy)
    '''
)


def download_new_files(last_date):
    new_dates = []
    new_filenames = []
    with Connection(settings.SFTP_HOST, username=settings.SFTP_USER,
                    private_key=settings.SFTP_PRIVATE_KEY) as conn:
        with conn.cd(settings.SFTP_DIR):
            dir_listing = conn.listdir()
            for filename in dir_listing:
                date = parse_filename(filename, settings.ACCOUNT_CODE)

                if date:
                    stat = conn.stat(filename)
                    if stat.st_size > SIZE_LIMIT_BYTES:
                        logger.error('%s is too large (%s), download skipped.'
                                     % (filename, stat.st_size))
                        continue

                    if last_date is None or date.date() > last_date.date():
                        local_path = os.path.join(settings.DS_NEW_FILES_DIR,
                                                  filename)
                        new_filenames.append(local_path)
                        new_dates.append(date)
                        conn.get(filename, localpath=local_path)

    NewFiles = namedtuple('NewFiles', ['new_dates', 'new_filenames'])
    return NewFiles(new_dates, new_filenames)


def parse_filename(filename, account_code):
    file_pattern = re.compile(
        file_pattern_str % {'code': account_code}, re.X
    )
    m = file_pattern.match(filename)
    if m:
        return datetime.strptime(m.group('date'), DATE_FORMAT)
    return None


def retrieve_data_services_files():
    # check for existing downloaded files and remove if found
    if os.path.exists(settings.DS_NEW_FILES_DIR):
        shutil.rmtree(settings.DS_NEW_FILES_DIR)
    os.mkdir(settings.DS_NEW_FILES_DIR)

    # check date of most recent transactions uploaded
    last_date = None
    conn = get_authenticated_connection()
    response = conn.bank_admin.transactions.get(ordering='-received_at', limit=1)
    if response.get('results'):
        last_date = response['results'][0]['received_at'][:10]
        last_date = datetime.strptime(last_date, '%Y-%m-%d')

    new_dates, new_filenames = download_new_files(last_date)

    new_last_date = None
    # find last dated file
    if len(new_dates) > 0:
        new_last_date = sorted(new_dates)[-1]

    RetrievedFiles = namedtuple('RetrievedFiles',
                                ['new_last_date', 'new_filenames'])
    return RetrievedFiles(new_last_date, new_filenames)


def upload_transactions_from_files(files):
    conn = get_authenticated_connection()
    for filename in files:
        logger.info('Processing %s...' % filename)
        with open(filename) as f:
            data_services_file = parse(f)
        transactions = get_transactions_from_file(data_services_file)
        if transactions:
            try:
                conn.bank_admin.transactions.post(clean_request_data(transactions))
                logger.info('...done.')
            except SlumberHttpBaseException as e:
                logger.error('...failed.\n' + getattr(e, 'content', ''))


def clean_request_data(data):
    cleaned_data = []
    for item in data:
        cleaned_item = {}
        for key in item:
            if item[key] is not None:
                cleaned_item[key] = item[key]
        cleaned_data.append(cleaned_item)
    return cleaned_data


def get_transactions_from_file(data_services_file):
    if not data_services_file.is_valid():
        logger.error('Errors: %s' % data_services_file.errors)
        return None

    if not data_services_file.accounts or \
            not data_services_file.accounts[0].records:
        logger.info('No records found.')
        return None

    transactions = []
    for record in data_services_file.accounts[0].records:
        # payment credits
        if (record.transaction_code == TransactionCode.credit_bacs_credit or
                record.transaction_code == TransactionCode.credit_sundry_credit):
            transaction = {
                'amount': record.amount,
                'category': 'credit',
                'source': 'bank_transfer',
                'sender_sort_code': record.originators_sort_code,
                'sender_account_number': record.originators_account_number,
                'sender_name': record.transaction_description,
                'reference': record.reference_number,
                'received_at': record.date.isoformat()
            }

            parsed_ref = parse_credit_reference(record.reference_number)
            if parsed_ref:
                number, dob = parsed_ref
                transaction['prisoner_number'] = number
                transaction['prisoner_dob'] = dob
            transactions.append(transaction)
        # other credits (e.g. bacs returned)
        elif record.is_credit() and not record.is_total():
            transaction = {
                'amount': record.amount,
                'category': 'credit',
                'source': 'administrative',
                'sender_sort_code': record.originators_sort_code,
                'sender_account_number': record.originators_account_number,
                'sender_name': record.transaction_description,
                'reference': record.reference_number,
                'received_at': record.date.isoformat()
            }
            transactions.append(transaction)
        # all debits
        elif record.is_debit() and not record.is_total():
            transaction = {
                'amount': record.amount,
                'category': 'debit',
                'source': 'administrative',
                'sender_sort_code': record.originators_sort_code,
                'sender_account_number': record.originators_account_number,
                'sender_name': record.transaction_description,
                'reference': record.reference_number,
                'received_at': record.date.isoformat(),
            }
            transactions.append(transaction)

    return transactions


def parse_credit_reference(ref):
    if ref:
        m = credit_ref_pattern.match(ref)
        if m:
            date_str = '%s/%s/%s' % (m.group(2), m.group(3), m.group(4))
            try:
                dob = datetime.strptime(date_str, '%d/%m/%Y')
            except ValueError:
                dob = datetime.strptime(date_str, '%d/%m/%y')

                # set correct century for 2 digit year
                if dob.year > datetime.today().year - 10:
                    dob = dob.replace(year=dob.year - 100)

            ParsedReference = namedtuple('ParsedReference',
                                         ['prisoner_number', 'prisoner_dob'])
            return ParsedReference(m.group(1), dob)


def main():
    last_date, files = retrieve_data_services_files()
    if len(files) == 0:
        logger.info('No new files available for download.')
        return

    logger.info('Downloaded... ' + ', '.join(files))
    logger.info('Uploading...')
    upload_transactions_from_files(files)
    logger.info('Upload complete.')
