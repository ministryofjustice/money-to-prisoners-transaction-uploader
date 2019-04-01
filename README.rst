MTP Transaction Uploader
========================

Usage
-----
The following environment variables determine how the uploader works:

.. code-block::

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

Testing
-------

.. code-block::

    ./run.py test

Deploying
---------

This is handled by `money-to-prisoners-deploy`_.

.. _money-to-prisoners-deploy: https://github.com/ministryofjustice/money-to-prisoners-deploy/
