#!/usr/bin/env python3
"""
Manual ResNet1D smoke check.

This file is kept as an ad hoc developer utility and is not part of the
automated pytest suite.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import torch
from ml.resnet1d_model import ResNet1DBaseline
from ml.ecg_image_converter import create_dummy_ecg_signal


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

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🎉 ResNet1D baseline shape checks are ready!")
        print("\nNext steps:")
        print("  1. Add model weight loading if ResNet1D becomes active again")
        print("  2. Add dedicated inference wiring before reintroducing CI coverage")
        print("  3. Keep this script as a manual architecture smoke check")

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
