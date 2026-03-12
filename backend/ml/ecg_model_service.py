"""
ECG Model Service with ResNet1D Integration
"""
import torch
import torch.nn.functional as F
from typing import Dict, List, Optional
import numpy as np
from pathlib import Path

from .resnet1d_model import (
    ResNet1DBaseline,
    create_resnet1d_model,
    PTBXL_SUPERCLASSES
)
from .ecg_image_converter import ECGImageToSignal, create_dummy_ecg_signal


class ECGModelService:
    """ECG诊断模型服务"""

    def __init__(
        self,
        model_type: str = "resnet1d",
        model_path: Optional[str] = None,
        num_classes: int = 5,
        signal_length: int = 1000,
        input_channels: int = 12,
        device: str = "cpu"
    ):
        self.device = torch.device(device)
        self.model_type = model_type
        self.signal_length = signal_length
        self.input_channels = input_channels
        self.num_classes = num_classes

        # 加载模型
        if model_type == "resnet1d":
            self.model = create_resnet1d_model(
                num_classes=num_classes,
                signal_length=signal_length,
                input_channels=input_channels,
                pretrained=model_path is not None,
                checkpoint_path=model_path
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        self.model.to(self.device)
        self.model.eval()

        # 创建图像转换器
        self.image_converter = ECGImageToSignal(
            signal_length=signal_length,
            num_leads=input_channels
        )

        # 类别名称
        self.class_names = PTBXL_SUPERCLASSES[:num_classes]

        print(f"✅ Model service initialized: {model_type}")
        print(f"   Device: {self.device}")
        print(f"   Classes: {self.class_names}")

    def preprocess_image(self, image_array: np.ndarray) -> torch.Tensor:
        """
        预处理ECG图像

        Args:
            image_array: 图像数组 [H, W, C] 或 [H, W]

        Returns:
            处理后的tensor [1, num_leads, signal_length]
        """
        # 将图像转换为信号
        signal_tensor = self.image_converter(image_array)

        return signal_tensor.to(self.device)

    def predict(
        self,
        image_array: np.ndarray,
        return_probs: bool = True
    ) -> Dict:
        """
        对ECG图像进行预测

        Args:
            image_array: ECG图像数组
            return_probs: 是否返回所有类别的概率

        Returns:
            预测结果字典
        """
        # 预处理
        input_tensor = self.preprocess_image(image_array)

        # 推理
        with torch.no_grad():
            logits = self.model(input_tensor)
            probabilities = F.softmax(logits, dim=1)

            # 获取top-1预测
            confidence, predicted = torch.max(probabilities, 1)

            result = {
                "prediction": self.class_names[predicted.item()],
                "confidence": float(confidence.item()),
                "class_index": int(predicted.item()),
            }

            # 返回所有类别的概率
            if return_probs:
                all_probs = probabilities[0].cpu().numpy()
                result["all_probabilities"] = {
                    name: float(prob)
                    for name, prob in zip(self.class_names, all_probs)
                }

                # Top-3预测
                top3_probs, top3_indices = torch.topk(probabilities[0], k=min(3, len(self.class_names)))
                result["top3_predictions"] = [
                    {
                        "class": self.class_names[idx.item()],
                        "probability": float(prob.item())
                    }
                    for idx, prob in zip(top3_indices, top3_probs)
                ]

        return result

    def predict_from_signal(
        self,
        signal: np.ndarray,
        return_probs: bool = True
    ) -> Dict:
        """
        直接从ECG信号进行预测（跳过图像处理）

        Args:
            signal: ECG信号数组 [num_leads, signal_length]
            return_probs: 是否返回所有类别的概率

        Returns:
            预测结果字典
        """
        # 转换为tensor
        signal_tensor = torch.from_numpy(signal).float()
        if signal_tensor.dim() == 2:
            signal_tensor = signal_tensor.unsqueeze(0)  # 添加batch维度

        signal_tensor = signal_tensor.to(self.device)

        # 推理
        with torch.no_grad():
            logits = self.model(signal_tensor)
            probabilities = F.softmax(logits, dim=1)

            confidence, predicted = torch.max(probabilities, 1)

            result = {
                "prediction": self.class_names[predicted.item()],
                "confidence": float(confidence.item()),
                "class_index": int(predicted.item()),
            }

            if return_probs:
                all_probs = probabilities[0].cpu().numpy()
                result["all_probabilities"] = {
                    name: float(prob)
                    for name, prob in zip(self.class_names, all_probs)
                }

                top3_probs, top3_indices = torch.topk(probabilities[0], k=min(3, len(self.class_names)))
                result["top3_predictions"] = [
                    {
                        "class": self.class_names[idx.item()],
                        "probability": float(prob.item())
                    }
                    for idx, prob in zip(top3_indices, top3_probs)
                ]

        return result

    def test_with_dummy_signal(self) -> Dict:
        """
        使用虚拟信号测试模型

        Returns:
            测试结果
        """
        print("🧪 Testing with dummy ECG signal...")

        # 创建虚拟信号
        dummy_signal = create_dummy_ecg_signal(
            signal_length=self.signal_length,
            num_leads=self.input_channels
        )

        # 预测
        result = self.predict_from_signal(dummy_signal.squeeze(0).numpy())

        print("✅ Test completed")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['confidence']:.2%}")

        return result


if __name__ == "__main__":
    # 测试服务
    service = ECGModelService(
        model_type="resnet1d",
        num_classes=5,
        device="cpu"
    )

    # 测试虚拟信号
    result = service.test_with_dummy_signal()
    print("\n📊 Test Result:")
    print(f"Prediction: {result['prediction']}")
    print(f"Confidence: {result['confidence']:.2%}")

    if 'top3_predictions' in result:
        print("\nTop-3 Predictions:")
        for i, pred in enumerate(result['top3_predictions'], 1):
            print(f"  {i}. {pred['class']}: {pred['probability']:.2%}")
