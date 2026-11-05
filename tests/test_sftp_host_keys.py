from contextlib import contextmanager
from datetime import date
import io
from pathlib import Path
import socket
import stat
import tempfile
import threading
from unittest import mock, TestCase
import warnings

import paramiko
from pysftp import Connection, HostKeysException

from mtp_transaction_uploader import upload


FILENAME = 'Y01A.CARS.#D.444444.D091214'


class BankServer(paramiko.ServerInterface):
    def __init__(self, user_key):
        self.user_key = user_key
        self.authentication_attempted = False

    def check_auth_publickey(self, username, key):
        self.authentication_attempted = True
        if username == 'uploader' and key == self.user_key:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'publickey'

    def check_channel_request(self, kind, channel_id):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


class BankFiles(paramiko.SFTPServerInterface):
    contents = b'synthetic bank statement\n'

    def stat(self, path):
        attrs = paramiko.SFTPAttributes()
        if path in ('.', '/', '/incoming', 'incoming'):
            attrs.st_mode = stat.S_IFDIR | 0o755
        elif path in (FILENAME, '/incoming/' + FILENAME):
            attrs.st_mode = stat.S_IFREG | 0o644
            attrs.st_size = len(self.contents)
        else:
            return paramiko.SFTP_NO_SUCH_FILE
        return attrs

    def list_folder(self, path):
        attrs = self.stat(FILENAME)
        attrs.filename = FILENAME
        return [attrs]

    def open(self, path, flags, attr):
        if path != '/incoming/' + FILENAME:
            return paramiko.SFTP_NO_SUCH_FILE
        handle = paramiko.SFTPHandle(flags)
        handle.readfile = io.BytesIO(self.contents)
        return handle


@contextmanager
def bank_server(host_key, user_key):
    server = BankServer(user_key)
    stopped = threading.Event()
    errors = []
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(5)
        port = listener.getsockname()[1]

        def serve():
            try:
                connection, _ = listener.accept()
                with paramiko.Transport(connection) as transport:
                    transport.add_server_key(host_key)
                    transport.set_subsystem_handler('sftp', paramiko.SFTPServer, BankFiles)
                    transport.start_server(server=server)
                    stopped.wait(10)
            except EOFError:
                pass  # The client closes immediately when it rejects the server key.
            except (OSError, paramiko.SSHException) as error:
                errors.append(error)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            yield port, server
        finally:
            stopped.set()
            thread.join(timeout=6)
            if thread.is_alive():
                raise AssertionError('Local SFTP server did not stop')
        if errors:
            raise AssertionError(f'Local SFTP server failed: {errors}')


class SFTPHostKeyTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank_key = paramiko.RSAKey.generate(2048)
        cls.attacker_key = paramiko.RSAKey.generate(2048)
        cls.user_key = paramiko.RSAKey.generate(2048)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.known_hosts = self.root / 'known_hosts'
        self.private_key = self.root / 'id_rsa'
        self.user_key.write_private_key_file(str(self.private_key))
        self.write_pin(self.bank_key)
        patcher = mock.patch.multiple(
            upload.settings, SFTP_HOST='127.0.0.1', SFTP_USER='uploader',
            SFTP_PRIVATE_KEY=str(self.private_key), SFTP_DIR='/incoming',
            SFTP_KNOWN_HOSTS=str(self.known_hosts), ACCOUNT_CODE='444444',
            DS_NEW_FILES_DIR=str(self.root), create=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_pin(self, key, hostname='127.0.0.1'):
        self.known_hosts.write_text(f'{hostname} {key.get_name()} {key.get_base64()}\n')

    def connect_to_local_server(self, port):
        def connect(host, **kwargs):
            return Connection(host, port=port, **kwargs)
        return mock.patch.object(upload, 'Connection', side_effect=connect)

    def test_download_succeeds_with_the_configured_bank_key(self):
        with bank_server(self.bank_key, self.user_key) as (port, server):
            with self.connect_to_local_server(port):
                dates, filenames = upload.download_new_files(None)
            self.assertTrue(server.authentication_attempted)
        self.assertEqual(dates, [date(2014, 12, 9)])
        self.assertEqual(filenames, [str(self.root / FILENAME)])
        self.assertEqual((self.root / FILENAME).read_bytes(), BankFiles.contents)

    def test_hashed_hostname_pin_still_allows_the_download(self):
        self.write_pin(self.bank_key, hostname=paramiko.HostKeys.hash_host('127.0.0.1'))
        with bank_server(self.bank_key, self.user_key) as (port, server):
            with self.connect_to_local_server(port):
                upload.download_new_files(None)
            self.assertTrue(server.authentication_attempted)
        self.assertEqual((self.root / FILENAME).read_bytes(), BankFiles.contents)

    def test_verified_replacement_pin_allows_the_replacement_key(self):
        self.write_pin(self.attacker_key)
        with bank_server(self.attacker_key, self.user_key) as (port, server):
            with self.connect_to_local_server(port):
                upload.download_new_files(None)
            self.assertTrue(server.authentication_attempted)
        self.assertEqual((self.root / FILENAME).read_bytes(), BankFiles.contents)

    def test_changed_server_key_is_rejected_before_authentication(self):
        with bank_server(self.attacker_key, self.user_key) as (port, server):
            with self.connect_to_local_server(port):
                with self.assertRaisesRegex(paramiko.SSHException, 'Bad host key'):
                    upload.download_new_files(None)
            self.assertFalse(server.authentication_attempted)
        self.assertFalse((self.root / FILENAME).exists())

    def test_changed_pin_rejects_the_old_server_key(self):
        self.write_pin(self.attacker_key)
        with bank_server(self.bank_key, self.user_key) as (port, server):
            with self.connect_to_local_server(port):
                with self.assertRaisesRegex(paramiko.SSHException, 'Bad host key'):
                    upload.download_new_files(None)
            self.assertFalse(server.authentication_attempted)

    def test_invalid_trust_configuration_fails_before_connecting(self):
        for contents in ('', '# no approved key\n', 'not a host key\n', '127.0.0.1 ssh-rsa invalid-base64\n'):
            with self.subTest(contents=contents):
                self.known_hosts.write_text(contents)
                with mock.patch.object(upload, 'Connection') as connect:
                    errors = (HostKeysException, paramiko.SSHException, paramiko.hostkeys.InvalidHostKey)
                    with self.assertRaises(errors):
                        upload.download_new_files(None)
                    connect.assert_not_called()

    def test_other_host_entry_is_not_trusted_for_the_bank(self):
        self.write_pin(self.bank_key, hostname='other.example.test')
        with mock.patch.object(upload, 'Connection') as connect:
            with self.assertRaises(paramiko.SSHException):
                upload.download_new_files(None)
            connect.assert_not_called()

    def test_missing_trust_file_fails_before_connecting(self):
        self.known_hosts.unlink()
        with warnings.catch_warnings(), mock.patch.object(upload, 'Connection') as connect:
            warnings.simplefilter('ignore', UserWarning)
            with self.assertRaises(paramiko.SSHException):
                upload.download_new_files(None)
            connect.assert_not_called()

    def test_unreadable_trust_file_fails_before_connecting(self):
        with mock.patch('paramiko.hostkeys.open', side_effect=PermissionError, create=True):
            with warnings.catch_warnings(), mock.patch.object(upload, 'Connection') as connect:
                warnings.simplefilter('ignore', UserWarning)
                with self.assertRaises(paramiko.SSHException):
                    upload.download_new_files(None)
                connect.assert_not_called()

    def test_no_configured_trust_file_does_not_fall_back_to_user_defaults(self):
        for value in ('', None):
            with self.subTest(value=value), mock.patch.object(upload.settings, 'SFTP_KNOWN_HOSTS', value):
                with mock.patch.object(upload, 'Connection') as connect:
                    with self.assertRaisesRegex(ValueError, 'SFTP_KNOWN_HOSTS'):
                        upload.download_new_files(None)
                    connect.assert_not_called()
