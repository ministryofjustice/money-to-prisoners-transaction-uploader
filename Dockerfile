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
  python3-all-dev python3-setuptools python3-pip python3-wheel python3-venv \
  && \
  rm -rf /var/lib/apt/lists/* \
  && \
  pip3 install -U setuptools pip wheel
ENV LANG=en_GB.UTF-8
ENV TZ=Europe/London

WORKDIR /app

# install virtual environment
RUN set -ex; \
  /usr/bin/python3 -m venv venv && \
  venv/bin/pip install -U setuptools pip wheel

# cache python packages, unless requirements change
COPY ./requirements requirements
RUN venv/bin/pip install -r requirements/docker.txt

# add app
COPY . /app

# add mtp user and log files
RUN set -ex; \
  useradd -u 1000 -M -d /app -s /usr/sbin/nologin mtp \
  && \
  chown -R mtp /app /var/log /var/run /run
USER 1000

ARG APP_GIT_COMMIT
ARG APP_GIT_BRANCH
ARG APP_BUILD_TAG
ARG APP_BUILD_DATE
ENV APP_GIT_COMMIT ${APP_GIT_COMMIT}
ENV APP_GIT_BRANCH ${APP_GIT_BRANCH}
ENV APP_BUILD_TAG ${APP_BUILD_TAG}
ENV APP_BUILD_DATE ${APP_BUILD_DATE}

CMD venv/bin/python3 /app/mtp_transaction_uploader/main.py
