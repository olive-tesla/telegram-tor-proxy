FROM alpine:3.23
RUN apk add --no-cache openssl curl unzip
ADD https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip /tmp/xray.zip
RUN unzip /tmp/xray.zip -d /usr/local/bin/ && rm /tmp/xray.zip && chmod +x /usr/local/bin/xray
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]