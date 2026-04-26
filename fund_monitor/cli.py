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


def main():
    args = _parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. 加载配置
    config_path = _resolve(root, args.config)
    try:
        config = Config.load(config_path)
    except FileNotFoundError:
        sys.exit(f"❌ 配置文件不存在: {config_path}")
    except Exception as e:
        sys.exit(f"❌ 配置文件错误: {e}")

    # 2. 确定基金列表
    funds = config.funds
    if args.fund_codes:
        funds = [f for f in funds if f["code"] in args.fund_codes]
        if not funds:
            sys.exit(f"❌ 指定的基金代码不在配置中: {args.fund_codes}")

    print(f"🚀 开始查询 {len(funds)} 只基金...")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 3. 抓取数据
    results = fetch_all(funds)

    # 4. 记录历史 & 检测变化
    if not args.no_history:
        history = History(_resolve(root, config.history_file))
        changes = history.update(results)
        text = History.format_changes(changes)
        if text:
            print(text)

    # 5. 生成卡片图
    image_url = ""
    if not args.no_image:
        date_str = datetime.now().strftime("%Y%m%d")
        image_name = f"fund_card_{date_str}.png"
        image_path = os.path.join(root, "output", image_name)
        generate(results, image_path)

        if config.github_repo:
            image_url = (
                f"https://raw.githubusercontent.com/"
                f"{config.github_repo}/main/output/{image_name}"
            )

    # 6. 发送飞书通知
    if not args.no_notify:
        webhook = "" if args.dry_run else config.feishu_webhook
        FeishuNotifier(webhook).send_reminder(image_url)

    # 7. 统计
    errors = sum(1 for r in results if r.get("error"))
    if errors:
        print(f"\n⚠️ {errors} 只基金查询失败")
    print("\n✅ 完成！")


def _parse_args():
    p = argparse.ArgumentParser(
        description="支付宝纳斯达克 QDII 基金限购监控"
    )
    p.add_argument("--config", default="config.json", help="配置文件路径")
    p.add_argument("--fund-codes", nargs="+", help="只查询指定基金代码")
    p.add_argument("--dry-run", action="store_true", help="不推送飞书")
    p.add_argument("--no-history", action="store_true", help="不记录历史")
    p.add_argument("--no-image", action="store_true", help="不生成图片")
    p.add_argument("--no-notify", action="store_true", help="不发送通知")
    return p.parse_args()


def _resolve(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)
