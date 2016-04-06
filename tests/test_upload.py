from datetime import datetime, date
from unittest import mock, TestCase

from bankline_parser.data_services import parse

from mtp_transaction_uploader import upload


class CreditReferenceParsingTestCase(TestCase):

    def _test_successful_parse(self, reference, prisoner_number, prisoner_dob):
        parsed_number, parsed_dob = upload.parse_credit_reference(reference)
        self.assertEqual(parsed_number, prisoner_number)
        self.assertEqual(parsed_dob, prisoner_dob)

    def test_correct_format_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/86', 'A1234GY', date(1986, 12, 9)
        )

    def test_trailing_whitespace_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/86        ', 'A1234GY', date(1986, 12, 9)
        )

    def test_leading_whitespace_parses(self):
        self._test_successful_parse(
            '      A1234GY 09/12/86', 'A1234GY', date(1986, 12, 9)
        )

    def test_trailing_non_digits_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/86.', 'A1234GY', date(1986, 12, 9)
        )

    def test_no_space_parses(self):
        self._test_successful_parse(
            'A1234GY09/12/86', 'A1234GY', date(1986, 12, 9)
        )

    def test_arbitrary_divider_parses(self):
        self._test_successful_parse(
            'A1234GY:::09/12/1986', 'A1234GY', date(1986, 12, 9)
        )

    def test_hyphenated_date_parses(self):
        self._test_successful_parse(
            'A1234GY 09-12-86', 'A1234GY', date(1986, 12, 9)
        )

    def test_non_separated_date_parses(self):
        self._test_successful_parse(
            'A1234GY091286', 'A1234GY', date(1986, 12, 9)
        )

    def test_space_separated_date_parses(self):
        self._test_successful_parse(
            'A1234GY 09 12 86', 'A1234GY', date(1986, 12, 9)
        )

    def test_non_zero_padded_date_parses(self):
        self._test_successful_parse(
            'A1234GY 9/6/86', 'A1234GY', date(1986, 6, 9)
        )

    def test_four_digit_year_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/1986', 'A1234GY', date(1986, 12, 9)
        )

    def test_invalid_prisoner_number_does_not_parse_1(self):
        self.assertEqual(upload.parse_credit_reference('A1234Y 09/12/1986'), None)

    def test_invalid_prisoner_number_does_not_parse_2(self):
        self.assertEqual(upload.parse_credit_reference('AA1234GY 09/12/1986'), None)

    def test_one_digit_year_does_not_parse(self):
        self.assertEqual(upload.parse_credit_reference('A1234GY 1/1/1'), None)

    def test_three_digit_year_does_not_parse(self):
        self.assertEqual(upload.parse_credit_reference('A1234GY 09/12/198'), None)

    def test_too_many_date_digits_does_not_parse(self):
        self.assertEqual(upload.parse_credit_reference('A1234GY 0931231986'), None)

    def test_trailing_digits_does_not_parse(self):
        self.assertEqual(upload.parse_credit_reference('A1234GY 09/12/198600000'), None)

    def test_impossible_day_does_not_parse(self):
        self.assertEqual(upload.parse_credit_reference('A1234GY 32/12/1986'), None)

    def test_impossible_month_does_not_parse(self):
        self.assertEqual(upload.parse_credit_reference('A1234GY 09/13/1986'), None)


class FilenameParsingTestCase(TestCase):

    def test_correct_format_returns_correct_date(self):
        filename = 'Y01A.CARS.#D.444444.D091214'
        expected_date = date(2014, 12, 9)
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_datetime.date())

    def test_correct_format_returns_correct_date_pre_2000(self):
        filename = 'Y01A.CARS.#D.444444.D091299'
        expected_date = date(1999, 12, 9)
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_datetime.date())

    def test_incorrect_format_returns_none(self):
        filename = 'unrelated_file'
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(None, parsed_datetime)

    def test_incorrect_account_code_returns_none(self):
        filename = 'Y01A.CARS.#D.555555.D091214'
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(None, parsed_datetime)

    def test_parsing_date_from_full_path_succeeds(self):
        filename = '/random/Y01A.CARS.#D.444444.D091214'
        expected_date = date(2014, 12, 9)
        parsed_datetime = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_datetime.date())


@mock.patch('mtp_transaction_uploader.upload.settings')
@mock.patch('mtp_transaction_uploader.upload.Connection')
class FileDownloadTestCase(TestCase):

    def _download_new_files(self, mock_connection_class, mock_settings, dirlist, last_date):
        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'

        return upload.download_new_files(last_date)

    def test_download_new_files(self, mock_connection_class, mock_settings):
        dirlist = [
            'Y01A.CARS.#D.444444.D091214',
            'Y01A.CARS.#D.444444.D101214',
            'Y01A.CARS.#D.444444.D111214',
            'Y01A.CARS.#D.444444.D121214',
            'Y01A.CARS.#D.444444.D131214',
            'Y01A.CARS.#D.444444.D141214',
        ]

        new_dates, new_filenames = self._download_new_files(
            mock_connection_class, mock_settings, dirlist, None
        )

        self.assertEqual([
            date(2014, 12, 9),
            date(2014, 12, 10),
            date(2014, 12, 11),
            date(2014, 12, 12),
            date(2014, 12, 13),
            date(2014, 12, 14),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/Y01A.CARS.#D.444444.D091214',
            '/Y01A.CARS.#D.444444.D101214',
            '/Y01A.CARS.#D.444444.D111214',
            '/Y01A.CARS.#D.444444.D121214',
            '/Y01A.CARS.#D.444444.D131214',
            '/Y01A.CARS.#D.444444.D141214',
        ], new_filenames)

    def test_files_ordered_by_date(self, mock_connection_class, mock_settings):
        dirlist = [
            'Y01A.CARS.#D.444444.D111214',
            'Y01A.CARS.#D.444444.D091214',
            'Y01A.CARS.#D.444444.D101214',
        ]

        new_dates, new_filenames = self._download_new_files(
            mock_connection_class, mock_settings, dirlist, None
        )

        self.assertEqual([
            date(2014, 12, 9),
            date(2014, 12, 10),
            date(2014, 12, 11),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/Y01A.CARS.#D.444444.D091214',
            '/Y01A.CARS.#D.444444.D101214',
            '/Y01A.CARS.#D.444444.D111214',
        ], new_filenames)

    def test_download_new_files_skips_other_accounts(
        self,
        mock_connection_class,
        mock_settings
    ):
        dirlist = [
            'Y01A.CARS.#D.444444.D091214',
            'Y01A.CARS.#D.444444.D101214',
            'Y01A.CARS.#D.444444.D111214',
            'Y01A.CARS.#D.444444.D121214',
            'Y01A.CARS.#D.555555.D131214',
            'Y01A.CARS.#D.444444.D141214',
        ]

        new_dates, new_filenames = self._download_new_files(
            mock_connection_class, mock_settings, dirlist, None
        )

        self.assertEqual([
            date(2014, 12, 9),
            date(2014, 12, 10),
            date(2014, 12, 11),
            date(2014, 12, 12),
            date(2014, 12, 14),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/Y01A.CARS.#D.444444.D091214',
            '/Y01A.CARS.#D.444444.D101214',
            '/Y01A.CARS.#D.444444.D111214',
            '/Y01A.CARS.#D.444444.D121214',
            '/Y01A.CARS.#D.444444.D141214',
        ], new_filenames)

    def test_download_new_files_skips_old_files(
        self,
        mock_connection_class,
        mock_settings
    ):
        dirlist = [
            'Y01A.CARS.#D.444444.D091214',
            'Y01A.CARS.#D.444444.D101214',
            'Y01A.CARS.#D.444444.D111214',
            'Y01A.CARS.#D.444444.D121214',
            'Y01A.CARS.#D.444444.D131214',
            'Y01A.CARS.#D.444444.D141214',
        ]

        new_dates, new_filenames = self._download_new_files(
            mock_connection_class, mock_settings, dirlist, datetime(2014, 12, 11)
        )

        self.assertEqual([
            date(2014, 12, 12),
            date(2014, 12, 13),
            date(2014, 12, 14),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/Y01A.CARS.#D.444444.D121214',
            '/Y01A.CARS.#D.444444.D131214',
            '/Y01A.CARS.#D.444444.D141214',
        ], new_filenames)

    def test_download_new_files_skips_large_files(
        self,
        mock_connection_class,
        mock_settings
    ):
        dirlist = [
            'Y01A.CARS.#D.444444.D091214',
            'Y01A.CARS.#D.444444.D101214',
            'Y01A.CARS.#D.444444.D111214',
            'Y01A.CARS.#D.444444.D121214',
            'Y01A.CARS.#D.444444.D131214',
            'Y01A.CARS.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.side_effect = [
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 1000})(),
            type("", (), {'st_size': 100000000})(),
            type("", (), {'st_size': 1000})(),
        ]

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'

        new_dates, new_filenames = upload.download_new_files(None)

        self.assertEqual([
            date(2014, 12, 9),
            date(2014, 12, 10),
            date(2014, 12, 11),
            date(2014, 12, 12),
            date(2014, 12, 14),
        ], [dt.date() for dt in new_dates])
        self.assertEqual([
            '/Y01A.CARS.#D.444444.D091214',
            '/Y01A.CARS.#D.444444.D101214',
            '/Y01A.CARS.#D.444444.D111214',
            '/Y01A.CARS.#D.444444.D121214',
            '/Y01A.CARS.#D.444444.D141214',
        ], new_filenames)


class RetrieveNewFilesTestCase(TestCase):

    @mock.patch('mtp_transaction_uploader.upload.Connection')
    @mock.patch('mtp_transaction_uploader.upload.settings')
    @mock.patch('mtp_transaction_uploader.upload.os')
    @mock.patch('mtp_transaction_uploader.upload.shutil')
    @mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
    def test_retrieve_new_files(
        self,
        mock_get_connection,
        mock_shutil,
        mock_os,
        mock_settings,
        mock_connection_class
    ):
        mock_os.path.exists.side_effect = [False]
        mock_get_connection().bank_admin.transactions.get.return_value =\
            {'count': 1, 'results': [{'received_at': '2014-12-115T19:09:02Z'}]}

        dirlist = [
            'Y01A.CARS.#D.444444.D091214',
            'Y01A.CARS.#D.444444.D101214',
            'Y01A.CARS.#D.444444.D111214',
            'Y01A.CARS.#D.444444.D121214',
            'Y01A.CARS.#D.444444.D131214',
            'Y01A.CARS.#D.444444.D141214',
        ]

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'
        mock_os.path.join = lambda a, b: a + b

        new_last_date, new_filenames = upload.retrieve_data_services_files()

        self.assertFalse(mock_shutil.rmtree.called)

        self.assertEqual([
            '/Y01A.CARS.#D.444444.D121214',
            '/Y01A.CARS.#D.444444.D131214',
            '/Y01A.CARS.#D.444444.D141214',
        ], new_filenames)
        self.assertEqual(date(2014, 12, 14), new_last_date.date())

    @mock.patch('mtp_transaction_uploader.upload.Connection')
    @mock.patch('mtp_transaction_uploader.upload.settings')
    @mock.patch('mtp_transaction_uploader.upload.os')
    @mock.patch('mtp_transaction_uploader.upload.shutil')
    @mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
    def test_retrieve_new_files_no_files_available(
        self,
        mock_get_connection,
        mock_shutil,
        mock_os,
        mock_settings,
        mock_connection_class
    ):
        mock_os.path.exists.side_effect = [False]
        mock_get_connection().bank_admin.transactions.get.return_value =\
            {'count': 1, 'results': [{'received_at': '2014-12-115T19:09:02Z'}]}

        dirlist = []

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type("", (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'
        mock_os.path.join = lambda a, b: a + b

        new_last_date, new_filenames = upload.retrieve_data_services_files()

        self.assertFalse(mock_shutil.rmtree.called)

        self.assertEqual([], new_filenames)
        self.assertEqual(None, new_last_date)


class TransactionsFromFileTestCase(TestCase):

    def test_get_transactions(self):
        with open('tests/data/testfile_1') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 3)

        # transaction 0 - debit
        self.assertEqual(transactions[0]['category'], 'debit')
        self.assertEqual(transactions[0]['source'], 'administrative')
        self.assertEqual(transactions[0]['amount'], 288615)
        self.assertEqual(transactions[0]['received_at'], '2004-02-05T00:00:00')
        self.assertEqual(transactions[0]['processor_type_code'], '03')

        self.assertEqual(transactions[0]['reference'], 'Payment refund    ')
        self.assertEqual(transactions[0].get('prisoner_number'), None)
        self.assertEqual(transactions[0].get('prisoner_dob'), None)

        # transaction 1 - credit
        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['source'], 'bank_transfer')
        self.assertEqual(transactions[1]['amount'], 8939)
        self.assertEqual(transactions[1]['received_at'], '2004-02-05T00:00:00')
        self.assertEqual(transactions[1]['sender_account_number'], '29696666')
        self.assertEqual(transactions[1]['sender_sort_code'], '608006')
        self.assertEqual(transactions[1]['processor_type_code'], '99')

        self.assertEqual(transactions[1]['prisoner_number'], 'A1234BY')
        self.assertEqual(transactions[1]['prisoner_dob'], '1986-12-09')

        # transaction 2 - credit
        self.assertEqual(transactions[2]['category'], 'credit')
        self.assertEqual(transactions[2]['source'], 'bank_transfer')
        self.assertEqual(transactions[2]['amount'], 9802)
        self.assertEqual(transactions[2]['received_at'], '2004-02-05T00:00:00')
        self.assertEqual(transactions[2]['sender_account_number'], '78990056')
        self.assertEqual(transactions[2]['sender_sort_code'], '245432')
        self.assertEqual(transactions[2]['processor_type_code'], '93')

        self.assertEqual(transactions[2]['prisoner_number'], 'B4321XZ')
        self.assertEqual(transactions[2]['prisoner_dob'], '1992-11-08')

    def test_populates_roll_numbers_when_relevant_sort_codes_found(self):
        with open('tests/data/testfile_roll_number') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 7)

        self.assertEqual(transactions[0]['category'], 'credit')
        self.assertEqual(transactions[0]['sender_roll_number'], '123A 123456A')

        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['sender_roll_number'], 'A12345678SMI')

        self.assertEqual(transactions[2]['category'], 'credit')
        self.assertEqual(transactions[2]['sender_roll_number'], '1234/12345678')

        self.assertEqual(transactions[3]['category'], 'credit')
        self.assertEqual(transactions[3]['sender_roll_number'], '12-123456-12345')

        self.assertEqual(transactions[4]['category'], 'credit')
        self.assertEqual(transactions[4]['sender_roll_number'], '1234567890')

        self.assertEqual(transactions[5]['category'], 'debit')
        self.assertEqual(transactions[5]['sender_roll_number'], '1234567890')

        self.assertEqual(transactions[6]['category'], 'credit')
        self.assertEqual(transactions[6]['sender_roll_number'], 'A12345678')

    def test_does_not_populate_roll_number_typically(self):
        with open('tests/data/testfile_1') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 3)

        self.assertEqual(transactions[0]['sender_roll_number'], None)
        self.assertEqual(transactions[1]['sender_roll_number'], None)
        self.assertEqual(transactions[2]['sender_roll_number'], None)

    def test_does_not_populate_roll_number_if_not_matching_format(self):
        with open('tests/data/testfile_bs_sort_code_invalid_roll_number') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]['sender_roll_number'], None)

    def test_marks_incomplete_sender_information(self):
        with open('tests/data/testfile_sender_information') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 4)

        # check that account number is 0s instead of None for matching building society
        self.assertEqual(transactions[0]['category'], 'credit')
        self.assertEqual(transactions[0]['sender_account_number'], '00000000')

        self.assertEqual(transactions[1]['sender_sort_code'], None)
        self.assertTrue(transactions[1]['incomplete_sender_info'])

        self.assertEqual(transactions[2]['sender_account_number'], None)
        self.assertTrue(transactions[2]['incomplete_sender_info'])

        self.assertEqual(transactions[3]['sender_roll_number'], None)
        self.assertTrue(transactions[3]['incomplete_sender_info'])

    @mock.patch('mtp_transaction_uploader.upload.logger')
    def test_get_transactions_no_records(self, mock_logger):
        with open('tests/data/testfile_no_records') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)
        mock_logger.info.assert_called_with('No records found.')

        self.assertEqual(transactions, None)

    @mock.patch('mtp_transaction_uploader.upload.logger')
    def test_get_transactions_incorrect_totals(self, mock_logger):
        with open('tests/data/testfile_incorrect_totals') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)
        mock_logger.error.assert_called_with(
            "Errors: {'account 0': ['Monetary total of debit items does not "
            "match expected: counted 288615, expected 288610', "
            "'Monetary total of credit items does not match expected: "
            "counted 18741, expected 18732']}")

        self.assertEqual(transactions, None)


@mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
class UpdateNewBalanceTestCase(TestCase):

    def test_update_new_balance(self, mock_get_connection):
        transactions = [
            {'amount': 100, 'category': 'credit'},
            {'amount': 120, 'category': 'debit'},
            {'amount': 200, 'category': 'credit'},
            {'amount': 150, 'category': 'credit'},
        ]
        stmt_date = date(2016, 3, 3)

        conn = mock_get_connection()
        conn.balances.get.return_value = {
            'count': 1,
            'results': [{'closing_balance': 1000}]
        }

        upload.update_new_balance(transactions, stmt_date)

        conn.balances.post.assert_called_with({
            'date': stmt_date.isoformat(),
            'closing_balance': 1330,
        })

    def test_update_new_balance_with_no_previous_balance(self, mock_get_connection):
        transactions = [
            {'amount': 100, 'category': 'credit'},
            {'amount': 120, 'category': 'debit'},
            {'amount': 200, 'category': 'credit'},
            {'amount': 150, 'category': 'credit'},
        ]
        stmt_date = date(2016, 3, 3)

        conn = mock_get_connection()
        conn.balances.get.return_value = {
            'count': 0,
            'results': []
        }

        upload.update_new_balance(transactions, stmt_date)

        conn.balances.post.assert_called_with({
            'date': stmt_date.isoformat(),
            'closing_balance': 330,
        })
