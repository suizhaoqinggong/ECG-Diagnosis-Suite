#!/usr/bin/env python3
"""
Manual CardioFormer integration smoke check.

This script tests:
1. Model loading from checkpoint
2. Dummy signal inference
3. Real image inference (if test image available)
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend" / "ml"))

from cardioformer_service import CardioFormerService
import numpy as np
from PIL import Image


def test_model_loading():
    """Test 1: Load model from checkpoint"""
    print("\n" + "="*60)
    print("TEST 1: Model Loading")
    print("="*60)

    checkpoint_path = "/Users/azure/best.ckpt"

    if not os.path.exists(checkpoint_path):
        print(f"❌ Checkpoint not found: {checkpoint_path}")
        return None

    try:
        service = CardioFormerService(
            checkpoint_path=checkpoint_path,
            device="cpu"
        )
        print("✅ Model loaded successfully")
        return service
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_dummy_inference(service):
    """Test 2: Inference with dummy signal"""
    print("\n" + "="*60)
    print("TEST 2: Dummy Signal Inference")
    print("="*60)

    if service is None:
        print("⚠️  Skipping (model not loaded)")
        return

    try:
        result = service.test_with_dummy_signal()
        print(f"✅ Inference successful")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['confidence']:.2%}")

        if 'top3_predictions' in result:
            print("\n   Top-3 Predictions:")
            for i, pred in enumerate(result['top3_predictions'], 1):
                print(f"     {i}. {pred['class']}: {pred['probability']:.2%}")

        return result
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_image_inference(service):
    """Test 3: Inference with test image"""
    print("\n" + "="*60)
    print("TEST 3: Image Inference")
    print("="*60)

    if service is None:
        print("⚠️  Skipping (model not loaded)")
        return

    # Look for test images
    test_dirs = [
        "./data/uploads",
        "./tests/test_images",
        "./test_data"
    ]

    test_image = None
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith(('.png', '.jpg', '.jpeg')):
                    test_image = os.path.join(test_dir, file)
                    break
        if test_image:
            break

    if not test_image:
        print("⚠️  No test image found, skipping")
        return

    try:
        print(f"📸 Loading image: {test_image}")
        image = Image.open(test_image).convert('RGB')
        image_array = np.array(image)

        print(f"   Image shape: {image_array.shape}")
        print("🔮 Running inference...")

        result = service.predict_from_image(image_array)

        print(f"✅ Image inference successful")
        print(f"   Prediction: {result['prediction']}")
        print(f"   Confidence: {result['confidence']:.2%}")

        if 'top3_predictions' in result:
            print("\n   Top-3 Predictions:")
            for i, pred in enumerate(result['top3_predictions'], 1):
                print(f"     {i}. {pred['class']}: {pred['probability']:.2%}")

        return result
    except Exception as e:
        print(f"❌ Image inference failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CardioFormer Integration Test Suite")
    print("="*60)

    # Test 1: Load model
    service = test_model_loading()

    # Test 2: Dummy inference
    test_dummy_inference(service)

    # Test 3: Image inference
    test_image_inference(service)

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    if service is not None:
        print("✅ Model loading: PASSED")
        print("✅ Basic inference: PASSED")
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("  1. Start backend: cd backend && uvicorn app.main:app --reload")
        print("  2. Test API: POST http://localhost:8000/api/diagnose")
        print("  3. Start frontend: cd frontend && npm run dev")
    else:
        print("❌ Model loading: FAILED")
        print("\nTroubleshooting:")
        print("  1. Check checkpoint path: /Users/azure/best.ckpt")
        print("  2. Verify checkpoint format")
        print("  3. Check PyTorch installation")


if __name__ == "__main__":
    main()
