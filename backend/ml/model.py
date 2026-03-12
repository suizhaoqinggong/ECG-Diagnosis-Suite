"""
ECG Classification Model
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple
import numpy as np


class ECGClassifier(nn.Module):
    """
    ECG分类模型（示例架构）

    可以替换为你自己的模型架构
    """

    def __init__(self, num_classes: int = 10, input_channels: int = 1):
        super().__init__()

        # 特征提取层
        self.features = nn.Sequential(
            # Conv Block 1
            nn.Conv2d(input_channels, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            # Conv Block 2
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            # Conv Block 3
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            # Conv Block 4
            nn.Conv2d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )

        # 分类器
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            x: 输入张量 shape: (B, C, H, W)

        Returns:
            logits shape: (B, num_classes)
        """
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


class ECGModelService:
    """模型推理服务"""

    def __init__(
        self,
        model_path: str,
        num_classes: int = 10,
        device: str = "cpu",
        class_names: List[str] = None
    ):
        self.device = torch.device(device)
        self.model = self._load_model(model_path, num_classes)
        self.model.eval()

        # 默认类别名称
        self.class_names = class_names or [
            "正常", "房颤", "心房扑动", "室性心动过速",
            "室上性心动过速", "心动过缓", "心动过速",
            "心肌梗死", "束支传导阻滞", "其他"
        ]

    def _load_model(self, model_path: str, num_classes: int) -> nn.Module:
        """加载模型"""
        model = ECGClassifier(num_classes=num_classes)

        # 尝试加载权重
        try:
            state_dict = torch.load(model_path, map_location=self.device)
            model.load_state_dict(state_dict)
            print(f"✅ 模型加载成功: {model_path}")
        except FileNotFoundError:
            print(f"⚠️  模型文件未找到: {model_path}")
            print("使用随机初始化的模型（仅用于演示）")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")

        model.to(self.device)
        return model

    def predict(
        self,
        image: np.ndarray,
        return_probs: bool = True
    ) -> Dict[str, any]:
        """
        预测

        Args:
            image: 预处理后的图像 shape: (1, H, W, 1)
            return_probs: 是否返回所有类别的概率

        Returns:
            预测结果字典
        """
        # 转换为tensor
        image_tensor = torch.from_numpy(image).float()
        image_tensor = image_tensor.permute(0, 3, 1, 2)  # (B, H, W, C) -> (B, C, H, W)
        image_tensor = image_tensor.to(self.device)

        # 推理
        with torch.no_grad():
            logits = self.model(image_tensor)
            probabilities = F.softmax(logits, dim=1)

            # 获取top-1预测
            confidence, predicted = torch.max(probabilities, 1)

            result = {
                "prediction": self.class_names[predicted.item()],
                "confidence": confidence.item(),
                "class_index": predicted.item(),
            }

            # 返回所有类别的概率
            if return_probs:
                all_probs = probabilities[0].cpu().numpy()
                result["all_probabilities"] = {
                    name: float(prob)
                    for name, prob in zip(self.class_names, all_probs)
                }

                # Top-3预测
                top3_probs, top3_indices = torch.topk(probabilities[0], k=3)
                result["top3_predictions"] = [
                    {
                        "class": self.class_names[idx.item()],
                        "probability": prob.item()
                    }
                    for idx, prob in zip(top3_indices, top3_probs)
                ]

        return result

    def predict_batch(
        self,
        images: np.ndarray
    ) -> List[Dict[str, any]]:
        """
        批量预测

        Args:
            images: 批量图像 shape: (B, H, W, C)

        Returns:
            预测结果列表
        """
        results = []
        for i in range(images.shape[0]):
            image = images[i:i+1]
            result = self.predict(image)
            results.append(result)
        return results


if __name__ == "__main__":
    # 测试代码
    model = ECGClassifier(num_classes=10)
    print(f"模型参数数量: {sum(p.numel() for p in model.parameters()):,}")

    # 测试前向传播
    dummy_input = torch.randn(1, 1, 224, 224)
    output = model(dummy_input)
    print(f"输出shape: {output.shape}")
