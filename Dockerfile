FROM buildpack-deps:xenial

# setup environment
RUN apt-get update && apt-get install -y --no-install-recommends locales tzdata
RUN set -ex; echo en_GB.UTF-8 UTF-8 > /etc/locale.gen && locale-gen
ENV LANG=en_GB.UTF-8
ENV TZ=Europe/London
RUN timedatectl set-timezone Europe/London || true

# install libraries
RUN apt-get install -y --no-install-recommends software-properties-common build-essential cron python3-all-dev python3-pip python3-venv
RUN pip3 install -U setuptools pip wheel

# cleanup
RUN rm -rf /var/lib/apt/lists/*

# pre-create directories and log files
WORKDIR /app
RUN set -ex; touch \
  /var/log/transaction-uploader.stdout \
  /var/log/transaction-uploader.stderr

# add app and install python packages
ADD . /app
RUN pip3 install -r requirements/docker.txt

# wait until container is running to install crontab to ensure environment variables are available
CMD python3 /app/install_crontab.py && tail -f /var/log/transaction-uploader.stdout /var/log/transaction-uploader.stderr
