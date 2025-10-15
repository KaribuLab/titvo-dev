FROM node:24-alpine3.21

RUN apk add --no-cache curl

RUN npm install -g aws-cdk-local aws-cdk

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["npm", "run", "dev"]