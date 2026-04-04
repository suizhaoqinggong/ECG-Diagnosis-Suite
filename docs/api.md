# API 文档

## 基础信息

- Base URL: `http://127.0.0.1:8000`
- 交互式文档：`/docs`

完整 schema 以运行中的 OpenAPI 为准，这里只保留当前常用接口。

## 基础接口

### `GET /`

返回 API 基本信息。

### `GET /health`

返回服务健康状态与数据库可用性。

示例：

```json
{
  "status": "healthy",
  "database": {
    "ready": true,
    "error": null
  }
}
```

如果数据库初始化失败，`status` 会变成 `degraded`。

## 诊断接口

### `POST /api/diagnose`

上传单张 ECG 图片并返回诊断结果。

- Content-Type: `multipart/form-data`
- 字段：`file`
- 支持格式：`.png`、`.jpg`、`.jpeg`
- 鉴权：可匿名；带 Bearer token 时会把结果写入当前用户历史

### `POST /api/diagnose-dat`

上传一对同名的 `.dat + .hea` 文件并返回诊断结果。

- Content-Type: `multipart/form-data`
- 字段：重复的 `files`
- 必须同时包含一个 `.dat` 和一个 `.hea`
- 两个文件去掉扩展名后的文件名必须完全一致

### 诊断响应结构

返回值包含以下关键字段：

- `prediction`
- `confidence`
- `severity`
- `icd_code`
- `description`
- `recommendations`
- `top3_predictions`
- `all_probabilities`
- `report`
- `disclaimer`

## 历史与会话

### `GET /api/history`

兼容性保留接口，已弃用，且需要登录。

推荐改用聊天会话接口：

- `GET /api/chat/sessions`
- `POST /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}/messages`
- `POST /api/chat/sessions/{session_id}/messages`

## 认证接口

认证接口前缀为 `/api/auth`：

- `POST /register`
- `POST /login`
- `POST /refresh`
- `POST /logout`
- `GET /me`
- `POST /change-password`
- `POST /delete-account`

`/refresh` 使用 HttpOnly refresh cookie，前端会在 401 后自动尝试刷新 access token。

## cURL 示例

### 图片诊断

```bash
curl -X POST http://127.0.0.1:8000/api/diagnose \
  -F "file=@ecg.png"
```

### `.dat + .hea` 诊断

```bash
curl -X POST http://127.0.0.1:8000/api/diagnose-dat \
  -F "files=@record.dat" \
  -F "files=@record.hea"
```
