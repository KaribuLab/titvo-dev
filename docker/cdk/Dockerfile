FROM node:24-alpine3.21

RUN apk add --no-cache curl aws-cli

ARG CDK_VERSION=2.1145.0
RUN npm install -g aws-cdk-local aws-cdk@${CDK_VERSION}

COPY entrypoint.sh /entrypoint.sh
COPY get-api-key.sh /usr/local/bin/get-api-key.sh

RUN chmod +x /entrypoint.sh
RUN chmod +x /usr/local/bin/get-api-key.sh
RUN ln -s /usr/local/bin/get-api-key.sh /usr/local/bin/get-api-key

ENTRYPOINT ["/entrypoint.sh"]

CMD ["npm", "run", "dev"]