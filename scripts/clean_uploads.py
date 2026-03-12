"""
Clean uploaded files and generated reports
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta


def clean_uploads(
    upload_dir: str = "./data/uploads",
    days_old: int = 7,
    dry_run: bool = False
):
    """
    清理旧的上传文件

    Args:
        upload_dir: 上传目录
        days_old: 保留天数
        dry_run: 仅模拟，不实际删除
    """
    upload_path = Path(upload_dir)

    if not upload_path.exists():
        print(f"❌ 目录不存在: {upload_path}")
        return

    cutoff_date = datetime.now() - timedelta(days=days_old)

    print(f"🧹 清理 {days_old} 天前的文件...")
    print(f"📁 目录: {upload_path.absolute()}")
    print(f"📅 截止日期: {cutoff_date}")
    print()

    deleted_count = 0
    deleted_size = 0

    for file_path in upload_path.glob("*"):
        if file_path.is_file():
            # 获取文件修改时间
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

            if mtime < cutoff_date:
                file_size = file_path.stat().st_size

                if dry_run:
                    print(f"📝 将删除: {file_path.name} ({file_size} bytes)")
                else:
                    print(f"🗑️  删除: {file_path.name}")
                    file_path.unlink()

                deleted_count += 1
                deleted_size += file_size

    print()
    print(f"✅ 清理完成！")
    print(f"删除文件数: {deleted_count}")
    print(f"释放空间: {deleted_size / 1024 / 1024:.2f} MB")

    if dry_run:
        print("\n⚠️  这是模拟运行，文件未实际删除")
        print("使用 --execute 参数执行实际删除")


def clean_reports(
    report_dir: str = "./data/reports",
    days_old: int = 30,
    dry_run: bool = False
):
    """
    清理旧的报告文件

    Args:
        report_dir: 报告目录
        days_old: 保留天数
        dry_run: 仅模拟，不实际删除
    """
    print(f"📄 清理报告文件...")
    clean_uploads(report_dir, days_old, dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理工具")
    parser.add_argument(
        "--uploads",
        action="store_true",
        help="清理上传文件"
    )
    parser.add_argument(
        "--reports",
        action="store_true",
        help="清理报告文件"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="保留天数（默认7天）"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行删除（默认为模拟）"
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("⚠️  模拟模式 - 文件不会被实际删除")
        print("使用 --execute 参数执行实际删除")
        print()

    if args.uploads:
        clean_uploads(days_old=args.days, dry_run=dry_run)

    if args.reports:
        clean_reports(days_old=args.days, dry_run=dry_run)

    if not args.uploads and not args.reports:
        parser.print_help()
