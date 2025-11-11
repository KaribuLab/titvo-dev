#!/bin/bash

set -e

while inotifywait -e modify,create,delete .; do
    echo "Building image titvo/agent"
    exec "$@"
done