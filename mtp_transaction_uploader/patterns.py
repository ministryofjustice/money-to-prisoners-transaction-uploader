import re

from . import settings


_PRISONER_PATTERNS = {
    'number': """
        (?P<number>[A-Z][0-9]{4}[A-Z]{2})  # match prisoner number
    """,
    'date_of_birth': """
        (?P<day>[0-9]{1,2})          # match 1 or 2 digit day of month
        [^0-9]*                      # skip until next digit
        (?P<month>[0-9]{1,2})        # match 1 or 2 digit month
        [^0-9]*                      # skip until next digit
        (?P<year>[0-9]{4}|[0-9]{2})  # match 4 or 2 digit year
    """
}
CREDIT_REF_PATTERN = re.compile("""
    ^
    [^A-Z]*              # skip until first letter
    %(number)s
    [^0-9A-Z]*           # skip until dob, forbid trailing letters as they can be typos
    %(date_of_birth)s
    ([^0-9].*)?          # trailing characters are allowed, but first must not be numeric
    $
""" % _PRISONER_PATTERNS, re.X | re.I)
CREDIT_REF_PATTERN_REVERSED = re.compile("""
    ^
    [^0-9]*              # skip until first digit
    %(date_of_birth)s
    [^0-9A-Z]*           # skip until prisoner number, forbid trailing digits as they can be typos
    %(number)s
    ([^A-Z].*)?          # trailing characters are allowed, but first must not be a letter
    $
""" % _PRISONER_PATTERNS, re.X | re.I)

FILE_PATTERN_STR = (
    """
    Y01A\\.CARS\\.\\#D\\.         # static file format
    %(code)s\\.                   # our unique account code
    D(?P<date>[0-9]{6})           # date that file was generated (ddmmyy)
    """
)


NOMS_ACCOUNT_NUMBER_PATTERN = re.compile(settings.NOMS_AGENCY_ACCOUNT_NUMBER)
NOMS_SORT_CODE_PATTERN = re.compile(settings.NOMS_AGENCY_SORT_CODE)
WORLDPAY_SETTLEMENT_REFERENCE_PATTERN = re.compile(settings.WORLDPAY_SETTLEMENT_REFERENCE)


class PaymentIdentifier:

    def __init__(self, account_number, sort_code, sender_name, reference):
        self.account_number = account_number
        self.sort_code = sort_code
        self.sender_name = sender_name
        self.reference = reference

    def _field_matches(self, field, value):
        if field is None:
            return True
        value = value.strip() if value else ''
        return field.match(value) is not None

    def matches(self, account_number, sort_code, sender_name, reference):
        return (
            self._field_matches(self.account_number, account_number) and
            self._field_matches(self.sort_code, sort_code) and
            self._field_matches(self.sender_name, sender_name) and
            self._field_matches(self.reference, reference)
        )


ADMINISTRATIVE_IDENTIFIERS = [
    PaymentIdentifier(
        NOMS_ACCOUNT_NUMBER_PATTERN,
        NOMS_SORT_CODE_PATTERN,
        None,
        None
    ),
    PaymentIdentifier(
        None,
        None,
        WORLDPAY_SETTLEMENT_REFERENCE_PATTERN,
        None
    ),
]
