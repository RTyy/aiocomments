#!/bin/bash

psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
    CREATE USER aiocomments_user WITH PASSWORD 'aiocomments';
    CREATE DATABASE aiocomments ENCODING 'UTF8';
    GRANT ALL PRIVILEGES ON DATABASE aiocomments TO aiocomments_user;
    CREATE DATABASE aiocomments_test ENCODING 'UTF8';
    GRANT ALL PRIVILEGES ON DATABASE aiocomments_test TO aiocomments_user;
EOSQL

cd /opt/aiocomments/source
/opt/.env/bin/python /opt/aiocomments/source/run.py initdb -s
