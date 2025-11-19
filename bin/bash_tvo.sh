#!/bin/bash

api_key() {
    cd $TITVO_DEV_ROOT
    docker compose exec cdk get-api-key
    cd - > /dev/null 2>&1
}

cmd=$1

case $cmd in
    api-key)
        api_key $2
        ;;
    *)
        echo "Usage: tvo <api-key>"
        exit 1
        ;;
esac