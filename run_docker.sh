#!/bin/bash

docker rm aiocomments
docker run --name=aiocomments -v $PWD/source:/opt/aiocomments/source -p 8085:8085 aiocomments