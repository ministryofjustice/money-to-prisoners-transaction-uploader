from collections import namedtuple
import datetime
import itertools
import logging
import math
import os
import re
import shutil
import typing

from bankline_parser.data_services import parse
from bankline_parser.data_services.enums import TransactionCode
from mtp_common.bank_accounts import (
    is_correspondence_account, roll_number_required, roll_number_valid_for_account
)
from pysftp import Connection, CnOpts
from pytz import utc
from slumber.exceptions import SlumberHttpBaseException

from mtp_transaction_uploader import settings
from mtp_transaction_uploader.api_client import get_authenticated_connection
from mtp_transaction_uploader.patterns import (
    CREDIT_REF_PATTERN, CREDIT_REF_PATTERN_REVERSED, FILE_PATTERN_STR,
    ADMINISTRATIVE_IDENTIFIERS, WORLDPAY_SETTLEMENT_REFERENCE_PATTERN,
)

logger = logging.getLogger('mtp')

DATE_FORMAT = '%d%m%y'
SIZE_LIMIT_BYTES = 50 * 1000 * 1000  # 50MB

NewFiles = namedtuple('NewFiles', ['new_dates', 'new_filenames'])
RetrievedFiles = namedtuple('RetrievedFiles', ['new_last_date', 'new_filenames'])
PrisonerDetails = namedtuple('PrisonerDetails', ['prisoner_number', 'prisoner_dob', 'from_description_field'])
ParsedReference = namedtuple('ParsedReference', ['prisoner_number', 'prisoner_dob'])
SenderInformation = namedtuple(
    'SenderInformation',
    ['sort_code', 'account_number', 'roll_number', 'anonymous', 'incomplete', 'administrative']
)


def download_new_files(last_date: typing.Optional[datetime.date]):
    new_dates = []
    new_filenames = []
    opts = CnOpts()
    opts.hostkeys = None
    with Connection(settings.SFTP_HOST, username=settings.SFTP_USER,
                    private_key=settings.SFTP_PRIVATE_KEY, cnopts=opts) as conn:
        with conn.cd(settings.SFTP_DIR):
            dir_listing = conn.listdir()
            for filename in dir_listing:
                date = parse_filename(filename, settings.ACCOUNT_CODE)

                if date:
                    stat = conn.stat(filename)
                    if stat.st_size > SIZE_LIMIT_BYTES:
                        logger.error('%s is too large (%s), download skipped.', filename, stat.st_size)
                        continue

                    if last_date is None or date > last_date:
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


def parse_filename(filename, account_code) -> typing.Optional[datetime.date]:
    file_pattern = re.compile(
        FILE_PATTERN_STR % {'code': account_code}, re.X
    )
    m = file_pattern.search(filename)
    if m:
        return datetime.datetime.strptime(m.group('date'), DATE_FORMAT).date()
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
        last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()

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
        logger.info('Processing %s...', filename)
        with open(filename) as f:
            data_services_file = parse(f)
        transactions = get_transactions_from_file(data_services_file)
        if transactions:
            transaction_count = len(transactions)
            try:
                for i in range(math.ceil(transaction_count / settings.UPLOAD_REQUEST_SIZE)):
                    conn.transactions.post(
                        clean_request_data(transactions[
                            i * settings.UPLOAD_REQUEST_SIZE:
                            (i + 1) * settings.UPLOAD_REQUEST_SIZE
                        ])
                    )
                stmt_date = parse_filename(filename, settings.ACCOUNT_CODE)
                update_new_balance(transactions, stmt_date)
                logger.info('Uploaded %d transactions from %s', transaction_count, filename)
                successful_transaction_count += transaction_count
            except SlumberHttpBaseException as e:
                logger.error(
                    'Failed to upload %d transactions from %s.\n%s',
                    transaction_count,
                    filename,
                    getattr(e, 'content', e)
                )
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
        logger.error('Errors: %s', data_services_file.errors)
        return None

    filtered_records = filter_relevant_records_from_all_accounts(data_services_file.accounts)

    if not filtered_records:
        logger.info('No records found.')
        return None

    transactions = []
    for record in filtered_records:
        if record.is_total() or record.is_balance():
            continue

        sender_information = extract_sender_information(record)
        received_at = datetime.datetime.combine(record.date, datetime.time(12, 0, 0, tzinfo=utc))
        transaction = {
            'amount': record.amount,
            'sender_sort_code': sender_information.sort_code,
            'sender_account_number': sender_information.account_number,
            'sender_roll_number': sender_information.roll_number,
            'blocked': sender_information.anonymous,
            'incomplete_sender_info': sender_information.incomplete,
            'sender_name': record.transaction_description,
            'reference': record.reference_number,
            'received_at': received_at.isoformat(),
            'processor_type_code': record.transaction_code.value
        }
        # payment credits
        if ((record.transaction_code == TransactionCode.credit_bacs_credit or
                record.transaction_code == TransactionCode.credit_sundry_credit) and
                not sender_information.administrative):
            transaction['category'] = 'credit'
            transaction['source'] = 'bank_transfer'

            parsed_ref = extract_prisoner_details(record)
            if parsed_ref:
                number, dob, from_description_field = parsed_ref
                transaction['prisoner_number'] = number
                transaction['prisoner_dob'] = dob.isoformat()
                transaction['reference_in_sender_field'] = from_description_field

            if settings.MARK_TRANSACTIONS_AS_UNIDENTIFIED:
                # makes all credit-type transactions "unidentified" so that they will not be credited or refunded
                transaction['blocked'] = True
                transaction['incomplete_sender_info'] = True
        # other credits (e.g. bacs returned)
        elif record.is_credit():
            transaction['category'] = 'credit'
            transaction['source'] = 'administrative'

            batch_id = get_matching_batch_id_for_settlement(record)
            if batch_id:
                transaction['batch'] = batch_id
        # all debits
        elif record.is_debit():
            transaction['category'] = 'debit'
            transaction['source'] = 'administrative'

        transactions.append(transaction)

    return transactions


def filter_relevant_records_from_all_accounts(accounts):
    # read transactions from all data services file "accounts"
    # to cater for both single-account and multiple-account formats
    records = itertools.chain.from_iterable(account.records for account in accounts)
    # filter out only transactions involving account selected with settings
    records = filter(lambda record: (
        record.branch_sort_code == settings.NOMS_AGENCY_SORT_CODE and
        record.branch_account_number == settings.NOMS_AGENCY_ACCOUNT_NUMBER
    ), records)
    return list(records)


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
        matches = CREDIT_REF_PATTERN_REVERSED.match(ref)
    if not matches:
        return

    number, day, month, year = matches.group('number'), \
        matches.group('day'), matches.group('month'), matches.group('year')

    date_str = '%s/%s/%s' % (day, month, year)
    try:
        dob = datetime.datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        try:
            dob = datetime.datetime.strptime(date_str, '%d/%m/%y')
            # set correct century for 2 digit year
            if dob.year > datetime.datetime.today().year - 10:
                dob = dob.replace(year=dob.year - 100)
        except ValueError:
            return
    dob = dob.date()

    return ParsedReference(number.upper(), dob)


def extract_sender_information(record):
    sort_code = record.originators_sort_code
    account_number = record.originators_account_number
    roll_number = None
    roll_number_expected = False

    # 0 filled normally means absent, but some building societies
    # use it for roll number accounts
    building_soc_account_number = account_number or ('0' * 8)

    if roll_number_required(sort_code, building_soc_account_number):
        roll_number_expected = True
        account_number = building_soc_account_number

        if record.is_debit():
            candidate_roll_number = record.reference_number
        else:
            candidate_roll_number = record.transaction_description

        if roll_number_valid_for_account(sort_code, account_number, candidate_roll_number):
            roll_number = candidate_roll_number.strip()

    anonymous = sort_code is None or account_number is None
    incomplete_sender_info = (
        anonymous or
        (roll_number_expected and roll_number is None) or
        is_correspondence_account(sort_code, account_number)
    )

    return SenderInformation(
        sort_code, account_number, roll_number, anonymous, incomplete_sender_info,
        any([
            identifier.matches(
                account_number, sort_code, record.transaction_description, record.reference_number
            )
            for identifier in ADMINISTRATIVE_IDENTIFIERS
        ])
    )


def get_matching_batch_id_for_settlement(record):
    m = WORLDPAY_SETTLEMENT_REFERENCE_PATTERN.match(record.transaction_description)
    if not m:
        # not a worldpay settlement
        return

    relative_date = record.date.date()
    batch_date = m.group('date')
    try:
        if len(batch_date) == 4:
            batch_date = parse_4_digit_date(batch_date, relative_date)
        elif len(batch_date) == 2:
            batch_date = parse_2_digit_date(batch_date, relative_date)
        else:
            # no date provided so cannot match to a batch
            raise ValueError
    except ValueError:
        # settlement date cannot be parsed
        return

    # get batch id for date if found
    conn = get_authenticated_connection()
    response = conn.batches.get(date=batch_date.isoformat())
    if response.get('results'):
        return response['results'][0]['id']


def parse_2_digit_date(date_str, relative_date: datetime.date) -> datetime.date:
    batch_date = datetime.datetime.strptime(date_str, '%d').date()
    batch_date = batch_date.replace(year=relative_date.year, month=relative_date.month)
    if batch_date <= relative_date:
        return batch_date
    # batch cannot be in the future so go back 1 month
    if batch_date.month == 1:
        return batch_date.replace(year=relative_date.year - 1, month=12)
    else:
        return batch_date.replace(month=relative_date.month - 1)


def parse_4_digit_date(date_str, relative_date: datetime.date) -> datetime.date:
    batch_date = datetime.datetime.strptime(date_str, '%d%m').date()
    batch_date = batch_date.replace(year=relative_date.year)
    if batch_date <= relative_date:
        return batch_date
    # batch cannot be in the future so go back 1 year
    return batch_date.replace(year=relative_date.year - 1)


def update_new_balance(transactions, date: datetime.date):
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
        logger.info(
            'No new files available to upload',
            extra={
                'elk_fields': {
                    '@fields.file_count': file_count
                }
            }
        )
        return

    logger.info(
        'Uploading transactions from new files: %s', ', '.join(files),
        extra={
            'elk_fields': {
                '@fields.file_count': file_count
            }
        }
    )
    transaction_count = upload_transactions_from_files(files)
    logger.info(
        'Upload of %d transactions complete', transaction_count,
        extra={
            'elk_fields': {
                '@fields.transaction_count': transaction_count
            }
        }
    )
