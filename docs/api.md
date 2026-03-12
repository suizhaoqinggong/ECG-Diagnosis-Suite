# API文档

## 基础信息

**Base URL**: `http://localhost:8000`

**版本**: v1.0.0

---

## 端点列表

### 1. 根路径

**GET /**

返回API基本信息。

**响应示例**:
```json
{
  "message": "Welcome to ECG Diagnosis Suite API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### 2. 健康检查

**GET /health**

检查服务状态。

**响应示例**:
```json
{
  "status": "healthy"
}
```

---

### 3. ECG诊断

**POST /api/diagnose**

上传ECG图片并获取诊断结果。

**请求**:
- Content-Type: `multipart/form-data`
- Body: `file` (图片文件)

**响应示例**:
```json
{
  "prediction": "房颤",
  "confidence": 0.92,
  "severity": "中等",
  "icd_code": "I48.0",
  "description": "房颤是一种常见的心律失常...",
  "recommendations": [
    "建议尽快就医心内科",
    "避免剧烈运动和情绪激动"
  ],
  "timestamp": "2026-03-12T10:30:00",
  "disclaimer": "本结果仅供参考，不作为临床诊断依据"
}
```

**错误响应**:
- `400 Bad Request`: 文件类型不支持
- `422 Unprocessable Entity`: 缺少文件
- `500 Internal Server Error`: 服务器错误

---

### 4. 历史记录

**GET /api/history**

获取诊断历史记录。

**响应示例**:
```json
{
  "message": "功能开发中"
}
```

---

## 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求错误 |
| 401 | 未授权 |
| 404 | 未找到 |
| 422 | 验证错误 |
| 500 | 服务器错误 |

---

## 使用示例

### cURL

```bash
# 上传图片诊断
curl -X POST "http://localhost:8000/api/diagnose" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@ecg.png"
```

### Python (requests)

```python
import requests

url = "http://localhost:8000/api/diagnose"
files = {"file": open("ecg.png", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

### JavaScript (axios)

```javascript
import axios from 'axios';

const formData = new FormData();
formData.append('file', file);

const response = await axios.post(
  'http://localhost:8000/api/diagnose',
  formData,
  { headers: { 'Content-Type': 'multipart/form-data' } }
);

console.log(response.data);
```

---

## 交互式文档

启动服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
