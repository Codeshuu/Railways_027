import numpy as np
import pandas as pd

def generate_training_data(n_samples=500, output_file="training_data.csv", seed=42):
    """
    Generates synthetic training dataset for ML priority scoring model.
    """
    np.random.seed(seed)

    severity = np.random.randint(1, 6, size=n_samples)
    is_high_density = np.random.randint(0, 2, size=n_samples)
    days_overdue = np.random.randint(0, 31, size=n_samples)
    recurrence_count = np.random.randint(0, 6, size=n_samples)
    estimated_block_duration = np.random.uniform(1.0, 6.0, size=n_samples)

    # Calculate ground-truth component scores
    criticality_score = severity * 2.0
    urgency_score = np.minimum(10.0, days_overdue * 0.4 + recurrence_count * 1.2)
    impact_score = is_high_density * 6.0 + np.minimum(4.0, estimated_block_duration * 0.6)

    # Weighted ground-truth priority score
    base_score = 0.4 * criticality_score + 0.35 * urgency_score + 0.25 * impact_score

    # Add Gaussian noise (mean 0, std 0.3) and clip to [0, 10]
    noise = np.random.normal(loc=0.0, scale=0.3, size=n_samples)
    priority_score = np.clip(base_score + noise, 0.0, 10.0)

    df = pd.DataFrame({
        "severity": severity,
        "is_high_density": is_high_density,
        "days_overdue": days_overdue,
        "recurrence_count": recurrence_count,
        "estimated_block_duration": np.round(estimated_block_duration, 2),
        "priority_score": np.round(priority_score, 4)
    })

    df.to_csv(output_file, index=False)
    print(f"Successfully generated {len(df)} synthetic rows in {output_file}.")
    print("\nDataset Summary:")
    print(df.describe())
    return df

if __name__ == "__main__":
    generate_training_data()
