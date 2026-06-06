#!/bin/sh
set -e

DATA_DIR="/etc/xray"
mkdir -p "$DATA_DIR/certs"

# UUID
UUID_FILE="$DATA_DIR/uuid"
if [ -f "$UUID_FILE" ]; then
    UUID=$(cat "$UUID_FILE")
else
    UUID=$(cat /proc/sys/kernel/random/uuid)
    echo "$UUID" > "$UUID_FILE"
fi
echo "UUID: $UUID"

# Сертификат
CERT="$DATA_DIR/certs/cert.pem"
KEY="$DATA_DIR/certs/key.pem"
if [ ! -f "$CERT" ]; then
    openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
        -subj "/CN=localhost" -keyout "$KEY" -out "$CERT"
fi

# Автоопределение IP (если не удалось – CHANGE_ME)
IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "CHANGE_ME")
echo "IP: $IP"

# Конфиг Xray
cat > /etc/xray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "tag": "inbound-0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [{ "id": "$UUID", "level": 0 }],
        "decryption": "none",
        "flow": "xtls-rprx-vision"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
          "certificates": [
            {
              "certificateFile": "$CERT",
              "keyFile": "$KEY"
            }
          ]
        }
      },
      "sniffing": { "enabled": false }
    }
  ],
  "outbounds": [
    { "protocol": "freedom", "tag": "direct" },
    {
      "protocol": "socks",
      "tag": "tor",
      "settings": {
        "servers": [{ "address": "tor-proxy", "port": 9090 }]
      }
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "inboundTag": ["inbound-0"],
        "outboundTag": "tor"
      }
    ]
  }
}
EOF

# Ссылка для клиента
echo "========================================="
echo "VLESS link for client:"
echo "vless://$UUID@$IP:443?encryption=none&flow=xtls-rprx-vision&security=tls&type=tcp&headerType=none&allowInsecure=1#TorProxy"
echo "========================================="

exec /usr/local/bin/xray -config /etc/xray/config.json