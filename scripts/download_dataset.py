"""
Download and prepare PTB-XL dataset
"""
import wfdb
import os
from pathlib import Path
import requests
from tqdm import tqdm


def download_ptb_xl(output_dir: str = "./data/datasets/ptb-xl"):
    """
    Download PTB-XL dataset

    Args:
        output_dir: Output directory for dataset
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("⚠️  PTB-XL数据集较大（约1.8GB），下载可能需要一些时间")
    print(f"📁 下载目录: {output_path.absolute()}")

    # 下载链接
    base_url = "https://physionet.org/files/ptb-xl/1.0.3/"

    # 需要下载的文件列表
    files_to_download = [
        "ptbxl_database.csv",
        "scp_statements.csv",
        # 可以根据需要添加更多文件
    ]

    for filename in files_to_download:
        url = f"{base_url}{filename}"
        output_file = output_path / filename

        if output_file.exists():
            print(f"✅ {filename} 已存在，跳过")
            continue

        print(f"⬇️  下载 {filename}...")

        # 下载文件
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))

        with open(output_file, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        print(f"✅ {filename} 下载完成")

    print("\n✅ 数据集下载完成！")
    print(f"📊 数据位置: {output_path.absolute()}")


def list_available_datasets():
    """列出可用的ECG数据集"""
    datasets = {
        "PTB-XL": {
            "size": "1.8GB",
            "records": "21,799",
            "leads": 12,
            "url": "https://physionet.org/content/ptb-xl/",
            "description": "大规模公开ECG数据集"
        },
        "MIT-BIH": {
            "size": "500MB",
            "records": "4,800",
            "leads": 2,
            "url": "https://physionet.org/content/mitdb/",
            "description": "经典心律失常数据库"
        },
    }

    print("\n📊 可用的ECG数据集：\n")
    for name, info in datasets.items():
        print(f"名称: {name}")
        print(f"  大小: {info['size']}")
        print(f"  记录数: {info['records']}")
        print(f"  导联数: {info['leads']}")
        print(f"  描述: {info['description']}")
        print(f"  链接: {info['url']}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ECG数据集工具")
    parser.add_argument(
        "--download",
        action="store_true",
        help="下载PTB-XL数据集"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出可用数据集"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/datasets/ptb-xl",
        help="输出目录"
    )

    args = parser.parse_args()

    if args.list:
        list_available_datasets()
    elif args.download:
        download_ptb_xl(args.output)
    else:
        parser.print_help()
