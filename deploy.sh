#!/bin/bash

cd $DEPLOYMENT_TARGET

# Install system dependencies for Wordcloud
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip build-essential python3-setuptools python3-wheel libpng-dev libfreetype6-dev

# Install Wordcloud and Stylecloud
pip install wordcloud-1.8.2.2-py3-none-any.whl
pip install stylecloud-0.5.1-py3-none-any.whl

# Install requirements
pip install -r requirements.txt
