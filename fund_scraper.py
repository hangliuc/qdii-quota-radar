"""
基金限购额度 & 收益率抓取模块
数据源：天天基金网
"""

import re
import time
import random
import requests
from typing import Optional


# 天天基金网基金交易页面
FUND_TRADE_URL = "http://fund.eastmoney.com/{code}.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Referer": "http://fund.eastmoney.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_fund_purchase_info(fund_code: str) -> dict:
    """
    抓取单只基金的限购信息和近1年收益率

    Returns:
        dict: {
            "code": "008971",
            "name": "大成纳斯达克100ETF联接(QDII)C",
            "purchase_status": "限大额" | "开放申购" | "暂停申购",
            "purchase_limit": "200.00元" | "不限" | "暂停",
            "return_1y": "34.44%" | "",
            "raw_text": "原始文本",
            "error": None | "错误信息"
        }
    """
    result = {
        "code": fund_code,
        "name": "",
        "purchase_status": "未知",
        "purchase_limit": "未知",
        "return_1y": "",
        "raw_text": "",
        "error": None,
    }

    try:
        info = _fetch_from_trade_page(fund_code)
        if info:
            result.update(info)
            return result

        result["error"] = "未获取到限购信息"

    except Exception as e:
        result["error"] = str(e)

    return result


def _fetch_from_trade_page(fund_code: str) -> Optional[dict]:
    """从天天基金交易页面抓取限购信息和收益率"""
    url = FUND_TRADE_URL.format(code=fund_code)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        if resp.status_code != 200:
            return None

        html = resp.text
        info = {}

        # 1. 从 <title> 提取基金名称
        title_match = re.search(r"<title>(.+?)\((\d{6})\)", html)
        if title_match:
            info["name"] = title_match.group(1).strip()

        # 2. 提取近1年收益率
        # 页面中的格式: 近1年：</span><span class="...">34.44%</span>
        return_match = re.search(
            r"近1年[：:]</span>\s*<span[^>]*>([-\d.]+%)</span>",
            html,
        )
        if return_match:
            info["return_1y"] = return_match.group(1)

        # 3. 从 buyWayStatic 区域提取交易状态和限额
        buy_section = re.search(
            r'class="buyWayStatic">(.*?)</div>\s*</div>\s*</div>',
            html,
            re.DOTALL,
        )
        if not buy_section:
            buy_section = re.search(
                r'交易状态[：:](.*?)购买手续费',
                html,
                re.DOTALL,
            )

        if buy_section:
            section_text = re.sub(r"<[^>]+>", " ", buy_section.group(1))
            section_text = re.sub(r"\s+", " ", section_text).strip()
            info["raw_text"] = section_text[:200]

            # 解析交易状态
            if "暂停申购" in section_text:
                info["purchase_status"] = "暂停申购"
                info["purchase_limit"] = "暂停"
            elif "限大额" in section_text:
                info["purchase_status"] = "限大额"
            elif "开放申购" in section_text:
                info["purchase_status"] = "开放申购"
                info["purchase_limit"] = "不限"

            # 解析具体限额金额
            limit_patterns = [
                r"单日累计购买上限([\d,.]+)元",
                r"购买上限([\d,.]+)元",
                r"限大额.*?上限.*?([\d,.]+)\s*元",
                r"限大额.*?\((.*?元)\)",
                r"单日.*?限额.*?([\d,.]+)\s*元",
                r"限购金额.*?([\d,.]+)\s*元",
                r"每日限额.*?([\d,.]+)\s*元",
            ]

            for pattern in limit_patterns:
                match = re.search(pattern, section_text)
                if match:
                    amount = match.group(1).strip()
                    if "元" not in amount:
                        amount = f"{amount}元"
                    info["purchase_limit"] = amount
                    break

        # 4. 备用：从整个页面文本提取
        if "purchase_status" not in info:
            page_text = re.sub(r"<[^>]+>", " ", html)
            page_text = re.sub(r"\s+", " ", page_text)

            if "暂停申购" in page_text:
                info["purchase_status"] = "暂停申购"
                info["purchase_limit"] = info.get("purchase_limit", "暂停")
            elif "限大额" in page_text:
                info["purchase_status"] = "限大额"
                for pattern in [
                    r"单日累计购买上限([\d,.]+)元",
                    r"购买上限([\d,.]+)元",
                ]:
                    match = re.search(pattern, page_text)
                    if match:
                        info["purchase_limit"] = f"{match.group(1)}元"
                        break
            elif "开放申购" in page_text:
                info["purchase_status"] = "开放申购"
                info["purchase_limit"] = "不限"

        if info.get("purchase_status") or info.get("name"):
            return info

    except requests.RequestException:
        pass

    return None


def fetch_all_funds(fund_list: list[dict]) -> list[dict]:
    """
    批量抓取所有基金的限购信息

    Args:
        fund_list: [{"code": "008971", "name": "大成纳斯达克100ETF联接(QDII)C"}, ...]

    Returns:
        list[dict]: 每只基金的限购信息
    """
    results = []
    for i, fund in enumerate(fund_list):
        code = fund["code"]
        default_name = fund.get("name", "")

        print(f"  [{i+1}/{len(fund_list)}] 正在查询 {default_name} ({code})...")

        info = fetch_fund_purchase_info(code)

        # 如果没有获取到名称，使用配置中的名称
        if not info.get("name") or len(info["name"]) < 4:
            info["name"] = default_name

        results.append(info)

        # 随机延迟，避免请求过快
        if i < len(fund_list) - 1:
            time.sleep(random.uniform(1.0, 2.5))

    return results
