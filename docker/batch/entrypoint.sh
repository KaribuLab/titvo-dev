#!/bin/sh

set -e

cwd=$(pwd)

cd /runner
npm install
npm run start &

cd $cwd

"$@"

while inotifywait -r -e modify,create,delete,attrib .; do
    echo "Change detected, rebuilding..."
    "$@"
done