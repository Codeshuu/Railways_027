import sys
import pandas as pd
import numpy as np
import joblib

# Import train_model to register class definitions and split utilities
import train_model
from train_model import train_test_split, r2_score, mean_absolute_error

# Register classes in __main__ module to support unpickling regardless of export context
sys.modules['__main__'].RandomForestRegressor = train_model.RandomForestRegressor
if hasattr(train_model, 'DecisionTreeRegressorFallback'):
    sys.modules['__main__'].DecisionTreeRegressorFallback = train_model.DecisionTreeRegressorFallback


def test_model():
    print("=== 1. Loading priority_model.pkl & Verifying Metrics ===")
    model = joblib.load("priority_model.pkl")

    # 1. Reload training_data.csv, redo 80/20 train/test split with random_state=42
    df = pd.read_csv("training_data.csv")
    feature_cols = [
        "severity",
        "is_high_density",
        "days_overdue",
        "recurrence_count",
        "estimated_block_duration"
    ]
    target_col = "priority_score"

    X = df[feature_cols]
    y = df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    y_test_pred = model.predict(X_test)
    test_r2 = r2_score(y_test, y_test_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)

    print(f"  Reloaded Test R²  : {test_r2:.4f}")
    print(f"  Reloaded Test MAE : {test_mae:.4f}")

    metrics_ok = test_r2 > 0.8 and test_mae < 1.0

    # 2. Run 4 hand-built edge cases and print predicted scores
    print("\n=== 2. Running 4 Hand-Built Edge Cases ===")
    edge_cases = [
        {
            "name": "Case 1 (High Priority)",
            "data": {"severity": 5, "is_high_density": 1, "days_overdue": 25, "recurrence_count": 4, "estimated_block_duration": 5.0},
            "expectation": "High"
        },
        {
            "name": "Case 2 (Low Priority)",
            "data": {"severity": 1, "is_high_density": 0, "days_overdue": 0, "recurrence_count": 0, "estimated_block_duration": 1.0},
            "expectation": "Low"
        },
        {
            "name": "Case 3 (Mid Priority)",
            "data": {"severity": 3, "is_high_density": 1, "days_overdue": 10, "recurrence_count": 2, "estimated_block_duration": 3.0},
            "expectation": "Mid"
        },
        {
            "name": "Case 4 (Moderate-High Priority)",
            "data": {"severity": 5, "is_high_density": 0, "days_overdue": 0, "recurrence_count": 0, "estimated_block_duration": 1.0},
            "expectation": "Moderate-High"
        }
    ]

    edge_case_preds = []
    all_in_bounds = True

    for ec in edge_cases:
        case_df = pd.DataFrame([ec["data"]])[feature_cols]
        pred_val = float(model.predict(case_df)[0])
        edge_case_preds.append(pred_val)

        # 3. Assert prediction is within [0, 10]
        in_bounds = 0.0 <= pred_val <= 10.0
        assert in_bounds, f"Prediction {pred_val} for {ec['name']} is out of bounds [0, 10]"
        if not in_bounds:
            all_in_bounds = False

        print(f"  {ec['name']:32s} -> Predicted Score: {pred_val:.4f} (Expected: {ec['expectation']}, In Bounds [0, 10]: {in_bounds})")

    # 4. Print PASS/FAIL Summary
    all_passed = metrics_ok and all_in_bounds

    print("\n========================================")
    if all_passed:
        print("TEST SUMMARY: PASS")
        print("  - Test metrics match training expectations.")
        print("  - All 4 edge case predictions successfully computed.")
        print("  - All predictions satisfied [0, 10] bound assertions.")
    else:
        print("TEST SUMMARY: FAIL")
    print("========================================")

if __name__ == "__main__":
    test_model()
