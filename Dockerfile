FROM ubuntu:trusty

RUN echo "Europe/London" | cat > /etc/timezone && dpkg-reconfigure --frontend noninteractive tzdata
RUN locale-gen "en_GB.UTF-8"
ENV LC_CTYPE=en_GB.UTF-8

RUN apt-get update && \
    apt-get install -y \
        software-properties-common python-software-properties \
        build-essential git python3-all python3-all-dev python3-setuptools \
        curl ntp python3-pip python-pip libffi-dev libssl-dev

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

WORKDIR /app

RUN pip3 install -U setuptools pip wheel

ADD . /app
RUN pip3 install -r requirements/docker.txt

RUN touch /var/log/transaction-uploader.stdout
RUN touch /var/log/transaction-uploader.stderr

# wait until container is running to install crontab to ensure environment
# variables are available
CMD python3 /app/install_crontab.py && tail -f /var/log/transaction-uploader.stdout /var/log/transaction-uploader.stderr
