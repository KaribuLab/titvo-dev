#!/bin/sh

set -e

build(){
    echo "Building image titvo/agent"
    exec "$@"
}

build

while inotifywait -e modify,create,delete .; do
    build
done