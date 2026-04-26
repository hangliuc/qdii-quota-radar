#!/usr/bin/env python3
"""
支付宝纳斯达克 QDII 基金监控
每天定时抓取基金限购额度、收益率、手续费等信息，推送到飞书
"""

import argparse
import json
import os
import sys
from datetime import datetime

from fund_scraper import fetch_all_funds
from notifier import send_notification, format_report
from history import update_history, format_changes
from image_gen import generate_card


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 环境变量覆盖（用于 GitHub Actions）
    env_webhook = os.environ.get("FEISHU_WEBHOOK")
    if env_webhook:
        config["feishu_webhook"] = env_webhook

    return config


def main():
    parser = argparse.ArgumentParser(
        description="支付宝纳斯达克 QDII 基金监控 — 限购额度 / 收益率 / 手续费"
    )
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--no-history", action="store_true", help="不记录历史")
    parser.add_argument("--fund-codes", nargs="+", help="只查询指定基金代码")
    parser.add_argument(
        "--dry-run", action="store_true", help="只输出到控制台，不推送飞书"
    )
    parser.add_argument(
        "--no-image", action="store_true", help="不生成图片"
    )

    args = parser.parse_args()

    # 配置文件路径（相对于脚本目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(script_dir, config_path)

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件格式错误: {e}")
        sys.exit(1)

    # 确定要查询的基金列表
    fund_list = config["funds"]
    if args.fund_codes:
        fund_list = [f for f in fund_list if f["code"] in args.fund_codes]
        if not fund_list:
            print(f"❌ 指定的基金代码不在配置列表中: {args.fund_codes}")
            sys.exit(1)

    print(f"🚀 开始查询 {len(fund_list)} 只基金的限购信息...")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 抓取数据
    results = fetch_all_funds(fund_list)

    # 记录历史并检测变化
    changes_text = None
    if not args.no_history:
        history_file = config.get("history_file", "data/history.json")
        if not os.path.isabs(history_file):
            history_file = os.path.join(script_dir, history_file)
        changes = update_history(history_file, results)
        changes_text = format_changes(changes)

    # 格式化报告
    title, content = format_report(results)

    # 如果有变化，附加变化信息
    if changes_text:
        content = changes_text + "\n---\n" + content

    # 发送通知
    webhook = "" if args.dry_run else config.get("feishu_webhook", "")
    send_notification(webhook, title, content)

    # 生成图片
    if not args.no_image:
        image_dir = os.path.join(script_dir, "output")
        image_path = os.path.join(image_dir, f"fund_card_{datetime.now().strftime('%Y%m%d')}.png")
        generate_card(results, image_path)

    # 统计
    error_count = sum(1 for r in results if r.get("error"))
    if error_count > 0:
        print(f"\n⚠️ 有 {error_count} 只基金查询失败")

    print("\n✅ 查询完成！")


if __name__ == "__main__":
    main()
