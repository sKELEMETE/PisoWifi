#!/bin/bash

BACKUP_DIR="/opt/pisowifi/backups"
DATE=$(date +"%Y-%m-%d-%H%M")

mkdir -p "$BACKUP_DIR"

sudo mysqldump pisowifi > "$BACKUP_DIR/pisowifi-$DATE.sql"

find "$BACKUP_DIR" -name "*.sql" -mtime +14 -delete
