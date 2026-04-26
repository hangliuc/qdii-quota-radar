"""
通知推送模块 - 飞书机器人
"""

import requests
from datetime import datetime


def send_notification(webhook_url: str, title: str, content: str):
    """通过飞书机器人 webhook 发送卡片通知"""
    if not webhook_url:
        print("⚠️ 飞书 webhook 未配置，回退到控制台输出")
        print(f"\n{'='*60}")
        print(f"📢 {title}")
        print(f"{'='*60}")
        print(content)
        print(f"{'='*60}\n")
        return

    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {"tag": "markdown", "content": content},
            ],
        },
    }

    try:
        resp = requests.post(webhook_url, json=data, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                print("✅ 飞书推送成功")
            else:
                print(f"⚠️ 飞书返回错误: {result}")
        else:
            print(f"⚠️ 飞书 HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ 飞书推送失败: {e}")
        print(f"\n{title}\n{content}")


def format_reminder(image_url: str = "") -> tuple[str, str]:
    """
    格式化飞书提醒消息

    Args:
        image_url: 图片直链（GitHub raw URL）

    Returns:
        (title, content)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 纳斯达克基金限购日报 {today}"

    lines = ["今日限购卡片已生成，记得发小红书 📕"]
    if image_url:
        lines.append("")
        lines.append(f"![fund_card]({image_url})")

    return title, "\n".join(lines)
