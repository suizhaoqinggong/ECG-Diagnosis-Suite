"""
Conduction Disorder Detection Service

专门用于识别传导障碍的诊断服务
"""
import torch
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
import cv2

from .resnet1d_model import ResNet1DBaseline, PTBXL_SUPERCLASSES
from .ecg_image_converter import ECGImageToSignal, create_dummy_ecg_signal


class ConductionDisorderDetector:
    """
    传导障碍专项检测器

    传导障碍（Conduction Disorder, CD）是PTB-XL数据集中的第4类
    包括：房室传导阻滞、束支传导阻滞等
    """

    def __init__(
        self,
        model_path: str = None,
        device: str = "cpu"
    ):
        self.device = torch.device(device)
        self.class_index = 3  # 传导障碍在PTB-XL超类中的索引

        # 创建模型
        self.model = ResNet1DBaseline(
            num_classes=5,
            signal_length=1000,
            input_channels=12,
        )

        # 如果有预训练权重，加载
        if model_path and Path(model_path).exists():
            self._load_weights(model_path)

        self.model.to(self.device)
        self.model.eval()

        # 图像转换器
        self.image_converter = ECGImageToSignal(
            signal_length=1000,
            num_leads=12
        )

        print("✅ Conduction Disorder Detector initialized")
        print(f"   Device: {self.device}")
        print(f"   Target class: {PTBXL_SUPERCLASSES[self.class_index]}")

    def _load_weights(self, model_path: str):
        """加载模型权重"""
        print(f"Loading weights from {model_path}...")
        checkpoint = torch.load(model_path, map_location=self.device)

        # 处理不同的checkpoint格式
        if 'model_state' in checkpoint:
            state_dict = checkpoint['model_state']
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            state_dict = checkpoint

        # 移除前缀
        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith('model.'):
                new_state_dict[k[6:]] = v
            else:
                new_state_dict[k] = v

        try:
            self.model.load_state_dict(new_state_dict, strict=False)
            print("✅ Weights loaded successfully")
        except Exception as e:
            print(f"⚠️  Partial weights loaded: {e}")

    def detect_from_image(self, image: np.ndarray) -> Dict:
        """
        从ECG图像检测传导障碍

        Args:
            image: ECG图像数组 [H, W, C] 或 [H, W]

        Returns:
            检测结果字典
        """
        # 转换图像到信号
        signal = self.image_converter(image)

        # 预测
        return self.detect_from_signal(signal.squeeze(0).numpy())

    def detect_from_signal(self, signal: np.ndarray) -> Dict:
        """
        从ECG信号检测传导障碍

        Args:
            signal: ECG信号 [12, 1000]

        Returns:
            检测结果字典
        """
        # 转换为tensor
        signal_tensor = torch.from_numpy(signal).float()
        if signal_tensor.dim() == 2:
            signal_tensor = signal_tensor.unsqueeze(0)
        signal_tensor = signal_tensor.to(self.device)

        # 推理
        with torch.no_grad():
            logits = self.model(signal_tensor)
            probabilities = F.softmax(logits, dim=1)

            # 获取传导障碍的概率
            cd_probability = probabilities[0, self.class_index].item()

            # 获取所有类别的概率
            all_probs = {
                PTBXL_SUPERCLASSES[i]: probabilities[0, i].item()
                for i in range(5)
            }

            # 获取预测类别
            predicted_class = torch.argmax(probabilities, 1).item()
            predicted_label = PTBXL_SUPERCLASSES[predicted_class]

            # 判断是否为传导障碍
            is_cd = (predicted_class == self.class_index)

            result = {
                "is_conduction_disorder": is_cd,
                "prediction": predicted_label,
                "conduction_disorder_probability": cd_probability,
                "confidence": probabilities[0, predicted_class].item(),
                "all_probabilities": all_probs,
                "risk_level": self._get_risk_level(cd_probability),
                "description": self._get_description(cd_probability),
            }

        return result

    def _get_risk_level(self, probability: float) -> str:
        """
        根据概率评估风险等级

        Args:
            probability: 传导障碍概率

        Returns:
            风险等级
        """
        if probability >= 0.7:
            return "高风险"
        elif probability >= 0.4:
            return "中等风险"
        elif probability >= 0.2:
            return "低风险"
        else:
            return "正常"

    def _get_description(self, probability: float) -> str:
        """获取描述信息"""
        if probability >= 0.7:
            return (
                "⚠️ 高度怀疑传导障碍！心电图显示明显的传导异常特征。"
                "建议立即就医心内科进行详细检查，可能需要进行动态心电图监测。"
            )
        elif probability >= 0.4:
            return (
                "⚡ 存在传导障碍可能性。心电图显示一些可疑的传导异常迹象。"
                "建议尽快就医心内科进行评估和确诊。"
            )
        elif probability >= 0.2:
            return (
                "ℹ️ 传导障碍风险较低，但不能完全排除。"
                "建议定期复查心电图，如有不适症状及时就医。"
            )
        else:
            return (
                "✅ 心电图传导功能正常。"
                "未发现明显的传导障碍迹象。"
            )

    def analyze_features(self, signal: np.ndarray) -> Dict:
        """
        分析传导障碍的特征

        Args:
            signal: ECG信号 [12, 1000]

        Returns:
            特征分析结果
        """
        features = {}

        # 简化的特征分析（实际应用中需要更复杂的算法）
        # 1. 检查PR间期（房室传导）
        # 2. 检查QRS波群宽度（室内传导）
        # 3. 检查束支传导特征

        # 这里使用简化的规则作为演示
        for lead_idx in range(min(12, signal.shape[0])):
            lead_signal = signal[lead_idx]

            # 简单的特征提取
            # 实际应用中需要使用更复杂的算法
            features[f"lead_{lead_idx+1}"] = {
                "signal_quality": float(np.std(lead_signal)),
                "baseline_stability": float(np.mean(np.abs(np.diff(lead_signal)))),
            }

        return features

    def test_detector(self):
        """测试检测器"""
        print("\n🧪 Testing Conduction Disorder Detector...")

        # 创建测试信号
        test_signal = create_dummy_ecg_signal(
            signal_length=1000,
            num_leads=12
        )

        # 检测
        result = self.detect_from_signal(test_signal.squeeze(0).numpy())

        print("\n📊 Detection Result:")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Is Conduction Disorder: {result['is_conduction_disorder']}")
        print(f"   CD Probability: {result['conduction_disorder_probability']:.2%}")
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Description: {result['description']}")

        print("\n   All Probabilities:")
        for cls, prob in result['all_probabilities'].items():
            print(f"     {cls}: {prob:.2%}")

        return result


# 创建便捷函数
def create_cd_detector(model_path: str = None, device: str = "cpu") -> ConductionDisorderDetector:
    """
    创建传导障碍检测器

    Args:
        model_path: 模型权重路径（可选）
        device: 设备

    Returns:
        ConductionDisorderDetector实例
    """
    return ConductionDisorderDetector(model_path=model_path, device=device)


if __name__ == "__main__":
    # 测试检测器
    detector = create_cd_detector()
    result = detector.test_detector()

    print("\n✅ Conduction Disorder Detector is ready!")
