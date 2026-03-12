#!/usr/bin/env python3
"""
Test ResNet1D Model Integration

This script tests the ResNet1D model from ECG-Research
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import numpy as np
from ml.resnet1d_model import ResNet1DBaseline, create_resnet1d_model
from ml.ecg_image_converter import create_dummy_ecg_signal
from ml.ecg_model_service import ECGModelService


def test_model_creation():
    """测试模型创建"""
    print("=" * 60)
    print("Test 1: Model Creation")
    print("=" * 60)

    model = ResNet1DBaseline(
        num_classes=5,
        signal_length=1000,
        input_channels=12,
    )

    print(f"✅ Model created successfully")
    print(f"   Parameters: {sum(p.numel() for p in model.parameters()):,}")

    return model


def test_forward_pass(model):
    """测试前向传播"""
    print("\n" + "=" * 60)
    print("Test 2: Forward Pass")
    print("=" * 60)

    # 创建测试输入
    batch_size = 2
    num_leads = 12
    signal_length = 1000

    x = torch.randn(batch_size, num_leads, signal_length)

    print(f"   Input shape: {x.shape}")

    # 前向传播
    with torch.no_grad():
        output = model(x)

    print(f"   Output shape: {output.shape}")
    print(f"   Output (first sample): {output[0]}")

    print("✅ Forward pass successful")

    return output


def test_dummy_signal():
    """测试虚拟信号生成"""
    print("\n" + "=" * 60)
    print("Test 3: Dummy ECG Signal Generation")
    print("=" * 60)

    signal = create_dummy_ecg_signal(
        signal_length=1000,
        num_leads=12
    )

    print(f"   Signal shape: {signal.shape}")
    print(f"   Signal range: [{signal.min():.3f}, {signal.max():.3f}]")

    print("✅ Dummy signal generated successfully")

    return signal


def test_model_service():
    """测试模型服务"""
    print("\n" + "=" * 60)
    print("Test 4: Model Service")
    print("=" * 60)

    # 创建服务
    service = ECGModelService(
        model_type="resnet1d",
        num_classes=5,
        device="cpu"
    )

    # 测试虚拟信号
    result = service.test_with_dummy_signal()

    print("\n📊 Prediction Result:")
    print(f"   Prediction: {result['prediction']}")
    print(f"   Confidence: {result['confidence']:.2%}")

    if 'top3_predictions' in result:
        print("\n   Top-3 Predictions:")
        for i, pred in enumerate(result['top3_predictions'], 1):
            print(f"     {i}. {pred['class']}: {pred['probability']:.2%}")

    print("\n✅ Model service test successful")

    return service


def test_image_prediction():
    """测试图像预测"""
    print("\n" + "=" * 60)
    print("Test 5: Image Prediction")
    print("=" * 60)

    # 创建服务
    service = ECGModelService(
        model_type="resnet1d",
        num_classes=5,
        device="cpu"
    )

    # 创建虚拟图像
    dummy_image = np.random.randint(0, 255, (1200, 1000, 3), dtype=np.uint8)

    print(f"   Image shape: {dummy_image.shape}")

    # 预测
    result = service.predict(dummy_image)

    print("\n📊 Prediction Result:")
    print(f"   Prediction: {result['prediction']}")
    print(f"   Confidence: {result['confidence']:.2%}")

    print("\n✅ Image prediction test successful")

    return result


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("ResNet1D Model Integration Tests")
    print("🚀" * 30 + "\n")

    try:
        # Test 1: 创建模型
        model = test_model_creation()

        # Test 2: 前向传播
        output = test_forward_pass(model)

        # Test 3: 虚拟信号
        signal = test_dummy_signal()

        # Test 4: 模型服务
        service = test_model_service()

        # Test 5: 图像预测
        result = test_image_prediction()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🎉 ResNet1D model is ready for use!")
        print("\nNext steps:")
        print("  1. Integrate with FastAPI backend")
        print("  2. Test with real ECG images")
        print("  3. Deploy to production")

        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
