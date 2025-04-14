# Lumon SRT 宝塔 Docker 部署指南

本文档提供了在宝塔面板上使用 Docker 部署 Lumon SRT 字幕术语修正系统的详细步骤。

## 系统要求

- 宝塔面板 7.7.0 或更高版本
- Docker 和 Docker Compose（可通过宝塔面板安装）
- 域名（可选，用于 HTTPS 配置）

## 部署步骤

### 1. 在宝塔面板上安装 Docker

1. 登录宝塔面板
2. 进入软件商店，搜索并安装 Docker 管理器
3. 安装完成后，确保 Docker 和 Docker Compose 都已正确安装

### 2. 上传项目文件

1. 将整个项目上传到服务器，例如上传到 `/www/wwwroot/lumon-srt` 目录
2. 确保文件权限正确：
   ```bash
   chown -R www:www /www/wwwroot/lumon-srt
   chmod -R 755 /www/wwwroot/lumon-srt
   ```

### 3. 构建前端

1. 在服务器上安装 Node.js（可通过宝塔面板安装）
2. 进入前端目录并构建：
   ```bash
   cd /www/wwwroot/lumon-srt/frontend
   npm install
   npm run build
   ```

### 4. 运行部署脚本

1. 进入 deploy 目录：
   ```bash
   cd /www/wwwroot/lumon-srt/deploy
   ```

2. 给部署脚本添加执行权限：
   ```bash
   chmod +x baota_deploy.sh
   ```

3. 运行部署脚本，提供你的域名或服务器 IP：
   ```bash
   ./baota_deploy.sh your-domain.com
   ```
   如果不提供域名，将使用 localhost。

### 5. 配置宝塔面板中的网站

1. 在宝塔面板中创建一个新网站，指向 Docker 容器的端口
2. 网站配置：
   - 域名：your-domain.com
   - 端口：80
   - 反向代理：将所有请求转发到 http://127.0.0.1:80

3. 如果需要 HTTPS，可以在宝塔面板中为该网站申请 SSL 证书

## 目录结构说明

部署后，文件结构将如下：

```
/www/wwwroot/lumon-srt/
├── backend/             # Python 后端代码
├── frontend/            # React 前端代码
│   └── dist/            # 构建后的前端文件
├── deploy/              # 部署相关文件
│   ├── baota_deploy.sh  # 宝塔部署脚本
│   ├── Dockerfile       # Docker 配置文件
│   ├── docker-compose.yml # Docker Compose 配置
│   ├── nginx/           # Nginx 配置
│   ├── dictionaries/    # 词典文件（Docker 卷）
│   └── uploads/         # 上传文件（Docker 卷）
└── docs/                # 文档
```

## 数据持久化

Docker 部署使用卷来持久化数据：

- `dictionaries` 目录：存储词典文件
- `uploads` 目录：存储上传的文件

这些目录会被挂载到 Docker 容器中，确保数据在容器重启后仍然存在。

## 维护与更新

### 查看容器状态

```bash
cd /www/wwwroot/lumon-srt/deploy
docker-compose ps
```

### 查看日志

```bash
cd /www/wwwroot/lumon-srt/deploy
docker-compose logs
```

### 重启服务

```bash
cd /www/wwwroot/lumon-srt/deploy
docker-compose restart
```

### 更新应用

1. 拉取最新代码：
   ```bash
   cd /www/wwwroot/lumon-srt
   git pull
   ```

2. 重新构建前端：
   ```bash
   cd /www/wwwroot/lumon-srt/frontend
   npm install
   npm run build
   ```

3. 重新部署：
   ```bash
   cd /www/wwwroot/lumon-srt/deploy
   docker-compose down
   ./baota_deploy.sh your-domain.com
   ```

## 故障排除

### 容器无法启动

检查 Docker 日志：
```bash
cd /www/wwwroot/lumon-srt/deploy
docker-compose logs
```

### 网站无法访问

1. 检查 Docker 容器是否正在运行：
   ```bash
   docker ps
   ```

2. 检查宝塔面板中的网站配置，确保反向代理设置正确

3. 检查防火墙设置，确保端口 80 和 443（如果使用 HTTPS）已开放

### 文件上传问题

检查 `uploads` 目录的权限：
```bash
chmod -R 777 /www/wwwroot/lumon-srt/deploy/uploads
```

## 安全建议

1. 修改默认的词典 PIN 码（在 `backend/app.py` 中的 `DICTIONARY_PIN` 变量）

2. 配置 HTTPS 以加密传输数据

3. 定期备份 `dictionaries` 目录中的词典文件
