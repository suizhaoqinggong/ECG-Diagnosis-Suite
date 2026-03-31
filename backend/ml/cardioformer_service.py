"""
CardioFormer Service for ECG Diagnosis

Provides a high-level service interface for ECG diagnosis using CardioFormer model.
Supports both image-based and signal-based inference.
"""
import os
import torch
import torch.nn.functional as F
from typing import Dict, Optional
import numpy as np
from pathlib import Path

# Handle both relative and absolute imports
try:
    from .cardioformer_model import (
        CardioFormer,
        create_cardioformer_model,
        PTBXL_SUPERCLASSES
    )
    from .ecg_image_converter import ECGImageToSignal, create_dummy_ecg_signal
except ImportError:
    from cardioformer_model import (
        CardioFormer,
        create_cardioformer_model,
        PTBXL_SUPERCLASSES
    )
    from ecg_image_converter import ECGImageToSignal, create_dummy_ecg_signal


class CardioFormerService:
    """ECG诊断服务 - 基于CardioFormer模型"""

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        num_classes: int = 5,
        signal_length: int = 1000,
        input_channels: int = 12,
        device: str = "cpu",
        threshold: float = 0.5,
        **model_kwargs
    ):
        """
        初始化CardioFormer服务

        Args:
            checkpoint_path: 权重文件路径 (.ckpt 或 .pt)
            num_classes: 分类数量（默认5，对应PTB-XL的5个超类）
            signal_length: 信号长度（默认1000）
            input_channels: 输入通道数（默认12，标准12导联ECG）
            device: 计算设备 ("cpu" 或 "cuda")
            threshold: 多标签检测阈值（默认0.5）
            **model_kwargs: 其他模型参数
        """
        self.device = torch.device(device)
        self.signal_length = signal_length
        self.input_channels = input_channels
        self.num_classes = num_classes
        self.threshold = threshold

        # 创建模型
        self.model = create_cardioformer_model(
            num_classes=num_classes,
            signal_length=signal_length,
            input_channels=input_channels,
            checkpoint_path=checkpoint_path,
            **model_kwargs
        )

        self.model.to(self.device)
        self.model.eval()

        # 创建图像转换器（用于从图像预测）
        self.image_converter = ECGImageToSignal(
            signal_length=signal_length,
            num_leads=input_channels
        )

        # 类别名称
        self.class_names = PTBXL_SUPERCLASSES[:num_classes]

        # 类别中文映射
        self.class_names_zh = {
            "NORM": "正常",
            "MI": "心肌梗死",
            "STTC": "ST-T改变",
            "CD": "传导障碍",
            "HYP": "心室肥大"
        }

        print(f"✅ CardioFormer Service initialized")
        print(f"   Device: {self.device}")
        print(f"   Classes: {self.class_names}")
        print(f"   Checkpoint: {checkpoint_path or 'Random initialization'}")

    def preprocess_signal(self, signal: np.ndarray) -> torch.Tensor:
        """
        预处理ECG信号

        Applies global z-score normalization.  Both the DAT loader and the
        image converter already normalise per-lead before reaching this
        point, so the signal undergoes two normalization steps.  This
        pipeline matches the model's training setup — do not remove either
        step without A/B testing against a held-out set.

        Args:
            signal: 信号数组 [num_leads, signal_length] 或 [signal_length]

        Returns:
            处理后的tensor [1, num_leads, signal_length]
        """
        # 转换为numpy
        if isinstance(signal, torch.Tensor):
            signal = signal.numpy()

        # 确保是2D
        if signal.ndim == 1:
            signal = signal.reshape(1, -1)

        # 归一化到[-1, 1]
        signal = (signal - signal.mean()) / (signal.std() + 1e-8)

        # 转换为tensor
        signal_tensor = torch.from_numpy(signal).float()

        # 确保形状正确
        if signal_tensor.dim() == 2:
            signal_tensor = signal_tensor.unsqueeze(0)  # [1, leads, samples]

        return signal_tensor.to(self.device)

    def predict_from_signal(
        self,
        signal: np.ndarray,
        return_probs: bool = True,
        threshold: Optional[float] = None
    ) -> Dict:
        """
        直接从ECG信号进行预测

        Args:
            signal: ECG信号数组 [num_leads, signal_length]
            return_probs: 是否返回所有类别的概率
            threshold: 多标签检测阈值，None则使用self.threshold

        Returns:
            预测结果字典
        """
        # 预处理
        input_tensor = self.preprocess_signal(signal)

        # 推理
        with torch.no_grad():
            logits = self.model(input_tensor)
            # 使用sigmoid而非softmax：模型以BCE loss训练，属于多标签分类
            probabilities = torch.sigmoid(logits)

            # 获取top-1预测（最高sigmoid概率）
            confidence, predicted = torch.max(probabilities, 1)

            prediction_en = self.class_names[predicted.item()]
            prediction_zh = self.class_names_zh.get(prediction_en, prediction_en)

            result = {
                "prediction": prediction_zh,
                "prediction_en": prediction_en,
                "confidence": float(confidence.item()),
                "class_index": int(predicted.item()),
            }

            # 多标签检测：收集所有超过阈值的类别
            thresh = threshold if threshold is not None else self.threshold
            probs_np = probabilities[0].cpu().numpy()
            # 按概率降序排列所有超过阈值的类别索引
            above_mask = probs_np >= thresh
            above_indices = np.where(above_mask)[0]
            above_sorted = above_indices[np.argsort(-probs_np[above_indices])]

            detected_labels = [
                self.class_names_zh.get(self.class_names[i], self.class_names[i])
                for i in above_sorted
            ]
            result["detected_labels"] = detected_labels

            # 次要发现：排除主预测之外的检测标签
            primary_zh = prediction_zh
            result["secondary_findings"] = [
                label for label in detected_labels if label != primary_zh
            ]

            # 返回所有类别的概率
            if return_probs:
                all_probs = probabilities[0].cpu().numpy()
                result["all_probabilities"] = {
                    self.class_names_zh.get(name, name): float(prob)
                    for name, prob in zip(self.class_names, all_probs)
                }
                result["all_probabilities_en"] = {
                    name: float(prob)
                    for name, prob in zip(self.class_names, all_probs)
                }

                # Top-3预测
                top3_probs, top3_indices = torch.topk(
                    probabilities[0], k=min(3, len(self.class_names))
                )
                result["top3_predictions"] = [
                    {
                        "class": self.class_names_zh.get(
                            self.class_names[idx.item()],
                            self.class_names[idx.item()]
                        ),
                        "class_en": self.class_names[idx.item()],
                        "probability": float(prob.item())
                    }
                    for idx, prob in zip(top3_indices, top3_probs)
                ]

        return result

    def predict_from_image(
        self,
        image_array: np.ndarray,
        return_probs: bool = True
    ) -> Dict:
        """
        从ECG图像进行预测

        Args:
            image_array: ECG图像数组 [H, W, C] 或 [H, W]
            return_probs: 是否返回所有类别的概率

        Returns:
            预测结果字典
        """
        # 将图像转换为信号
        signal_tensor = self.image_converter(image_array)

        # 预测
        return self.predict_from_signal(
            signal_tensor.squeeze(0).cpu().numpy(),
            return_probs=return_probs
        )

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
    service = CardioFormerService(
        checkpoint_path=os.environ.get("MODEL_CHECKPOINT_PATH"),
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
