#!/bin/bash
set -e

PROJECT_DIR="/opt/l3-data-feed"

echo "Installing dependencies..."

cd "$PROJECT_DIR"

uv sync

sudo tee /etc/systemd/system/l3-data-feed.service > /dev/null << EOF
[Unit]
Description=L3 data feeder
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python -m __main__
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable l3-data-feed
sudo systemctl start l3-data-feed
