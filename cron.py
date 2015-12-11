import os
import re
import sys

from mtp_transaction_uploader import settings
from mtp_transaction_uploader.upload import main

if __name__ == '__main__':
    # ensure all required parameters are set
    re_env_name = re.compile(r'^[A-Z_]+$')
    missing_params = []
    for param in dir(settings):
        if not re_env_name.match(param):
            continue
        if not getattr(settings, param):
            missing_params.append(param)
    if missing_params:
        print('Missing environment variables: ' +
              ', '.join(missing_params), file=sys.stderr)
        sys.exit(1)

    # sentry exception handling
    client = None
    if os.environ.get('SENTRY_DSN'):
        from raven import Client

        client = Client(
            dsn=os.environ['SENTRY_DSN'],
            release=os.environ.get('APP_GIT_COMMIT', 'unknown'),
        )

    try:
        # run the transaction uploader
        main()
    except:
        if client:
            client.captureException()
