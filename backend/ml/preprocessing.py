"""
ECG Image Preprocessing Module
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional


class ECGPreprocessor:
    """ECG图像预处理器"""

    def __init__(
        self,
        target_size: Tuple[int, int] = (224, 224),
        normalize: bool = True
    ):
        self.target_size = target_size
        self.normalize = normalize

    def load_image(self, image_path: str) -> np.ndarray:
        """加载图像"""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法加载图像: {image_path}")
        return image

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """转换为灰度图"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """去噪"""
        return cv2.fastNlMeansDenoising(image, h=10)

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """增强对比度 (CLAHE)"""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    def resize(self, image: np.ndarray) -> np.ndarray:
        """调整尺寸"""
        return cv2.resize(image, self.target_size, interpolation=cv2.INTER_LINEAR)

    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """标准化到 [0, 1]"""
        return image.astype(np.float32) / 255.0

    def preprocess(self, image_path: str) -> np.ndarray:
        """
        完整的预处理流程

        Args:
            image_path: 图像路径

        Returns:
            预处理后的图像数组 shape: (1, H, W, 1)
        """
        # 1. 加载图像
        image = self.load_image(image_path)

        # 2. 转灰度
        image = self.to_grayscale(image)

        # 3. 去噪
        image = self.denoise(image)

        # 4. 增强对比度
        image = self.enhance_contrast(image)

        # 5. 调整尺寸
        image = self.resize(image)

        # 6. 标准化
        if self.normalize:
            image = self.normalize_image(image)

        # 7. 添加batch和channel维度
        image = np.expand_dims(image, axis=(0, -1))

        return image


def preprocess_ecg_image(
    image_path: str,
    target_size: Tuple[int, int] = (224, 224)
) -> np.ndarray:
    """
    便捷函数：预处理ECG图像

    Args:
        image_path: 图像路径
        target_size: 目标尺寸

    Returns:
        预处理后的图像
    """
    preprocessor = ECGPreprocessor(target_size=target_size)
    return preprocessor.preprocess(image_path)


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) > 1:
        result = preprocess_ecg_image(sys.argv[1])
        print(f"预处理完成，输出shape: {result.shape}")
    else:
        print("用法: python preprocessing.py <image_path>")
