import os
import datetime
import pandas as pd
import numpy as np
import joblib

# Import train_model module to support custom fallback classes unpickling if needed
try:
    import sys
    import train_model
    sys.modules['__main__'].RandomForestRegressor = train_model.RandomForestRegressor
    if hasattr(train_model, 'DecisionTreeRegressorFallback'):
        sys.modules['__main__'].DecisionTreeRegressorFallback = train_model.DecisionTreeRegressorFallback
except Exception:
    pass

MODEL_FILE = "priority_model.pkl"
MODEL = None

try:
    if os.path.exists(MODEL_FILE):
        MODEL = joblib.load(MODEL_FILE)
except Exception:
    MODEL = None


def _get_val(obj, key, default=None):
    """Safely extract key from dict, sqlite3.Row, pandas.Series, or object attributes."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        val = obj.get(key, default)
        return val if val is not None else default
    try:
        if hasattr(obj, "keys") and callable(obj.keys) and key in obj.keys():
            val = obj[key]
            return val if val is not None else default
    except Exception:
        pass
    try:
        if hasattr(obj, key):
            val = getattr(obj, key)
            return val if val is not None else default
    except Exception:
        pass
    try:
        val = obj[key]
        return val if val is not None else default
    except Exception:
        pass
    return default


def _calculate_days_overdue(due_date_val, ref_date=None):
    """Compute days overdue relative to ref_date (default today/2026-09-07). Returns 0 if not overdue."""
    if not due_date_val:
        return 0
    if ref_date is None:
        try:
            ref_date = datetime.date.today()
        except Exception:
            ref_date = datetime.date(2026, 9, 7)

    try:
        if isinstance(due_date_val, (datetime.date, datetime.datetime)):
            due_date = due_date_val.date() if isinstance(due_date_val, datetime.datetime) else due_date_val
        else:
            due_date = datetime.datetime.strptime(str(due_date_val)[:10], "%Y-%m-%d").date()

        diff = (ref_date - due_date).days
        return max(0, diff)
    except Exception:
        return 0


def _rule_based_priority(severity, is_high_density, days_overdue, recurrence_count, estimated_block_duration):
    """Ground-truth rule-based priority score calculation fallback."""
    criticality_score = severity * 2.0
    urgency_score = min(10.0, days_overdue * 0.4 + recurrence_count * 1.2)
    impact_score = is_high_density * 6.0 + min(4.0, estimated_block_duration * 0.6)
    base_score = 0.4 * criticality_score + 0.35 * urgency_score + 0.25 * impact_score
    return round(max(0.0, min(10.0, base_score)), 2)


def priority_score(defect_row, corridor_row=None) -> float:
    """
    Calculates maintenance priority score (0.0 to 10.0).
    Uses ML model loaded from priority_model.pkl with rule-based fallback.
    """
    try:
        severity = float(_get_val(defect_row, "severity", 3))
        is_high_density = int(_get_val(corridor_row, "is_high_density", 0))
        due_date = _get_val(defect_row, "due_date")
        days_overdue = _calculate_days_overdue(due_date)
        recurrence_count = int(_get_val(defect_row, "recurrence_count", 0))
        estimated_block_duration = float(_get_val(defect_row, "estimated_block_duration", 2.0))

        if MODEL is not None:
            features_df = pd.DataFrame([{
                "severity": severity,
                "is_high_density": is_high_density,
                "days_overdue": days_overdue,
                "recurrence_count": recurrence_count,
                "estimated_block_duration": estimated_block_duration
            }])
            pred = MODEL.predict(features_df)
            score = float(pred[0])
            score = max(0.0, min(10.0, score))
            return round(score, 2)
    except Exception:
        pass

    # Fallback to rule-based calculation if ML prediction is unavailable or fails
    try:
        sev = float(_get_val(defect_row, "severity", 3))
        hd = int(_get_val(corridor_row, "is_high_density", 0))
        d_overdue = _calculate_days_overdue(_get_val(defect_row, "due_date"))
        rec = int(_get_val(defect_row, "recurrence_count", 0))
        dur = float(_get_val(defect_row, "estimated_block_duration", 2.0))
        return _rule_based_priority(sev, hd, d_overdue, rec, dur)
    except Exception:
        return 5.0


def health_score(defect_row) -> float:
    """
    Calculates asset health score (0.0 to 100.0).
    Formula: 100 - (severity*15 + min(days_overdue, 20)*1.5), clipped to [0, 100].
    """
    try:
        severity = float(_get_val(defect_row, "severity", 3))
        due_date = _get_val(defect_row, "due_date")
        days_overdue = _calculate_days_overdue(due_date)

        raw_health = 100.0 - (severity * 15.0 + min(days_overdue, 20) * 1.5)
        return round(max(0.0, min(100.0, raw_health)), 1)
    except Exception:
        return 50.0
