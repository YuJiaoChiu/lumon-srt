#!/bin/bash

# 前后端通信测试脚本
# 使用方法: ./test_communication.sh [域名]

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
echo -e "${YELLOW}开始测试前后端通信...${NC}"
echo -e "${YELLOW}====================================================${NC}"

# 1. 检查后端API是否可直接访问
echo -e "\n${YELLOW}1. 检查后端API是否可直接访问...${NC}"
BACKEND_RESPONSE=$(curl -s http://localhost:5002/api/health)
if [[ $BACKEND_RESPONSE == *"status"*"ok"* ]]; then
  echo -e "${GREEN}✓ 后端API可直接访问${NC}"
  echo -e "   响应: $BACKEND_RESPONSE"
else
  echo -e "${RED}✗ 后端API无法直接访问${NC}"
  echo -e "   尝试启动后端服务..."
  sudo systemctl restart lumon-srt
  sleep 2
  BACKEND_RESPONSE=$(curl -s http://localhost:5002/api/health)
  if [[ $BACKEND_RESPONSE == *"status"*"ok"* ]]; then
    echo -e "${GREEN}✓ 重启后端服务后，API可直接访问${NC}"
    echo -e "   响应: $BACKEND_RESPONSE"
  else
    echo -e "${RED}✗ 后端API仍然无法直接访问${NC}"
  fi
fi

# 2. 检查通过Nginx代理的API是否可访问
echo -e "\n${YELLOW}2. 检查通过Nginx代理的API是否可访问...${NC}"
PROXY_RESPONSE=$(curl -s http://${DOMAIN}/api/health)
if [[ $PROXY_RESPONSE == *"status"*"ok"* ]]; then
  echo -e "${GREEN}✓ 通过Nginx代理的API可访问${NC}"
  echo -e "   响应: $PROXY_RESPONSE"
else
  echo -e "${RED}✗ 通过Nginx代理的API无法访问${NC}"
  echo -e "   检查Nginx配置..."
  sudo nginx -t
  echo -e "   重启Nginx..."
  sudo systemctl restart nginx
  sleep 2
  PROXY_RESPONSE=$(curl -s http://${DOMAIN}/api/health)
  if [[ $PROXY_RESPONSE == *"status"*"ok"* ]]; then
    echo -e "${GREEN}✓ 重启Nginx后，通过代理的API可访问${NC}"
    echo -e "   响应: $PROXY_RESPONSE"
  else
    echo -e "${RED}✗ 通过Nginx代理的API仍然无法访问${NC}"
    echo -e "   请检查Nginx配置和防火墙设置"
  fi
fi

# 3. 检查前端文件是否可访问
echo -e "\n${YELLOW}3. 检查前端文件是否可访问...${NC}"
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://${DOMAIN}/)
if [[ $FRONTEND_RESPONSE == "200" ]]; then
  echo -e "${GREEN}✓ 前端文件可访问${NC}"
else
  echo -e "${RED}✗ 前端文件无法访问 (HTTP状态码: $FRONTEND_RESPONSE)${NC}"
  echo -e "   检查前端文件是否存在..."
  if [ -f "/opt/lumon-srt/frontend/index.html" ]; then
    echo -e "${GREEN}✓ 前端文件存在${NC}"
    echo -e "   检查Nginx配置..."
    sudo nginx -t
    echo -e "   重启Nginx..."
    sudo systemctl restart nginx
    sleep 2
    FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://${DOMAIN}/)
    if [[ $FRONTEND_RESPONSE == "200" ]]; then
      echo -e "${GREEN}✓ 重启Nginx后，前端文件可访问${NC}"
    else
      echo -e "${RED}✗ 前端文件仍然无法访问${NC}"
    fi
  else
    echo -e "${RED}✗ 前端文件不存在${NC}"
    echo -e "   请确保前端已构建并复制到正确位置"
  fi
fi

# 4. 模拟前端到后端的API请求
echo -e "\n${YELLOW}4. 模拟前端到后端的API请求...${NC}"
echo -e "   测试获取词典..."
DICT_RESPONSE=$(curl -s http://${DOMAIN}/api/dictionaries/protection)
if [[ $DICT_RESPONSE == *"{"* ]]; then
  echo -e "${GREEN}✓ 成功获取保护词典${NC}"
  echo -e "   响应: $DICT_RESPONSE"
else
  echo -e "${RED}✗ 无法获取保护词典${NC}"
  echo -e "   响应: $DICT_RESPONSE"
fi

# 5. 浏览器访问测试
echo -e "\n${YELLOW}5. 浏览器访问测试...${NC}"
echo -e "   请在浏览器中访问以下URL，并检查前端是否能正常加载和与后端通信："
echo -e "   http://${DOMAIN}"
echo -e "   在页面加载后，检查是否能看到词典内容，这表明前端成功与后端通信。"

echo -e "\n${YELLOW}====================================================${NC}"
echo -e "${YELLOW}通信测试完成！${NC}"
echo -e "${YELLOW}====================================================${NC}"

# 6. 提供故障排除建议
echo -e "\n${YELLOW}6. 故障排除建议：${NC}"
echo -e "   如果测试失败，请检查以下内容："
echo -e "   - 后端服务是否运行: ${YELLOW}sudo systemctl status lumon-srt${NC}"
echo -e "   - Nginx是否运行: ${YELLOW}sudo systemctl status nginx${NC}"
echo -e "   - Nginx配置是否正确: ${YELLOW}sudo nginx -t${NC}"
echo -e "   - 防火墙是否允许HTTP流量: ${YELLOW}sudo ufw status${NC}"
echo -e "   - 查看后端日志: ${YELLOW}sudo journalctl -u lumon-srt${NC}"
echo -e "   - 查看Nginx错误日志: ${YELLOW}sudo tail -f /var/log/nginx/error.log${NC}"
