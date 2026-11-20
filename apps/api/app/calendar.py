from datetime import time


def build_period_labels(start_time: str, period_minutes: int, count: int) -> list[str]:
    start = time.fromisoformat(start_time)
    first_minute = start.hour * 60 + start.minute
    if period_minutes < 1 or count < 1 or count > 14:
        raise ValueError("Period duration and count are outside the supported range.")
    final_end = first_minute + count * period_minutes
    if final_end > 24 * 60:
        raise ValueError("The selected number of periods would extend past midnight.")
    return [f"{(first_minute + index * period_minutes) // 60:02d}:{(first_minute + index * period_minutes) % 60:02d}"
            for index in range(count)]


def maximum_period_count(start_time: str, period_minutes: int, maximum: int = 14) -> int:
    start = time.fromisoformat(start_time)
    available_minutes = 24 * 60 - (start.hour * 60 + start.minute)
    return min(maximum, available_minutes // period_minutes)


def calendar_break_slots(weekdays: list[int], period_labels: list[str], period_minutes: int,
                        breaks: list[dict]) -> set[tuple[int, int]]:
    blocked = set()
    for schedule_day, weekday in enumerate(weekdays):
        for item in breaks or []:
            if item.get("weekday") != weekday:
                continue
            start = time.fromisoformat(item["start_time"])
            end = time.fromisoformat(item["end_time"])
            break_start = start.hour * 60 + start.minute
            break_end = end.hour * 60 + end.minute
            for period, label in enumerate(period_labels):
                slot = time.fromisoformat(label)
                slot_start = slot.hour * 60 + slot.minute
                if slot_start < break_end and break_start < slot_start + period_minutes:
                    blocked.add((schedule_day, period))
    return blocked
