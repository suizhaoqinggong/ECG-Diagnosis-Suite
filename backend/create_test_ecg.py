#!/usr/bin/env python3
"""
创建测试用的ECG图像
"""
import numpy as np
import cv2
import sys
from pathlib import Path

def create_test_ecg_image(output_path: str = "test_ecg.png"):
    """创建测试ECG图像"""
    # 创建白色背景
    height, width = 1200, 1000
    image = np.ones((height, width, 3), dtype=np.uint8) * 255

    # 绘制网格线（标准ECG纸）
    # 小网格（1mm）
    for i in range(0, width, 20):
        cv2.line(image, (i, 0), (i, height), (200, 200, 200), 1)
    for i in range(0, height, 20):
        cv2.line(image, (0, i), (width, i), (200, 200, 200), 1)

    # 大网格（5mm）
    for i in range(0, width, 100):
        cv2.line(image, (i, 0), (i, height), (150, 150, 150), 1)
    for i in range(0, height, 100):
        cv2.line(image, (0, i), (width, i), (150, 150, 150), 1)

    # 模拟12导联的ECG波形
    lead_height = height // 12
    signal_color = (0, 0, 0)  # 黑色

    for lead_idx in range(12):
        y_offset = lead_idx * lead_height + lead_height // 2

        # 创建模拟ECG波形
        x = np.arange(0, width)
        # P波
        p_wave = 10 * np.sin(2 * np.pi * x / 200)
        # QRS波群
        qrs = np.zeros_like(x, dtype=float)
        for beat in range(5):
            beat_center = beat * 200 + 100
            qrs += 50 * np.exp(-((x - beat_center) ** 2) / 100) * np.sin(2 * np.pi * (x - beat_center) / 30)
        # T波
        t_wave = 15 * np.sin(2 * np.pi * (x - 50) / 150) * np.exp(-((x - 50) % 200 - 50) ** 2 / 500)

        signal = p_wave + qrs + t_wave

        # 添加到图像
        for i in range(len(x) - 1):
            y1 = int(y_offset - signal[i])
            y2 = int(y_offset - signal[i + 1])
            cv2.line(image, (x[i], y1), (x[i + 1], y2), signal_color, 2)

        # 添加导联标签
        lead_names = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
        cv2.putText(image, lead_names[lead_idx], (10, y_offset - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, signal_color, 1)

    # 添加标题
    cv2.putText(image, "12-Lead ECG Test Image", (width // 2 - 120, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    # 保存图像
    cv2.imwrite(output_path, image)
    print(f"✅ 测试ECG图像已创建: {output_path}")
    return output_path


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "test_ecg.png"
    create_test_ecg_image(output)
