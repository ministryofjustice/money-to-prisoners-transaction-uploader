import logging
import os
import socket
from unittest import mock, TestCase, skipUnless
from urllib.parse import urlparse

from mtp_transaction_uploader import upload, settings

logger = logging.getLogger('mtp')


@skipUnless('RUN_FUNCTIONAL_TESTS' in os.environ, 'functional tests are disabled')
class FileUploadFunctionalTestCase(TestCase):

    def setUp(self):
        self.load_test_data()

    def load_test_data(self):
        """
        Sends a command to the API controller port to reload test data
        (basically just to clear balances)
        """
        logger.info('Reloading test data')
        try:
            with socket.socket() as sock:
                sock.connect((
                    urlparse(settings.API_URL).netloc.split(':')[0],
                    int(os.environ.get('CONTROLLER_PORT', 8800))
                ))
                sock.sendall(b'load_test_data')
                response = sock.recv(1024).strip()
            if response != b'done':
                logger.error('Test data not reloaded!')
        except OSError:
            logger.exception('Error communicating with test server controller socket')

    def fail_on_error_log(self, msg, *args, **kwargs):
        if args:
            self.fail(msg % tuple(args))
        else:
            self.fail(msg)

    @mock.patch('mtp_transaction_uploader.upload.logger')
    def test_upload(self, mock_logger):
        mock_logger.error = self.fail_on_error_log

        files = ['./tests/data/Y01A.CARS.#D.444444.D050214']
        upload.upload_transactions_from_files(files)
