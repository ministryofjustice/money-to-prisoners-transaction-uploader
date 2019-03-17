FROM buildpack-deps:bionic

# setup UK environment and install libraries and python
RUN set -ex; \
  apt-get update \
  && \
  DEBIAN_FRONTEND=noninteractive apt-get install \
  -y --no-install-recommends --no-install-suggests \
  -o DPkg::Options::=--force-confdef \
  locales tzdata \
  && \
  echo en_GB.UTF-8 UTF-8 > /etc/locale.gen \
  && \
  locale-gen \
  && \
  rm /etc/localtime \
  && \
  ln -s /usr/share/zoneinfo/Europe/London /etc/localtime \
  && \
  dpkg-reconfigure --frontend noninteractive tzdata \
  && \
  DEBIAN_FRONTEND=noninteractive apt-get install \
  -y --no-install-recommends --no-install-suggests \
  -o DPkg::Options::=--force-confdef \
  software-properties-common build-essential \
  python3-all-dev python3-setuptools python3-pip python3-wheel \
  cron \
  && \
  rm -rf /var/lib/apt/lists/* \
  && \
  pip3 install -U setuptools pip wheel
ENV LANG=en_GB.UTF-8
ENV TZ=Europe/London

# pre-create directories and log files
WORKDIR /app
RUN set -ex; touch \
  /var/log/transaction-uploader.stdout \
  /var/log/transaction-uploader.stderr

# add app and install python packages
ADD . /app
RUN pip3 install -r requirements/docker.txt

ARG APP_GIT_COMMIT
ARG APP_GIT_BRANCH
ARG APP_BUILD_TAG
ARG APP_BUILD_DATE
ENV APP_GIT_COMMIT ${APP_GIT_COMMIT}
ENV APP_GIT_BRANCH ${APP_GIT_BRANCH}
ENV APP_BUILD_TAG ${APP_BUILD_TAG}
ENV APP_BUILD_DATE ${APP_BUILD_DATE}

# wait until container is running to install crontab to ensure environment variables are available
CMD python3 /app/install_crontab.py && tail -f /var/log/transaction-uploader.stdout /var/log/transaction-uploader.stderr
