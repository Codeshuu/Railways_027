import random

def priority_score(defect_row, corridor_row=None) -> float:
    """
    STUB implementation for ECE-2 integration.
    Returns a float priority score between 0.0 and 10.0.
    ECE-2 will overwrite this file with the actual weighted formula:
    priority_score = 0.4 * criticality_score + 0.35 * urgency_score + 0.25 * impact_score
    """
    # Deterministic dummy calculation based on task_id if present, else random
    task_id = defect_row.get("task_id", 0) if isinstance(defect_row, dict) else getattr(defect_row, "task_id", 0)
    severity = defect_row.get("severity", 3) if isinstance(defect_row, dict) else getattr(defect_row, "severity", 3)
    
    # Simple pseudo-random score using severity seed for reproducible stub output
    base_score = min(10.0, severity * 1.5 + (task_id % 3) * 0.8)
    return round(base_score, 2)

def health_score(defect_row) -> float:
    """
    STUB implementation for ECE-2 integration.
    Returns a float health score between 0.0 and 100.0.
    ECE-2 will overwrite this file with the actual formula:
    health_score = 100 - (severity*8 + min(days_overdue,20)*1.5 + is_overdue_flag*10)
    """
    severity = defect_row.get("severity", 3) if isinstance(defect_row, dict) else getattr(defect_row, "severity", 3)
    base_health = max(0.0, 100.0 - (severity * 15.0))
    return round(base_health, 1)
