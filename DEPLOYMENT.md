# SRT Subtitle Correction System Deployment Guide

This guide provides instructions for deploying the SRT Subtitle Correction System on a Linux server in China.

## System Requirements

- Linux server (Ubuntu 20.04 LTS or newer recommended)
- Docker and Docker Compose
- Node.js 16+ (for building the frontend)
- Nginx (for serving the frontend and proxying API requests)

## Deployment Steps

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 2. Build the Frontend

```bash
# Install dependencies
npm install

# Build for production
npm run build
```

This will create a `dist` directory with the compiled frontend assets.

### 3. Deploy the Backend

Navigate to the Python backend directory:

```bash
cd python
```

Start the Docker container:

```bash
docker-compose up -d
```

This will:
- Build the Docker image for the backend
- Start the container in detached mode
- Expose the API on port 5000
- Mount the dictionaries directory for persistence

### 4. Configure Nginx

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/srt-correction
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    # Serve frontend static files
    location / {
        root /path/to/your/dist;  # Path to the built frontend
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to the backend
    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/srt-correction /etc/nginx/sites-enabled/
sudo nginx -t  # Test the configuration
sudo systemctl restart nginx
```

### 5. Update API URL in the Frontend

Before building the frontend, update the API_URL in `src/App.tsx` to match your production server:

```typescript
const API_URL = 'http://your-domain.com/api';  // Replace with your domain
```

### 6. Firewall Configuration

Make sure to allow HTTP traffic:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp  # If using HTTPS
```

### 7. SSL Configuration (Recommended)

For production use, it's recommended to secure your site with SSL:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Maintenance

### Updating the Application

To update the application:

1. Pull the latest code:
   ```bash
   git pull
   ```

2. Rebuild the frontend:
   ```bash
   npm install
   npm run build
   ```

3. Restart the backend:
   ```bash
   cd python
   docker-compose down
   docker-compose up -d
   ```

### Backing Up Dictionaries

The dictionaries are stored in the `python/dictionaries` directory. To back them up:

```bash
cp -r python/dictionaries /path/to/backup/location
```

## Troubleshooting

### Backend API Not Accessible

Check if the Docker container is running:

```bash
docker ps
```

Check the logs:

```bash
cd python
docker-compose logs
```

### Frontend Not Loading

Check Nginx error logs:

```bash
sudo tail -f /var/log/nginx/error.log
```

### CORS Issues

If you encounter CORS issues, make sure the API_URL in the frontend matches the actual URL being used to access the application.

## China-Specific Considerations

### Docker Registry Mirrors

If you have trouble pulling Docker images, consider using a China-based Docker registry mirror:

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": ["https://registry.docker-cn.com"]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### NPM Registry

For faster npm package downloads, use a China-based npm mirror:

```bash
npm config set registry https://registry.npm.taobao.org
```

### Server Hosting

Consider using a China-based cloud provider like Alibaba Cloud (Aliyun) or Tencent Cloud for better performance within China.
