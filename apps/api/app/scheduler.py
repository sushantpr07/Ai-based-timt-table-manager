from collections import Counter, defaultdict

from ortools.sat.python import cp_model


class ScheduleInfeasible(ValueError):
    def __init__(self, message: str, diagnostics: list[dict] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or []


def generate_schedule(payload: dict, *, with_metadata: bool = False):
    """Assign each requested session to a room and period without section, faculty, or room overlap."""
    sessions = payload["sessions"]
    rooms = payload["rooms"]
    days = payload.get("days", 5)
    periods = payload.get("periods_per_day", 8)
    global_blocked = {tuple(slot) for slot in payload.get("global_blocked_slots", [])}
    model = cp_model.CpModel()
    choices = {}
    by_resource_slot = defaultdict(list)
    faculty_loads = defaultdict(list)
    section_day_loads = defaultdict(list)
    course_day_options = defaultdict(list)
    moved_session_preferences = []
    course_counts = Counter(session["course_key"] for session in sessions if session.get("course_key"))
    section_weekly_load = defaultdict(int)
    for session in sessions:
        section_weekly_load[session["section"]] += session.get("duration_periods", 1)

    for si, session in enumerate(sessions):
        unavailable = {tuple(slot) for slot in session.get("unavailable", [])}
        duration = session.get("duration_periods", 1)
        eligible_rooms = [ri for ri, room in enumerate(rooms)
                          if room["capacity"] >= session["students"]
                          and room["room_type"] == session.get("room_type", "classroom")]
        if not eligible_rooms:
            raise ScheduleInfeasible(
                f"No suitable room for {session['subject']} (capacity/type).",
                [{"category": "room_eligibility", "subject": session["subject"],
                  "required_room_type": session.get("room_type", "classroom"),
                  "minimum_capacity": session["students"]}],
            )
        options = []
        blocked_by_institution_break = False
        for day in range(days):
            for period in range(periods - duration + 1):
                if any((day, period + offset) in unavailable for offset in range(duration)):
                    continue
                if any((day, period + offset) in global_blocked for offset in range(duration)):
                    blocked_by_institution_break = True
                    continue
                for ri in eligible_rooms:
                    preferred = session.get("preferred_location")
                    if session.get("fixed") and preferred and (day, period, rooms[ri]["id"]) != (
                            preferred["day"], preferred["period"], preferred["room_id"]):
                        continue
                    variable = model.new_bool_var(f"s{si}_d{day}_p{period}_r{ri}")
                    choices[si, day, period, ri] = variable
                    options.append(variable)
                    for offset in range(duration):
                        for resource in (f"section:{session['section']}", f"faculty:{session['faculty']}", f"room:{rooms[ri]['id']}"):
                            by_resource_slot[resource, day, period + offset].append(variable)
                    faculty_loads[session["faculty"]].append(duration * variable)
                    section_day_loads[session["section"], day].append(duration * variable)
                    course_key = session.get("course_key")
                    if course_key and course_counts[course_key] <= days:
                        course_day_options[course_key, day].append(variable)
                    if preferred and not session.get("fixed") and (day, period, rooms[ri]["id"]) != (
                            preferred["day"], preferred["period"], preferred["room_id"]):
                        moved_session_preferences.append(variable)
        if not options:
            raise ScheduleInfeasible(
                f"No available periods for {session['subject']}.",
                [{"category": "time_availability", "subject": session["subject"],
                  "faculty": session["faculty"], "duration_periods": duration,
                  "days": days, "periods_per_day": periods,
                  "blocked_slots": len(unavailable),
                  "institution_breaks": blocked_by_institution_break}],
            )
        model.add_exactly_one(options)

    for variables in by_resource_slot.values():
        if len(variables) > 1:
            model.add_at_most_one(variables)

    max_loads = {session["faculty"]: session.get("faculty_max_weekly_periods")
                 for session in sessions if session.get("faculty_max_weekly_periods") is not None}
    for faculty, max_periods in max_loads.items():
        model.add(sum(faculty_loads[faculty]) <= max_periods)

    for variables in course_day_options.values():
        model.add_at_most_one(variables)

    # Prefer compact teaching days for both students and faculty. A gap is an
    # empty period with at least one occupied period before and after it.
    gap_terms = []
    teaching_resources = {
        *(f"section:{session['section']}" for session in sessions),
        *(f"faculty:{session['faculty']}" for session in sessions),
    }
    for resource in teaching_resources:
        for day in range(days):
            occupied = []
            for period in range(periods):
                slot_choices = by_resource_slot.get((resource, day, period), [])
                is_occupied = model.new_bool_var(f"occupied_{resource}_{day}_{period}")
                if slot_choices:
                    model.add(sum(slot_choices) == is_occupied)
                else:
                    model.add(is_occupied == 0)
                occupied.append(is_occupied)
            for period in range(1, periods - 1):
                gap = model.new_bool_var(f"gap_{resource}_{day}_{period}")
                before = model.new_bool_var(f"before_{resource}_{day}_{period}")
                after = model.new_bool_var(f"after_{resource}_{day}_{period}")
                model.add_max_equality(before, occupied[:period])
                model.add_max_equality(after, occupied[period + 1:])
                model.add(gap <= before)
                model.add(gap <= after)
                model.add(gap + occupied[period] <= 1)
                model.add(gap >= before + after - occupied[period] - 1)
                gap_terms.append(gap)

    # Balance each section's weekly load across days, then prefer earlier periods as a tie-breaker.
    penalty_terms = []
    for (si, day, period, ri), variable in choices.items():
        penalty_terms.append(period * variable)
    balance_terms = []
    for (section, day), terms in section_day_loads.items():
        max_load = section_weekly_load[section]
        load = model.new_int_var(0, max_load, f"load_{section}_{day}")
        square = model.new_int_var(0, max_load * max_load, f"load_sq_{section}_{day}")
        model.add(load == sum(terms))
        model.add_multiplication_equality(square, [load, load])
        balance_terms.append(square)
    balance_upper_bound = 10 * sum(load * load * days for load in section_weekly_load.values())
    period_upper_bound = len(sessions) * max(0, periods - 1)
    gap_weight = balance_upper_bound + period_upper_bound + 1
    max_gap_count = len(teaching_resources) * days * max(0, periods - 2)
    movement_weight = max_gap_count * gap_weight + balance_upper_bound + period_upper_bound + 1
    model.minimize(movement_weight * sum(moved_session_preferences)
                   + gap_weight * sum(gap_terms)
                   + 10 * sum(balance_terms)
                   + sum(penalty_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 25.0
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if status == cp_model.INFEASIBLE:
            suspected = ["section_overlap", "faculty_overlap", "room_overlap"]
            if any(session.get("unavailable") for session in sessions):
                suspected.append("faculty_availability")
            if global_blocked:
                suspected.append("institution_breaks")
            if any(session.get("faculty_max_weekly_periods") is not None for session in sessions):
                suspected.append("faculty_weekly_limits")
            if course_day_options:
                suspected.append("subject_spread_across_days")
            raise ScheduleInfeasible(
                "No conflict-free timetable fits the supplied constraints.",
                [{"category": "combined_constraints", "suspected_constraints": suspected}],
            )
        raise ScheduleInfeasible(
            "The optimizer reached its search limit before confirming a feasible timetable.",
            [{"category": "solver_limit", "solver_status": solver.status_name(status)}],
        )

    result = []
    for si, session in enumerate(sessions):
        for (idx, day, period, ri), variable in choices.items():
            if idx == si and solver.boolean_value(variable):
                result.append({"session_key": session.get("session_key", str(si)),
                               "subject": session["subject"], "faculty": session["faculty"],
                               "section": session["section"], "room": rooms[ri]["name"],
                               "room_id": rooms[ri]["id"], "day": day, "period": period,
                               "duration_periods": session.get("duration_periods", 1)})
    if with_metadata:
        return {"entries": result, "score": int(solver.objective_value),
                "status": "optimal" if status == cp_model.OPTIMAL else "feasible"}
    return result
