"""
图片生成模块
生成适合小红书发布的竖版基金限购信息卡片
"""

import re
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional


# ---------- 颜色常量 ----------
WHITE = "#FFFFFF"
BG_COLOR = "#F5F7FA"
CARD_BG = "#FFFFFF"
TITLE_BG = "#1A1A2E"
TITLE_TEXT = "#FFFFFF"
SUBTITLE_TEXT = "#8892A3"
OPEN_COLOR = "#10B981"
OPEN_BG = "#ECFDF5"
SUSPEND_COLOR = "#EF4444"
SUSPEND_BG = "#FEF2F2"
LIMIT_COLOR = "#1E293B"
NAME_COLOR = "#334155"
CODE_COLOR = "#94A3B8"
DIVIDER_COLOR = "#E2E8F0"
BADGE_OPEN = "#D1FAE5"
BADGE_SUSPEND = "#FEE2E2"
WATERMARK_COLOR = "#CBD5E1"

# ---------- 字体 ----------
# 按优先级尝试加载中文字体
FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    # Linux
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]

FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
]


def _find_font(candidates: list[str]) -> Optional[str]:
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_CANDIDATES
    path = _find_font(candidates)
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
    """提取基金公司简称，如 '大成纳斯达克100ETF联接(QDII)C' → '大成'"""
    # 去掉尾部的份额类型和括号
    companies = [
        "大成", "广发", "国泰", "华安", "易方达", "华夏", "南方", "天弘",
        "景顺长城", "嘉实", "博时", "招商", "华泰柏瑞", "摩根", "汇添富",
        "建信", "宝盈", "万家",
    ]
    for c in companies:
        if name.startswith(c):
            return c
    return name[:2]


def _format_limit(limit_str: str) -> str:
    """格式化限额显示，如 '200.00元' → '200元', '10.00元' → '10元'"""
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
    return limit_str or "未知"


def _draw_rounded_rect(draw, xy, radius, fill):
    """绘制圆角矩形"""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2 * radius, y0 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2 * radius, y0, x1, y0 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2 * radius, x0 + 2 * radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2 * radius, y1 - 2 * radius, x1, y1], 0, 90, fill=fill)


def generate_card(results: list[dict], output_path: str = "output/fund_card.png") -> str:
    """
    生成小红书风格的基金限购信息卡片

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

    # 各组内按额度从大到小
    def limit_sort(r):
        return (-_parse_limit_value(r.get("purchase_limit", "")), r.get("name", ""))

    open_funds.sort(key=limit_sort)
    suspended_funds.sort(key=limit_sort)

    today = datetime.now().strftime("%Y-%m-%d")

    # ---------- 布局参数 ----------
    W = 1080
    PADDING = 60
    CARD_PADDING = 40
    CARD_INNER_W = W - PADDING * 2
    ROW_H = 72
    SECTION_GAP = 36
    HEADER_H = 200
    CARD_RADIUS = 24

    # 计算总高度
    total_rows = len(open_funds) + len(suspended_funds)
    # header + stats + open section header + open rows + gap + suspend section header + suspend rows + footer
    content_h = (
        HEADER_H
        + 80  # 统计栏
        + 56  # "可申购" section header
        + len(open_funds) * ROW_H
        + SECTION_GAP
        + 56  # "暂停申购" section header
        + len(suspended_funds) * ROW_H
        + 80  # footer / watermark
        + 60  # bottom padding
    )
    H = content_h + PADDING * 2

    # ---------- 创建画布 ----------
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ---------- 字体 ----------
    font_title = _load_font(48, bold=True)
    font_subtitle = _load_font(28)
    font_section = _load_font(32, bold=True)
    font_name = _load_font(30)
    font_limit = _load_font(34, bold=True)
    font_badge = _load_font(24)
    font_code = _load_font(22)
    font_stat_num = _load_font(44, bold=True)
    font_stat_label = _load_font(22)
    font_watermark = _load_font(22)

    y = PADDING

    # ---------- 标题区域 ----------
    _draw_rounded_rect(draw, (PADDING, y, W - PADDING, y + HEADER_H), CARD_RADIUS, TITLE_BG)

    # 标题文字
    title_text = "纳斯达克 QDII 基金限购"
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y + 45), title_text, fill=TITLE_TEXT, font=font_title)

    # 副标题
    sub_text = f"支付宝渠道 · C类份额 · {today} 更新"
    bbox = draw.textbbox((0, 0), sub_text, font=font_subtitle)
    sw = bbox[2] - bbox[0]
    draw.text(((W - sw) // 2, y + 115), sub_text, fill="#8892A3", font=font_subtitle)

    y += HEADER_H + 24

    # ---------- 统计栏 ----------
    _draw_rounded_rect(draw, (PADDING, y, W - PADDING, y + 80), 16, CARD_BG)

    stat_w = CARD_INNER_W // 3
    stats = [
        (str(len(open_funds) + len(suspended_funds)), "只基金", NAME_COLOR),
        (str(len(open_funds)), "可申购", OPEN_COLOR),
        (str(len(suspended_funds)), "暂停中", SUSPEND_COLOR),
    ]
    for i, (num, label, color) in enumerate(stats):
        cx = PADDING + stat_w * i + stat_w // 2
        bbox = draw.textbbox((0, 0), num, font=font_stat_num)
        nw = bbox[2] - bbox[0]
        draw.text((cx - nw // 2, y + 8), num, fill=color, font=font_stat_num)
        bbox = draw.textbbox((0, 0), label, font=font_stat_label)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, y + 52), label, fill=SUBTITLE_TEXT, font=font_stat_label)

    y += 80 + 24

    # ---------- 可申购区域 ----------
    open_card_h = 56 + len(open_funds) * ROW_H + 16
    _draw_rounded_rect(draw, (PADDING, y, W - PADDING, y + open_card_h), CARD_RADIUS, CARD_BG)

    # section header
    draw.text((PADDING + CARD_PADDING, y + 14), "🟢 可申购", fill=OPEN_COLOR, font=font_section)
    y += 56

    for i, r in enumerate(open_funds):
        ry = y + i * ROW_H
        name = _short_name(r.get("name", ""))
        code = r.get("code", "")
        limit = _format_limit(r.get("purchase_limit", ""))

        # 分隔线
        if i > 0:
            draw.line(
                [(PADDING + CARD_PADDING, ry), (W - PADDING - CARD_PADDING, ry)],
                fill=DIVIDER_COLOR, width=1,
            )

        # 基金名称
        draw.text((PADDING + CARD_PADDING, ry + 12), name, fill=NAME_COLOR, font=font_name)

        # 基金代码
        name_bbox = draw.textbbox((0, 0), name, font=font_name)
        name_w = name_bbox[2] - name_bbox[0]
        draw.text(
            (PADDING + CARD_PADDING + name_w + 12, ry + 18),
            code, fill=CODE_COLOR, font=font_code,
        )

        # 限额 badge（右侧）
        limit_bbox = draw.textbbox((0, 0), limit, font=font_limit)
        limit_w = limit_bbox[2] - limit_bbox[0]
        limit_x = W - PADDING - CARD_PADDING - limit_w
        draw.text((limit_x, ry + 14), limit, fill=OPEN_COLOR, font=font_limit)

        # 额度标签
        tag = "限额"
        tag_bbox = draw.textbbox((0, 0), tag, font=font_code)
        tag_w = tag_bbox[2] - tag_bbox[0]
        draw.text((limit_x - tag_w - 8, ry + 22), tag, fill=CODE_COLOR, font=font_code)

    y += len(open_funds) * ROW_H + 16 + SECTION_GAP

    # ---------- 暂停申购区域 ----------
    suspend_card_h = 56 + len(suspended_funds) * ROW_H + 16
    _draw_rounded_rect(draw, (PADDING, y, W - PADDING, y + suspend_card_h), CARD_RADIUS, CARD_BG)

    draw.text((PADDING + CARD_PADDING, y + 14), "🔴 暂停申购", fill=SUSPEND_COLOR, font=font_section)
    y += 56

    for i, r in enumerate(suspended_funds):
        ry = y + i * ROW_H
        name = _short_name(r.get("name", ""))
        code = r.get("code", "")
        limit = _format_limit(r.get("purchase_limit", ""))

        if i > 0:
            draw.line(
                [(PADDING + CARD_PADDING, ry), (W - PADDING - CARD_PADDING, ry)],
                fill=DIVIDER_COLOR, width=1,
            )

        draw.text((PADDING + CARD_PADDING, ry + 12), name, fill=NAME_COLOR, font=font_name)

        name_bbox = draw.textbbox((0, 0), name, font=font_name)
        name_w = name_bbox[2] - name_bbox[0]
        draw.text(
            (PADDING + CARD_PADDING + name_w + 12, ry + 18),
            code, fill=CODE_COLOR, font=font_code,
        )

        limit_bbox = draw.textbbox((0, 0), limit, font=font_limit)
        limit_w = limit_bbox[2] - limit_bbox[0]
        limit_x = W - PADDING - CARD_PADDING - limit_w
        draw.text((limit_x, ry + 14), limit, fill=SUSPEND_COLOR, font=font_limit)

        tag = "限额"
        tag_bbox = draw.textbbox((0, 0), tag, font=font_code)
        tag_w = tag_bbox[2] - tag_bbox[0]
        draw.text((limit_x - tag_w - 8, ry + 22), tag, fill=CODE_COLOR, font=font_code)

    y += len(suspended_funds) * ROW_H + 16 + 24

    # ---------- 底部水印 ----------
    watermark = "数据来源：天天基金  ·  仅供参考，不构成投资建议"
    bbox = draw.textbbox((0, 0), watermark, font=font_watermark)
    ww = bbox[2] - bbox[0]
    draw.text(((W - ww) // 2, y + 10), watermark, fill=WATERMARK_COLOR, font=font_watermark)

    # ---------- 保存 ----------
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG", quality=95)
    print(f"📸 卡片已生成: {output_path}")
    return output_path
