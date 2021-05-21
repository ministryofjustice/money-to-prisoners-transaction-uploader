import logging
import logging.config
import os
import sys

from mtp_transaction_uploader import settings
from mtp_transaction_uploader.upload import main as transaction_uploader


def setup_monitoring():
    """
    Setup logging and exception reporting
    """
    logging_conf = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'simple': {
                'format': '%(asctime)s [%(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S',
            },
            'elk': {
                '()': 'mtp_common.logging.ELKFormatter'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple' if settings.ENVIRONMENT == 'local' else 'elk',
            },
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console'],
        },
        'loggers': {
            'mtp': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
        },
    }
    sentry = None
    if os.environ.get('SENTRY_DSN'):
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=settings.APP_GIT_COMMIT,
            send_default_pii=False,
            traces_sample_rate=1.0,
        )
    logging.config.dictConfig(logging_conf)
    logger = logging.getLogger('mtp')

    return logger, sentry


def main():
    logger, sentry = setup_monitoring()

    if settings.UPLOADER_DISABLED:
        logger.info('Transaction uploader is disabled')
        sys.exit(0)

    # ensure all required parameters are set
    missing_params = []
    required_params = {'SFTP_HOST', 'SFTP_USER', 'SFTP_PRIVATE_KEY', 'ACCOUNT_CODE',
                       'API_URL', 'API_CLIENT_ID', 'API_CLIENT_SECRET',
                       'API_USERNAME', 'API_PASSWORD'}
    for param in dir(settings):
        if param in required_params and not getattr(settings, param):
            missing_params.append(param)
    if missing_params:
        logger.error('Missing environment variables: ' +
                     ', '.join(missing_params))
        sys.exit(1)

    try:
        # run the transaction uploader
        transaction_uploader()
    except:  # noqa
        if sentry:
            sentry.captureException()
        else:
            logger.exception('Unhandled error')
        sys.exit(2)


if __name__ == '__main__':
    main()
