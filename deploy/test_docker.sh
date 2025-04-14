#!/bin/bash

# 测试 Docker 部署的脚本

# 检查 Docker 是否安装
echo "检查 Docker 安装..."
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装。请先安装 Docker。"
    exit 1
fi

# 检查 Docker Compose 是否安装
echo "检查 Docker Compose 安装..."
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装。请先安装 Docker Compose。"
    exit 1
fi

# 检查 Docker 服务是否运行
echo "检查 Docker 服务状态..."
if ! docker info &> /dev/null; then
    echo "错误: Docker 服务未运行。请启动 Docker 服务。"
    exit 1
fi

echo "Docker 环境检查通过！"

# 检查必要的目录
echo "检查必要的目录..."
for dir in "dictionaries" "uploads" "nginx/conf.d" "nginx/ssl"; do
    if [ ! -d "$dir" ]; then
        echo "创建目录: $dir"
        mkdir -p "$dir"
    fi
done

# 检查 Nginx 配置
echo "检查 Nginx 配置..."
if [ ! -f "nginx/conf.d/default.conf" ]; then
    echo "错误: Nginx 配置文件不存在。请确保 nginx/conf.d/default.conf 文件存在。"
    exit 1
fi

# 检查前端构建
echo "检查前端构建..."
if [ ! -d "../frontend/dist" ]; then
    echo "警告: 前端构建目录不存在。请先构建前端。"
    echo "运行以下命令构建前端:"
    echo "  cd ../frontend"
    echo "  npm install"
    echo "  npm run build"
    echo "  cd ../deploy"
    exit 1
fi

echo "所有检查通过！您可以运行 ./baota_deploy.sh 来部署应用。"
