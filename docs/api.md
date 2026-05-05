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

当前历史能力统一走聊天会话接口：

- `GET /api/chat/sessions`
- `POST /api/chat/sessions`
- `PATCH /api/chat/sessions/{session_id}`
- `DELETE /api/chat/sessions/{session_id}`
- `DELETE /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}/messages`
- `POST /api/chat/sessions/{session_id}/messages`

## 健康分析接口

### `POST /api/health/jobs`

创建统一的健康分析任务。

- Content-Type: `multipart/form-data`
- 字段：可重复的 `files`（支持 `.pdf`、`.png`、`.jpg`、`.jpeg`、`.dat`、`.hea`），可选的 `note`（临床备注），可选的 `session_id`
- 鉴权：可匿名；带 Bearer token 时结果会关联到当前用户
- 报告图片会在配置 `OPENAI_HEALTH_VISION_MODEL` 和对应 API 凭证后走视觉提取；文件名包含 `ecg` / `lead` / `心电图` 的图片会路由到 ECG AI 分析
- 返回 `queued` 状态的任务 ID

### `GET /api/health/jobs/{job_id}`

轮询健康分析任务的状态与结果。

- 返回 `queued`、`processing`、`completed` 或 `failed` 状态
- `completed` 时附带 `result`（含 `summary`、`overallRisk`、`findings`、`nextSteps`、`limitations`、`disclaimer`，以及可选的 `ecgResult`）
- `findings` 的关键字段包括 `sourceType`、`title`、`summary`、`severity`、`actionHint`、`evidence`
- `failed` 时附带 `error` 字段说明失败原因

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
