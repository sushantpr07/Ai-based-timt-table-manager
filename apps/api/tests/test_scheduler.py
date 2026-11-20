import pytest

from app.scheduler import ScheduleInfeasible, generate_schedule


def base_payload():
    return {
        "days": 2,
        "periods_per_day": 2,
        "sessions": [
            {"subject": "Algorithms", "faculty": "f1", "section": "s1", "students": 24},
            {"subject": "Databases", "faculty": "f1", "section": "s2", "students": 24},
        ],
        "rooms": [
            {"id": "r1", "name": "Room 1", "capacity": 30, "room_type": "classroom"},
        ],
    }


def test_assigns_all_sessions_without_resource_overlap():
    result = generate_schedule(base_payload())
    assert len(result) == 2
    assert len({(entry["day"], entry["period"], entry["faculty"]) for entry in result}) == 2


def test_reports_when_room_capacity_is_insufficient():
    payload = base_payload()
    payload["sessions"][0]["students"] = 80
    with pytest.raises(ScheduleInfeasible, match="No suitable room") as exc:
        generate_schedule(payload)
    assert exc.value.diagnostics == [{"category": "room_eligibility", "subject": "Algorithms",
                                      "required_room_type": "classroom", "minimum_capacity": 80}]


def test_reports_when_no_time_is_available():
    payload = base_payload()
    payload["sessions"] = [payload["sessions"][0]]
    payload["sessions"][0]["unavailable"] = [[0, 0], [0, 1], [1, 0], [1, 1]]
    with pytest.raises(ScheduleInfeasible, match="No available periods") as exc:
        generate_schedule(payload)
    assert exc.value.diagnostics[0]["category"] == "time_availability"
    assert exc.value.diagnostics[0]["blocked_slots"] == 4


def test_double_period_sessions_reserve_both_slots():
    payload = base_payload()
    payload["days"] = 1
    payload["periods_per_day"] = 2
    payload["sessions"] = [
        {"subject": "Physics Lab", "faculty": "f1", "section": "s1", "students": 24, "duration_periods": 2},
        {"subject": "Chemistry Lab", "faculty": "f2", "section": "s2", "students": 24, "duration_periods": 2},
    ]
    with pytest.raises(ScheduleInfeasible) as exc:
        generate_schedule(payload)
    assert exc.value.diagnostics[0]["category"] == "combined_constraints"
    assert "room_overlap" in exc.value.diagnostics[0]["suspected_constraints"]


def test_faculty_weekly_workload_limit_is_hard():
    payload = base_payload()
    payload["sessions"] = [
        {"subject": "Algorithms", "faculty": "f1", "section": "s1", "students": 24, "faculty_max_weekly_periods": 1},
        {"subject": "Databases", "faculty": "f1", "section": "s2", "students": 24, "faculty_max_weekly_periods": 1},
    ]
    with pytest.raises(ScheduleInfeasible):
        generate_schedule(payload)


def test_repeated_subject_sessions_are_spread_across_available_days():
    payload = base_payload()
    payload["days"] = 3
    payload["periods_per_day"] = 3
    payload["sessions"] = [
        {"subject": "Statistics", "faculty": "f1", "section": "s1", "students": 24, "course_key": "stats:s1"},
        {"subject": "Statistics", "faculty": "f1", "section": "s1", "students": 24, "course_key": "stats:s1"},
        {"subject": "Statistics", "faculty": "f1", "section": "s1", "students": 24, "course_key": "stats:s1"},
    ]
    result = generate_schedule(payload)
    assert len({entry["day"] for entry in result}) == 3


def test_repair_preferences_keep_unaffected_sessions_in_place():
    payload = base_payload()
    payload["days"] = 1
    payload["periods_per_day"] = 2
    payload["sessions"] = [
        {"subject": "Algorithms", "faculty": "f1", "section": "s1", "students": 24,
         "course_key": "a:s1", "preferred_location": {"day": 0, "period": 0, "room_id": "r1"}},
        {"subject": "Databases", "faculty": "f1", "section": "s2", "students": 24,
         "course_key": "b:s2", "preferred_location": {"day": 0, "period": 0, "room_id": "r1"}},
    ]
    result = generate_schedule(payload)
    unchanged = sum((entry["day"], entry["period"], entry["room_id"]) == (0, 0, "r1") for entry in result)
    assert unchanged == 1


def test_locked_session_is_not_moved_by_the_optimizer():
    payload = base_payload()
    payload["sessions"] = [
        {"subject": "Algorithms", "faculty": "f1", "section": "s1", "students": 24,
         "preferred_location": {"day": 0, "period": 0, "room_id": "r1"}, "fixed": True},
        {"subject": "Databases", "faculty": "f1", "section": "s2", "students": 24,
         "preferred_location": {"day": 0, "period": 0, "room_id": "r1"}},
    ]
    result = generate_schedule(payload)
    locked = next(entry for entry in result if entry["subject"] == "Algorithms")
    assert (locked["day"], locked["period"], locked["room_id"]) == (0, 0, "r1")


def test_global_calendar_breaks_are_excluded_from_candidate_periods():
    payload = base_payload()
    payload["days"] = 1
    payload["periods_per_day"] = 2
    payload["sessions"] = [payload["sessions"][0]]
    payload["global_blocked_slots"] = [[0, 0]]
    result = generate_schedule(payload)
    assert result[0]["period"] == 1


def test_optimizer_prefers_compact_days_over_earlier_start_with_a_gap():
    payload = {
        "days": 1,
        "periods_per_day": 5,
        "sessions": [
            {"subject": "Algorithms", "faculty": "f1", "section": "s1", "students": 24,
             "unavailable": [[0, 1], [0, 2], [0, 4]]},
            {"subject": "Databases", "faculty": "f1", "section": "s1", "students": 24,
             "unavailable": [[0, 0], [0, 1], [0, 3]]},
        ],
        "rooms": [{"id": "r1", "name": "Room 1", "capacity": 30, "room_type": "classroom"}],
    }

    result = generate_schedule(payload)

    assert {entry["period"] for entry in result} == {2, 3}
