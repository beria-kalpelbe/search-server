#!/bin/bash
set -e

# Must run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

# Get installation directory (parent of the directory containing this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/search-server"
VENV_DIR="$INSTALL_DIR/venv"

# Ensure python3-venv is installed
echo "Checking for python3-venv..."
if ! dpkg -l | grep -q python3-venv; then
  echo "Installing python3-venv..."
  apt-get update
  apt-get install -y python3-venv
fi

# Create installation directory if it doesn't exist
echo "Creating installation directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Copy all project files to the installation directory
echo "Copying project files to installation directory..."
cp -r "$PARENT_DIR"/* "$INSTALL_DIR"/

# Create and activate virtual environment
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install Python dependencies if requirements.txt exists
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
  echo "Installing Python dependencies in virtual environment..."
  "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
fi

# Deactivate virtual environment
deactivate

# Create service file with virtual environment python
echo "Creating systemd service file..."
cat > /etc/systemd/system/search-server.service << EOF
[Unit]
Description=This server recive a request and return if the query is found in the dtafile or not
After=network.target

[Service]
User=USER_TO_REPLACE
Group=GROUP_TO_REPLACE
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/src/server/server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=search-server
Environment=PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

# Replace user and group in service file
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" = "root" ]; then
  # If running as root, ask for the user to run the service as
  read -p "Enter the username to run the service as (default: $SUDO_USER): " SERVICE_USER
  SERVICE_USER=${SERVICE_USER:-$SUDO_USER}
  SERVICE_GROUP=$(id -gn $SERVICE_USER)
else
  # Use current user
  SERVICE_USER=$CURRENT_USER
  SERVICE_GROUP=$(id -gn)
fi

# Replace user and group in service file
sed -i "s/USER_TO_REPLACE/$SERVICE_USER/g" /etc/systemd/system/search-server.service
sed -i "s/GROUP_TO_REPLACE/$SERVICE_GROUP/g" /etc/systemd/system/search-server.service

# Set appropriate permissions
echo "Setting permissions..."
chown -R $SERVICE_USER:$SERVICE_GROUP "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/src/server/server.py"

# Reload systemd, enable and start service
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable search-server.service
systemctl start search-server.service

echo "Service installed and started successfully!"
echo "Check status with: systemctl status search-server.service"
echo "View logs with: sudo journalctl -u search-server.service -f"