# Transaction Uploader – Prisoner Money

Reads bank account files via SFTP to facilitate reconciliation by uploading transactions to the API.
Part of the [Prisoner Money suite of apps](https://github.com/ministryofjustice/money-to-prisoners).

This app does not have a web interface. It is run as a cron-like job.
An overview of this application is available [here](OVERVIEW.md).
## Requirements

- Unix-like platform
- Python 3.12+
- SFTP access to bank transaction files

## Setup

It is recommended that you use a Python virtual environment to isolate each application.

```shell
python3 -m venv venv    # creates a virtual environment for dependencies; only needed the first time
. venv/bin/activate     # activates the virtual environment; needed every time you use this app
```

Install dependencies:

```shell
pip install -r requirements/base.txt
```

For development, also install:

```shell
pip install -r requirements/dev.txt
```

Alternatively, using the provided runner:

```shell
./run.py
```

This will automatically pre-install `mtp-common` and base requirements.

## Configuration

You can copy `mtp_transaction_uploader/local.py.sample` to `mtp_transaction_uploader/local.py` to overlay local settings that won't be committed.

### Environment Variables

The following environment variables determine how the uploader works:

#### SFTP Settings
- `SFTP_HOST`: Host to download data services files from.
- `SFTP_USER`: SFTP username.
- `SFTP_PRIVATE_KEY`: Private key for SFTP user (default: `~/.ssh/id_rsa`).
- `SFTP_DIR`: Directory on SFTP host where files can be found.

#### API Settings
- `API_URL`: Base URL of API (default: `http://localhost:8000`).
- `API_CLIENT_ID`: API client ID.
- `API_CLIENT_SECRET`: API client secret.
- `API_USERNAME`: Username for API access.
- `API_PASSWORD`: Password for API access.

#### Application Settings
- `ACCOUNT_CODE`: Account code to filter transactions (default: `444444`).
- `DS_NEW_FILES_DIR`: Path of directory in which to store downloaded files (default: `/tmp/ds_new_files`).
- `UPLOADER_DISABLED`: Set to any non-empty value to disable the uploader.
- `ENV`: Environment name (default: `local`).
- `SENTRY_DSN`: Sentry DSN for error reporting.

## Usage

To run the uploader once:

```shell
python main.py
```

## Development

### Running Tests

Run tests with the runner:

```shell
./run.py test
```

Or directly with pytest:

```shell
pytest
```

### Build Tasks

All build/development actions can be listed with:

```shell
./run.py --verbosity 2 help
```

Common tasks:
- `./run.py build`: Builds necessary assets (precompiles Python code).
- `./run.py clean`: Deletes build outputs.
- `./run.py clean --delete-dependencies`: Deletes build outputs and the `venv` directory.

### Project Structure

- `main.py`: Entry point for the application.
- `run.py`: Development task runner.
- `mtp_transaction_uploader/`: Core application package.
    - `upload.py`: Main upload logic.
    - `settings.py`: Application configuration.
    - `api_client.py`: Client for interacting with the MTP API.
- `tests/`: Test suite.
- `requirements/`: Dependency files.

## Deployment

Deployment is handled by [money-to-prisoners-deploy](https://github.com/ministryofjustice/money-to-prisoners-deploy/).

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
