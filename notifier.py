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


def _is_suspended(r: dict) -> bool:
    """判断是否暂停申购"""
    return "暂停" in r.get("purchase_status", "")


def format_report(results: list[dict]) -> tuple[str, str]:
    """
    格式化飞书卡片 Markdown 报告

    状态只分两种：开放（含限大额）、暂停申购
    排序：开放额度从大到小 → 暂停额度从大到小

    Returns:
        (title, content)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"📊 支付宝纳斯达克 QDII 基金限购监控 {today}"

    lines = []

    # 排序：开放在前（额度从大到小），暂停在后（额度从大到小）
    def sort_key(r):
        suspended = _is_suspended(r)
        val = _parse_limit_value(r.get("purchase_limit", "未知"))
        # 开放=0 排前面，暂停=1 排后面；同组内按额度从大到小
        return (1 if suspended else 0, -val, r.get("name", ""))

    sorted_results = sorted(results, key=sort_key)

    # 统计
    open_count = sum(1 for r in results if not _is_suspended(r) and not r.get("error"))
    suspended_count = sum(1 for r in results if _is_suspended(r))
    errors = sum(1 for r in results if r.get("error"))

    lines.append(f"🟢 开放: {open_count}  🔴 暂停: {suspended_count}  ❌ 失败: {errors}")
    lines.append("---")

    prev_suspended = None
    for r in sorted_results:
        # 在开放和暂停之间插入分隔线
        cur_suspended = _is_suspended(r)
        if prev_suspended is not None and not prev_suspended and cur_suspended:
            lines.append("---")
        prev_suspended = cur_suspended

        name = r.get("name", "未知")
        code = r.get("code", "")
        limit = r.get("purchase_limit", "未知")
        error = r.get("error")

        if error:
            icon = "❌"
            status_text = "查询失败"
        elif cur_suspended:
            icon = "🔴"
            status_text = "暂停申购"
        else:
            icon = "🟢"
            status_text = "开放"

        lines.append(f"{icon} **{name}**（{code}）")
        lines.append(f"　　额度: **{limit}** ｜ 状态: {status_text}")

    content = "\n".join(lines)
    return title, content
