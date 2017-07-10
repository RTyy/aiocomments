FROM postgres:9.4
MAINTAINER Tyomkeen <a@itd.su>

ENV PGDATA /var/lib/postgresql/data/pgdata

# install system-wide stuff
RUN echo deb http://ftp.de.debian.org/debian experimental main >> /etc/apt/sources.list && echo deb http://ftp.de.debian.org/debian unstable main >> /etc/apt/sources.list && apt-get update && apt-get install -y python3.6 python3.6-venv && mkdir -p /opt/aiocomments/source && mkdir /opt/aiocomments/files && mkdir /opt/aiocomments/static

ADD docker/entrypoint/install.sh /docker-entrypoint-initdb.d/
ADD docker/entrypoint/run.sh /opt/aiocomments/
ADD docker/entrypoint/run_tests.sh /opt/aiocomments/
ADD source/requirements.txt /opt/aiocomments/
# ADD source/ /opt/aiocomments/source

# create virtual env for python
RUN python3.6 -m venv /opt/.env
WORKDIR /opt/aiocomments
RUN /opt/.env/bin/pip install wheel && /opt/.env/bin/pip install -r requirements.txt

EXPOSE 8085

# start
#CMD ["/opt/.env/bin/python", "./run.py"]