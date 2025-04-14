#!/bin/bash

# 手动部署脚本 - 在 Linux 服务器上部署 Lumon SRT 项目
# 使用方法: ./manual_deploy.sh

set -e

echo "开始手动部署 Lumon SRT..."

# 安装系统依赖
echo "请确保已安装以下依赖："
echo "- Python 3.9 或更高版本"
echo "- pip"
echo "- virtualenv 或 venv"
echo "- Nginx"

# 创建应用目录
echo "创建应用目录..."
APP_DIR="$HOME/lumon-srt"
mkdir -p ${APP_DIR}/logs
mkdir -p ${APP_DIR}/backend/uploads
mkdir -p ${APP_DIR}/backend/dictionaries
mkdir -p ${APP_DIR}/frontend

# 复制项目文件
echo "复制项目文件..."
cp -r ../backend/* ${APP_DIR}/backend/
cp -r ../frontend/dist/* ${APP_DIR}/frontend/

# 创建 Python 虚拟环境
echo "设置 Python 虚拟环境..."
python3 -m venv ${APP_DIR}/venv
source ${APP_DIR}/venv/bin/activate

# 安装 Python 依赖
echo "安装 Python 依赖..."
pip install --upgrade pip
pip install -r ${APP_DIR}/backend/requirements.txt
pip install gunicorn

# 初始化词典文件
if [ ! -f "${APP_DIR}/backend/dictionaries/protection_dict.json" ]; then
    echo '{}' > ${APP_DIR}/backend/dictionaries/protection_dict.json
fi

if [ ! -f "${APP_DIR}/backend/dictionaries/correction_dict.json" ]; then
    echo '{}' > ${APP_DIR}/backend/dictionaries/correction_dict.json
fi

# 创建启动脚本
echo "创建启动脚本..."
cat > ${APP_DIR}/start.sh << EOF
#!/bin/bash
source ${APP_DIR}/venv/bin/activate
cd ${APP_DIR}/backend
gunicorn --workers 4 --bind 127.0.0.1:5002 wsgi:app
EOF

chmod +x ${APP_DIR}/start.sh

echo "手动部署完成！"
echo "你现在可以通过以下命令启动应用："
echo "cd ${APP_DIR} && ./start.sh"
echo ""
echo "请确保配置 Nginx 以代理前端和后端 API。"
echo "前端目录: ${APP_DIR}/frontend"
echo "后端 API: http://127.0.0.1:5002/api/"
