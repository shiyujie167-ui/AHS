from datetime import datetime, timedelta
# ======= Helper Functions =======

def normalize_time_format(tstr):
    """标准化时间格式为HH:MM"""
    if not isinstance(tstr, str):
        tstr = str(tstr) if tstr is not None else ""
    tstr = tstr.strip()
    if not tstr:
        return ""
    import re
    # 如果只输入了类似 '12'、'8' 的数字，就自动补上 ':00'
    if re.match(r'^\d{1,2}$', tstr):
        tstr = tstr + ":00"
    parts = tstr.split(":")
    if len(parts) >= 2 and len(parts[0]) == 1:
        parts[0] = "0" + parts[0]
    tstr_norm = ":".join(parts)
    try:
        dt = datetime.strptime(tstr_norm, "%H:%M")
        return dt.strftime("%H:%M")
    except:
        return tstr_norm


def normalize_shift(shift_str):
    """标准化班次格式为HH:MM-HH:MM"""
    if not isinstance(shift_str, str):
        shift_str = str(shift_str) if shift_str is not None else ""
    if not shift_str.strip():
        return ""
    parts = shift_str.split("-")
    norm_parts = [normalize_time_format(p) for p in parts]
    return "-".join(norm_parts)


def floor_to_half_hour(dt):
    """向下取整到半小时"""
    if dt.minute < 30:
        return dt.replace(minute=0, second=0, microsecond=0)
    else:
        return dt.replace(minute=30, second=0, microsecond=0)


def ceil_to_half_hour(dt):
    """向上取整到半小时"""
    if dt.minute == 0 or dt.minute == 30:
        return dt.replace(second=0, microsecond=0)
    elif dt.minute < 30:
        return dt.replace(minute=30, second=0, microsecond=0)
    else:
        dt_next = dt.replace(second=0, microsecond=0)
        dt_next += timedelta(hours=1)
        return dt_next.replace(minute=0, second=0, microsecond=0)


def slot_fully_in_interval(slot_start, slot_end, interval_str):
    """
    判断时间段 slot 是否完整落在 interval_str 表示的区间内，
    interval_str 格式要求 "HH:MM-HH:MM"
    """
    if not interval_str or not interval_str.strip():
        return False
    try:
        start_str, end_str = interval_str.split("-")
        interval_start = datetime.strptime(start_str.strip(), "%H:%M")
        interval_end = datetime.strptime(end_str.strip(), "%H:%M")
        return slot_start >= interval_start and slot_end <= interval_end
    except:
        return False


def slot_in_interval(slot_start, slot_end, interval_str):
    """
    判断给定时间段(slot_start-slot_end)的中点是否落在 interval_str 表示的区间内，
    interval_str 格式为 "HH:MM-HH:MM"
    """
    if not interval_str or not interval_str.strip():
        return False
    try:
        start_str, end_str = interval_str.split("-")
        interval_start = datetime.strptime(start_str.strip(), "%H:%M")
        interval_end = datetime.strptime(end_str.strip(), "%H:%M")
        mid = slot_start + (slot_end - slot_start) / 2
        return interval_start <= mid < interval_end
    except:
        return False


def compute_interval_hours(interval_str):
    """
    解析类似 "14:00-18:00" 的时间段，返回持续时间（小时）
    """
    if not interval_str or not interval_str.strip():
        return 0.0
    try:
        start_str, end_str = interval_str.split("-")
        start_dt = datetime.strptime(start_str.strip(), "%H:%M")
        end_dt = datetime.strptime(end_str.strip(), "%H:%M")
        diff = (end_dt - start_dt).total_seconds() / 3600.0
        return max(diff, 0.0)
    except:
        return 0.0


def compute_shift_effective_hours(shift_str, lunch_str, dinner_str, leave_str, off_str):
    """
    计算单个排班记录的班次有效工时：
    班次工时 = (班次结束时间 - 班次开始时间)
    扣除午餐和晚餐（若均提供则扣1小时，若仅提供一项扣0.5小时）
    再扣除请假和放休时间段（时长）
    """
    if not shift_str or "-" not in shift_str:
        return 0.0
    try:
        shift_start_str, shift_end_str = shift_str.split("-")
        shift_start = datetime.strptime(shift_start_str.strip(), "%H:%M")
        shift_end = datetime.strptime(shift_end_str.strip(), "%H:%M")
        shift_hours = (shift_end - shift_start).total_seconds() / 3600.0
    except:
        return 0.0
    # 午餐晚餐扣除：若两项均有，扣1小时；若仅一项，扣0.5小时；否则不扣
    meal_break = 0.0
    if lunch_str.strip() and dinner_str.strip():
        meal_break = 1.0
    elif lunch_str.strip() or dinner_str.strip():
        meal_break = 0.5
    leave_hours = compute_interval_hours(leave_str)
    off_hours = compute_interval_hours(off_str)
    effective = shift_hours - meal_break - leave_hours - off_hours
    return max(effective, 0.0)


def parse_single_time_as_interval(time_str, duration_minutes=30):
    """
    将单点时间（如 "12:00"）转换为一个 duration_minutes 长度的时间段，
    返回类似 "12:00-12:30" 的字符串；若 time_str 无效或为空，则返回 ""
    """
    time_str = time_str.strip()
    if not time_str:
        return ""
    time_str = normalize_time_format(time_str)
    try:
        start_dt = datetime.strptime(time_str, "%H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        return f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
    except:
        return ""


