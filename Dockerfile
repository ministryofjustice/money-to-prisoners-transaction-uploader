FROM base

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

CMD venv/bin/python main.py
