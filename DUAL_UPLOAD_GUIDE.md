# 双文件上传功能使用指南

## ✅ 功能已更新

现在前端支持**同时上传.dat和.hea两个文件**！

## 🎯 使用方法

### 方法1：浏览器上传（推荐）

1. **打开前端**: http://localhost:5173

2. **点击上传区域**，文件选择器会打开

3. **同时选择两个文件**:
   - 按住 `Ctrl` (Windows/Linux) 或 `Cmd` (Mac)
   - 点击 `.dat` 文件
   - 点击对应的 `.hea` 文件
   - 点击"打开"

4. **自动上传**: 系统会自动识别并上传这两个文件

5. **查看结果**: 等待AI分析完成，查看诊断结果

### 方法2：拖拽上传

1. 在文件管理器中，**同时选中** `.dat` 和 `.hea` 文件
2. **拖拽到上传区域**
3. 松开鼠标，自动开始上传

### 方法3：命令行测试（开发用）

```bash
# 直接使用 curl
curl -X POST http://127.0.0.1:8000/api/diagnose-dat \
  -F "files=@record.dat" \
  -F "files=@record.hea"
```

## 📝 文件要求

### 必须满足的条件

✅ **两个文件**: 必须同时有 .dat 和 .hea 文件
✅ **文件名相同**: 除了扩展名，文件名必须完全相同
✅ **PTB-XL格式**: 使用wfdb兼容的格式
✅ **大小限制**: 每个文件不超过10MB

### 示例

```
✅ 正确的文件名:
   patient001.dat
   patient001.hea

❌ 错误的文件名:
   patient001.dat
   patient002.hea  (文件名不同)

   record1.dat
   record1.hea.txt (扩展名错误)
```

## 🔄 工作流程

```
用户操作:
1. 选择 .dat + .hea 文件
2. 点击上传

前端处理:
3. 验证文件数量和类型
4. 检查文件名是否匹配
5. 发送到后端

后端处理:
6. 保存两个文件到临时目录
7. 使用wfdb读取.dat文件
8. 重采样到1000采样点
9. 标准化到12导联
10. CardioFormer推理
11. 返回诊断结果
12. 清理临时文件

显示结果:
13. 预测类别和置信度
14. Top-3预测
15. 完整概率分布
16. 医学建议
```

## 🎨 UI提示

上传区域会根据文件类型显示不同的提示：

### 图片上传
```
📸 图片格式: PNG, JPG, JPEG (单文件)
```

### .dat + .hea 上传
```
📁 ECG数据: .dat + .hea (同时选择两个文件)
💡 .dat文件需同时上传对应的.hea文件
提示: 在文件选择器中按住Ctrl/Cmd可多选
```

## ⚠️ 错误处理

系统会智能检测并提示以下错误：

### 错误1: 只上传了一个文件
```
❌ 请同时上传.dat和.hea文件
```
**解决**: 在文件选择器中同时选择两个文件

### 错误2: 文件名不匹配
```
❌ .dat和.hea文件名必须相同
```
**解决**: 确保两个文件的基本名相同（只有扩展名不同）

### 错误3: 格式不支持
```
❌ 必须包含一个.dat文件和一个.hea文件
```
**解决**: 检查文件扩展名是否正确

### 错误4: 信号格式错误
```
❌ 信号数据格式无效，请检查数据完整性
```
**解决**: 检查.dat文件是否损坏，.hea文件格式是否正确

## 🔧 技术细节

### 前端实现
- 使用 `react-dropzone` 支持多文件选择
- `maxFiles: 2` - 最多上传2个文件
- 自动识别文件类型（图片 vs .dat/.hea）
- 文件名匹配验证

### 后端实现
- 新增 `/api/diagnose-dat` 端点
- 接收 `files: List[UploadFile]`
- 自动识别.dat和.hea文件
- 保存到临时目录进行处理
- 处理完成后自动清理

### API端点

#### 单文件上传（图片）
```
POST /api/diagnose
Content-Type: multipart/form-data
Body: file=<image_file>
```

#### 双文件上传（.dat + .hea）
```
POST /api/diagnose-dat
Content-Type: multipart/form-data
Body: files=<dat_file>&files=<hea_file>
```

## 📊 响应示例

```json
{
  "prediction": "心肌梗死",
  "confidence": 0.8289,
  "severity": "严重",
  "icd_code": "I21.0",
  "description": "心电图提示可能存在心肌梗死...",
  "recommendations": [
    "立即就医急诊科",
    "需要紧急冠脉造影评估",
    "遵医嘱服用抗血小板药物"
  ],
  "timestamp": "2026-03-26T10:15:30.123456",
  "all_probabilities": {
    "正常": 0.0113,
    "心肌梗死": 0.8289,
    "ST-T改变": 0.0241,
    "传导障碍": 0.1030,
    "心室肥大": 0.0327
  },
  "top3_predictions": [
    {"class": "心肌梗死", "class_en": "MI", "probability": 0.8289},
    {"class": "传导障碍", "class_en": "CD", "probability": 0.1030},
    {"class": "心室肥大", "class_en": "HYP", "probability": 0.0327}
  ],
  "disclaimer": "本结果仅供参考，不作为临床诊断依据"
}
```

## 💡 使用技巧

### 技巧1: 快速多选
在文件选择器中：
- Windows/Linux: 按住 `Ctrl` 点击文件
- Mac: 按住 `Cmd` 点击文件

### 技巧2: 拖拽上传
- 在文件管理器中选中两个文件
- 直接拖到浏览器上传区域
- 更快捷方便

### 技巧3: 验证文件
上传前检查：
```bash
# 确认文件名相同
ls -l record.*

# 输出应该是:
# record.dat
# record.hea
```

## 🎉 完整示例

假设你有PTB-XL数据文件：
```
data/
  ├── patient001.dat
  └── patient001.hea
```

**步骤:**
1. 打开 http://localhost:5173
2. 点击上传区域
3. 按住 Ctrl/Cmd，选择两个文件
4. 点击"打开"
5. 等待处理（~200-500ms）
6. 查看诊断结果

**就是这么简单！** 🎊

---

## 📚 相关文档

- [API 文档](/Users/azure/ECG-Diagnosis-Suite/docs/api.md)
- [开发指南](/Users/azure/ECG-Diagnosis-Suite/docs/development.md)
- [API文档](http://localhost:8000/docs)
