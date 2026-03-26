#!/usr/bin/env python3
"""
验证.dat+.hea双文件上传修复
"""
import requests
import sys
import os

def test_dual_upload(dat_path, hea_path):
    """测试双文件上传"""
    print("="*60)
    print("测试.dat+.hea双文件上传")
    print("="*60)

    # 检查文件存在
    if not os.path.exists(dat_path):
        print(f"❌ .dat文件不存在: {dat_path}")
        return False

    if not os.path.exists(hea_path):
        print(f"❌ .hea文件不存在: {hea_path}")
        return False

    print(f"\n📁 上传文件:")
    print(f"   .dat: {os.path.basename(dat_path)}")
    print(f"   .hea: {os.path.basename(hea_path)}")

    # 上传文件
    try:
        with open(dat_path, 'rb') as dat_f, open(hea_path, 'rb') as hea_f:
            files = [
                ('files', (os.path.basename(dat_path), dat_f)),
                ('files', (os.path.basename(hea_path), hea_f))
            ]

            print("\n🔄 上传中...")
            response = requests.post(
                'http://127.0.0.1:8000/api/diagnose-dat',
                files=files,
                timeout=30
            )

        if response.status_code == 200:
            print("✅ 上传成功！\n")
            result = response.json()

            print("📊 诊断结果:")
            print(f"   预测: {result['prediction']}")
            print(f"   置信度: {result['confidence']:.2%}")
            print(f"   严重程度: {result.get('severity', 'N/A')}")

            if 'top3_predictions' in result:
                print(f"\n   Top-3预测:")
                for i, pred in enumerate(result['top3_predictions'], 1):
                    print(f"     {i}. {pred['class']}: {pred['probability']:.2%}")

            if 'all_probabilities' in result:
                print(f"\n   完整概率分布:")
                for cls, prob in result['all_probabilities'].items():
                    print(f"     {cls}: {prob:.2%}")

            return True
        else:
            print(f"❌ 上传失败 (状态码: {response.status_code})")
            print(f"   错误: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python test_upload_fix.py <dat文件> <hea文件>")
        print("\n示例:")
        print("  python test_upload_fix.py 04000_lr.dat 04000_lr.hea")
        sys.exit(1)

    dat_file = sys.argv[1]
    hea_file = sys.argv[2]

    success = test_dual_upload(dat_file, hea_file)
    sys.exit(0 if success else 1)
