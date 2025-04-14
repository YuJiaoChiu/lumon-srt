#!/bin/bash

# 清理并部署 Lumon SRT 项目脚本
# 使用方法: sudo ./clean_and_deploy.sh <域名>

set -e

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
  echo "请以 root 权限运行此脚本"
  exit 1
fi

# 检查参数
if [ -z "$1" ]; then
  echo "请提供域名作为参数"
  echo "使用方法: sudo ./clean_and_deploy.sh <域名>"
  exit 1
fi

DOMAIN=$1
APP_DIR="/opt/lumon-srt"
PYTHON_VERSION="3.9"
NGINX_CONF="/etc/nginx/sites-available/lumon-srt"
SYSTEMD_SERVICE="/etc/systemd/system/lumon-srt.service"

echo "====================================================="
echo "开始清理并部署 Lumon SRT 到 $DOMAIN..."
echo "====================================================="

# 1. 清理旧的 Nginx 配置
echo "1. 清理旧的 Nginx 配置..."
echo "---------------------------------------------------"

# 停止 Nginx
systemctl stop nginx

# 备份当前 Nginx 配置
BACKUP_DIR="/root/nginx_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r /etc/nginx/* $BACKUP_DIR/
echo "已备份 Nginx 配置到 $BACKUP_DIR"

# 清理 sites-enabled 目录
rm -f /etc/nginx/sites-enabled/*
echo "已清理 sites-enabled 目录"

# 恢复默认配置
cp /etc/nginx/nginx.conf.default /etc/nginx/nginx.conf 2>/dev/null || true
if [ ! -f /etc/nginx/nginx.conf ]; then
  # 如果没有默认配置备份，创建一个基本配置
  cat > /etc/nginx/nginx.conf << EOF
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
    # multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOF
  echo "已创建新的 nginx.conf 配置文件"
fi

# 2. 清理旧的应用程序
echo "2. 清理旧的应用程序..."
echo "---------------------------------------------------"

# 停止并禁用所有可能的旧服务
for service in $(systemctl list-units --type=service --state=running | grep -E '(web|app|flask|gunicorn|uwsgi)' | awk '{print $1}'); do
  echo "停止并禁用服务: $service"
  systemctl stop $service 2>/dev/null || true
  systemctl disable $service 2>/dev/null || true
done

# 特别检查并停止我们的服务
if systemctl is-active --quiet lumon-srt; then
  echo "停止 lumon-srt 服务"
  systemctl stop lumon-srt
  systemctl disable lumon-srt
fi

# 备份旧的应用目录（如果存在）
if [ -d "$APP_DIR" ]; then
  BACKUP_APP_DIR="/root/app_backup_$(date +%Y%m%d_%H%M%S)"
  echo "备份旧的应用目录到 $BACKUP_APP_DIR"
  cp -r $APP_DIR $BACKUP_APP_DIR
  
  # 删除旧的应用目录
  echo "删除旧的应用目录"
  rm -rf $APP_DIR
fi

# 3. 安装依赖
echo "3. 安装系统依赖..."
echo "---------------------------------------------------"
apt-get update
apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip nginx certbot python3-certbot-nginx supervisor

# 4. 创建应用目录
echo "4. 创建应用目录..."
echo "---------------------------------------------------"
mkdir -p ${APP_DIR}/logs
mkdir -p ${APP_DIR}/backend/uploads
mkdir -p ${APP_DIR}/backend/dictionaries
mkdir -p ${APP_DIR}/frontend

# 5. 复制项目文件
echo "5. 复制项目文件..."
echo "---------------------------------------------------"
cp -r ../backend/* ${APP_DIR}/backend/
cp -r ../frontend/dist/* ${APP_DIR}/frontend/

# 6. 创建 Python 虚拟环境
echo "6. 设置 Python 虚拟环境..."
echo "---------------------------------------------------"
python${PYTHON_VERSION} -m venv ${APP_DIR}/venv
source ${APP_DIR}/venv/bin/activate

# 7. 安装 Python 依赖
echo "7. 安装 Python 依赖..."
echo "---------------------------------------------------"
pip install --upgrade pip
pip install -r ${APP_DIR}/backend/requirements.txt
pip install gunicorn

# 8. 初始化词典文件
echo "8. 初始化词典文件..."
echo "---------------------------------------------------"
if [ ! -f "${APP_DIR}/backend/dictionaries/protection_dict.json" ]; then
    echo '{}' > ${APP_DIR}/backend/dictionaries/protection_dict.json
fi

if [ ! -f "${APP_DIR}/backend/dictionaries/correction_dict.json" ]; then
    echo '{}' > ${APP_DIR}/backend/dictionaries/correction_dict.json
fi

# 9. 设置目录权限
echo "9. 设置目录权限..."
echo "---------------------------------------------------"
chown -R www-data:www-data ${APP_DIR}
chmod -R 755 ${APP_DIR}
chown -R www-data:www-data ${APP_DIR}/backend/uploads
chown -R www-data:www-data ${APP_DIR}/backend/dictionaries

# 10. 配置 Nginx
echo "10. 配置 Nginx..."
echo "---------------------------------------------------"
cat > ${NGINX_CONF} << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    # 前端静态文件
    location / {
        root ${APP_DIR}/frontend;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:5002/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # 增加上传文件的超时时间
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # 增加上传文件大小限制
        client_max_body_size 20M;
    }
}
EOF

# 启用 Nginx 配置
ln -sf ${NGINX_CONF} /etc/nginx/sites-enabled/
nginx -t
systemctl start nginx

# 11. 配置 Systemd 服务
echo "11. 配置 Systemd 服务..."
echo "---------------------------------------------------"
cat > ${SYSTEMD_SERVICE} << EOF
[Unit]
Description=Lumon SRT Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}/backend
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5002 wsgi:app
Restart=always
Environment="PATH=${APP_DIR}/venv/bin"
Environment="PYTHONPATH=${APP_DIR}"
TimeoutSec=300

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
systemctl daemon-reload
systemctl enable lumon-srt
systemctl start lumon-srt

# 12. 设置 SSL（可选）
echo "12. 是否设置 SSL？(y/n)"
read -p ">" ssl_choice

if [ "$ssl_choice" = "y" ] || [ "$ssl_choice" = "Y" ]; then
    echo "设置 SSL..."
    certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --redirect || true
fi

echo "====================================================="
echo "清理和部署完成！"
echo "====================================================="
echo "应用现在应该可以通过 http://${DOMAIN} 访问"
if [ "$ssl_choice" = "y" ] || [ "$ssl_choice" = "Y" ]; then
    echo "或者通过 https://${DOMAIN} 访问（如果 SSL 设置成功）"
fi
echo ""
echo "服务状态检查："
systemctl status nginx --no-pager
systemctl status lumon-srt --no-pager
echo ""
echo "如果遇到问题，请检查以下日志："
echo "- Nginx 错误日志: /var/log/nginx/error.log"
echo "- 应用日志: journalctl -u lumon-srt"
