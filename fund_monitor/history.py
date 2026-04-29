"""
历史记录 & 变动检测
"""

import json
import os
from datetime import datetime
from typing import Optional


class History:
    def __init__(self, path: str, namespace: str = "default"):
        self.path = path
        self.ns = namespace
        self._data = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def update(self, results: list[dict]) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        ns_data = self._data.setdefault(self.ns, {})
        last = ns_data.get("latest", {})
        changes = []

        today_record = {}
        for r in results:
            code = r["code"]
            today_record[code] = {
                "name": r.get("name", ""),
                "purchase_status": r.get("purchase_status", "未知"),
                "purchase_limit": r.get("purchase_limit", "未知"),
            }
            old = last.get(code, {})
            if old:
                ol, nl = old.get("purchase_limit", "未知"), r.get("purchase_limit", "未知")
                os_, ns_ = old.get("purchase_status", "未知"), r.get("purchase_status", "未知")
                if ol != nl or os_ != ns_:
                    changes.append({
                        "code": code, "name": r.get("name", ""),
                        "old_limit": ol, "new_limit": nl,
                        "old_status": os_, "new_status": ns_,
                    })

        ns_data["latest"] = today_record
        daily = ns_data.setdefault("daily", {})
        daily[today] = today_record
        if len(daily) > 30:
            for d in sorted(daily.keys())[:-30]:
                del daily[d]

        self._save()
        return changes

    @staticmethod
    def format_changes(changes: list[dict]) -> Optional[str]:
        """格式化变化信息（控制台打印用）"""
        if not changes:
            return None
        lines = ["📢 限购额度变化：", ""]
        for c in changes:
            lines.append(f"  {c['name']}({c['code']}):")
            if c["old_status"] != c["new_status"]:
                lines.append(f"    状态: {c['old_status']} → {c['new_status']}")
            if c["old_limit"] != c["new_limit"]:
                lines.append(f"    额度: {c['old_limit']} → {c['new_limit']}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_changes_for_feishu(all_changes: list[dict]) -> Optional[str]:
        """
        格式化变化信息（飞书推送用，可直接复制到小红书文案）

        Args:
            all_changes: 所有变化列表（被动+主动合并）
        """
        if not all_changes:
            return None
        today = datetime.now().strftime("%-m.%-d")
        lines = [
            f"（{today}）纳指主动基、被动基限额更新！",
            "",
            "📢 限购额度变化：",
            "",
        ]
        for c in all_changes:
            lines.append(f"{c['name']}({c['code']}):")
            if c["old_status"] != c["new_status"]:
                lines.append(f"  状态: {c['old_status']} → {c['new_status']}")
            if c["old_limit"] != c["new_limit"]:
                lines.append(f"  额度: {c['old_limit']} → {c['new_limit']}")
            lines.append("")
        return "\n".join(lines)
