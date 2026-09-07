import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error


def train():
    # 1. Load training data
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

    # 2. Split 80/20 train/test with random_state=42
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 3. Train RandomForestRegressor
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        random_state=42
    )
    model.fit(X_train, y_train)

    # 4. Evaluate metrics
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)

    print("Model Evaluation Metrics:")
    print(f"  Train R² : {train_r2:.4f}")
    print(f"  Test R²  : {test_r2:.4f}")
    print(f"  Train MAE: {train_mae:.4f}")
    print(f"  Test MAE : {test_mae:.4f}")

    # 5. Save model via joblib
    model_filename = "priority_model.pkl"
    joblib.dump(model, model_filename)
    print(f"\nModel saved to {model_filename}")

    # 6. Print Feature Importances (sorted descending)
    print("\nFeature Importances:")
    importances = model.feature_importances_
    for name, importance in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
        print(f"  {name:25s}: {importance:.4f}")


if __name__ == "__main__":
    train()
