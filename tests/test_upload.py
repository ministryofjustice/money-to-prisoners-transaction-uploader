import unittest
from datetime import datetime

from mtp_transaction_uploader.upload import parse_reference


class ReferenceParsingTestCase(unittest.TestCase):

    def _test_successful_parse(self, reference, prisoner_number, prisoner_dob):
        parsed_number, parsed_dob = parse_reference(reference)
        self.assertEqual(parsed_number, prisoner_number)
        self.assertEqual(parsed_dob, prisoner_dob)

    def test_correct_format_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/86', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_no_space_parses(self):
        self._test_successful_parse(
            'A1234GY09/12/86', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_arbitrary_divider_parses(self):
        self._test_successful_parse(
            'A1234GY:::09/12/1986', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_hyphenated_date_parses(self):
        self._test_successful_parse(
            'A1234GY 09-12-86', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_non_separated_date_parses(self):
        self._test_successful_parse(
            'A1234GY 091286', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_non_zero_padded_date_parses(self):
        self._test_successful_parse(
            'A1234GY 9/6/86', 'A1234GY', datetime(1986, 6, 9)
        )

    def test_four_digit_year_parses(self):
        self._test_successful_parse(
            'A1234GY 09/12/1986', 'A1234GY', datetime(1986, 12, 9)
        )

    def test_invalid_prisoner_number_does_not_parse(self):
        self.assertEqual(parse_reference('A1234Y 09/12/1986'), None)

    def test_invalid_year_does_not_parse(self):
        self.assertEqual(parse_reference('A1234GY 1/1/1'), None)
