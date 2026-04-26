"""
飞书通知
通过 webhook 发送卡片消息（提醒 + 图片按钮）
"""

import requests
from datetime import datetime


class FeishuNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_reminder(self, image_url: str = ""):
        """发送每日提醒卡片（含查看图片按钮）"""
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"📊 纳斯达克基金限购日报 {today}"

        elements = [
            {"tag": "markdown", "content": "今日限购卡片已生成，记得发小红书 📕"},
        ]
        if image_url:
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📸 查看今日卡片图"},
                    "type": "primary",
                    "url": image_url,
                }],
            })

        self._send_card(title, elements)

    def _send_card(self, title: str, elements: list):
        if not self.webhook_url:
            print(f"⚠️ 飞书 webhook 未配置，回退到控制台")
            print(f"\n{'=' * 60}")
            print(f"📢 {title}")
            print(f"{'=' * 60}")
            for el in elements:
                if el.get("tag") == "markdown":
                    print(el["content"])
                elif el.get("tag") == "action":
                    for btn in el.get("actions", []):
                        url = btn.get("url", "")
                        label = btn.get("text", {}).get("content", "")
                        print(f"  🔗 {label} → {url}")
            print(f"{'=' * 60}\n")
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
            resp = requests.post(self.webhook_url, json=data, timeout=10)
            if resp.status_code == 200:
                body = resp.json()
                if body.get("code") == 0 or body.get("StatusCode") == 0:
                    print("✅ 飞书推送成功")
                else:
                    print(f"⚠️ 飞书返回错误: {body}")
            else:
                print(f"⚠️ 飞书 HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"⚠️ 飞书推送失败: {e}")
