FROM docker:28.5.1-dind

RUN apk add inotify-tools

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh
RUN mkdir -p /app

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]

CMD ["docker","build","-t","titvo/agent","."]