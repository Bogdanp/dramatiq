#!/usr/bin/env bash

set -euo pipefail

case "$GITHUB_ACTION" in
    "Test 3.5")
        ENV=py35
        ;;

    "Test 3.6")
        ENV=py36
        ;;

    "Test 3.7")
        ENV=py37
        ;;

    *)
        echo "error: unexpected action '$GITHUB_ACTION'"
        exit 1
        ;;
esac

pip install tox &
service memcached start &
service rabbitmq-server start &
service redis-server start &
wait

cp -r "$GITHUB_WORKSPACE" "/tmp/test$ENV"
pushd "/tmp/test$ENV"

tox -e "$ENV"
