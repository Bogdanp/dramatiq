#!/usr/bin/env bash

set -euo pipefail

cp -r "$GITHUB_WORKSPACE" /tmp/lint
pushd /tmp/lint

pip install tox
tox -e lint
