"""
历史记录模块
记录每天的限购额度变化，方便对比
"""

import json
import os
from datetime import datetime
from typing import Optional


def load_history(history_file: str) -> dict:
    """加载历史记录"""
    if not os.path.exists(history_file):
        return {}
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_history(history_file: str, history: dict):
    """保存历史记录"""
    os.makedirs(os.path.dirname(history_file) or ".", exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def update_history(history_file: str, results: list[dict]) -> list[dict]:
    """
    更新历史记录并返回变化列表

    Returns:
        list[dict]: 变化列表 [{"code", "name", "old_limit", "new_limit", "old_status", "new_status"}, ...]
    """
    history = load_history(history_file)
    today = datetime.now().strftime("%Y-%m-%d")
    changes = []

    # 获取上一次的记录
    last_record = history.get("latest", {})

    # 构建今天的记录
    today_record = {}
    for r in results:
        code = r["code"]
        today_record[code] = {
            "name": r.get("name", ""),
            "purchase_status": r.get("purchase_status", "未知"),
            "purchase_limit": r.get("purchase_limit", "未知"),
        }

        # 对比变化
        old = last_record.get(code, {})
        if old:
            old_limit = old.get("purchase_limit", "未知")
            new_limit = r.get("purchase_limit", "未知")
            old_status = old.get("purchase_status", "未知")
            new_status = r.get("purchase_status", "未知")

            if old_limit != new_limit or old_status != new_status:
                changes.append({
                    "code": code,
                    "name": r.get("name", ""),
                    "old_limit": old_limit,
                    "new_limit": new_limit,
                    "old_status": old_status,
                    "new_status": new_status,
                })

    # 更新历史
    history["latest"] = today_record
    if "daily" not in history:
        history["daily"] = {}
    history["daily"][today] = today_record

    # 只保留最近30天的记录
    daily = history["daily"]
    if len(daily) > 30:
        sorted_dates = sorted(daily.keys())
        for old_date in sorted_dates[:-30]:
            del daily[old_date]

    save_history(history_file, history)

    return changes


def format_changes(changes: list[dict]) -> Optional[str]:
    """格式化变化信息"""
    if not changes:
        return None

    lines = []
    lines.append("📢 限购额度变化提醒：")
    lines.append("")

    for c in changes:
        name = c["name"]
        code = c["code"]
        lines.append(f"  {name}({code}):")
        if c["old_status"] != c["new_status"]:
            lines.append(f"    状态: {c['old_status']} → {c['new_status']}")
        if c["old_limit"] != c["new_limit"]:
            lines.append(f"    额度: {c['old_limit']} → {c['new_limit']}")
        lines.append("")

    return "\n".join(lines)
