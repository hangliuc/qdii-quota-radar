"""
卡片图生成
生成适合小红书发布的竖版基金限购信息卡片（含近1年收益率）
"""

import re
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

# ── 颜色 ──────────────────────────────────────────
BG       = "#F5F7FA"
CARD     = "#FFFFFF"
TITLE_BG = "#1A1A2E"
TITLE_FG = "#FFFFFF"
SUB_FG   = "#8892A3"
GREEN    = "#10B981"
RED      = "#EF4444"
TEXT     = "#334155"
MUTED    = "#94A3B8"
DIVIDER  = "#E2E8F0"
LABEL    = "#64748B"

# ── 字体 ──────────────────────────────────────────
_FONT_PATHS = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]

_font_cache: dict[int, ImageFont.FreeTypeFont] = {}


def _font(size: int) -> ImageFont.FreeTypeFont:
    if size in _font_cache:
        return _font_cache[size]
    for p in _FONT_PATHS:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            _font_cache[size] = f
            return f
    return ImageFont.load_default()


# ── 工具函数 ──────────────────────────────────────
_COMPANIES = [
    "华泰柏瑞", "景顺长城", "易方达", "汇添富",
    "大成", "广发", "国泰", "华安", "华夏", "南方", "天弘",
    "嘉实", "博时", "招商", "摩根", "建信", "宝盈", "万家",
]


def _short_name(name: str) -> str:
    for c in _COMPANIES:
        if name.startswith(c):
            return c
    return name[:2]


def _limit_val(s: str) -> float:
    if "不限" in (s or ""):
        return float("inf")
    if "暂停" in (s or ""):
        return -1
    m = re.search(r"([\d,.]+)", s or "")
    return float(m.group(1).replace(",", "")) if m else -2


def _fmt_limit(s: str) -> str:
    m = re.search(r"([\d,.]+)", s or "")
    if m:
        v = float(m.group(1).replace(",", ""))
        return f"{int(v)}元" if v == int(v) else f"{v}元"
    if "不限" in (s or ""):
        return "不限"
    if "暂停" in (s or ""):
        return "暂停"
    return s or "—"


def _is_suspended(r: dict) -> bool:
    return "暂停" in r.get("purchase_status", "")


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, r, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    for cx, cy, s, e in [
        (x0, y0, 180, 270), (x1 - 2*r, y0, 270, 360),
        (x0, y1 - 2*r, 90, 180), (x1 - 2*r, y1 - 2*r, 0, 90),
    ]:
        draw.pieslice([cx, cy, cx + 2*r, cy + 2*r], s, e, fill=fill)


# ── 主函数 ────────────────────────────────────────
def generate(results: list[dict], output_path: str) -> str:
    """
    生成卡片图并保存。

    Args:
        results: scraper.fetch_all 返回的列表
        output_path: 输出 PNG 路径

    Returns:
        output_path
    """
    # 分组 & 排序
    opened, suspended = [], []
    for r in results:
        if r.get("error"):
            continue
        (_l := suspended if _is_suspended(r) else opened).append(r)

    key = lambda r: (-_limit_val(r.get("purchase_limit", "")), r.get("name", ""))
    opened.sort(key=key)
    suspended.sort(key=key)

    today = datetime.now().strftime("%Y-%m-%d")

    # 布局常量
    W, PAD, CPAD = 1080, 60, 40
    ROW_H, GAP, HDR_H, CR = 72, 32, 180, 24
    COL_HDR_H = 48
    IL, IR = PAD + CPAD, W - PAD - CPAD
    COL_RET = 680  # 收益率列中心 x

    open_h = COL_HDR_H + len(opened) * ROW_H + 20
    susp_h = COL_HDR_H + len(suspended) * ROW_H + 20
    H = PAD + HDR_H + 20 + 80 + 20 + open_h + GAP + susp_h + PAD

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 字体
    ft, fs, fsc, fch = _font(46), _font(26), _font(30), _font(22)
    fn, fc, fl, fr = _font(30), _font(22), _font(34), _font(30)
    fsn, fsl = _font(42), _font(22)

    y = PAD

    # ── 标题 ──
    _rounded_rect(d, (PAD, y, W - PAD, y + HDR_H), CR, TITLE_BG)
    _center_text(d, W, y + 40, "纳斯达克 QDII 基金限购日报", ft, TITLE_FG)
    _center_text(d, W, y + 110, f"C类份额 · {today}", fs, SUB_FG)
    y += HDR_H + 20

    # ── 统计栏 ──
    _rounded_rect(d, (PAD, y, W - PAD, y + 80), 16, CARD)
    sw = (W - PAD * 2) // 3
    for i, (n, lb, co) in enumerate([
        (str(len(opened) + len(suspended)), "只基金", TEXT),
        (str(len(opened)), "可申购", GREEN),
        (str(len(suspended)), "暂停中", RED),
    ]):
        cx = PAD + sw * i + sw // 2
        _center_text(d, cx * 2, y + 6, n, fsn, co, absolute_center=cx)
        _center_text(d, cx * 2, y + 50, lb, fsl, SUB_FG, absolute_center=cx)
    y += 100

    # ── 列表 ──
    def _section(y, funds, label, color, is_open):
        h = COL_HDR_H + len(funds) * ROW_H + 20
        _rounded_rect(d, (PAD, y, W - PAD, y + h), CR, CARD)
        d.text((IL, y + 10), label, fill=color, font=fsc)
        # 列标题
        _right_text(d, IR, y + 14, "限额", fch, LABEL)
        bb = d.textbbox((0, 0), "近1年", font=fch)
        d.text((COL_RET - (bb[2] - bb[0]) // 2, y + 14), "近1年", fill=LABEL, font=fch)

        ry = y + COL_HDR_H
        for i, r in enumerate(funds):
            if i > 0:
                d.line([(IL, ry), (IR, ry)], fill=DIVIDER, width=1)
            _draw_row(d, ry, r, is_open)
            ry += ROW_H
        return y + h

    def _draw_row(d, ry, r, is_open):
        nm = _short_name(r.get("name", ""))
        code = r.get("code", "")
        lim = _fmt_limit(r.get("purchase_limit", ""))
        ret = r.get("return_1y", "—") or "—"

        d.text((IL, ry + 14), nm, fill=TEXT, font=fn)
        nb = d.textbbox((0, 0), nm, font=fn)
        d.text((IL + nb[2] - nb[0] + 12, ry + 20), code, fill=MUTED, font=fc)

        # 收益率
        rc = RED if ret != "—" and not ret.startswith("-") else (GREEN if ret.startswith("-") else MUTED)
        rb = d.textbbox((0, 0), ret, font=fr)
        d.text((COL_RET - (rb[2] - rb[0]) // 2, ry + 14), ret, fill=rc, font=fr)

        # 限额
        lc = GREEN if is_open else RED
        _right_text(d, IR, ry + 12, lim, fl, lc)

    y = _section(y, opened, "🟢 可申购", GREEN, True)
    y += GAP
    _section(y, suspended, "🔴 暂停申购", RED, False)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"📸 卡片已生成: {output_path}")
    return output_path


def _center_text(d, w, y, text, font, fill, absolute_center=None):
    bb = d.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    x = (absolute_center - tw // 2) if absolute_center else ((w - tw) // 2)
    d.text((x, y), text, fill=fill, font=font)


def _right_text(d, right_x, y, text, font, fill):
    bb = d.textbbox((0, 0), text, font=font)
    d.text((right_x - (bb[2] - bb[0]), y), text, fill=fill, font=font)
