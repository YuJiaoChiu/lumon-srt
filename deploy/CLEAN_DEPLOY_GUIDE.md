# Lumon SRT 清理与部署指南

本文档提供了如何使用 `clean_and_deploy.sh` 脚本清理服务器上的旧项目并部署 Lumon SRT 项目的详细说明。

## 脚本功能

`clean_and_deploy.sh` 脚本会执行以下操作：

1. **备份并清理 Nginx 配置**
   - 备份当前所有 Nginx 配置到 `/root/nginx_backup_日期时间/` 目录
   - 清空 `/etc/nginx/sites-enabled/` 目录
   - 重置 Nginx 主配置文件

2. **清理旧应用**
   - 停止并禁用所有可能的旧 Web 服务
   - 备份旧的应用目录（如果存在）到 `/root/app_backup_日期时间/`
   - 删除旧的应用目录

3. **安装必要依赖**
   - 更新系统包
   - 安装 Python、Nginx 和其他必要组件

4. **部署 Lumon SRT 项目**
   - 创建应用目录结构
   - 复制项目文件
   - 设置 Python 虚拟环境
   - 安装 Python 依赖
   - 初始化词典文件
   - 设置正确的目录权限

5. **配置服务**
   - 配置 Nginx
   - 设置 Systemd 服务
   - 可选配置 SSL

## 使用前准备

1. 确保您已经构建了前端项目，并且 `frontend/dist` 目录中包含了构建好的前端文件。

   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

2. 确保您有 root 权限或 sudo 权限。

3. 确保您知道要部署到的域名或服务器 IP 地址。

## 使用方法

1. 进入 `deploy` 目录：

   ```bash
   cd deploy
   ```

2. 确保脚本有执行权限：

   ```bash
   chmod +x clean_and_deploy.sh
   ```

3. 以 root 权限运行脚本，并提供域名或服务器 IP：

   ```bash
   sudo ./clean_and_deploy.sh your-domain.com
   ```

   或者

   ```bash
   sudo ./clean_and_deploy.sh 123.456.789.10
   ```

4. 脚本会询问是否设置 SSL。如果您有域名并希望启用 HTTPS，请输入 `y`；否则输入 `n`。

## 注意事项

1. **数据备份**：脚本会自动备份旧的 Nginx 配置和应用目录，但为了安全起见，建议您在运行脚本前手动备份重要数据。

2. **域名设置**：如果您使用域名，请确保域名已正确解析到您的服务器 IP。

3. **防火墙设置**：确保服务器防火墙允许 HTTP（80 端口）和 HTTPS（443 端口）流量。

   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

4. **SSL 证书**：如果选择设置 SSL，脚本会使用 Certbot 自动获取 Let's Encrypt 证书。这需要您的域名已正确解析到服务器，并且 80 端口可以从外部访问。

## 故障排除

如果部署后遇到问题，请检查以下日志：

- Nginx 错误日志：`/var/log/nginx/error.log`
- 应用日志：`journalctl -u lumon-srt`

常见问题：

1. **502 Bad Gateway**
   - 检查后端服务是否运行：`sudo systemctl status lumon-srt`
   - 检查端口是否正确：后端应该监听 5002 端口

2. **无法上传文件**
   - 检查上传目录权限：`sudo chown -R www-data:www-data /opt/lumon-srt/backend/uploads`
   - 检查 Nginx 配置中的 `client_max_body_size` 设置

3. **SSL 证书问题**
   - 手动运行 Certbot：`sudo certbot --nginx -d your-domain.com`

## 手动恢复

如果需要恢复到部署前的状态：

1. 恢复 Nginx 配置：

   ```bash
   sudo cp -r /root/nginx_backup_日期时间/* /etc/nginx/
   sudo systemctl restart nginx
   ```

2. 恢复应用目录：

   ```bash
   sudo cp -r /root/app_backup_日期时间 /opt/your-old-app
   ```

3. 重新启动旧服务（如果有）。
