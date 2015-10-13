import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='money-to-prisoners-transaction-uploader',
    version='0.1',
    packages=[
        'mtp_transaction_uploader',
    ],
    entry_points={
        'console_scripts': ['upload-transactions = mtp_transaction_uploader.upload:main']
    },
    include_package_data=True,
    license='BSD License',
    description='Retrieve direct services file, process, and upload transactions',
    long_description=README,
    dependency_links=[
        'https://github.com/ministryofjustice/bankline-direct-parser/tarball/data-services-parser#egg=bankline-direct-parser'
    ],
    install_requires=[
        'requests-oauthlib==0.5.0',
        'slumber==0.7.1',
        'pysftp==0.2.8',
        'bankline-direct-parser'
    ],
    classifiers=[
        'Intended Audience :: Python Developers',
    ],
    test_suite='tests'
)
