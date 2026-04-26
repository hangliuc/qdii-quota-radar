"""
历史记录 & 变动检测
记录每天的限购额度，对比前一天的变化
"""

import json
import os
from datetime import datetime
from typing import Optional


class History:
    def __init__(self, path: str):
        self.path = path
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
        """
        写入今天的数据，返回与上次的差异列表。

        Returns:
            [{"code", "name", "old_limit", "new_limit", "old_status", "new_status"}, ...]
        """
        today = datetime.now().strftime("%Y-%m-%d")
        last = self._data.get("latest", {})
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
                os_, ns = old.get("purchase_status", "未知"), r.get("purchase_status", "未知")
                if ol != nl or os_ != ns:
                    changes.append({
                        "code": code,
                        "name": r.get("name", ""),
                        "old_limit": ol, "new_limit": nl,
                        "old_status": os_, "new_status": ns,
                    })

        self._data["latest"] = today_record
        self._data.setdefault("daily", {})[today] = today_record

        # 只保留最近 30 天
        daily = self._data["daily"]
        if len(daily) > 30:
            for old_date in sorted(daily.keys())[:-30]:
                del daily[old_date]

        self._save()
        return changes

    @staticmethod
    def format_changes(changes: list[dict]) -> Optional[str]:
        if not changes:
            return None
        lines = ["📢 限购额度变化提醒：", ""]
        for c in changes:
            lines.append(f"  {c['name']}({c['code']}):")
            if c["old_status"] != c["new_status"]:
                lines.append(f"    状态: {c['old_status']} → {c['new_status']}")
            if c["old_limit"] != c["new_limit"]:
                lines.append(f"    额度: {c['old_limit']} → {c['new_limit']}")
            lines.append("")
        return "\n".join(lines)
