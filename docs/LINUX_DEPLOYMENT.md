# Linux 部署指南

本文档提供了在 Linux 服务器上部署 Lumon SRT 字幕术语修正系统的详细步骤。

## 系统要求

- Ubuntu 20.04 LTS 或更高版本（推荐）
- Python 3.9 或更高版本
- Nginx
- 域名（用于 HTTPS 配置）

## 自动部署

我们提供了一个自动部署脚本，可以简化部署过程。

### 使用自动部署脚本

1. 将项目代码复制到服务器：

```bash
git clone https://github.com/yourusername/lumon-srt.git
cd lumon-srt
```

2. 构建前端：

```bash
cd frontend
npm install
npm run build
cd ..
```

3. 运行部署脚本：

```bash
cd deploy
chmod +x deploy.sh
sudo ./deploy.sh your-domain.com
```

脚本将自动执行以下操作：
- 安装所需的系统依赖
- 设置 Python 虚拟环境
- 配置 Nginx
- 设置 SSL 证书
- 创建并启动 Systemd 服务

## 手动部署

如果你想手动部署，请按照以下步骤操作：

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip nginx certbot python3-certbot-nginx supervisor
```

### 2. 创建应用目录

```bash
sudo mkdir -p /opt/lumon-srt/logs
```

### 3. 复制项目文件

```bash
sudo cp -r backend /opt/lumon-srt/
sudo cp -r frontend/dist /opt/lumon-srt/frontend
```

### 4. 设置 Python 虚拟环境

```bash
sudo python3.9 -m venv /opt/lumon-srt/venv
sudo /opt/lumon-srt/venv/bin/pip install --upgrade pip
sudo /opt/lumon-srt/venv/bin/pip install -r /opt/lumon-srt/backend/requirements.txt
sudo /opt/lumon-srt/venv/bin/pip install gunicorn
```

### 5. 设置目录权限

```bash
sudo chown -R www-data:www-data /opt/lumon-srt
sudo chmod -R 755 /opt/lumon-srt
```

### 6. 配置 Nginx

创建 Nginx 配置文件：

```bash
sudo nano /etc/nginx/sites-available/lumon-srt
```

添加以下内容（替换 `your-domain.com` 为你的实际域名）：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/lumon-srt/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:5002/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 增加上传文件的超时时间
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # 增加上传文件大小限制
        client_max_body_size 20M;
    }
}
```

启用配置并重启 Nginx：

```bash
sudo ln -sf /etc/nginx/sites-available/lumon-srt /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. 配置 Systemd 服务

创建服务文件：

```bash
sudo nano /etc/systemd/system/lumon-srt.service
```

添加以下内容：

```ini
[Unit]
Description=Lumon SRT Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/lumon-srt/backend
ExecStart=/opt/lumon-srt/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5002 wsgi:app
Restart=always
Environment="PATH=/opt/lumon-srt/venv/bin"
Environment="PYTHONPATH=/opt/lumon-srt"

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable lumon-srt
sudo systemctl start lumon-srt
```

### 8. 设置 SSL

```bash
sudo certbot --nginx -d your-domain.com
```

按照提示完成 SSL 配置。

## 验证部署

部署完成后，你可以通过以下方式验证部署是否成功：

1. 访问你的域名 `https://your-domain.com`，应该能看到前端界面
2. 检查后端 API 是否正常工作：`curl https://your-domain.com/api/health`
3. 检查服务状态：`sudo systemctl status lumon-srt`
4. 检查 Nginx 状态：`sudo systemctl status nginx`

## 故障排除

### 查看日志

- 后端日志：`sudo journalctl -u lumon-srt`
- Nginx 访问日志：`sudo tail -f /var/log/nginx/access.log`
- Nginx 错误日志：`sudo tail -f /var/log/nginx/error.log`

### 常见问题

1. **502 Bad Gateway**
   - 检查后端服务是否运行：`sudo systemctl status lumon-srt`
   - 检查端口是否正确：后端应该监听 5002 端口

2. **无法上传文件**
   - 检查上传目录权限：`sudo chown -R www-data:www-data /opt/lumon-srt/backend/uploads`
   - 检查 Nginx 配置中的 `client_max_body_size` 设置

3. **SSL 证书问题**
   - 更新证书：`sudo certbot renew`

## 更新应用

要更新应用，请按照以下步骤操作：

1. 拉取最新代码：
   ```bash
   git pull
   ```

2. 重新构建前端：
   ```bash
   cd frontend
   npm install
   npm run build
   sudo cp -r dist/* /opt/lumon-srt/frontend/
   ```

3. 更新后端：
   ```bash
   sudo cp -r backend/* /opt/lumon-srt/backend/
   sudo systemctl restart lumon-srt
   ```

4. 重启 Nginx（如果需要）：
   ```bash
   sudo systemctl restart nginx
   ```
