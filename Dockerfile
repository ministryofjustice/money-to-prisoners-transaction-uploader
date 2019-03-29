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

# add app and install python packages
WORKDIR /app
COPY requirements /app/requirements
RUN pip3 install -r requirements/docker.txt
COPY . /app

# add mtp user and log files
RUN set -ex; \
  useradd -M -d /app -s /usr/sbin/nologin mtp \
  && \
  test $(id -u mtp) = 1000 \
  && \
  touch /var/log/transaction-uploader.stdout /var/log/transaction-uploader.stderr \
  && \
  chown -R mtp /app /var/log /var/run /run
# template-deploy version must run as root because of how cron works
# cloud-platform can call /app/cron.py as user 1000
# USER 1000

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
