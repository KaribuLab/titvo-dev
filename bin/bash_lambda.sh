#!/bin/bash
logs() {
    cd $TITVO_DEV_ROOT
    docker compose exec $1 logs-lambda
    cd - > /dev/null 2>&1
}

api_gateway_url() {
    cd $TITVO_DEV_ROOT
    docker compose exec $1 api-gateway-url
    cd - > /dev/null 2>&1
}

cmd=$1

case $cmd in
    logs)
        logs $2
        ;;
    api-url)
        api_gateway_url $2
        ;;
    *)
        echo "Usage: lambda <logs|api-gateway-url> <docker-service-name>"
        exit 1
        ;;
esac