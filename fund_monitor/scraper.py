"""
基金数据抓取
从天天基金网获取限购额度、近1年收益率等信息
"""

import re
import time
import random
import requests
from typing import Optional

FUND_URL = "http://fund.eastmoney.com/{code}.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "http://fund.eastmoney.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _empty_result(code: str) -> dict:
    return {
        "code": code,
        "name": "",
        "purchase_status": "未知",
        "purchase_limit": "未知",
        "return_1y": "",
        "error": None,
    }


def _parse_page(html: str) -> Optional[dict]:
    """从天天基金页面 HTML 中解析限购信息和收益率"""
    info = {}

    # 基金名称（从 <title>）
    m = re.search(r"<title>(.+?)\((\d{6})\)", html)
    if m:
        info["name"] = m.group(1).strip()

    # 近1年收益率
    m = re.search(r"近1年[：:]</span>\s*<span[^>]*>([-\d.]+%)</span>", html)
    if m:
        info["return_1y"] = m.group(1)

    # 交易状态区域
    section = re.search(
        r'class="buyWayStatic">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL
    )
    if not section:
        section = re.search(r"交易状态[：:](.*?)购买手续费", html, re.DOTALL)

    text = ""
    if section:
        text = re.sub(r"<[^>]+>", " ", section.group(1))
        text = re.sub(r"\s+", " ", text).strip()

    if not text:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)

    # 申购状态
    if "暂停申购" in text:
        info["purchase_status"] = "暂停申购"
        info["purchase_limit"] = "暂停"
    elif "限大额" in text:
        info["purchase_status"] = "限大额"
    elif "开放申购" in text:
        info["purchase_status"] = "开放申购"
        info["purchase_limit"] = "不限"

    # 具体限额
    for pattern in [
        r"单日累计购买上限([\d,.]+)元",
        r"购买上限([\d,.]+)元",
        r"限大额.*?上限.*?([\d,.]+)\s*元",
        r"限大额.*?\((.*?元)\)",
        r"单日.*?限额.*?([\d,.]+)\s*元",
    ]:
        m = re.search(pattern, text)
        if m:
            amount = m.group(1).strip()
            info["purchase_limit"] = amount if "元" in amount else f"{amount}元"
            break

    if info.get("purchase_status") or info.get("name"):
        return info
    return None


def fetch_one(code: str) -> dict:
    """抓取单只基金信息"""
    result = _empty_result(code)
    try:
        resp = requests.get(
            FUND_URL.format(code=code), headers=HEADERS, timeout=15
        )
        resp.encoding = "utf-8"
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"
            return result

        info = _parse_page(resp.text)
        if info:
            result.update(info)
        else:
            result["error"] = "未获取到限购信息"
    except Exception as e:
        result["error"] = str(e)
    return result


def fetch_all(fund_list: list[dict]) -> list[dict]:
    """
    批量抓取基金信息

    Args:
        fund_list: [{"code": "008971", "name": "..."}, ...]
    """
    results = []
    total = len(fund_list)
    for i, fund in enumerate(fund_list):
        code = fund["code"]
        name = fund.get("name", "")
        print(f"  [{i + 1}/{total}] {name} ({code})...")

        info = fetch_one(code)
        if not info.get("name") or len(info["name"]) < 4:
            info["name"] = name
        results.append(info)

        if i < total - 1:
            time.sleep(random.uniform(1.0, 2.5))

    return results
