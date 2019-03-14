#!/usr/bin/env bash

set -euo pipefail

pushd "$GITHUB_WORKSPACE"
pip install tox
tox -e lint
