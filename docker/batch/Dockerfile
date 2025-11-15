FROM docker:28.5.1-dind

RUN apk add inotify-tools nodejs npm
RUN mkdir -p /app

COPY runner /runner
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]

CMD ["docker","build","-t","titvo/agent","."]