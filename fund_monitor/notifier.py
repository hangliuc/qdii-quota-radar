"""
飞书通知
"""

import requests
from datetime import datetime


class FeishuNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_reminder(self, image_urls: list = None):
        """发送每日提醒（含查看图片按钮）"""
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"📊 纳斯达克基金限购日报 {today}"

        elements = [
            {"tag": "markdown", "content": "今日限购卡片已生成，记得发小红书 📕"},
        ]

        buttons = []
        for url in (image_urls or []):
            if "passive" in url:
                label = "📸 被动型（指数基金）"
            elif "active" in url:
                label = "📸 主动型（主动管理）"
            else:
                label = "📸 查看卡片图"
            buttons.append({
                "tag": "button",
                "text": {"tag": "plain_text", "content": label},
                "type": "primary",
                "url": url,
            })

        if buttons:
            elements.append({"tag": "action", "actions": buttons})

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
                        print(f"  🔗 {btn['text']['content']} → {btn.get('url', '')}")
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


def upload_to_imgbb(image_path: str, api_key: str) -> str:
    """
    上传图片到 imgbb，返回直链 URL。
    imgbb 免费版支持匿名上传，国内可访问。

    需要在 https://api.imgbb.com/ 注册获取免费 API key。
    """
    import base64
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key, "image": b64},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("success"):
        return data["data"]["url"]
    raise RuntimeError(f"imgbb upload failed: {data}")
