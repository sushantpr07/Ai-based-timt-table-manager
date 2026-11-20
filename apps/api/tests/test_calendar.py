from app.calendar import calendar_break_slots


def test_recurring_breaks_map_to_overlapping_periods_using_selected_weekdays():
    blocked = calendar_break_slots(
        [0, 2], ["09:00", "10:00", "11:00"], 60,
        [
            {"weekday": 0, "start_time": "09:30", "end_time": "10:15"},
            {"weekday": 2, "start_time": "11:00", "end_time": "12:00"},
        ],
    )
    assert blocked == {(0, 0), (0, 1), (1, 2)}
