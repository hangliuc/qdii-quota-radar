"""配置加载"""

import json
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    feishu_webhook: str = ""
    passive_funds: list[dict] = field(default_factory=list)
    active_funds: list[dict] = field(default_factory=list)
    history_file: str = "data/history.json"
    image_base_url: str = ""

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # 环境变量覆盖
        for env_key, conf_key in [
            ("FEISHU_WEBHOOK", "feishu_webhook"),
            ("IMAGE_BASE_URL", "image_base_url"),
        ]:
            val = os.environ.get(env_key)
            if val:
                raw[conf_key] = val

        return cls(
            feishu_webhook=raw.get("feishu_webhook", ""),
            passive_funds=raw.get("passive_funds", []),
            active_funds=raw.get("active_funds", []),
            history_file=raw.get("history_file", "data/history.json"),
            image_base_url=raw.get("image_base_url", ""),
        )
