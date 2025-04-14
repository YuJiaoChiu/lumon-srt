#!/bin/bash

# 部署检查脚本 - 验证 Lumon SRT 项目是否正确部署
# 使用方法: ./check_deployment.sh [域名]

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 如果提供了域名，使用它；否则使用 localhost
if [ -z "$1" ]; then
  DOMAIN="localhost"
else
  DOMAIN="$1"
fi

echo -e "${YELLOW}====================================================${NC}"
echo -e "${YELLOW}开始检查 Lumon SRT 部署状态...${NC}"
echo -e "${YELLOW}====================================================${NC}"

# 1. 检查 Nginx 状态
echo -e "\n${YELLOW}1. 检查 Nginx 状态...${NC}"
if systemctl is-active --quiet nginx; then
  echo -e "${GREEN}✓ Nginx 正在运行${NC}"
else
  echo -e "${RED}✗ Nginx 未运行${NC}"
  echo "尝试启动 Nginx..."
  sudo systemctl start nginx
  if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx 已成功启动${NC}"
  else
    echo -e "${RED}✗ 无法启动 Nginx${NC}"
  fi
fi

# 2. 检查应用服务状态
echo -e "\n${YELLOW}2. 检查应用服务状态...${NC}"
if systemctl is-active --quiet lumon-srt; then
  echo -e "${GREEN}✓ Lumon SRT 服务正在运行${NC}"
else
  echo -e "${RED}✗ Lumon SRT 服务未运行${NC}"
  echo "尝试启动服务..."
  sudo systemctl start lumon-srt
  if systemctl is-active --quiet lumon-srt; then
    echo -e "${GREEN}✓ Lumon SRT 服务已成功启动${NC}"
  else
    echo -e "${RED}✗ 无法启动 Lumon SRT 服务${NC}"
  fi
fi

# 3. 检查端口
echo -e "\n${YELLOW}3. 检查端口状态...${NC}"
if netstat -tuln | grep -q ":5002 "; then
  echo -e "${GREEN}✓ 后端端口 5002 已开放${NC}"
else
  echo -e "${RED}✗ 后端端口 5002 未开放${NC}"
fi

if netstat -tuln | grep -q ":80 "; then
  echo -e "${GREEN}✓ HTTP 端口 80 已开放${NC}"
else
  echo -e "${RED}✗ HTTP 端口 80 未开放${NC}"
fi

if netstat -tuln | grep -q ":443 "; then
  echo -e "${GREEN}✓ HTTPS 端口 443 已开放${NC}"
else
  echo -e "${YELLOW}! HTTPS 端口 443 未开放（如果未配置 SSL 可忽略）${NC}"
fi

# 4. 检查 API 健康状态
echo -e "\n${YELLOW}4. 检查 API 健康状态...${NC}"
if curl -s "http://localhost:5002/api/health" | grep -q "status.*ok"; then
  echo -e "${GREEN}✓ API 健康检查通过${NC}"
else
  echo -e "${RED}✗ API 健康检查失败${NC}"
fi

# 5. 检查前端文件
echo -e "\n${YELLOW}5. 检查前端文件...${NC}"
if [ -f "/opt/lumon-srt/frontend/index.html" ]; then
  echo -e "${GREEN}✓ 前端文件存在${NC}"
else
  echo -e "${RED}✗ 前端文件不存在${NC}"
fi

# 6. 检查目录权限
echo -e "\n${YELLOW}6. 检查目录权限...${NC}"
if [ -d "/opt/lumon-srt/backend/uploads" ] && [ "$(stat -c '%U' /opt/lumon-srt/backend/uploads)" = "www-data" ]; then
  echo -e "${GREEN}✓ 上传目录权限正确${NC}"
else
  echo -e "${RED}✗ 上传目录权限不正确${NC}"
  echo "尝试修复权限..."
  sudo chown -R www-data:www-data /opt/lumon-srt/backend/uploads
  echo -e "${GREEN}✓ 已修复上传目录权限${NC}"
fi

if [ -d "/opt/lumon-srt/backend/dictionaries" ] && [ "$(stat -c '%U' /opt/lumon-srt/backend/dictionaries)" = "www-data" ]; then
  echo -e "${GREEN}✓ 词典目录权限正确${NC}"
else
  echo -e "${RED}✗ 词典目录权限不正确${NC}"
  echo "尝试修复权限..."
  sudo chown -R www-data:www-data /opt/lumon-srt/backend/dictionaries
  echo -e "${GREEN}✓ 已修复词典目录权限${NC}"
fi

# 7. 检查外部访问
echo -e "\n${YELLOW}7. 检查外部访问...${NC}"
echo -e "${YELLOW}请尝试在浏览器中访问以下地址：${NC}"
echo -e "   http://${DOMAIN}"
echo -e "   http://${DOMAIN}/api/health"

# 8. 显示日志路径
echo -e "\n${YELLOW}8. 日志文件位置：${NC}"
echo -e "   Nginx 访问日志: ${YELLOW}/var/log/nginx/access.log${NC}"
echo -e "   Nginx 错误日志: ${YELLOW}/var/log/nginx/error.log${NC}"
echo -e "   应用日志: ${YELLOW}journalctl -u lumon-srt${NC}"

echo -e "\n${YELLOW}====================================================${NC}"
echo -e "${YELLOW}检查完成！${NC}"
echo -e "${YELLOW}====================================================${NC}"
