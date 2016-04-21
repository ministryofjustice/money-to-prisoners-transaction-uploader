import logging
import logging.config
import os
import re
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
                'formatter': 'simple' if settings.ENV == 'local' else 'elk',
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
        from raven import Client

        sentry = Client(
            dsn=os.environ['SENTRY_DSN'],
            release=os.environ.get('APP_GIT_COMMIT', 'unknown'),
        )
        logging_conf['handlers']['sentry'] = {
            'level': 'ERROR',
            'class': 'raven.handlers.logging.SentryHandler',
            'client': sentry,
        }
        logging_conf['root']['handlers'].append('sentry')
        logging_conf['loggers']['mtp']['handlers'].append('sentry')
    logging.config.dictConfig(logging_conf)
    logger = logging.getLogger('mtp')

    return logger, sentry


def main():
    logger, sentry = setup_monitoring()

    if settings.UPLOADER_DISABLED:
        logger.info('Transaction uploader is disabled')
        sys.exit(0)

    # ensure all required parameters are set
    re_env_name = re.compile(r'^[A-Z_]+$')
    missing_params = []
    for param in dir(settings):
        if not re_env_name.match(param):
            continue
        if not getattr(settings, param):
            missing_params.append(param)
    if missing_params:
        logger.error('Missing environment variables: ' +
                     ', '.join(missing_params))
        sys.exit(1)

    try:
        # run the transaction uploader
        transaction_uploader()
    except:
        if sentry:
            sentry.captureException()
        else:
            logger.exception('Unhandled error')
        sys.exit(2)


if __name__ == '__main__':
    main()
