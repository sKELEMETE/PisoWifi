#!/usr/bin/env bash
# ==============================================================================
# PisoWiFi MariaDB Automated Setup & Optimization Script for Flash/SBC Appliances
# ==============================================================================

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "[ERROR] This script must be run as root (or via sudo)." >&2
    exit 1
fi

DB_NAME="pisowifi"
DB_USER="pisowifi"
ENV_FILE="/opt/pisowifi/.env"
[ ! -f "$ENV_FILE" ] && ENV_FILE="$(dirname "$(dirname "$(readlink -f "$0")")")/.env"

echo "[INFO] Checking MariaDB installation..."
if ! command -v mariadb &>/dev/null && ! command -v mysql &>/dev/null; then
    echo "[INFO] MariaDB not found. Installing mariadb-server..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y mariadb-server mariadb-client
fi

echo "[INFO] Ensuring MariaDB service is active..."
systemctl enable mariadb
systemctl start mariadb

# Generate strong random password if not already present in environment
if [[ -z "${DB_PASSWORD:-}" ]]; then
    if [[ -f "$ENV_FILE" ]] && grep -q "^DATABASE_PASSWORD=" "$ENV_FILE" && ! grep -q "^DATABASE_PASSWORD=password$" "$ENV_FILE"; then
        DB_PASSWORD=$(grep "^DATABASE_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"'"'")
    else
        DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    fi
fi

echo "[INFO] Configuring MariaDB database and permissions..."
mariadb -e "
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
"

echo "[INFO] Configuring flash storage (eMMC/MicroSD) optimizations..."
CONF_DIR="/etc/mysql/mariadb.conf.d"
[ ! -d "$CONF_DIR" ] && CONF_DIR="/etc/mysql/conf.d"
mkdir -p "$CONF_DIR"

cat <<'EOF' > "${CONF_DIR}/99-pisowifi-flash.cnf"
[mysqld]
# Flash memory write endurance optimizations
innodb_flush_log_at_trx_commit = 2
innodb_buffer_pool_size = 128M
innodb_log_file_size = 32M
innodb_flush_method = O_DIRECT
innodb_doublewrite = 1
max_connections = 100
wait_timeout = 600
interactive_timeout = 600
EOF

systemctl restart mariadb

echo "[INFO] Validating database connection..."
mariadb -u"${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" -e "SELECT 1;" >/dev/null

echo "[INFO] MariaDB setup and validation successful!"

if [[ -f "$ENV_FILE" ]]; then
    echo "[INFO] Updating database settings in $ENV_FILE..."
    sed -i "s/^DATABASE_PASSWORD=.*/DATABASE_PASSWORD=${DB_PASSWORD}/" "$ENV_FILE"
    sed -i "s/^PISOWIFI_DATABASE_TYPE=.*/PISOWIFI_DATABASE_TYPE=mysql/" "$ENV_FILE"
    chmod 0600 "$ENV_FILE"
fi
