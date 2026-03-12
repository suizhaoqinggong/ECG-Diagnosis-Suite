"""
Diagnosis API endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from datetime import datetime

router = APIRouter()


class DiagnosisResponse(BaseModel):
    prediction: str
    confidence: float
    severity: Optional[str] = None
    icd_code: Optional[str] = None
    description: Optional[str] = None
    recommendations: Optional[List[str]] = None
    timestamp: str
    disclaimer: str = "本结果仅供参考，不作为临床诊断依据"


# 模拟症状数据库
SYMPTOM_DATABASE = {
    "正常": {
        "severity": "正常",
        "icd_code": "R00.0",
        "description": "心电图波形正常，未发现明显异常。",
        "recommendations": [
            "保持健康的生活方式",
            "定期体检",
            "适量运动",
        ],
    },
    "房颤": {
        "severity": "中等",
        "icd_code": "I48.0",
        "description": "房颤是一种常见的心律失常，心房跳动不规则且快速，可能导致血栓形成。",
        "recommendations": [
            "建议尽快就医心内科",
            "避免剧烈运动和情绪激动",
            "定期监测心率和血压",
            "遵医嘱服用抗凝药物",
            "戒烟限酒，保持健康生活方式",
        ],
    },
    # 可以添加更多症状...
}


@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose_ecg(file: UploadFile = File(...)):
    """
    上传ECG图片并获取诊断结果
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    # 保存上传的文件
    upload_dir = "./data/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(upload_dir, f"{timestamp}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # TODO: 这里调用实际的模型推理
        # result = await model.predict(file_path)

        # 临时返回模拟数据
        prediction = "正常"  # 模拟预测结果
        confidence = 0.95  # 模拟置信度

        # 从数据库获取症状信息
        symptom_info = SYMPTOM_DATABASE.get(prediction, {})

        return DiagnosisResponse(
            prediction=prediction,
            confidence=confidence,
            severity=symptom_info.get("severity"),
            icd_code=symptom_info.get("icd_code"),
            description=symptom_info.get("description"),
            recommendations=symptom_info.get("recommendations"),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        # 清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")


@router.get("/history")
async def get_diagnosis_history():
    """
    获取诊断历史记录
    """
    # TODO: 从数据库查询历史记录
    return {"message": "功能开发中"}
