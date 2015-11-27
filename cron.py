import re
import sys

from mtp_transaction_uploader import settings
from mtp_transaction_uploader.upload import main

if __name__ == '__main__':
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

    main()
