from types import SimpleNamespace
from unittest import mock, TestCase

import main


class RequiredSFTPConfigurationTests(TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            UPLOADER_DISABLED='', SFTP_HOST='bank.example.test', SFTP_USER='uploader',
            SFTP_PRIVATE_KEY='/configured/private-key', SFTP_KNOWN_HOSTS='/configured/known_hosts',
            ACCOUNT_CODE='444444', API_URL='https://api.example.test', API_CLIENT_ID='client',
            API_CLIENT_SECRET='secret', API_USERNAME='user', API_PASSWORD='password',
        )

    def test_missing_known_hosts_stops_before_running_the_uploader(self):
        self.settings.SFTP_KNOWN_HOSTS = ''
        with mock.patch.object(main, 'settings', self.settings):
            with mock.patch.object(main, 'setup_monitoring', return_value=(mock.Mock(), False)):
                with mock.patch.object(main, 'transaction_uploader') as run:
                    with self.assertRaises(SystemExit) as error:
                        main.main()
                    self.assertEqual(error.exception.code, 1)
                    run.assert_not_called()

    def test_disabled_uploader_does_not_need_bank_configuration(self):
        self.settings.UPLOADER_DISABLED = 'True'
        self.settings.SFTP_KNOWN_HOSTS = ''
        with mock.patch.object(main, 'settings', self.settings):
            with mock.patch.object(main, 'setup_monitoring', return_value=(mock.Mock(), False)):
                with mock.patch.object(main, 'transaction_uploader') as run:
                    with self.assertRaises(SystemExit) as error:
                        main.main()
                    self.assertEqual(error.exception.code, 0)
                    run.assert_not_called()
