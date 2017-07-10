aioComments
===========

Simple server side for handling Comments based on aiohttp.

Requirements
============

* Python3.6 (3.5)
    Python3.5 may crash the tests due to unordered dict responses from json.loads
* PostgreSQL 9.4+

* aiofiles
* aiohttp
* aiohttp-jinja2
* aiopg
* lxml
* psycopg2
* pytest-aiohttp
* SQLAlchemy
* trafaret
* trafaret-config

API Description
===============

https://github.com/RTyy/aiocomments/wiki/aioComments


Docker Installation
===================

Build Docker Image::

    $ docker build --tag=aiocomments .

Run Container (in the interactive mode)::
    
    $ ./run_docker.sh

Run Application (in the interactive mode)::

    $ docker/run_app.sh

Run Tests (in the interactive mode)::

    $ docker/run_tests.sh

Source code of the project will be connected to the docker container as a Volume.
Database will be created from the scratch each time you will run a container.

Local Installation
==================

Create database for the project::

    $ devops/install.sh

Run application::

    $ cd source
    $ ./run.py

Run application in Development Mode::

    $ cd source
    $ ./run.py serve


Run integration tests::
    
    $ cd source
    $ pytest -s -vv core/tests aiocomments/tests

With TOX::
    
    $ pip install tox
    $ cd source
    $ tox
