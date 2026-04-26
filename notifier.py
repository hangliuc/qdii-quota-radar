"""
通知推送模块 - 飞书机器人
"""

import re
import requests
from datetime import datetime


def _parse_limit_value(limit_str: str) -> float:
    """
    将限额字符串解析为数值，用于排序。
    "200.00元" → 200.0
    "不限" → float('inf')
    "暂停" → -1
    "未知" → -2
    "查询失败" → -3
    """
    if not limit_str:
        return -2
    if "暂停" in limit_str:
        return -1
    if "不限" in limit_str:
        return float("inf")
    if "未知" in limit_str or "失败" in limit_str:
        return -2
    match = re.search(r"([\d,.]+)", limit_str)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return -2
    return -2


def send_notification(webhook_url: str, title: str, content: str):
    """
    通过飞书机器人 webhook 发送通知

    Args:
        webhook_url: 飞书机器人 webhook 地址
        title: 通知标题
        content: 通知内容（富文本）
    """
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
                "title": {
                    "tag": "plain_text",
                    "content": title,
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content,
                }
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
        # 回退到控制台
        print(f"\n{title}\n{content}")


def format_report(results: list[dict]) -> tuple[str, str]:
    """
    格式化飞书卡片 Markdown 报告
    按限额从大到小排序：不限 > 1000元 > 200元 > ... > 暂停 > 失败

    Returns:
        (title, content)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 支付宝纳斯达克 QDII 基金限购监控 {today}"

    lines = []

    # 按限额从大到小排序
    def sort_key(r):
        if r.get("error"):
            return (-100, "")
        val = _parse_limit_value(r.get("purchase_limit", "未知"))
        # 暂停排最后（-1），未知/失败更后面
        # 正常数值和不限(inf)按从大到小
        return (-val if val >= 0 else val, r.get("name", ""))

    sorted_results = sorted(results, key=sort_key)

    # 统计
    suspended = sum(1 for r in results if "暂停" in r.get("purchase_status", ""))
    limited = sum(
        1
        for r in results
        if "限" in r.get("purchase_status", "")
        and "暂停" not in r.get("purchase_status", "")
    )
    opened = sum(1 for r in results if "开放" in r.get("purchase_status", ""))
    errors = sum(1 for r in results if r.get("error"))

    lines.append(
        f"🟢 开放: {opened}  🟡 限额: {limited}  🔴 暂停: {suspended}  ❌ 失败: {errors}"
    )
    lines.append("---")

    for r in sorted_results:
        name = r.get("name", "未知")
        code = r.get("code", "")
        limit = r.get("purchase_limit", "未知")
        status = r.get("purchase_status", "未知")
        error = r.get("error")

        if error:
            icon = "❌"
            limit = "查询失败"
        elif "暂停" in status:
            icon = "🔴"
        elif "开放" in status:
            icon = "🟢"
        elif "限" in status:
            icon = "🟡"
        else:
            icon = "⚪"

        lines.append(f"{icon} **{name}**（{code}）")
        lines.append(f"　　额度: **{limit}** ｜ 状态: {status}")

    content = "\n".join(lines)
    return title, content
