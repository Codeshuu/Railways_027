import pandas as pd
from scoring import priority_score


def _parse_time_to_minutes(t_str: str) -> int:
    """Helper to convert HH:MM string to integer minutes from midnight."""
    try:
        parts = t_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


def _parse_slot_range(slot_str: str):
    """Helper to parse 'HH:MM-HH:MM' slot string into (slot_start, slot_end, start_min, end_min)."""
    try:
        if "-" in slot_str:
            s_start, s_end = slot_str.split("-")
        else:
            s_start, s_end = slot_str, slot_str
        s_start, s_end = s_start.strip(), s_end.strip()
        start_min = _parse_time_to_minutes(s_start)
        end_min = _parse_time_to_minutes(s_end)
        if end_min <= start_min and end_min != 0:
            end_min += 24 * 60
        return s_start, s_end, start_min, end_min
    except Exception:
        return "00:00", "04:00", 0, 240


def _is_same_or_adjacent_slot(slot1, slot2) -> bool:
    """Check if two parsed slots on the same corridor & date are same or adjacent."""
    start1, end1 = slot1["start_min"], slot1["end_min"]
    start2, end2 = slot2["start_min"], slot2["end_min"]

    # Same slot or overlapping
    if (start1 == start2 and end1 == end2) or (max(start1, start2) < min(end1, end2)):
        return True

    # Adjacent slots (touching boundaries or within 60 minutes)
    if abs(end1 - start2) <= 60 or abs(end2 - start1) <= 60:
        return True

    return False


def generate_schedule(defects_df: pd.DataFrame, corridors_df: pd.DataFrame, timetable_df: pd.DataFrame, whatif_params: dict = None) -> pd.DataFrame:
    """
    Greedy priority-ordered scheduler for Indian Railways Automatic Block Planning.
    1. Computes priority_score for each defect (joining corridor info from corridors_df).
    2. Sorts defects descending by priority_score.
    3. Assigns defects to low-traffic slots (bottom 40% traffic per corridor in timetable_df).
    4. Bundles/merges defects on the same corridor in same or adjacent time windows.
    5. Defers tasks past 7-day horizon if no low-traffic slot is available this week.
    """
    columns = [
        "task_id", "corridor_id", "date", "slot_start", "slot_end",
        "priority_score", "merged_with", "explanation_text"
    ]

    if defects_df is None or defects_df.empty:
        return pd.DataFrame(columns=columns)

    # 1. Build corridor lookup map
    corridor_map = {}
    if corridors_df is not None and not corridors_df.empty:
        for _, c_row in corridors_df.iterrows():
            corridor_map[str(c_row["corridor_id"])] = c_row.to_dict()

    # Apply whatif_params overrides if provided
    defects = defects_df.to_dict(orient="records")
    if whatif_params and "override_defect" in whatif_params:
        override = whatif_params["override_defect"]
        override_id = override.get("task_id")
        for d in defects:
            if d.get("task_id") == override_id:
                d.update(override)

    # Calculate priority score for each defect
    for d in defects:
        c_id = str(d.get("corridor_id", ""))
        c_info = corridor_map.get(c_id)
        d["calculated_priority"] = priority_score(d, c_info)

    # 2. Sort defects descending by priority_score
    defects.sort(key=lambda d: (-d["calculated_priority"], d.get("due_date", ""), int(d.get("task_id", 0))))

    # 3. Identify low-traffic timetable slots per corridor (bottom 40% total_traffic)
    low_traffic_slots = {}
    if timetable_df is not None and not timetable_df.empty:
        tt_df = timetable_df.copy()
        tt_df["total_traffic"] = tt_df["train_count"] + tt_df["goods_forecast_count"]

        for c_id, group in tt_df.groupby("corridor_id"):
            c_id_str = str(c_id)
            threshold = group["total_traffic"].quantile(0.40)
            eligible = group[group["total_traffic"] <= threshold].copy()
            if eligible.empty:
                min_traffic = group["total_traffic"].min()
                eligible = group[group["total_traffic"] == min_traffic].copy()

            parsed_slots = []
            for _, s_row in eligible.iterrows():
                slot_str = str(s_row["time_slot"])
                s_start, s_end, start_min, end_min = _parse_slot_range(slot_str)
                parsed_slots.append({
                    "corridor_id": c_id_str,
                    "date": str(s_row["date"]),
                    "time_slot": slot_str,
                    "slot_start": s_start,
                    "slot_end": s_end,
                    "start_min": start_min,
                    "end_min": end_min,
                    "total_traffic": int(s_row["total_traffic"])
                })
            parsed_slots.sort(key=lambda x: (x["date"], x["start_min"]))
            low_traffic_slots[c_id_str] = parsed_slots

    # 4. Schedule defects in greedy priority order
    scheduled_results = []
    corridor_schedule_map = {}

    for d in defects:
        task_id = int(d.get("task_id", 0))
        c_id = str(d.get("corridor_id", ""))
        severity = int(d.get("severity", 3))
        p_score = float(d["calculated_priority"])

        c_slots = low_traffic_slots.get(c_id, [])
        assigned = False

        if c_id not in corridor_schedule_map:
            corridor_schedule_map[c_id] = []

        # Try to find a slot or bundle with an existing task on the same corridor
        for s_item in c_slots:
            date_str = s_item["date"]
            s_start = s_item["slot_start"]
            s_end = s_item["slot_end"]

            # Check for existing task on same corridor in same or adjacent slot on same date
            existing_matches = [
                prev for prev in corridor_schedule_map[c_id]
                if prev["date"] == date_str and _is_same_or_adjacent_slot(s_item, prev["slot_info"])
            ]

            if existing_matches:
                target_match = existing_matches[0]
                other_task_id = target_match["task_id"]
                merged_with_str = f"TASK-{other_task_id}"

                explanation = (
                    f"Scheduled maintenance for severity {severity} defect in window {s_start}-{s_end}. "
                    f"Multi-department bundled block with {merged_with_str}."
                )

                result_entry = {
                    "task_id": task_id,
                    "corridor_id": c_id,
                    "date": date_str,
                    "slot_start": s_start,
                    "slot_end": s_end,
                    "priority_score": p_score,
                    "merged_with": merged_with_str,
                    "explanation_text": explanation,
                    "slot_info": s_item
                }

                if not target_match.get("merged_with"):
                    target_match["merged_with"] = f"TASK-{task_id}"
                    target_match["explanation_text"] += f" Multi-department bundled block with TASK-{task_id}."

                corridor_schedule_map[c_id].append(result_entry)
                scheduled_results.append(result_entry)
                assigned = True
                break
            else:
                slot_occupied = any(
                    prev for prev in corridor_schedule_map[c_id]
                    if prev["date"] == date_str and prev["slot_info"]["time_slot"] == s_item["time_slot"]
                )
                if not slot_occupied:
                    explanation = f"Scheduled maintenance for severity {severity} defect in window {s_start}-{s_end} on low-traffic slot."
                    result_entry = {
                        "task_id": task_id,
                        "corridor_id": c_id,
                        "date": date_str,
                        "slot_start": s_start,
                        "slot_end": s_end,
                        "priority_score": p_score,
                        "merged_with": None,
                        "explanation_text": explanation,
                        "slot_info": s_item
                    }
                    corridor_schedule_map[c_id].append(result_entry)
                    scheduled_results.append(result_entry)
                    assigned = True
                    break

        # 5. Fallback past 7-day horizon if no low-traffic slot is available
        if not assigned:
            past_horizon_date = "2026-09-14"
            default_slot_start = "00:00"
            default_slot_end = "04:00"
            explanation = "No low-traffic slot available this week."

            result_entry = {
                "task_id": task_id,
                "corridor_id": c_id,
                "date": past_horizon_date,
                "slot_start": default_slot_start,
                "slot_end": default_slot_end,
                "priority_score": p_score,
                "merged_with": None,
                "explanation_text": explanation,
                "slot_info": {
                    "start_min": 0,
                    "end_min": 240,
                    "time_slot": "00:00-04:00"
                }
            }
            corridor_schedule_map[c_id].append(result_entry)
            scheduled_results.append(result_entry)

    res_df = pd.DataFrame(scheduled_results)
    if res_df.empty:
        return pd.DataFrame(columns=columns)

    return res_df[columns]
