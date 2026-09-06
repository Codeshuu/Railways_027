import pandas as pd
import random

def generate_schedule(defects_df: pd.DataFrame, corridors_df: pd.DataFrame, timetable_df: pd.DataFrame) -> pd.DataFrame:
    """
    STUB implementation for CSE-2 integration.
    Returns a dummy pandas DataFrame matching schedule_results columns:
    (task_id, corridor_id, date, slot_start, slot_end, priority_score, merged_with, explanation_text)
    
    CSE-2 will replace this function with the greedy priority scheduling algorithm and corridor merge rules.
    """
    columns = [
        "task_id", "corridor_id", "date", "slot_start", "slot_end", 
        "priority_score", "merged_with", "explanation_text"
    ]
    
    if defects_df is None or defects_df.empty:
        return pd.DataFrame(columns=columns)

    results = []
    sample_dates = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13"]
    sample_slots = [("01:00", "04:00"), ("04:00", "07:00"), ("11:00", "13:00"), ("14:00", "17:00"), ("22:00", "01:00")]

    for idx, row in defects_df.iterrows():
        task_id = int(row["task_id"]) if "task_id" in row and pd.notna(row["task_id"]) else (idx + 1)
        corridor_id = str(row["corridor_id"]) if "corridor_id" in row and pd.notna(row["corridor_id"]) else "CORR-01"
        severity = int(row["severity"]) if "severity" in row and pd.notna(row["severity"]) else 3
        
        # Pick date and slot based on index for deterministic test reproducibility
        date = sample_dates[idx % len(sample_dates)]
        slot = sample_slots[idx % len(sample_slots)]
        score = round(min(10.0, 3.5 + severity * 1.2), 2)
        
        merged_with = None
        if idx % 3 == 0 and len(defects_df) > 1:
            other_task = int(defects_df.iloc[(idx + 1) % len(defects_df)]["task_id"])
            merged_with = f"TASK-{other_task}"

        explanation = f"Scheduled maintenance for severity {severity} defect in window {slot[0]}-{slot[1]}."
        if merged_with:
            explanation += f" Multi-department bundled block with {merged_with}."

        results.append({
            "task_id": task_id,
            "corridor_id": corridor_id,
            "date": date,
            "slot_start": slot[0],
            "slot_end": slot[1],
            "priority_score": score,
            "merged_with": merged_with,
            "explanation_text": explanation
        })

    return pd.DataFrame(results, columns=columns)
