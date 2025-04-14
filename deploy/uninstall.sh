#!/bin/bash

# 卸载脚本 - 完全卸载 Lumon SRT 项目
# 使用方法: sudo ./uninstall.sh

set -e

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
  echo "请以 root 权限运行此脚本"
  exit 1
fi

APP_DIR="/opt/lumon-srt"
NGINX_CONF="/etc/nginx/sites-available/lumon-srt"
NGINX_ENABLED="/etc/nginx/sites-enabled/lumon-srt"
SYSTEMD_SERVICE="/etc/systemd/system/lumon-srt.service"

echo "====================================================="
echo "开始卸载 Lumon SRT 项目..."
echo "====================================================="

# 询问确认
echo "此操作将完全删除 Lumon SRT 项目，包括："
echo "- 应用程序文件"
echo "- Nginx 配置"
echo "- Systemd 服务"
echo "- 所有上传的文件和词典"
echo ""
echo "是否继续？(y/n)"
read -p ">" choice

if [ "$choice" != "y" ] && [ "$choice" != "Y" ]; then
  echo "卸载已取消"
  exit 0
fi

# 1. 停止并禁用服务
echo "1. 停止并禁用服务..."
echo "---------------------------------------------------"
if systemctl is-active --quiet lumon-srt; then
  systemctl stop lumon-srt
  systemctl disable lumon-srt
  echo "已停止并禁用 lumon-srt 服务"
else
  echo "lumon-srt 服务未运行"
fi

# 2. 删除 Systemd 服务文件
echo "2. 删除 Systemd 服务文件..."
echo "---------------------------------------------------"
if [ -f "$SYSTEMD_SERVICE" ]; then
  rm -f $SYSTEMD_SERVICE
  systemctl daemon-reload
  echo "已删除 Systemd 服务文件"
else
  echo "Systemd 服务文件不存在"
fi

# 3. 删除 Nginx 配置
echo "3. 删除 Nginx 配置..."
echo "---------------------------------------------------"
if [ -f "$NGINX_CONF" ]; then
  rm -f $NGINX_CONF
  echo "已删除 Nginx 配置文件"
else
  echo "Nginx 配置文件不存在"
fi

if [ -f "$NGINX_ENABLED" ]; then
  rm -f $NGINX_ENABLED
  echo "已删除 Nginx 启用的配置链接"
else
  echo "Nginx 启用的配置链接不存在"
fi

# 重启 Nginx
systemctl restart nginx
echo "已重启 Nginx"

# 4. 删除应用目录
echo "4. 删除应用目录..."
echo "---------------------------------------------------"
if [ -d "$APP_DIR" ]; then
  # 询问是否备份
  echo "是否在删除前备份应用目录？(y/n)"
  read -p ">" backup_choice
  
  if [ "$backup_choice" = "y" ] || [ "$backup_choice" = "Y" ]; then
    BACKUP_DIR="/root/lumon_backup_$(date +%Y%m%d_%H%M%S)"
    cp -r $APP_DIR $BACKUP_DIR
    echo "已备份应用目录到 $BACKUP_DIR"
  fi
  
  rm -rf $APP_DIR
  echo "已删除应用目录"
else
  echo "应用目录不存在"
fi

echo "====================================================="
echo "卸载完成！"
echo "====================================================="
echo "Lumon SRT 项目已完全卸载。"
if [ "$backup_choice" = "y" ] || [ "$backup_choice" = "Y" ]; then
  echo "备份文件位于: $BACKUP_DIR"
fi
