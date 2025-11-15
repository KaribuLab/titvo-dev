FROM node:24-alpine3.21

# Argumento de build para el GID del grupo docker
ARG DOCKER_GID=999

COPY entrypoint.sh /entrypoint.sh
COPY tail-cloudwatch-logs.sh /usr/local/bin/tail-cloudwatch-logs.sh
COPY get-api-gateway-url.sh /usr/local/bin/get-api-gateway-url.sh

RUN apk add --no-cache zip curl aws-cli jq tzdata && \
    mkdir -p /home/node/app && \
    chown -R node:node /home/node/app && \
    npm install -g aws-cdk-local aws-cdk && \
    chmod +x /entrypoint.sh && \
    chmod +x /usr/local/bin/tail-cloudwatch-logs.sh && \
    chmod +x /usr/local/bin/get-api-gateway-url.sh && \
    ln -s /usr/local/bin/tail-cloudwatch-logs.sh /usr/local/bin/logs-lambda && \
    ln -s /usr/local/bin/get-api-gateway-url.sh /usr/local/bin/api-gateway-url && \
    (getent group ${DOCKER_GID} || addgroup -g ${DOCKER_GID} docker) && \
    adduser node $(getent group ${DOCKER_GID} | cut -d: -f1)

WORKDIR /home/node/app

USER node

ENTRYPOINT ["/entrypoint.sh"]

CMD ["npm", "run", "dev"]