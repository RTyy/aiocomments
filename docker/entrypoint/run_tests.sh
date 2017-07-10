#!/bin/bash

source /opt/.env/bin/activate
cd /opt/aiocomments/source
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
pytest -s core/tests aiocomments/tests