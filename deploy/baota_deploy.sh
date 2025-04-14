#!/bin/bash

# Lumon SRT Docker Deployment Script for Baota
# This script prepares and deploys the Lumon SRT application using Docker on a Baota server

# Exit on error
set -e

# Display help message
show_help() {
    echo "Usage: $0 [domain]"
    echo "  domain: Your domain name or server IP (optional)"
    echo "          If not provided, will use localhost"
    echo ""
    echo "Example: $0 example.com"
    exit 1
}

# Check if help is requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
fi

# Set domain name
DOMAIN=${1:-localhost}
echo "Using domain: $DOMAIN"

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p dictionaries
mkdir -p uploads
mkdir -p nginx/ssl
mkdir -p nginx/conf.d

# Update Nginx configuration
echo "Updating Nginx configuration..."
cat > nginx/conf.d/default.conf << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://lumon-srt:5002/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_cache_bypass \$http_upgrade;
        
        client_max_body_size 20M;
    }
}
EOF

# Build frontend
echo "Building frontend..."
cd ../frontend
npm install
npm run build
cd ../deploy

# Copy dictionaries if they exist
if [ -d "../backend/dictionaries" ]; then
    echo "Copying dictionaries..."
    cp -r ../backend/dictionaries/* dictionaries/
fi

# Create a docker-compose.yml file with absolute paths
echo "Creating docker-compose.yml with absolute paths..."
DEPLOY_DIR=$(pwd)
cat > docker-compose.yml << EOF
version: '3'
services:
  lumon-srt:
    build:
      context: ${DEPLOY_DIR}/..
      dockerfile: ${DEPLOY_DIR}/Dockerfile
    ports:
      - "5002:5002"
    volumes:
      - ${DEPLOY_DIR}/../backend:/app/backend
      - ${DEPLOY_DIR}/dictionaries:/app/backend/dictionaries
      - ${DEPLOY_DIR}/uploads:/app/backend/uploads
    environment:
      - PYTHONPATH=/app
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ${DEPLOY_DIR}/../frontend/dist:/usr/share/nginx/html
      - ${DEPLOY_DIR}/nginx/conf.d:/etc/nginx/conf.d
      - ${DEPLOY_DIR}/nginx/ssl:/etc/nginx/ssl
    depends_on:
      - lumon-srt
    restart: always
EOF

# Start the application
echo "Starting the application..."
docker-compose up -d

echo "Deployment completed successfully!"
echo "You can access the application at: http://${DOMAIN}"
echo ""
echo "To check the status of the containers, run: docker-compose ps"
echo "To view logs, run: docker-compose logs"
echo "To stop the application, run: docker-compose down"
