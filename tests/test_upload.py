from datetime import date
from unittest import mock, TestCase

from bankline_parser.data_services import parse
from bankline_parser.data_services.models import DataRecord

from mtp_transaction_uploader import upload


class CreditReferenceParsingTestCase(TestCase):
    successful = {
        'correct_format_1': ('A1234GY 09/12/86', 'A1234GY', date(1986, 12, 9)),
        'correct_format_2': ('A1214GY 10/06/80', 'A1214GY', date(1980, 6, 10)),
        'lower_case': ('a1214gy 10/06/80', 'A1214GY', date(1980, 6, 10)),
        'mixed_case': ('A1214gy 10/06/80', 'A1214GY', date(1980, 6, 10)),
        'trailing_whitespace': ('A1234GY 09/12/86        ', 'A1234GY', date(1986, 12, 9)),
        'leading_whitespace': ('      A1234GY 09/12/86', 'A1234GY', date(1986, 12, 9)),
        'trailing_non_digits': ('A1234GY 09/12/86.', 'A1234GY', date(1986, 12, 9)),
        'no_space': ('A1234GY09/12/86', 'A1234GY', date(1986, 12, 9)),
        'arbitrary_divider': ('A1234GY:::09/12/1986', 'A1234GY', date(1986, 12, 9)),
        'whitespace_divider': ('A1234GY    09/12/1986', 'A1234GY', date(1986, 12, 9)),
        'hyphenated_date': ('A1234GY 09-12-86', 'A1234GY', date(1986, 12, 9)),
        'non_separated_date': ('A1234GY091286', 'A1234GY', date(1986, 12, 9)),
        'non_separated_long_date': ('A1234GY09121986', 'A1234GY', date(1986, 12, 9)),
        'space_separated_date': ('A1234GY 09 12 86', 'A1234GY', date(1986, 12, 9)),
        'non_zero_padded_date': ('A1234GY 9/6/86', 'A1234GY', date(1986, 6, 9)),
        'four_digit_year': ('A1234GY 09/12/1986', 'A1234GY', date(1986, 12, 9)),
        'reference_generator_format': ('A1234GY/09/12/1986', 'A1234GY', date(1986, 12, 9)),

        'trailing_characters_1': ('A1234GY091286A6', 'A1234GY', date(1986, 12, 9)),
        'trailing_characters_2': ('A1234GY091286 61', 'A1234GY', date(1986, 12, 9)),

        'reversed_format_1': ('09/12/86 A1234GY', 'A1234GY', date(1986, 12, 9)),
        'reversed_format_2': ('10/06/80 A1214GY', 'A1214GY', date(1980, 6, 10)),
        'reversed_natural_date': ('1/6/1980 A1214GY', 'A1214GY', date(1980, 6, 1)),
        'reversed_with_whitespace': ('  09/12/86 A1234GY  ', 'A1234GY', date(1986, 12, 9)),
        'reversed_with_whitespace_long_year': ('  09/12/1986 A1234GY  ', 'A1234GY', date(1986, 12, 9)),
        'reversed_with_separators': ('9/12/86/A1234GY', 'A1234GY', date(1986, 12, 9)),
        'reversed_with_separators_long_year': ('9/12/1986/A1234GY', 'A1234GY', date(1986, 12, 9)),
        'reversed_without_spaces': ('091286A1234GY', 'A1234GY', date(1986, 12, 9)),
        'reversed_without_spaces_long_year': ('09121986A1234GY', 'A1234GY', date(1986, 12, 9)),

        'reversed_trailing_characters_1': ('091286A1234GY67', 'A1234GY', date(1986, 12, 9)),
        'reversed_trailing_characters_2': ('091286A1234GY A', 'A1234GY', date(1986, 12, 9)),
    }

    unsuccessful = {
        'blank': '',
        'null': None,
        'invalid': 'JOHN HALLS',
        'no_date': 'A1234GY',
        'no_prisoner_number': '09/12/1986',

        'truncated_prisoner_number': 'A1234Y 09/12/1986',
        'long_prisoner_number': 'AA1234GY 09/12/1986',
        'one_digit_year': 'A1234GY 1/1/1',
        'three_digit_year': 'A1234GY 09/12/198',
        'too_many_date_digits': 'A1234GY 0931231986',
        'trailing_digits': 'A1234GY 09/12/198600000',
        'impossible_day': 'A1234GY 32/12/1986',
        'impossible_month': 'A1234GY 09/13/1986',
        'invalid_leap_day': 'A1234GY 29/02/1981',

        'trailing_characters_no_non_numeric': 'A1234GY0912198661',

        'reversed_trailing_letters': '29/02/1981 A1234GYA',
        'reversed_invalid_leap_day': '29/02/1981 A1234GY',
        'reversed_three_digit_year': '09/12/198 A1234GY',

        'reversed_trailing_characters_no_non_letter': '091286A1234GYA7',
    }

    @classmethod
    def add_methods(cls):
        today = date.today()
        cls.successful['short_year_this_century'] = (
            'A1234GY 01/02/%s' % str(today.year - 10)[-2:], 'A1234GY', date(today.year - 10, 2, 1)
        )
        cls.successful['short_year_last_century'] = (
            'A1234GY 01/02/%s' % str(today.year - 9)[-2:], 'A1234GY', date(today.year - 9 - 100, 2, 1)
        )

        for name, values in cls.successful.items():
            cls.add_successful_method(name, *values)
        for name, reference in cls.unsuccessful.items():
            cls.add_unsuccessful_method(name, reference)

    @classmethod
    def add_successful_method(cls, name, reference, prisoner_number, prisoner_dob):
        def method(self):
            parsed_number, parsed_dob = upload.parse_credit_reference(reference)
            self.assertEqual(parsed_number, prisoner_number)
            self.assertEqual(parsed_dob, prisoner_dob)

        name = 'test_%s_parses' % name
        method.__name__ = name
        setattr(cls, name, method)

    @classmethod
    def add_unsuccessful_method(cls, name, reference):
        def method(self):
            self.assertEqual(upload.parse_credit_reference(reference), None)

        name = 'test_%s_does_not_parse' % name
        method.__name__ = name
        setattr(cls, name, method)


CreditReferenceParsingTestCase.add_methods()


class ExtractPrisonerDetailsTestCase(TestCase):

    def _test_successful_extraction(self, record, prisoner_number,
                                    prisoner_dob, from_description_field):
        parsed_number, parsed_dob, parsed_field = upload.extract_prisoner_details(record)
        self.assertEqual(parsed_number, prisoner_number)
        self.assertEqual(parsed_dob, prisoner_dob)
        self.assertEqual(parsed_field, from_description_field)

    def test_extraction_from_reference_field(self):
        record = DataRecord(
            '1234566717531509960800629696666000000000008939NORTHERN DIY'
            '   E  A1234BY 09/12/86                     04036          '
            '                       '
        )
        self._test_successful_extraction(record, 'A1234BY', date(1986, 12, 9), False)

    def test_extraction_from_description_field(self):
        record = DataRecord(
            '1234566717531509960800629696666000000000008939A1234BY 09/12/86'
            '                                       04036                  '
            '               '
        )
        self._test_successful_extraction(record, 'A1234BY', date(1986, 12, 9), True)

    def test_failed_extraction(self):
        record = DataRecord(
            '1234566717531509960800629696666000000000008939XXXXXXX Z1212P86'
            '                                       04036                  '
            '               '
        )
        self.assertEqual(upload.extract_prisoner_details(record), None)


class FilenameParsingTestCase(TestCase):

    def test_correct_format_returns_correct_date(self):
        filename = 'Y01A.CARS.#D.444444.D091214'
        expected_date = date(2014, 12, 9)
        parsed_date = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_date)

    def test_correct_format_returns_correct_date_pre_2000(self):
        filename = 'Y01A.CARS.#D.444444.D091299'
        expected_date = date(1999, 12, 9)
        parsed_date = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_date)

    def test_incorrect_format_returns_none(self):
        filename = 'unrelated_file'
        parsed_date = upload.parse_filename(filename, '444444')
        self.assertEqual(None, parsed_date)

    def test_incorrect_account_code_returns_none(self):
        filename = 'Y01A.CARS.#D.555555.D091214'
        parsed_date = upload.parse_filename(filename, '444444')
        self.assertEqual(None, parsed_date)

    def test_parsing_date_from_full_path_succeeds(self):
        filename = '/random/Y01A.CARS.#D.444444.D091214'
        expected_date = date(2014, 12, 9)
        parsed_date = upload.parse_filename(filename, '444444')
        self.assertEqual(expected_date, parsed_date)


@mock.patch('mtp_transaction_uploader.upload.settings')
@mock.patch('mtp_transaction_uploader.upload.Connection')
class FileDownloadTestCase(TestCase):

    def _download_new_files(self, mock_connection_class, mock_settings, dirlist, last_date):
        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type('', (), {'st_size': 1000})()

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
        ], [new_date for new_date in new_dates])
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
        ], [new_date for new_date in new_dates])
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
        ], [new_date for new_date in new_dates])
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
            mock_connection_class, mock_settings, dirlist, date(2014, 12, 11)
        )

        self.assertEqual([
            date(2014, 12, 12),
            date(2014, 12, 13),
            date(2014, 12, 14),
        ], [new_date for new_date in new_dates])
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
            type('', (), {'st_size': 1000})(),
            type('', (), {'st_size': 1000})(),
            type('', (), {'st_size': 1000})(),
            type('', (), {'st_size': 1000})(),
            type('', (), {'st_size': 100000000})(),
            type('', (), {'st_size': 1000})(),
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
        ], [new_date for new_date in new_dates])
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
        mock_get_connection().transactions.get.return_value =\
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
        mock_connection.stat.return_value = type('', (), {'st_size': 1000})()

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
        self.assertEqual(date(2014, 12, 14), new_last_date)

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
        mock_get_connection().transactions.get.return_value =\
            {'count': 1, 'results': [{'received_at': '2014-12-115T19:09:02Z'}]}

        dirlist = []

        mock_connection = mock.MagicMock()
        mock_connection_class().__enter__.return_value = mock_connection

        mock_connection.listdir.return_value = dirlist
        mock_connection.stat.return_value = type('', (), {'st_size': 1000})()

        mock_settings.ACCOUNT_CODE = '444444'
        mock_settings.DS_NEW_FILES_DIR = '/'
        mock_os.path.join = lambda a, b: a + b

        new_last_date, new_filenames = upload.retrieve_data_services_files()

        self.assertFalse(mock_shutil.rmtree.called)

        self.assertEqual([], new_filenames)
        self.assertEqual(None, new_last_date)


def setup_settings(mock_settings, mark_transactions_as_unidentified=False):
    mock_settings.NOMS_AGENCY_ACCOUNT_NUMBER = '67175315'
    mock_settings.NOMS_AGENCY_SORT_CODE = '123456'
    mock_settings.MARK_TRANSACTIONS_AS_UNIDENTIFIED = mark_transactions_as_unidentified


class TransactionsFromFileTestCase(TestCase):
    @mock.patch('mtp_transaction_uploader.upload.settings')
    def test_get_transactions(self, mock_settings):
        setup_settings(mock_settings)

        with open('tests/data/testfile_1') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 3)

        # transaction 0 - debit
        self.assertEqual(transactions[0]['category'], 'debit')
        self.assertEqual(transactions[0]['source'], 'administrative')
        self.assertEqual(transactions[0]['amount'], 288615)
        self.assertEqual(transactions[0]['received_at'], '2004-02-05T12:00:00+00:00')
        self.assertEqual(transactions[0]['processor_type_code'], '03')

        self.assertEqual(transactions[0]['reference'], 'Payment refund    ')
        self.assertEqual(transactions[0].get('prisoner_number'), None)
        self.assertEqual(transactions[0].get('prisoner_dob'), None)

        # transaction 1 - credit
        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['source'], 'bank_transfer')
        self.assertEqual(transactions[1]['amount'], 8939)
        self.assertEqual(transactions[1]['received_at'], '2004-02-05T12:00:00+00:00')
        self.assertEqual(transactions[1]['sender_account_number'], '29696666')
        self.assertEqual(transactions[1]['sender_sort_code'], '608006')
        self.assertEqual(transactions[1]['processor_type_code'], '99')

        self.assertEqual(transactions[1]['prisoner_number'], 'A1234BY')
        self.assertEqual(transactions[1]['prisoner_dob'], '1986-12-09')

        self.assertEqual(transactions[1]['blocked'], False)
        self.assertEqual(transactions[1]['incomplete_sender_info'], False)

        # transaction 2 - credit
        self.assertEqual(transactions[2]['category'], 'credit')
        self.assertEqual(transactions[2]['source'], 'bank_transfer')
        self.assertEqual(transactions[2]['amount'], 9802)
        self.assertEqual(transactions[2]['received_at'], '2004-02-05T12:00:00+00:00')
        self.assertEqual(transactions[2]['sender_account_number'], '78990056')
        self.assertEqual(transactions[2]['sender_sort_code'], '245432')
        self.assertEqual(transactions[2]['processor_type_code'], '93')

        self.assertEqual(transactions[2]['prisoner_number'], 'B4321XZ')
        self.assertEqual(transactions[2]['prisoner_dob'], '1992-11-08')

        self.assertEqual(transactions[2]['blocked'], False)
        self.assertEqual(transactions[2]['incomplete_sender_info'], False)

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

    @mock.patch('mtp_transaction_uploader.upload.settings')
    def test_marks_incomplete_sender_information(self, mock_settings):
        setup_settings(mock_settings)

        with open('tests/data/testfile_sender_information') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 4)

        # check that account number is 0s instead of None for matching building society
        self.assertEqual(transactions[0]['category'], 'credit')
        self.assertEqual(transactions[0]['sender_account_number'], '00000000')
        self.assertFalse(transactions[0]['incomplete_sender_info'])

        # no sort code
        self.assertEqual(transactions[1]['sender_sort_code'], None)
        self.assertTrue(transactions[1]['incomplete_sender_info'])
        self.assertTrue(transactions[1]['blocked'])

        # no account number
        self.assertEqual(transactions[2]['sender_account_number'], None)
        self.assertTrue(transactions[2]['incomplete_sender_info'])
        self.assertTrue(transactions[2]['blocked'])

        # no roll number
        self.assertEqual(transactions[3]['sender_roll_number'], None)
        self.assertTrue(transactions[3]['incomplete_sender_info'])
        self.assertFalse(transactions[3]['blocked'])

    @mock.patch('mtp_transaction_uploader.upload.settings')
    def test_marks_incomplete_sender_information_for_metro_bank(self, mock_settings):
        setup_settings(mock_settings)

        with open('tests/data/testfile_metro_bank') as f:
            data_services_file = parse(f)

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 4)

        self.assertEqual(transactions[3]['sender_roll_number'], None)
        self.assertTrue(transactions[3]['incomplete_sender_info'])
        self.assertFalse(transactions[3]['blocked'])

    @mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
    def test_marks_administrative_transactions(self, mock_get_conn):
        with open('tests/data/testfile_administrative_credits') as f:
            # records are from 36th date of 2004, i.e. 2004-02-05 (see last 5 digits in each record)
            data_services_file = parse(f)

        conn = mock_get_conn()
        conn.batches.get.return_value = {
            'count': 1,
            'results': [{'id': 10}]
        }

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(transactions[0]['category'], 'debit')
        self.assertEqual(transactions[0]['source'], 'administrative')
        self.assertTrue('batch' not in transactions[0])
        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['source'], 'administrative')
        self.assertTrue('batch' not in transactions[1])
        self.assertEqual(transactions[2]['category'], 'credit')
        self.assertEqual(transactions[2]['source'], 'administrative')
        self.assertEqual(transactions[2]['batch'], 10)

        # settlement is for ?-09-22 (assumed to be nearest date in the past)
        conn.batches.get.assert_called_with(date='2003-09-22')

    @mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
    def testfile_settlement_credits(self, mock_get_conn):
        with open('tests/data/testfile_settlement_credits') as f:
            # records are from 36th date of 2004, i.e. 2004-02-05 (see last 5 digits in each record)
            data_services_file = parse(f)

        conn = mock_get_conn()
        conn.batches.get.return_value = {
            'count': 1,
            'results': [{'id': 10}]
        }

        transactions = upload.get_transactions_from_file(data_services_file)

        # test file has 3 settlement transactions which are all "administrative" credits
        self.assertEqual(len(transactions), 3)
        self.assertTrue(all(
            transaction['category'] == 'credit' and transaction['source'] == 'administrative'
            for transaction in transactions
        ))

        # one settlement does not have a date that can be parsed so is not matched to a batch
        self.assertNotIn('batch', transactions[0])

        # two settlements have a date that can be parsed and matched to a batch
        self.assertEqual(len(conn.batches.get.call_args_list), 2)
        # first settlement is for ?-09-22 (assumed to be nearest date in the past)
        self.assertEqual(transactions[1]['batch'], 10)
        self.assertEqual(
            conn.batches.get.call_args_list[0],
            ((), {'date': '2003-09-22'})
        )
        # second settlement is for ?-?-21 (assumed to be nearest date in the past)
        self.assertEqual(transactions[2]['batch'], 10)
        self.assertEqual(
            conn.batches.get.call_args_list[1],
            ((), {'date': '2004-01-21'})
        )

    @mock.patch('mtp_transaction_uploader.upload.settings')
    def test_marking_all_credit_transactions_as_unidentified(self, mock_settings):
        setup_settings(mock_settings, mark_transactions_as_unidentified=True)

        with open('tests/data/testfile_1') as f:
            data_services_file = parse(f)
        transactions = upload.get_transactions_from_file(data_services_file)
        self.assertEqual(len(transactions), 3)

        # transaction 0 - debit
        self.assertEqual(transactions[0]['category'], 'debit')
        self.assertEqual(transactions[0]['source'], 'administrative')

        # transaction 1 - credit
        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['source'], 'bank_transfer')
        self.assertEqual(transactions[1]['sender_account_number'], '29696666')
        self.assertEqual(transactions[1]['sender_sort_code'], '608006')
        self.assertEqual(transactions[1]['prisoner_number'], 'A1234BY')
        self.assertEqual(transactions[1]['prisoner_dob'], '1986-12-09')
        self.assertEqual(transactions[1]['blocked'], True)
        self.assertEqual(transactions[1]['incomplete_sender_info'], True)

        # transaction 2 - credit
        self.assertEqual(transactions[2]['category'], 'credit')
        self.assertEqual(transactions[2]['source'], 'bank_transfer')
        self.assertEqual(transactions[2]['sender_account_number'], '78990056')
        self.assertEqual(transactions[2]['sender_sort_code'], '245432')
        self.assertEqual(transactions[2]['prisoner_number'], 'B4321XZ')
        self.assertEqual(transactions[2]['prisoner_dob'], '1992-11-08')
        self.assertEqual(transactions[2]['blocked'], True)
        self.assertEqual(transactions[2]['incomplete_sender_info'], True)

    @mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
    @mock.patch('mtp_transaction_uploader.upload.settings')
    def test_not_marking_administrative_credits_as_unidentified(self, mock_settings, mock_get_conn):
        setup_settings(mock_settings, mark_transactions_as_unidentified=True)

        with open('tests/data/testfile_administrative_credits') as f:
            data_services_file = parse(f)
        conn = mock_get_conn()
        conn.batches.get.return_value = {
            'count': 1,
            'results': [{'id': 10}]
        }
        transactions = upload.get_transactions_from_file(data_services_file)
        self.assertEqual(len(transactions), 3)

        self.assertEqual(transactions[0]['category'], 'debit')
        self.assertEqual(transactions[0]['source'], 'administrative')
        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['source'], 'administrative')
        self.assertEqual(transactions[1]['blocked'], False)
        self.assertEqual(transactions[1]['incomplete_sender_info'], False)
        self.assertEqual(transactions[2]['category'], 'credit')
        self.assertEqual(transactions[2]['source'], 'administrative')
        self.assertEqual(transactions[2]['blocked'], False)
        self.assertEqual(transactions[2]['incomplete_sender_info'], False)

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
            'Errors: %s',
            {
                'account 0': [
                    'Monetary total of debit items does not match expected: counted 288615, expected 288610',
                    'Monetary total of credit items does not match expected: counted 18741, expected 18732',
                ]
            }
        )

        self.assertEqual(transactions, None)

    @mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
    def test_excludes_records_from_other_accounts(self, mock_get_conn):
        with open('tests/data/testfile_multiple_accounts') as f:
            data_services_file = parse(f)

        conn = mock_get_conn()
        conn.batches.get.return_value = {
            'count': 1,
            'results': [{'id': 10}]
        }

        transactions = upload.get_transactions_from_file(data_services_file)

        self.assertEqual(len(transactions), 2)
        # transaction 0 - debit
        self.assertEqual(transactions[0]['category'], 'debit')
        self.assertEqual(transactions[0]['source'], 'administrative')
        self.assertEqual(transactions[0]['amount'], 288615)
        self.assertEqual(transactions[0]['received_at'], '2004-02-05T12:00:00+00:00')
        # transaction 1 - credit (actually credit record 2 but credit 1 is filtered out)
        self.assertEqual(transactions[1]['category'], 'credit')
        self.assertEqual(transactions[1]['source'], 'bank_transfer')
        self.assertEqual(transactions[1]['amount'], 9802)
        self.assertEqual(transactions[1]['received_at'], '2004-02-07T12:00:00+00:00')


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


class SettlementDateParsingTestCase(TestCase):
    def test_parsable_settlement_2_digit_dates(self):
        values = [
            ('31', date(2021, 1, 31), date(2021, 1, 31)),
            ('30', date(2021, 1, 31), date(2021, 1, 30)),
            ('29', date(2021, 1, 31), date(2021, 1, 29)),
            ('28', date(2021, 1, 31), date(2021, 1, 28)),
            ('01', date(2021, 1, 31), date(2021, 1, 1)),

            ('27', date(2021, 2, 28), date(2021, 2, 27)),
            ('27', date(2021, 2, 27), date(2021, 2, 27)),
            ('27', date(2021, 2, 26), date(2021, 1, 27)),
            ('27', date(2021, 2, 25), date(2021, 1, 27)),

            ('02', date(2021, 1, 2), date(2021, 1, 2)),
            ('01', date(2021, 1, 2), date(2021, 1, 1)),
            ('31', date(2021, 1, 2), date(2020, 12, 31)),
            ('30', date(2021, 1, 2), date(2020, 12, 30)),
        ]
        for date_str, relative_date, expected_date in values:
            resulting_date = upload.parse_2_digit_date(date_str, relative_date)
            self.assertEqual(
                resulting_date, expected_date,
                msg=f'{date_str} relative to {relative_date} should parse to {expected_date}'
            )

    def test_parsable_settlement_4_digit_dates(self):
        values = [
            ('3101', date(2021, 1, 31), date(2021, 1, 31)),
            ('3001', date(2021, 1, 31), date(2021, 1, 30)),
            ('0101', date(2021, 1, 31), date(2021, 1, 1)),
            ('0202', date(2021, 1, 31), date(2020, 2, 2)),
            ('0202', date(2021, 6, 30), date(2021, 2, 2)),
            ('3112', date(2021, 6, 30), date(2020, 12, 31)),
        ]
        for date_str, relative_date, expected_date in values:
            resulting_date = upload.parse_4_digit_date(date_str, relative_date)
            self.assertEqual(
                resulting_date, expected_date,
                msg=f'{date_str} relative to {relative_date} should parse to {expected_date}'
            )

    def test_unparsable_settlement_2_digit_dates(self):
        values = [
            # overflows day of previous month
            ('30', date(2021, 3, 1)),
            ('31', date(2021, 5, 1)),
            # not a date
            ('33', date(2021, 2, 1)),
            ('xx', date(2021, 2, 1)),
        ]
        for date_str, relative_date in values:
            with self.assertRaises(ValueError, msg=f'{date_str} relative to {relative_date} should not parse'):
                upload.parse_2_digit_date(date_str, relative_date)

    def test_unparsable_settlement_4_digit_dates(self):
        values = [
            # overflows day of month
            ('3002', date(2021, 3, 1)),
            ('3104', date(2021, 5, 1)),
            # not a date
            ('3301', date(2021, 2, 1)),
            ('ddmm', date(2021, 2, 1)),
        ]
        for date_str, relative_date in values:
            with self.assertRaises(ValueError, msg=f'{date_str} relative to {relative_date} should not parse'):
                upload.parse_4_digit_date(date_str, relative_date)


@mock.patch('mtp_transaction_uploader.upload.get_authenticated_connection')
class GetMatchingBatchIdForSettlementTestCase(TestCase):

    def _test_successful_match(self, mock_get_conn, record, expected_date):
        conn = mock_get_conn()
        conn.batches.get.return_value = {
            'count': 1,
            'results': [{'id': 10}]
        }
        batch_id = upload.get_matching_batch_id_for_settlement(record)

        self.assertEqual(batch_id, 10)
        conn.batches.get.assert_called_with(date=expected_date.isoformat())

    def test_get_matching_batch(self, mock_get_conn):
        # record is for 36th date of 2004, i.e. 2004-02-05 (last 5 digits in record)
        # settlement is for ?-01-01 (assumed to be nearest date in the past)
        expected_date = date(2004, 1, 1)
        record = DataRecord(
            '1234566717531509324543278990056000000000009802'
            'TT- GGGGGGGG -0101WORLDPAY                    '
            '         04036                      '
        )
        self._test_successful_match(mock_get_conn, record, expected_date)

    def test_get_matching_batch_for_2_digit_date(self, mock_get_conn):
        # record is for 36th date of 2004, i.e. 2004-02-05 (last 5 digits in record)
        # settlement is for ?-?-01 (assumed to be nearest date in the past)
        expected_date = date(2004, 2, 1)
        record = DataRecord(
            '1234566717531509324543278990056000000000009802'
            'TT- GGGGGGGG -01  WORLDPAY                    '
            '         04036                      '
        )
        self._test_successful_match(mock_get_conn, record, expected_date)

    def test_get_matching_batch_from_previous_year(self, mock_get_conn):
        # record is for 36th date of 2004, i.e. 2004-02-05 (last 5 digits in record)
        # settlement is for ?-12-31 (assumed to be nearest date in the past)
        expected_date = date(2003, 12, 31)
        record = DataRecord(
            '1234566717531509324543278990056000000000009802'
            'TT- GGGGGGGG -3112WORLDPAY                    '
            '         04036                      '
        )
        self._test_successful_match(mock_get_conn, record, expected_date)

    def test_get_matching_batch_from_previous_year_for_2_digit_date(self, mock_get_conn):
        # record is for 3rd date of 2004, i.e. 2004-01-03 (last 5 digits in record)
        # settlement is for ?-?-31 (assumed to be nearest date in the past)
        expected_date = date(2003, 12, 31)
        record = DataRecord(
            '1234566717531509324543278990056000000000009802'
            'TT- GGGGGGGG -31  WORLDPAY                    '
            '         04003                      '
        )
        self._test_successful_match(mock_get_conn, record, expected_date)

    def test_invalid_date_is_ignored(self, mock_get_conn):
        # record is for 36th date of 2004, i.e. 2004-02-05 (last 5 digits in record)
        # but settlement date cannot be parsed
        record = DataRecord(
            '1234566717531509324543278990056000000000009802'
            'TT- GGGGGGGG -9934WORLDPAY                    '
            '         04036                      '
        )

        batch_id = upload.get_matching_batch_id_for_settlement(record)
        self.assertIsNone(batch_id)
