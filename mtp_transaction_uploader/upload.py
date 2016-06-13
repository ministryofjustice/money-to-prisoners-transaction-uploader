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
from .patterns import CREDIT_REF_PATTERN, FILE_PATTERN_STR, ROLL_NUMBER_PATTERNS

logger = logging.getLogger('mtp')

DATE_FORMAT = '%d%m%y'
SIZE_LIMIT_BYTES = 50 * 1000 * 1000  # 50MB

NewFiles = namedtuple('NewFiles', ['new_dates', 'new_filenames'])
RetrievedFiles = namedtuple('RetrievedFiles', ['new_last_date', 'new_filenames'])
PrisonerDetails = namedtuple('PrisonerDetails', ['prisoner_number', 'prisoner_dob', 'from_description_field'])
ParsedReference = namedtuple('ParsedReference', ['prisoner_number', 'prisoner_dob'])
SenderInformation = namedtuple('SenderInformation', ['sort_code', 'account_number', 'roll_number', 'incomplete'])


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

    if new_dates and new_filenames:
        sorted_dates, sorted_files = zip(*sorted(zip(new_dates, new_filenames)))
        return NewFiles(list(sorted_dates), list(sorted_files))
    else:
        return NewFiles([], [])


def parse_filename(filename, account_code):
    file_pattern = re.compile(
        FILE_PATTERN_STR % {'code': account_code}, re.X
    )
    m = file_pattern.search(filename)
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
    response = conn.transactions.get(ordering='-received_at', limit=1)
    if response.get('results'):
        last_date = response['results'][0]['received_at'][:10]
        last_date = datetime.strptime(last_date, '%Y-%m-%d')

    new_dates, new_filenames = download_new_files(last_date)

    new_last_date = None
    # find last dated file
    if len(new_dates) > 0:
        new_last_date = sorted(new_dates)[-1]

    return RetrievedFiles(new_last_date, new_filenames)


def upload_transactions_from_files(files):
    conn = get_authenticated_connection()
    successful_transaction_count = 0
    for filename in files:
        logger.info('Processing %s...' % filename)
        with open(filename) as f:
            data_services_file = parse(f)
        transactions = get_transactions_from_file(data_services_file)
        if transactions:
            transaction_count = len(transactions)
            try:
                conn.transactions.post(clean_request_data(transactions))
                stmt_date = parse_filename(filename, settings.ACCOUNT_CODE).date()
                update_new_balance(transactions, stmt_date)
                logger.info('Uploaded %d transactions from %s' % (transaction_count, filename))
                successful_transaction_count += transaction_count
            except SlumberHttpBaseException as e:
                logger.error('Failed to upload %d transactions from %s.\n%s' % (
                    transaction_count,
                    filename,
                    getattr(e, 'content', e)
                ))
    return successful_transaction_count


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
        if record.is_total() or record.is_balance():
            continue

        sender_information = extract_sender_information(record)
        transaction = {
            'amount': record.amount,
            'sender_sort_code': sender_information.sort_code,
            'sender_account_number': sender_information.account_number,
            'sender_roll_number': sender_information.roll_number,
            'incomplete_sender_info': sender_information.incomplete,
            'sender_name': record.transaction_description,
            'reference': record.reference_number,
            'received_at': record.date.isoformat(),
            'processor_type_code': record.transaction_code.value
        }
        # payment credits
        if (record.transaction_code == TransactionCode.credit_bacs_credit or
                record.transaction_code == TransactionCode.credit_sundry_credit):
            transaction['category'] = 'credit'
            transaction['source'] = 'bank_transfer'

            parsed_ref = extract_prisoner_details(record)
            if parsed_ref:
                number, dob, from_description_field = parsed_ref
                transaction['prisoner_number'] = number
                transaction['prisoner_dob'] = dob.isoformat()
                transaction['reference_in_sender_field'] = from_description_field
        # other credits (e.g. bacs returned)
        elif record.is_credit():
            transaction['category'] = 'credit'
            transaction['source'] = 'administrative'
        # all debits
        elif record.is_debit():
            transaction['category'] = 'debit'
            transaction['source'] = 'administrative'

        transactions.append(transaction)

    return transactions


def extract_prisoner_details(record):
    from_description_field = False
    parsed_ref = parse_credit_reference(record.reference_number)
    if parsed_ref is None:
        parsed_ref = parse_credit_reference(record.transaction_description)
        if parsed_ref:
            from_description_field = True

    if parsed_ref:
        prisoner_number, prisoner_dob = parsed_ref
        return PrisonerDetails(prisoner_number, prisoner_dob, from_description_field)


def parse_credit_reference(ref):
    if not ref:
        return
    matches = CREDIT_REF_PATTERN.match(ref)
    if not matches:
        return

    reference, day, month, year = matches.group('reference_1'), \
        matches.group('day_1'), matches.group('month_1'), matches.group('year_1')
    if not reference:
        reference, day, month, year = matches.group('reference_2'), \
            matches.group('day_2'), matches.group('month_2'), matches.group('year_2')

    date_str = '%s/%s/%s' % (day, month, year)
    try:
        dob = datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        try:
            dob = datetime.strptime(date_str, '%d/%m/%y')
            # set correct century for 2 digit year
            if dob.year > datetime.today().year - 10:
                dob = dob.replace(year=dob.year - 100)
        except ValueError:
            return

    return ParsedReference(reference.upper(), dob.date())


def extract_sender_information(record):
    sort_code = record.originators_sort_code
    account_number = record.originators_account_number
    roll_number = None
    roll_number_expected = False

    if record.is_debit():
        candidate_roll_number = record.reference_number
    else:
        candidate_roll_number = record.transaction_description

    if record.originators_sort_code in ROLL_NUMBER_PATTERNS:
        patterns = ROLL_NUMBER_PATTERNS[record.originators_sort_code]
        if isinstance(patterns, dict):
            pattern = patterns.get(record.originators_account_number)
        else:
            pattern = patterns

        if pattern:
            roll_number_expected = True
            if account_number is None:
                # 0 filled normally means absent, but some building societies
                # use it for roll number accounts
                account_number = '0' * 8
            if candidate_roll_number:
                m = pattern.match(candidate_roll_number)
                if m:
                    roll_number = candidate_roll_number.strip()

    return SenderInformation(
        sort_code, account_number, roll_number,
        sort_code is None or account_number is None or
        (roll_number_expected and roll_number is None)
    )


def update_new_balance(transactions, date):
    conn = get_authenticated_connection()
    response = conn.balances.get(limit=1, date__lt=date.isoformat())
    if response.get('results'):
        balance = response['results'][0]['closing_balance']
    else:
        balance = 0

    for t in transactions:
        if t['category'] == 'credit':
            balance += t['amount']
        elif t['category'] == 'debit':
            balance -= t['amount']

    conn.balances.post({'date': date.isoformat(),
                        'closing_balance': balance})


def main():
    last_date, files = retrieve_data_services_files()
    file_count = len(files)
    if file_count == 0:
        logger.info('No new files available to upload', extra={
            'elk_fields': {
                '@fields.file_count': file_count
            }
        })
        return

    logger.info('Uploading transactions from new files: ' + ', '.join(files), extra={
        'elk_fields': {
            '@fields.file_count': file_count
        }
    })
    transaction_count = upload_transactions_from_files(files)
    logger.info(
        'Upload of %d transactions complete' % transaction_count,
        extra={
            'elk_fields': {
                '@fields.transaction_count': transaction_count
            }
        }
    )
