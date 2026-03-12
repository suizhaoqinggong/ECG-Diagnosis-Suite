"""
Conduction Disorder Detection API

专门的传导障碍检测API端点
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import os
import shutil
from datetime import datetime
import cv2
import numpy as np

# 导入传导障碍检测器
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.conduction_disorder_detector import create_cd_detector

router = APIRouter()

# 初始化检测器（全局单例）
cd_detector = None


def get_detector():
    """获取检测器实例"""
    global cd_detector
    if cd_detector is None:
        cd_detector = create_cd_detector()
    return cd_detector


class ConductionDisorderResult(BaseModel):
    """传导障碍检测结果模型"""
    is_conduction_disorder: bool
    prediction: str
    conduction_disorder_probability: float
    confidence: float
    risk_level: str
    description: str
    all_probabilities: Dict[str, float]
    timestamp: str
    disclaimer: str = "本结果仅供参考，不作为临床诊断依据。如有疑虑，请及时就医咨询专业医生。"


@router.post("/detect/conduction-disorder", response_model=ConductionDisorderResult)
async def detect_conduction_disorder(file: UploadFile = File(...)):
    """
    检测传导障碍

    上传ECG图片，检测是否存在传导障碍

    Args:
        file: ECG图片文件

    Returns:
        ConductionDisorderResult: 检测结果
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    # 保存上传的文件
    upload_dir = "./data/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(upload_dir, f"{timestamp}_{file.filename}")

    try:
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 读取图像
        image = cv2.imread(file_path)
        if image is None:
            raise HTTPException(status_code=400, detail="无法读取图片文件")

        # 获取检测器
        detector = get_detector()

        # 执行检测
        result = detector.detect_from_image(image)

        # 构建响应
        response = ConductionDisorderResult(
            is_conduction_disorder=result["is_conduction_disorder"],
            prediction=result["prediction"],
            conduction_disorder_probability=result["conduction_disorder_probability"],
            confidence=result["confidence"],
            risk_level=result["risk_level"],
            description=result["description"],
            all_probabilities=result["all_probabilities"],
            timestamp=datetime.now().isoformat(),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        # 清理文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.get("/detect/conduction-disorder/info")
async def get_conduction_disorder_info():
    """
    获取传导障碍检测信息

    Returns:
        传导障碍相关的医学信息
    """
    return {
        "name": "传导障碍（Conduction Disorder）",
        "description": "心脏传导系统异常导致的心律失常",
        "types": [
            "房室传导阻滞",
            "右束支传导阻滞",
            "左束支传导阻滞",
            "室内传导阻滞",
        ],
        "symptoms": [
            "心悸",
            "头晕",
            "乏力",
            "晕厥（严重时）",
        ],
        "risk_factors": [
            "器质性心脏病",
            "心肌缺血",
            "药物影响",
            "电解质紊乱",
        ],
        "diagnosis_methods": [
            "心电图（ECG）",
            "动态心电图",
            "电生理检查",
        ],
        "treatment": [
            "药物治疗",
            "起搏器植入（严重时）",
            "治疗原发疾病",
        ],
        "recommendations": {
            "高风险": "立即就医心内科，可能需要紧急治疗",
            "中等风险": "尽快就医心内科进行详细检查",
            "低风险": "定期复查，如有不适症状及时就医",
            "正常": "保持健康生活方式，定期体检",
        },
        "supported_leads": [
            "I, II, III, aVR, aVL, aVF",
            "V1, V2, V3, V4, V5, V6",
        ],
    }


@router.get("/detect/conduction-disorder/stats")
async def get_detection_stats():
    """
    获取检测统计信息（示例）

    Returns:
        检测统计
    """
    return {
        "total_detections": 100,
        "conduction_disorder_detected": 15,
        "risk_distribution": {
            "高风险": 3,
            "中等风险": 5,
            "低风险": 7,
            "正常": 85,
        },
        "accuracy": "95%",
        "model_info": {
            "type": "ResNet1DBaseline",
            "classes": 5,
            "input_channels": 12,
            "signal_length": 1000,
        }
    }
