"""
图片生成模块
生成适合小红书发布的竖版基金限购信息卡片
"""

import re
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional


# ---------- 颜色 ----------
BG_COLOR = "#F5F7FA"
CARD_BG = "#FFFFFF"
TITLE_BG = "#1A1A2E"
TITLE_TEXT = "#FFFFFF"
SUBTITLE_TEXT = "#8892A3"
OPEN_COLOR = "#10B981"
SUSPEND_COLOR = "#EF4444"
LIMIT_COLOR = "#1E293B"
NAME_COLOR = "#334155"
CODE_COLOR = "#94A3B8"
DIVIDER_COLOR = "#E2E8F0"
RETURN_POS_COLOR = "#EF4444"
RETURN_NEG_COLOR = "#10B981"
HEADER_LABEL_COLOR = "#64748B"

# ---------- 字体查找 ----------
FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]


def _find_font() -> Optional[str]:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    path = _find_font()
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _parse_limit_value(limit_str: str) -> float:
    if not limit_str:
        return -2
    if "暂停" in limit_str:
        return -1
    if "不限" in limit_str:
        return float("inf")
    match = re.search(r"([\d,.]+)", limit_str)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return -2
    return -2


def _is_suspended(r: dict) -> bool:
    return "暂停" in r.get("purchase_status", "")


def _short_name(name: str) -> str:
    """提取基金公司简称"""
    companies = [
        "华泰柏瑞", "景顺长城", "易方达", "汇添富",
        "大成", "广发", "国泰", "华安", "华夏", "南方", "天弘",
        "嘉实", "博时", "招商", "摩根", "建信", "宝盈", "万家",
    ]
    for c in companies:
        if name.startswith(c):
            return c
    return name[:2]


def _format_limit(limit_str: str) -> str:
    match = re.search(r"([\d,.]+)", limit_str or "")
    if match:
        val = float(match.group(1).replace(",", ""))
        if val == int(val):
            return f"{int(val)}元"
        return f"{val}元"
    if "不限" in (limit_str or ""):
        return "不限"
    if "暂停" in (limit_str or ""):
        return "暂停"
    return limit_str or "—"


def _draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)


def _draw_fund_row(draw, ry, r, fonts, layout, is_open):
    """绘制单行基金数据"""
    font_name, font_code, font_limit, font_return = fonts
    pad_l, col_return_x, col_limit_x, pad_r = layout

    name = _short_name(r.get("name", ""))
    code = r.get("code", "")
    limit = _format_limit(r.get("purchase_limit", ""))
    return_1y = r.get("return_1y", "—") or "—"

    # 基金名称
    draw.text((pad_l, ry + 14), name, fill=NAME_COLOR, font=font_name)
    name_bbox = draw.textbbox((0, 0), name, font=font_name)
    name_w = name_bbox[2] - name_bbox[0]
    # 基金代码
    draw.text((pad_l + name_w + 12, ry + 20), code, fill=CODE_COLOR, font=font_code)

    # 近1年收益率（居中对齐到列）
    if return_1y != "—" and return_1y.replace("-", "").replace(".", "").replace("%", "").isdigit():
        ret_color = RETURN_NEG_COLOR if return_1y.startswith("-") else RETURN_POS_COLOR
    else:
        ret_color = CODE_COLOR
    ret_bbox = draw.textbbox((0, 0), return_1y, font=font_return)
    ret_w = ret_bbox[2] - ret_bbox[0]
    draw.text((col_return_x - ret_w // 2, ry + 14), return_1y, fill=ret_color, font=font_return)

    # 限额（右对齐）
    limit_color = OPEN_COLOR if is_open else SUSPEND_COLOR
    lim_bbox = draw.textbbox((0, 0), limit, font=font_limit)
    lim_w = lim_bbox[2] - lim_bbox[0]
    draw.text((pad_r - lim_w, ry + 12), limit, fill=limit_color, font=font_limit)


def generate_card(results: list[dict], output_path: str = "output/fund_card.png") -> str:
    """
    生成小红书风格的基金限购信息卡片（含近1年收益率）

    Args:
        results: fetch_all_funds 返回的结果列表
        output_path: 输出图片路径

    Returns:
        输出图片的路径
    """
    # ---------- 数据准备 ----------
    open_funds = []
    suspended_funds = []
    for r in results:
        if r.get("error"):
            continue
        if _is_suspended(r):
            suspended_funds.append(r)
        else:
            open_funds.append(r)

    def limit_sort(r):
        return (-_parse_limit_value(r.get("purchase_limit", "")), r.get("name", ""))

    open_funds.sort(key=limit_sort)
    suspended_funds.sort(key=limit_sort)

    today = datetime.now().strftime("%Y-%m-%d")

    # ---------- 布局参数 ----------
    W = 1080
    PAD = 60          # 画布边距
    CPAD = 40         # 卡片内边距
    ROW_H = 72
    SECTION_GAP = 32
    HEADER_H = 180
    CARD_R = 24
    COL_HDR_H = 48    # 列标题行高
    CARD_INNER_L = PAD + CPAD
    CARD_INNER_R = W - PAD - CPAD

    # 列位置
    COL_RETURN_X = 680   # 近1年收益率列中心
    COL_LIMIT_X = W - PAD - CPAD  # 限额列右对齐

    # 计算高度
    open_card_h = COL_HDR_H + len(open_funds) * ROW_H + 20
    suspend_card_h = COL_HDR_H + len(suspended_funds) * ROW_H + 20
    H = (
        PAD
        + HEADER_H + 20
        + 80 + 20          # 统计栏
        + open_card_h + SECTION_GAP
        + suspend_card_h
        + PAD
    )

    # ---------- 画布 ----------
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ---------- 字体 ----------
    f_title = _load_font(46)
    f_sub = _load_font(26)
    f_section = _load_font(30)
    f_col_hdr = _load_font(22)
    f_name = _load_font(30)
    f_code = _load_font(22)
    f_limit = _load_font(34)
    f_return = _load_font(30)
    f_stat_num = _load_font(42)
    f_stat_label = _load_font(22)

    y = PAD

    # ---------- 标题 ----------
    _draw_rounded_rect(draw, (PAD, y, W - PAD, y + HEADER_H), CARD_R, TITLE_BG)

    title = "纳斯达克 QDII 基金限购日报"
    tb = draw.textbbox((0, 0), title, font=f_title)
    draw.text(((W - tb[2] + tb[0]) // 2, y + 40), title, fill=TITLE_TEXT, font=f_title)

    sub = f"C类份额 · {today}"
    sb = draw.textbbox((0, 0), sub, font=f_sub)
    draw.text(((W - sb[2] + sb[0]) // 2, y + 110), sub, fill=SUBTITLE_TEXT, font=f_sub)

    y += HEADER_H + 20

    # ---------- 统计栏 ----------
    _draw_rounded_rect(draw, (PAD, y, W - PAD, y + 80), 16, CARD_BG)
    stat_w = (W - PAD * 2) // 3
    stats = [
        (str(len(open_funds) + len(suspended_funds)), "只基金", NAME_COLOR),
        (str(len(open_funds)), "可申购", OPEN_COLOR),
        (str(len(suspended_funds)), "暂停中", SUSPEND_COLOR),
    ]
    for i, (num, label, color) in enumerate(stats):
        cx = PAD + stat_w * i + stat_w // 2
        nb = draw.textbbox((0, 0), num, font=f_stat_num)
        draw.text((cx - (nb[2] - nb[0]) // 2, y + 6), num, fill=color, font=f_stat_num)
        lb = draw.textbbox((0, 0), label, font=f_stat_label)
        draw.text((cx - (lb[2] - lb[0]) // 2, y + 50), label, fill=SUBTITLE_TEXT, font=f_stat_label)

    y += 80 + 20

    # ---------- 绘制基金列表卡片 ----------
    def _draw_section(y, funds, section_label, section_color, is_open):
        card_h = COL_HDR_H + len(funds) * ROW_H + 20
        _draw_rounded_rect(draw, (PAD, y, W - PAD, y + card_h), CARD_R, CARD_BG)

        # section 标题
        draw.text((CARD_INNER_L, y + 10), section_label, fill=section_color, font=f_section)

        # 列标题（右侧）
        hdr_y = y + 10
        # "近1年" 列标题
        h1 = "近1年"
        hb = draw.textbbox((0, 0), h1, font=f_col_hdr)
        draw.text((COL_RETURN_X - (hb[2] - hb[0]) // 2, hdr_y + 4), h1, fill=HEADER_LABEL_COLOR, font=f_col_hdr)
        # "限额" 列标题
        h2 = "限额"
        hb2 = draw.textbbox((0, 0), h2, font=f_col_hdr)
        draw.text((CARD_INNER_R - (hb2[2] - hb2[0]), hdr_y + 4), h2, fill=HEADER_LABEL_COLOR, font=f_col_hdr)

        row_y = y + COL_HDR_H
        fonts = (f_name, f_code, f_limit, f_return)
        layout = (CARD_INNER_L, COL_RETURN_X, COL_LIMIT_X, CARD_INNER_R)

        for i, r in enumerate(funds):
            ry = row_y + i * ROW_H
            if i > 0:
                draw.line(
                    [(CARD_INNER_L, ry), (CARD_INNER_R, ry)],
                    fill=DIVIDER_COLOR, width=1,
                )
            _draw_fund_row(draw, ry, r, fonts, layout, is_open)

        return y + card_h

    # 可申购
    y = _draw_section(y, open_funds, "🟢 可申购", OPEN_COLOR, True)
    y += SECTION_GAP

    # 暂停申购
    _draw_section(y, suspended_funds, "🔴 暂停申购", SUSPEND_COLOR, False)

    # ---------- 保存 ----------
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"📸 卡片已生成: {output_path}")
    return output_path
