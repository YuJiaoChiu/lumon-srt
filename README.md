# Lumon SRT - 字幕术语修正系统

这是一个前后端分离的 SRT 字幕术语修正系统，用于自动修正字幕文件中的术语。系统包含矫正词典和保护词典，可以根据规则自动修正字幕文件中的术语。

## 功能特点

- 前后端分离架构，易于部署和维护
- 支持矫正词典和保护词典管理
- PIN码保护的词典管理系统
- 便捷的术语搜索和管理功能
- 支持多文件批量处理和一键下载
- 实时显示处理进度
- 详细的替换统计信息
- 支持深色模式和交互式界面
- 支持在中国的 Linux 服务器上部署

## 系统要求

- Python 3.9 或更高版本
- 现代浏览器（Chrome、Firefox、Edge 等）
- Nginx（用于生产环境部署）
- 支持 HTTPS 的域名（推荐用于生产环境）

## 快速开始

### 本地开发环境

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/srt-correction.git
cd srt-correction
```

2. 安装 Python 依赖：

```bash
pip install -r requirements.txt
```

3. 启动后端服务：

```bash
cd python
python backend.py
```

4. 在浏览器中打开前端页面：

```
frontend/index.html
```

### 生产环境部署

1. 克隆仓库到服务器：

```bash
git clone https://github.com/yourusername/srt-correction.git
cd srt-correction
```

2. 运行部署脚本（需要 root 权限）：

```bash
cd deploy
chmod +x setup.sh
sudo ./setup.sh
```

3. 按照脚本提示完成部署。

## 系统架构

### 前端

- React + TypeScript
- Tailwind CSS 用于 UI 样式
- Vite 构建工具
- Lucide React 图标库

### 后端

- Flask 框架提供 RESTful API
- 支持并发处理多个文件
- 实时进度跟踪
- 基于 `sub2024_9.py` 的字幕修正逻辑

## API 接口

### 健康检查

```
GET /api/health
```

### 词典管理

```
GET /api/dictionaries/correction
POST /api/dictionaries/correction
GET /api/dictionaries/protection
POST /api/dictionaries/protection
POST /api/dictionaries/update-term
GET /api/dictionaries/search
```

### 文件处理

```
POST /api/process
GET /api/tasks/{task_id}
GET /api/download/{filename}
POST /api/download-multiple
```

## 词典规则

### 矫正词典

矫正词典用于定义需要替换的术语。格式为 JSON 对象，其中键是错误的术语，值是正确的术语。

例如：

```json
{
  "错误术语1": "正确术语1",
  "错误术语2": "正确术语2",
  "要删除的术语": ""
}
```

### 保护词典

保护词典用于定义不应被替换的术语。格式为 JSON 对象，其中键是需要保护的术语。

例如：

```json
{
  "保护术语1": "",
  "保护术语2": ""
}
```

## 修正规则

1. 按照矫正词典中的定义替换术语
2. 保护词典中的术语不会被替换
3. 如果一个术语是保护词典中某个术语的一部分，则不会被替换
4. 替换时保持原始大小写格式
5. 删除被括号括起来的行

## 新增功能

### PIN码保护

所有词典修改操作都需要提供PIN码验证，防止未授权的修改。默认PIN码为"1234"。

### 多文件处理

支持同时上传和处理多个文件，并提供一键下载所有处理后的文件。

### 深色模式

支持深色模式，可以在设置中切换。

### 交互式设计

提供丰富的动画和交互效果，提升用户体验。

## 许可证

© 2025 Lumon Industries. 保留所有权利。
