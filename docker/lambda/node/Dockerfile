FROM node:24-alpine3.21

COPY entrypoint.sh /entrypoint.sh
COPY tail-cloudwatch-logs.sh /usr/local/bin/tail-cloudwatch-logs.sh

RUN apk add --no-cache zip curl aws-cli jq tzdata && \
    mkdir -p /home/node/app && \
    chown -R node:node /home/node/app && \
    npm install -g aws-cdk-local aws-cdk && \
    chmod +x /entrypoint.sh && \
    chmod +x /usr/local/bin/tail-cloudwatch-logs.sh && \
    ln -s /usr/local/bin/tail-cloudwatch-logs.sh /usr/local/bin/logs-lambda

WORKDIR /home/node/app

USER node

ENTRYPOINT ["/entrypoint.sh"]

CMD ["npm", "run", "dev"]