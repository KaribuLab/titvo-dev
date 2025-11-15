#!/bin/sh

set -e

cwd=$(pwd)

cd /runner
npm install
npm run start &

cd $cwd

"$@"

while inotifywait -e modify,create,delete .; do
    "$@"
done