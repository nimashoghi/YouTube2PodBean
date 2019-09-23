#!/usr/bin/fish

apt-get update
apt-get install --no-install-recommends --yes libjpeg-dev zlib1g-dev
poetry install
