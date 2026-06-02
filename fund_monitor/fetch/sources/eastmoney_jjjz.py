"""
主数据源：天天基金 JSON 接口（基金申购状态汇总表）

接口：https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx
特点：
- 一次拉全市场（约 2.6 万只），本地查表，避免 N 次 HTML 请求
- 字段结构稳定（前端改版几乎不影响）
- 直接给出"申购状态"和"日累计限定金额"两个字段

字段顺序（基于 akshare.fund_purchase_em 实现，已实测确认）：
  [0]  fcode             基金代码
  [1]  shortname         基金简称
  [2]  fundtype          基金类型（如"指数型-海外股票"）
  [3]  nav               最新净值/万份收益
  [4]  navdate           报告时间（"MM-DD"）
  [5]  buy_status        申购状态（"开放申购"/"限大额"/"暂停申购"）
  [6]  redeem_status     赎回状态
  [7]  next_open         下一开放日
  [8]  buy_min           购买起点（单位：元）
  [9]  day_limit         日累计限定金额（单位：元）
  [12] fee               手续费
"""

import json
import re
import requests
from typing import Optional

from fund_monitor.fetch.sources.base import SourceRecord, empty_record, format_limit_yuan

URL = "https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://fund.eastmoney.com/",
    "Accept": "*/*",
}


def _parse_response(text: str) -> Optional[list]:
    """
    返回形如：var reData={datas:[[...],[...]], record:"26660", ...}
    用正则取出 datas 数组并 json 解析。
    """
    m = re.search(r"datas:(\[.*?\]\])\s*,", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _row_to_record(row: list) -> SourceRecord:
    rec = empty_record(row[0])
    rec["name"] = row[1] or ""
    rec["nav"] = _safe_float(row[3])
    rec["nav_date"] = row[4] or ""

    status = row[5] or "未知"
    rec["purchase_status"] = status

    if "暂停" in status:
        rec["purchase_limit"] = "暂停"
    elif "开放" in status:
        rec["purchase_limit"] = "不限"
    else:
        rec["purchase_limit"] = format_limit_yuan(_safe_float(row[9]))

    return rec


def _safe_float(v) -> Optional[float]:
    try:
        return float(v) if v not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def fetch_market_snapshot(timeout: int = 30) -> dict[str, SourceRecord]:
    """
    一次拉全市场，返回 {code: SourceRecord} 映射。
    失败抛异常，由调用方决定是否回落备源。
    """
    params = {"t": "8", "page": "1,50000", "js": "reData", "sort": "fcode,asc"}
    resp = requests.get(URL, params=params, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    rows = _parse_response(resp.text)
    if not rows:
        raise ValueError("JJJZ 接口返回结构异常，未解析到 datas")
    return {row[0]: _row_to_record(row) for row in rows if row and row[0]}


def fetch_one(code: str, snapshot: dict[str, SourceRecord]) -> SourceRecord:
    """从 snapshot 中查找单只基金；不存在时返回 error 记录。"""
    rec = snapshot.get(code)
    if rec is None:
        out = empty_record(code)
        out["error"] = "JJJZ 中未找到该基金"
        return out
    # 复制一份避免被外部修改
    return dict(rec)
