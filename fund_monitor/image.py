"""
卡片图生成
生成适合小红书发布的竖版基金限购信息卡片（含近1年收益率）
小红书最佳比例: 3:4 (1080×1440) 或 2:3 (1080×1620)
"""

import re
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

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
    # Docker（与 macOS 相同的 STHeiti Medium）
    "/usr/share/fonts/custom/STHeiti-Medium.ttc",
    # macOS
    "/System/Library/Fonts/STHeiti Medium.ttc",
]

_font_cache = {}


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

def _limit_val(s: str) -> float:
    """解析限额为数值（单位：元），用于排序"""
    if "不限" in (s or ""):
        return float("inf")
    if "暂停" in (s or ""):
        return -1
    m = re.search(r"([\d,.]+)\s*万", s or "")
    if m:
        return float(m.group(1).replace(",", "")) * 10000
    m = re.search(r"([\d,.]+)", s or "")
    return float(m.group(1).replace(",", "")) if m else -2


def _fmt_limit(s: str) -> str:
    """格式化限额显示"""
    m = re.search(r"([\d,.]+)\s*万元", s or "")
    if m:
        v = float(m.group(1).replace(",", ""))
        return f"{int(v)}万元" if v == int(v) else f"{v}万元"
    m = re.search(r"([\d,.]+)\s*元", s or "")
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


def _rounded_rect(draw, xy, r, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    for cx, cy, s, e in [
        (x0, y0, 180, 270), (x1 - 2*r, y0, 270, 360),
        (x0, y1 - 2*r, 90, 180), (x1 - 2*r, y1 - 2*r, 0, 90),
    ]:
        draw.pieslice([cx, cy, cx + 2*r, cy + 2*r], s, e, fill=fill)


def _center_text(d, w, y, text, font, fill, absolute_center=None):
    bb = d.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    x = (absolute_center - tw // 2) if absolute_center else ((w - tw) // 2)
    d.text((x, y), text, fill=fill, font=font)


def _right_text(d, right_x, y, text, font, fill):
    bb = d.textbbox((0, 0), text, font=font)
    d.text((right_x - (bb[2] - bb[0]), y), text, fill=fill, font=font)


# ── 主函数 ────────────────────────────────────────

def generate(results: list[dict], output_path: str,
             title: str = "纳斯达克 QDII 基金限购日报",
             subtitle_prefix: str = "C类份额") -> str:
    """生成卡片图并保存，返回 output_path。"""

    # 分组 & 排序（开放按限额从大到小，暂停同理）
    opened, suspended = [], []
    for r in results:
        if r.get("error"):
            continue
        (suspended if _is_suspended(r) else opened).append(r)

    sort_key = lambda r: (-_limit_val(r.get("purchase_limit", "")), r.get("name", ""))
    opened.sort(key=sort_key)
    suspended.sort(key=sort_key)

    today = datetime.now().strftime("%Y-%m-%d")

    # ── 布局（针对小红书优化，目标比例 ≈ 3:4） ──
    W       = 1080       # 小红书标准宽度
    PAD     = 36         # 外边距（60→36）
    CPAD    = 36         # 卡片内边距（40→36）
    ROW_H   = 64         # 行高（80→64，更紧凑）
    GAP     = 20         # 两个 section 间距（36→20）
    HDR_H   = 148        # 标题区高度（200→148）
    CR      = 20         # 圆角半径（24→20）
    COL_HDR_H = 44       # 列头高度（52→44）
    STAT_H  = 76         # 统计栏高度（88→76）
    CARD_PAD = 16        # 卡片底部内边距（24→16）

    IL, IR = PAD + CPAD, W - PAD - CPAD
    COL_RET = 690        # 收益率列中心（700→690，微调）

    open_h = COL_HDR_H + len(opened) * ROW_H + CARD_PAD
    susp_h = COL_HDR_H + len(suspended) * ROW_H + CARD_PAD
    H = PAD + HDR_H + 14 + STAT_H + 14 + open_h + GAP + susp_h + PAD

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ── 字体（整体缩小 2-4px，适配紧凑行高） ──
    ft  = _font(44)   # 标题（48→44）
    fs  = _font(26)   # 副标题（28→26）
    fsc = _font(30)   # section 标题（32→30）
    fch = _font(22)   # 列标题（24→22）
    fn  = _font(28)   # 基金名称（30→28）
    fc  = _font(22)   # 基金代码（24→22）
    fl  = _font(32)   # 限额数字（36→32）
    fr  = _font(28)   # 收益率数字（30→28）
    fsn = _font(40)   # 统计栏数字（44→40）
    fsl = _font(22)   # 统计栏标签（24→22）

    y = PAD

    # ── 标题 ──
    _rounded_rect(d, (PAD, y, W - PAD, y + HDR_H), CR, TITLE_BG)
    _center_text(d, W, y + 34, title, ft, TITLE_FG)
    _center_text(d, W, y + 96, f"{subtitle_prefix} · {today}", fs, SUB_FG)
    y += HDR_H + 14

    # ── 统计栏 ──
    _rounded_rect(d, (PAD, y, W - PAD, y + STAT_H), 14, CARD)
    sw = (W - PAD * 2) // 3
    for i, (n, lb, co) in enumerate([
        (str(len(opened) + len(suspended)), "只基金", TEXT),
        (str(len(opened)), "可申购", GREEN),
        (str(len(suspended)), "暂停中", RED),
    ]):
        cx = PAD + sw * i + sw // 2
        _center_text(d, cx * 2, y + 6, n, fsn, co, absolute_center=cx)
        _center_text(d, cx * 2, y + 48, lb, fsl, SUB_FG, absolute_center=cx)
    y += STAT_H + 14

    # ── 列表绘制 ──
    def draw_section(y, funds, label, color, is_open):
        h = COL_HDR_H + len(funds) * ROW_H + CARD_PAD
        _rounded_rect(d, (PAD, y, W - PAD, y + h), CR, CARD)
        d.text((IL, y + 10), label, fill=color, font=fsc)
        _right_text(d, IR, y + 14, "限额", fch, LABEL)
        bb = d.textbbox((0, 0), "近1年", font=fch)
        d.text((COL_RET - (bb[2] - bb[0]) // 2, y + 14), "近1年", fill=LABEL, font=fch)

        ry = y + COL_HDR_H
        for i, r in enumerate(funds):
            if i > 0:
                d.line([(IL, ry), (IR, ry)], fill=DIVIDER, width=1)
            draw_row(d, ry, r, is_open)
            ry += ROW_H
        return y + h

    def draw_row(d, ry, r, is_open):
        nm = r.get("display") or r.get("name", "")
        code = r.get("code", "")
        lim = _fmt_limit(r.get("purchase_limit", ""))
        ret = r.get("return_1y", "—") or "—"

        # 垂直居中偏移
        text_y = ry + (ROW_H - 28) // 2  # 基于名称字号居中
        code_y = text_y + 4               # 代码略偏下对齐基线
        limit_y = ry + (ROW_H - 32) // 2  # 基于限额字号居中
        ret_y = text_y                     # 收益率与名称对齐

        # 名称 + 代码
        d.text((IL, text_y), nm, fill=TEXT, font=fn)
        nb = d.textbbox((0, 0), nm, font=fn)
        d.text((IL + nb[2] - nb[0] + 10, code_y), code, fill=MUTED, font=fc)

        # 收益率
        rc = RED if ret != "—" and not ret.startswith("-") else (GREEN if ret.startswith("-") else MUTED)
        rb = d.textbbox((0, 0), ret, font=fr)
        d.text((COL_RET - (rb[2] - rb[0]) // 2, ret_y), ret, fill=rc, font=fr)

        # 限额
        _right_text(d, IR, limit_y, lim, fl, GREEN if is_open else RED)

    y = draw_section(y, opened, "可申购", GREEN, True)
    y += GAP
    draw_section(y, suspended, "暂停申购", RED, False)

    # ── 保存 ──
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"📸 卡片已生成: {output_path}  ({W}×{H}, 比例 {H/W:.2f})")
    return output_path
