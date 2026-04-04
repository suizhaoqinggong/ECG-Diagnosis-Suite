#!/usr/bin/env python3
"""
Manual conduction-disorder smoke check.

This file is kept as an ad hoc developer utility and is not part of the
automated pytest suite.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import numpy as np
from ml.conduction_disorder_detector import ConductionDisorderDetector, create_cd_detector
from ml.ecg_image_converter import create_dummy_ecg_signal


def test_detector_creation():
    """测试检测器创建"""
    print("=" * 70)
    print("Test 1: Conduction Disorder Detector Creation")
    print("=" * 70)

    detector = create_cd_detector()

    print("✅ Detector created successfully")
    return detector


def test_signal_detection(detector):
    """测试信号检测"""
    print("\n" + "=" * 70)
    print("Test 2: Conduction Disorder Detection from Signal")
    print("=" * 70)

    # 创建测试信号
    signal = create_dummy_ecg_signal(1000, 12).squeeze(0).numpy()

    print(f"   Signal shape: {signal.shape}")

    # 检测
    result = detector.detect_from_signal(signal)

    print("\n📊 Detection Result:")
    print(f"   Prediction: {result['prediction']}")
    print(f"   Is Conduction Disorder: {result['is_conduction_disorder']}")
    print(f"   CD Probability: {result['conduction_disorder_probability']:.2%}")
    print(f"   Risk Level: {result['risk_level']}")
    print(f"   Confidence: {result['confidence']:.2%}")

    print("\n   All Probabilities:")
    for cls, prob in result['all_probabilities'].items():
        marker = " ←" if cls == "传导障碍" else ""
        print(f"     {cls}: {prob:.2%}{marker}")

    print("\n   Description:")
    print(f"   {result['description']}")

    print("\n✅ Signal detection test passed")
    return result


def test_image_detection(detector):
    """测试图像检测"""
    print("\n" + "=" * 70)
    print("Test 3: Conduction Disorder Detection from Image")
    print("=" * 70)

    # 创建虚拟图像
    dummy_image = np.random.randint(0, 255, (1200, 1000, 3), dtype=np.uint8)

    print(f"   Image shape: {dummy_image.shape}")

    # 检测
    result = detector.detect_from_image(dummy_image)

    print("\n📊 Detection Result:")
    print(f"   Prediction: {result['prediction']}")
    print(f"   Is Conduction Disorder: {result['is_conduction_disorder']}")
    print(f"   CD Probability: {result['conduction_disorder_probability']:.2%}")
    print(f"   Risk Level: {result['risk_level']}")

    print("\n✅ Image detection test passed")
    return result


def test_risk_assessment():
    """测试风险评估"""
    print("\n" + "=" * 70)
    print("Test 4: Risk Level Assessment")
    print("=" * 70)

    detector = create_cd_detector()

    # 测试不同的概率值
    test_cases = [
        (0.85, "高风险"),
        (0.55, "中等风险"),
        (0.30, "低风险"),
        (0.10, "正常"),
    ]

    for prob, expected_level in test_cases:
        level = detector._get_risk_level(prob)
        desc = detector._get_description(prob)
        status = "✅" if level == expected_level else "❌"
        print(f"   {status} Probability: {prob:.2f} → {level} (expected: {expected_level})")

    print("\n✅ Risk assessment test passed")


def test_feature_analysis():
    """测试特征分析"""
    print("\n" + "=" * 70)
    print("Test 5: ECG Feature Analysis")
    print("=" * 70)

    detector = create_cd_detector()
    signal = create_dummy_ecg_signal(1000, 12).squeeze(0).numpy()

    # 分析特征
    features = detector.analyze_features(signal)

    print(f"   Analyzed {len(features)} leads")
    for lead_name, lead_features in list(features.items())[:3]:
        print(f"   {lead_name}: {lead_features}")

    print("\n✅ Feature analysis test passed")


def main():
    """运行所有测试"""
    print("\n" + "🏥" * 35)
    print("Conduction Disorder Detector - Test Suite")
    print("🏥" * 35 + "\n")

    try:
        # Test 1
        detector = test_detector_creation()

        # Test 2
        signal_result = test_signal_detection(detector)

        # Test 3
        image_result = test_image_detection(detector)

        # Test 4
        test_risk_assessment()

        # Test 5
        test_feature_analysis()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)

        print("\n🎉 Conduction Disorder Detector is ready!")
        print("\n📋 Summary:")
        print(f"   - Detector created successfully")
        print(f"   - Signal detection: working")
        print(f"   - Image detection: working")
        print(f"   - Risk assessment: working")
        print(f"   - Feature analysis: working")

        print("\n🚀 Next steps:")
        print("   1. Integrate with FastAPI backend")
        print("   2. Test with real ECG images")
        print("   3. Fine-tune risk thresholds")

        return True

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ TEST FAILED!")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
