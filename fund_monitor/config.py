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
    github_repo: str = ""
    imgbb_api_key: str = ""

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        env_webhook = os.environ.get("FEISHU_WEBHOOK")
        if env_webhook:
            raw["feishu_webhook"] = env_webhook

        env_repo = os.environ.get("GITHUB_REPOSITORY")
        if env_repo:
            raw["github_repo"] = env_repo

        return cls(
            feishu_webhook=raw.get("feishu_webhook", ""),
            passive_funds=raw.get("passive_funds", raw.get("funds", [])),
            active_funds=raw.get("active_funds", []),
            history_file=raw.get("history_file", "data/history.json"),
            github_repo=raw.get("github_repo", ""),
            imgbb_api_key=raw.get("imgbb_api_key", ""),
        )
