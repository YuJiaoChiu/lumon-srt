# Lumon SRT Linux 部署指南

本文档提供了在 Ubuntu Linux 系统上部署 Lumon SRT 字幕术语修正系统的简要步骤。

## 系统要求

- Ubuntu 20.04 LTS 或更高版本
- Python 3.9 或更高版本
- Nginx
- 域名（可选，用于 HTTPS 配置）

## 部署方法

### 方法一：使用自动部署脚本（推荐）

1. 将项目代码复制到服务器：

```bash
git clone <项目仓库地址>
cd lumon-srt
```

2. 如果需要在服务器上构建前端，请先安装 Node.js 并构建：

```bash
# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs

# 构建前端
cd frontend
npm install
npm run build
cd ..
```

3. 运行部署脚本：

```bash
cd deploy
chmod +x deploy.sh
sudo ./deploy.sh your-domain.com  # 替换为你的域名或服务器 IP
```

### 方法二：手动部署

如果你想手动部署，请按照 `docs/LINUX_DEPLOYMENT.md` 中的详细步骤操作。

## 验证部署

部署完成后，你可以通过以下方式验证部署是否成功：

1. 访问你的域名或服务器 IP，应该能看到前端界面
2. 检查后端 API 是否正常工作：`curl http://your-domain.com/api/health`
3. 检查服务状态：`sudo systemctl status lumon-srt`
4. 检查 Nginx 状态：`sudo systemctl status nginx`

## 故障排除

如果遇到问题，请查看以下日志：

- 后端日志：`sudo journalctl -u lumon-srt`
- Nginx 访问日志：`sudo tail -f /var/log/nginx/access.log`
- Nginx 错误日志：`sudo tail -f /var/log/nginx/error.log`

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
