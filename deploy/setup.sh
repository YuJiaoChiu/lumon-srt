#!/bin/bash

# SRT Correction System Setup Script
# This script sets up the SRT Correction System on a Linux server

# Exit on error
set -e

# Configuration
APP_DIR="/var/www/srt-correction"
PYTHON_VERSION="3.9"
DOMAIN="srt-correction.example.com"  # Replace with your actual domain

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

# Update system
print_message "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
print_message "Installing dependencies..."
apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip nginx certbot python3-certbot-nginx supervisor

# Create application directory
print_message "Creating application directory..."
mkdir -p ${APP_DIR}
mkdir -p ${APP_DIR}/logs
mkdir -p ${APP_DIR}/python
mkdir -p ${APP_DIR}/frontend

# Copy application files
print_message "Copying application files..."
cp -r ../python/* ${APP_DIR}/python/
cp -r ../frontend/* ${APP_DIR}/frontend/

# Create Python virtual environment
print_message "Setting up Python virtual environment..."
python${PYTHON_VERSION} -m venv ${APP_DIR}/venv
source ${APP_DIR}/venv/bin/activate

# Install Python dependencies
print_message "Installing Python dependencies..."
pip install --upgrade pip
pip install flask flask-cors gunicorn werkzeug flask-limiter

# Create initial dictionary files if they don't exist
print_message "Creating initial dictionary files..."
if [ ! -f "${APP_DIR}/python/terms.json" ]; then
    echo '{}' > ${APP_DIR}/python/terms.json
fi

if [ ! -f "${APP_DIR}/python/保护terms.json" ]; then
    echo '{}' > ${APP_DIR}/python/保护terms.json
fi

# Set permissions
print_message "Setting permissions..."
chown -R www-data:www-data ${APP_DIR}
chmod -R 755 ${APP_DIR}

# Configure Nginx
print_message "Configuring Nginx..."
cp nginx.conf /etc/nginx/sites-available/srt-correction
ln -sf /etc/nginx/sites-available/srt-correction /etc/nginx/sites-enabled/
sed -i "s/srt-correction.example.com/${DOMAIN}/g" /etc/nginx/sites-available/srt-correction

# Configure Supervisor
print_message "Configuring Supervisor..."
cat > /etc/supervisor/conf.d/srt-correction.conf << EOF
[program:srt-correction]
directory=${APP_DIR}/python
command=${APP_DIR}/venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 backend:app
autostart=true
autorestart=true
stderr_logfile=${APP_DIR}/logs/gunicorn.err.log
stdout_logfile=${APP_DIR}/logs/gunicorn.out.log
user=www-data
environment=PYTHONPATH="${APP_DIR}"
EOF

# Restart services
print_message "Restarting services..."
systemctl restart nginx
systemctl restart supervisor

# Setup SSL with Certbot
print_message "Setting up SSL with Certbot..."
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN}

print_message "Installation complete!"
print_message "Your SRT Correction System is now available at https://${DOMAIN}"
print_message "Please update the domain in the configuration files if needed."
