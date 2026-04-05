from datetime import time

WEEKDAY_NAMES = ['月', '火', '水', '木', '金', '土', '日']


def get_weekday_name(date):
    return WEEKDAY_NAMES[date.weekday()]


def format_date_jp(date):
    return f'{date.year}年{date.month}月{date.day}日({get_weekday_name(date)})'


def get_available_time_slots(date):
    """利用可能な時間枠を返す（1時間単位）"""
    weekday = date.weekday()
    slots = []

    if weekday < 5:  # 平日（月〜金）
        for hour in range(16, 21):
            slots.append((time(hour, 0), time(hour + 1, 0)))
    else:  # 土日
        for hour in range(8, 12):
            slots.append((time(hour, 0), time(hour + 1, 0)))
        for hour in range(13, 21):
            slots.append((time(hour, 0), time(hour + 1, 0)))

    return slots


def time_slot_label(start, end):
    return f'{start.strftime("%H:%M")}〜{end.strftime("%H:%M")}'
