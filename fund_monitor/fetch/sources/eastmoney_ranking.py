"""
主数据源（之二）：天天基金"基金排行"接口

接口：https://fund.eastmoney.com/data/rankhandler.aspx
特点：
- 一次拉全市场（约 1.9 万只开放式基金），本地查表
- JSON 风格结构（带 "var rankData = " 包裹），字段顺序稳定
- 提供 JJJZ 拿不到的 **近1年/3年/5年/今年 等历史收益率**

字段顺序（实测，CSV 风格的字符串数组）：
  [0]  基金代码
  [1]  基金简称
  [2]  拼音缩写
  [3]  净值日期           "YYYY-MM-DD"
  [4]  单位净值
  [5]  累计净值
  [6]  日涨幅 (%)
  [7]  近1周 (%)
  [8]  近1月 (%)
  [9]  近3月 (%)
  [10] 近6月 (%)
  [11] 近1年 (%)         ← 我们要的字段
  [12] 近2年 (%)
  [13] 近3年 (%)
  [14] 近5年 (%)
  [15] 今年来 (%)
  [16] 成立日期
  [17] 自定义起始日涨幅
  [18] 自定义起始日累计净值
  [19] 手续费
  [20-24] 其他展示字段（折扣/起购等）
"""

import re
import requests
from datetime import datetime, timedelta
from typing import Optional

from fund_monitor.fetch.sources.base import SourceRecord, empty_record

URL = "https://fund.eastmoney.com/data/rankhandler.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://fund.eastmoney.com/data/fundranking.html",
    "Accept": "*/*",
}


def _parse_response(text: str) -> Optional[list[list[str]]]:
    """
    返回形如：var rankData = {datas:["a,b,c","d,e,f",...], allRecords:N, ...}
    取 datas 数组中的字符串，每项再用逗号切成单条记录。
    """
    m = re.search(r"datas:\s*\[(.*?)\]", text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    rows = re.findall(r'"([^"]*)"', raw)
    if not rows:
        return None
    return [row.split(",") for row in rows]


def _row_to_record(row: list[str]) -> SourceRecord:
    rec = empty_record(row[0])
    rec["name"] = row[1] if len(row) > 1 else ""
    rec["nav_date"] = row[3] if len(row) > 3 else ""
    rec["nav"] = _safe_float(row[4]) if len(row) > 4 else None
    # 近1年收益率（百分比，附 % 号方便直接渲染）
    if len(row) > 11 and row[11] not in ("", "--"):
        rec["return_1y"] = f"{row[11]}%"
    return rec


def _safe_float(v) -> Optional[float]:
    try:
        return float(v) if v not in (None, "", "-", "--") else None
    except (TypeError, ValueError):
        return None


def fetch_market_snapshot(timeout: int = 30) -> dict[str, SourceRecord]:
    """
    一次拉全市场，返回 {code: SourceRecord} 映射。
    失败抛异常，由调用方决定是否回落备源。

    sd/ed 给一年区间，让接口能算出近1年收益率（关键参数）。
    """
    today = datetime.now().date()
    sd = (today - timedelta(days=365)).isoformat()
    ed = today.isoformat()

    params = {
        "op": "ph",
        "dt": "kf",
        "ft": "all",
        "rs": "",
        "gs": "0",
        "sc": "1nzf",
        "st": "desc",
        "sd": sd,
        "ed": ed,
        "qdii": "",
        "tabSubtype": ",,,,,",
        "pi": "1",
        "pn": "50000",
        "dx": "0",  # 0=包含暂停申购的基金；默认 1 会过滤掉它们
    }
    resp = requests.get(URL, params=params, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    rows = _parse_response(resp.text)
    if not rows:
        raise ValueError("RANKING 接口返回结构异常，未解析到 datas")
    return {row[0]: _row_to_record(row) for row in rows if row and row[0]}


def fetch_one(code: str, snapshot: dict[str, SourceRecord]) -> SourceRecord:
    """从 snapshot 中查找单只基金；不存在时返回 error 记录。"""
    rec = snapshot.get(code)
    if rec is None:
        out = empty_record(code)
        out["error"] = "RANKING 中未找到该基金"
        return out
    return dict(rec)
