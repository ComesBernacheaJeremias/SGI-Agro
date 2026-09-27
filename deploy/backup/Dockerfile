FROM postgres:16-alpine
RUN apk add --no-cache rclone
COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh
CMD ["backup.sh", "loop"]
