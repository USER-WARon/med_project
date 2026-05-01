import pandas as pd
import numpy as np
import joblib

# 👇 UNLOCK EXPERIMENTAL FEATURES (Required for older sklearn versions)
from sklearn.experimental import enable_hist_gradient_boosting  
from sklearn.ensemble import HistGradientBoostingRegressor

# Set seed for reproducible results
np.random.seed(42)
n_samples = 6000

print("Generating synthetic patient data...")

# 1. GENERATE SICK PATIENTS (Standard Spaces used here)
data = {
    'hemoglobin': np.random.uniform(5, 20, n_samples),
    'wbc': np.random.uniform(2, 25, n_samples),
    'platelets': np.random.uniform(20, 900, n_samples),
    'creatinine': np.random.uniform(0.3, 5.0, n_samples),
    'bloodSugar': np.random.uniform(50, 400, n_samples),
    'urea': np.random.uniform(10, 120, n_samples),
    'sodium': np.random.uniform(120, 160, n_samples),
    'potassium': np.random.uniform(2.0, 7.0, n_samples),
    'chloride': np.random.uniform(90, 120, n_samples),
    'calcium': np.random.uniform(7.0, 12.0, n_samples),
    'albumin': np.random.uniform(2.0, 5.5, n_samples),
    'bilirubin': np.random.uniform(0.1, 3.0, n_samples)
}
df = pd.DataFrame(data)

# 2. INJECT HEALTHY PATIENTS
healthy_data = {
    'hemoglobin': np.random.uniform(13, 16, 1000),
    'wbc': np.random.uniform(5, 10, 1000),
    'platelets': np.random.uniform(200, 400, 1000),
    'creatinine': np.random.uniform(0.7, 1.1, 1000),
    'bloodSugar': np.random.uniform(80, 120, 1000),
    'urea': np.random.uniform(20, 40, 1000),
    'sodium': np.random.uniform(136, 144, 1000),
    'potassium': np.random.uniform(3.8, 5.0, 1000),
    'chloride': np.random.uniform(98, 104, 1000),
    'calcium': np.random.uniform(9.0, 10.0, 1000),
    'albumin': np.random.uniform(4.0, 4.8, 1000),
    'bilirubin': np.random.uniform(0.4, 1.0, 1000)
}
healthy_df = pd.DataFrame(healthy_data)
df = pd.concat([df, healthy_df], ignore_index=True)

# 3. TEACH IT TO HANDLE MISSING DATA
cmp_cols = ['creatinine', 'bloodSugar', 'urea', 'sodium', 'potassium', 'chloride', 'calcium', 'albumin', 'bilirubin']
cbc_only_indices = df.sample(frac=0.30).index 
df.loc[cbc_only_indices, cmp_cols] = np.nan

cbc_cols = ['hemoglobin', 'wbc', 'platelets']
cmp_only_indices = df.loc[~df.index.isin(cbc_only_indices)].sample(frac=0.15).index
df.loc[cmp_only_indices, cbc_cols] = np.nan

for col in df.columns:
    random_missing = df.sample(frac=0.05).index
    df.loc[random_missing, col] = np.nan

# 4. SCORING LOGIC
def score_range(value, low, high, crit_low=None, crit_high=None, weight=1.0):
    if pd.isna(value): return 0 # Zero penalty for missing data
    penalty = 0
    if crit_low is not None and value < crit_low: return 30 * weight
    if crit_high is not None and value > crit_high: return 30 * weight
    if value < low: penalty = (low - value) * 2
    elif value > high: penalty = (value - high) * 2
    return penalty * weight

def calculate_synthetic_risk(row):
    score = 0
    score += score_range(row['hemoglobin'], 12, 17, crit_low=7, weight=2)
    score += score_range(row['wbc'], 4, 11, crit_high=15, weight=1.5)
    score += score_range(row['platelets'], 150, 450, crit_low=50, weight=1.2)
    score += score_range(row['creatinine'], 0.6, 1.3, crit_high=2, weight=3)
    score += score_range(row['bloodSugar'], 70, 140, crit_high=250, weight=1.5)
    score += score_range(row['urea'], 15, 50, weight=1)
    score += score_range(row['sodium'], 135, 145, weight=1.2)
    score += score_range(row['potassium'], 3.5, 5.5, crit_high=6, weight=2)
    score += score_range(row['chloride'], 96, 106, weight=1)
    score += score_range(row['calcium'], 8.5, 10.5, weight=1.5)
    score += score_range(row['albumin'], 3.5, 5.0, weight=2)
    score += score_range(row['bilirubin'], 0.3, 1.2, weight=2)
    return min(100, max(0, score))

print("Applying clinical weighting system...")
df['target_risk_score'] = df.apply(calculate_synthetic_risk, axis=1)

X = df.drop('target_risk_score', axis=1)
y = df['target_risk_score']

# 5. TRAIN NEW MODEL
print("Training NaN-aware HistGradientBoosting model... (This may take a few seconds)")
model = HistGradientBoostingRegressor(max_iter=150, max_depth=12, random_state=42)
model.fit(X, y)

joblib.dump(model, 'risk_engine_model.joblib')
print("✅ HistGradient model trained and saved successfully as 'risk_engine_model.joblib'!")