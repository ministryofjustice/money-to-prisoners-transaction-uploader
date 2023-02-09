# Transaction Uploader – Prisoner Money

Reads bank account to facilitate reconciliation.
Part of the [Prisoner Money suite of apps](https://github.com/ministryofjustice/money-to-prisoners).

This app does not have a web interface. It’s run as a cron-like job.

## Requirements

- Unix-like platform with Python 3.10

## Usage

It’s recommended that you use a python virtual environment to isolate each application.

The simplest way to do this is using:

```shell
python3 -m venv venv    # creates a virtual environment for dependencies; only needed the first time
. venv/bin/activate     # activates the virtual environment; needed every time you use this app
```

Some build tasks expect the active virtual environment to be at `/venv/`, but should generally work regardless of
its location.

You can copy `mtp_transaction_uploader/local.py.sample` to `local.py` to overlay local settings that won’t be committed,
but it’s not required for a standard setup.

The following environment variables determine how the uploader works:

    SFTP_HOST - host to download data services files from
    SFTP_USER - sftp username
    SFTP_PRIVATE_KEY - private key for sftp user
    SFTP_DIR - directory on sftp host where files can be found

    API_USERNAME - username for API access
    API_PASSWORD - password for API access

    API_CLIENT_ID - API client ID
    API_CLIENT_SECRET - API client secret
    API_URL - base URL of API

    DS_LAST_DATE_FILE - path of file in which to store last date processed
    DS_NEW_FILES_DIR - path of directory in which to store downloaded files

## Developing

[![CircleCI](https://circleci.com/gh/ministryofjustice/money-to-prisoners-transaction-uploader.svg?style=svg)](https://circleci.com/gh/ministryofjustice/money-to-prisoners-transaction-uploader)

Run tests with `./run.py test`.

All build/development actions can be listed with `./run.py --verbosity 2 help`.

Deployment is handled by [money-to-prisoners-deploy](https://github.com/ministryofjustice/money-to-prisoners-deploy/).
