#!/bin/bash

DOMAIN=$1
APP_DIR="/opt/lumon-srt"
PYTHON_VERSION="3.10"  # 改为 3.10
NGINX_CONF="/etc/nginx/sites-available/lumon-srt"
SYSTEMD_SERVICE="/etc/systemd/system/lumon-srt.service"

echo "开始部署 Lumon SRT 到 $DOMAIN..."

# 安装依赖
echo "安装系统依赖..."
apt-get update
apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip nginx certbot python3-certbot-nginx supervisor

# 其余部分保持不变
# 安装 Node.js (如果需要在服务器上构建前端)
# echo "安装 Node.js..."
# curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
# apt-get install -y nodejs

# 创建应用目录
echo "创建应用目录..."
mkdir -p ${APP_DIR}/logs

# 复制项目文件
echo "复制项目文件..."
cp -r ../backend ${APP_DIR}/
cp -r ../frontend/dist ${APP_DIR}/frontend

# 创建 Python 虚拟环境
echo "设置 Python 虚拟环境..."
python${PYTHON_VERSION} -m venv ${APP_DIR}/venv
source ${APP_DIR}/venv/bin/activate

# 安装 Python 依赖
echo "安装 Python 依赖..."
pip install --upgrade pip
pip install -r ${APP_DIR}/backend/requirements.txt
pip install gunicorn

# 确保目录权限正确
echo "设置目录权限..."
chown -R www-data:www-data ${APP_DIR}
chmod -R 755 ${APP_DIR}

# 创建上传和词典目录
mkdir -p ${APP_DIR}/backend/uploads
mkdir -p ${APP_DIR}/backend/dictionaries

# 初始化词典文件
if [ ! -f "${APP_DIR}/backend/dictionaries/protection_dict.json" ]; then
    echo '{}' > ${APP_DIR}/backend/dictionaries/protection_dict.json
fi

if [ ! -f "${APP_DIR}/backend/dictionaries/correction_dict.json" ]; then
    echo '{}' > ${APP_DIR}/backend/dictionaries/correction_dict.json
fi

chown -R www-data:www-data ${APP_DIR}/backend/uploads
chown -R www-data:www-data ${APP_DIR}/backend/dictionaries

# 配置 Nginx
echo "配置 Nginx..."
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
systemctl restart nginx

# 配置 Systemd 服务
echo "配置 Systemd 服务..."
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

# 设置 SSL
echo "设置 SSL..."
certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos --redirect

echo "部署完成！"
echo "应用现在应该可以通过 https://${DOMAIN} 访问"
