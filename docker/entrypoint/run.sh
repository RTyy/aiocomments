#!/bin/bash

source /opt/.env/bin/activate
cd /opt/aiocomments/source
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
./run.py