"""
交易日判断

支付宝 QDII 基金的申购/赎回遵循中国 A 股交易日：
- 周末不开放
- 中国法定节假日不开放（含调休）

依赖 chinese_calendar 库；若未安装，则降级为仅判断周末。
"""

from datetime import date, datetime
from typing import Optional

try:
    import chinese_calendar  # type: ignore
    _HAS_CN_CAL = True
except ImportError:  # pragma: no cover
    _HAS_CN_CAL = False


def is_trading_day(d: Optional[date] = None) -> tuple[bool, str]:
    """
    判断给定日期是否为交易日。

    Returns:
        (是否交易日, 说明原因)
    """
    d = d or datetime.now().date()

    # 先判断周末
    weekday = d.weekday()  # Mon=0, Sun=6
    if weekday >= 5:
        return False, f"{d} 是{'周六' if weekday == 5 else '周日'}"

    if not _HAS_CN_CAL:
        return True, f"{d} 是工作日（未安装 chinese_calendar，仅判断周末）"

    # chinese_calendar 处理调休：节假日返回 True，调休补班的周末返回 False
    try:
        if chinese_calendar.is_holiday(d):
            holiday_detail = chinese_calendar.get_holiday_detail(d)
            # get_holiday_detail 返回 (is_holiday, name)
            name = holiday_detail[1] if isinstance(holiday_detail, tuple) and len(holiday_detail) > 1 else ""
            reason = f"{d} 是法定节假日"
            if name:
                reason += f"（{name}）"
            return False, reason
    except NotImplementedError:
        # chinese_calendar 数据未覆盖该年份
        return True, f"{d} 不在 chinese_calendar 数据范围内，按工作日处理"

    return True, f"{d} 是交易日"
