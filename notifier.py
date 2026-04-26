"""
通知推送模块 - 飞书机器人
"""

import requests
from datetime import datetime


def send_notification(webhook_url: str, title: str, elements: list):
    """
    通过飞书机器人 webhook 发送卡片通知

    Args:
        webhook_url: 飞书机器人 webhook 地址
        title: 卡片标题
        elements: 飞书卡片 elements 列表
    """
    if not webhook_url:
        print("⚠️ 飞书 webhook 未配置，回退到控制台输出")
        print(f"\n{'='*60}")
        print(f"📢 {title}")
        print(f"{'='*60}")
        for el in elements:
            if el.get("tag") == "markdown":
                print(el.get("content", ""))
            elif el.get("tag") == "action":
                for btn in el.get("actions", []):
                    print(f"  🔗 {btn.get('text', {}).get('content', '')} → {btn.get('url', '')}")
        print(f"{'='*60}\n")
        return

    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": elements,
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


def build_reminder_elements(image_url: str = "") -> tuple[str, list]:
    """
    构建飞书卡片消息：提醒文字 + 查看图片按钮

    Returns:
        (title, elements)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 纳斯达克基金限购日报 {today}"

    elements = [
        {
            "tag": "markdown",
            "content": "今日限购卡片已生成，记得发小红书 📕",
        },
    ]

    if image_url:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📸 查看今日卡片图"},
                    "type": "primary",
                    "url": image_url,
                }
            ],
        })

    return title, elements
