# Lumon SRT API 文档

本文档描述了 Lumon SRT 字幕术语修正系统的 API 接口。

## 基本信息

- 基础 URL: `http://your-server.com/api`
- 所有请求和响应均使用 JSON 格式
- 所有请求都应包含 `Content-Type: application/json` 头部
- 错误响应包含 `error` 字段，描述错误原因

## 健康检查

### 获取 API 状态

```
GET /health
```

**响应示例:**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": 1625097600
}
```

## 词典管理

### 获取矫正词典

```
GET /dictionaries/correction
```

**响应示例:**

```json
{
  "错误术语1": "正确术语1",
  "错误术语2": "正确术语2"
}
```

### 更新矫正词典

```
POST /dictionaries/correction
```

**请求参数:**

```json
{
  "pin": "1324",
  "dictionary": {
    "错误术语1": "正确术语1",
    "错误术语2": "正确术语2"
  }
}
```

**响应示例:**

```json
{
  "status": "success",
  "message": "Correction dictionary updated",
  "count": 2
}
```

### 获取保护词典

```
GET /dictionaries/protection
```

**响应示例:**

```json
{
  "保护术语1": "",
  "保护术语2": ""
}
```

### 更新保护词典

```
POST /dictionaries/protection
```

**请求参数:**

```json
{
  "pin": "1324",
  "dictionary": {
    "保护术语1": "",
    "保护术语2": ""
  }
}
```

**响应示例:**

```json
{
  "status": "success",
  "message": "Protection dictionary updated",
  "count": 2
}
```

### 更新单个术语

```
POST /dictionaries/update-term
```

**请求参数:**

```json
{
  "pin": "1324",
  "type": "correction",  // 或 "protection"
  "term": "术语",
  "value": "修正值",  // 对于保护词典，此值通常为空字符串
  "action": "add"  // 可选值: "add", "update", "delete"
}
```

**响应示例:**

```json
{
  "status": "success",
  "message": "Term '术语' added in correction dictionary",
  "count": 10
}
```

### 搜索术语

```
GET /dictionaries/search?q=搜索词&type=all
```

**查询参数:**

- `q`: 搜索关键词
- `type`: 搜索类型，可选值: `all`, `correction`, `protection`

**响应示例:**

```json
{
  "results": {
    "correction": {
      "错误术语1": "正确术语1"
    },
    "protection": {
      "保护术语1": ""
    }
  }
}
```

## 文件处理

### 处理 SRT 文件

```
POST /process
```

**请求参数:**

- 使用 `multipart/form-data` 格式
- 文件字段名: `files` (可以包含多个文件)

**响应示例:**

```json
{
  "status": "success",
  "message": "Processing started for 2 files",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 获取任务状态

```
GET /tasks/{task_id}
```

**响应示例 (处理中):**

```json
{
  "status": "processing",
  "progress": 45.5,
  "created_at": 1625097600
}
```

**响应示例 (已完成):**

```json
{
  "status": "completed",
  "progress": 100,
  "created_at": 1625097600,
  "results": [
    {
      "original_filename": "example.srt",
      "corrected_filename": "example_corrected.srt",
      "replacements": {
        "错误术语1 -> 正确术语1": 5,
        "错误术语2 -> 正确术语2": 3
      },
      "download_url": "/api/download/example_corrected.srt",
      "status": "success"
    }
  ],
  "statistics": {
    "totalFiles": 1,
    "filesProcessed": 1,
    "totalCorrections": 8,
    "processingTime": 1.25
  }
}
```

### 下载处理后的文件

```
GET /download/{filename}
```

**响应:**

- 文件内容，带有 `Content-Disposition: attachment` 头部

## 错误处理

所有 API 错误都会返回适当的 HTTP 状态码和包含 `error` 字段的 JSON 响应。

**示例:**

```json
{
  "error": "Invalid PIN code"
}
```

常见错误状态码:

- `400 Bad Request`: 请求参数无效
- `403 Forbidden`: PIN 码无效
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误
