"""命令行入口"""

import argparse
import os
import sys
from datetime import datetime

from fund_monitor.config import Config
from fund_monitor.scraper import fetch_all
from fund_monitor.history import History
from fund_monitor.image import generate
from fund_monitor.notifier import FeishuNotifier

IMAGE_DIR = "docs"


def main():
    args = _parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    config_path = _resolve(root, args.config)
    try:
        config = Config.load(config_path)
    except FileNotFoundError:
        sys.exit(f"❌ 配置文件不存在: {config_path}")
    except Exception as e:
        sys.exit(f"❌ 配置文件错误: {e}")

    date_str = datetime.now().strftime("%Y%m%d")
    image_dir = os.path.join(root, IMAGE_DIR)
    image_urls = []

    # ── 被动型基金 ──
    if config.passive_funds:
        funds = _filter(config.passive_funds, args.fund_codes)
        print(f"🚀 被动型基金：查询 {len(funds)} 只...")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        results = fetch_all(funds)
        _record_history(args, root, config, results, "passive")

        if not args.no_image:
            name = f"passive_{date_str}.png"
            generate(results, os.path.join(image_dir, name),
                     title="纳斯达克被动型基金限购日报",
                     subtitle_prefix="指数基金 · C类份额")
            if config.image_base_url:
                image_urls.append(f"{config.image_base_url}/{name}")

    # ── 主动型基金 ──
    if config.active_funds:
        funds = _filter(config.active_funds, args.fund_codes)
        print(f"\n🚀 主动型基金：查询 {len(funds)} 只...")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        results = fetch_all(funds)
        _record_history(args, root, config, results, "active")

        if not args.no_image:
            name = f"active_{date_str}.png"
            generate(results, os.path.join(image_dir, name),
                     title="纳斯达克主动型基金限购日报",
                     subtitle_prefix="主动管理 QDII")
            if config.image_base_url:
                image_urls.append(f"{config.image_base_url}/{name}")

    # ── 飞书通知 ──
    if not args.no_notify:
        webhook = "" if args.dry_run else config.feishu_webhook
        FeishuNotifier(webhook).send_reminder(image_urls)

    print("\n✅ 完成！")


def _filter(funds, codes):
    if not codes:
        return funds
    return [f for f in funds if f["code"] in codes]


def _record_history(args, root, config, results, prefix):
    if args.no_history:
        return
    path = _resolve(root, config.history_file)
    history = History(path, namespace=prefix)
    changes = history.update(results)
    text = History.format_changes(changes)
    if text:
        print(text)
    errors = sum(1 for r in results if r.get("error"))
    if errors:
        print(f"  ⚠️ {errors} 只基金查询失败")


def _parse_args():
    p = argparse.ArgumentParser(description="支付宝纳斯达克 QDII 基金限购监控")
    p.add_argument("--config", default="config.json", help="配置文件路径")
    p.add_argument("--fund-codes", nargs="+", help="只查询指定基金代码")
    p.add_argument("--dry-run", action="store_true", help="不推送飞书")
    p.add_argument("--no-history", action="store_true", help="不记录历史")
    p.add_argument("--no-image", action="store_true", help="不生成图片")
    p.add_argument("--no-notify", action="store_true", help="不发送通知")
    return p.parse_args()


def _resolve(root, path):
    return path if os.path.isabs(path) else os.path.join(root, path)
