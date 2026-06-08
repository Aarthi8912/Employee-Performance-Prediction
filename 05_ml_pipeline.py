"""
05_ml_pipeline.py
HR Analytics Platform — Machine Learning Pipeline
Trains and evaluates multiple models to predict Employee Performance.
"""

import os, sys, warnings, joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report, confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

warnings.filterwarnings('ignore')
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'cleaned')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 60)
print("  HR Analytics Platform — Machine Learning Pipeline")
print("=" * 60)

# 1. Load Data
print("\n[1/7] Loading processed features...")
try:
    df = pd.read_csv(os.path.join(DATA_DIR, 'ml_features.csv'))
except FileNotFoundError:
    print("Error: ml_features.csv not found. Run 02_data_cleaning.py first.")
    sys.exit(1)

# Ensure no leakage and drop identifiers
drop_cols = ['EmployeeID', 'EmployeeName', 'PerformanceRating'] # PerformanceRating directly determines label
X_raw = df.drop(columns=[c for c in drop_cols if c in df.columns] + ['PerformanceLabel'])
y_raw = df['PerformanceLabel']

print(f"Features: {X_raw.shape[1]}, Samples: {X_raw.shape[0]}")
print(f"Target distribution:\n{y_raw.value_counts()}")

# 2. Preprocessing
print("\n[2/7] Preprocessing (Encoding & Scaling)...")

# Label encode target
le_target = LabelEncoder()
y = le_target.fit_transform(y_raw)
joblib.dump(le_target, os.path.join(MODELS_DIR, 'label_encoder.pkl'))

# Map categorical features
categorical_cols = X_raw.select_dtypes(include=['object', 'category']).columns.tolist()
numeric_cols = X_raw.select_dtypes(exclude=['object', 'category']).columns.tolist()

X_encoded = pd.get_dummies(X_raw, columns=categorical_cols, drop_first=True)
feature_names = X_encoded.columns.tolist()
joblib.dump(feature_names, os.path.join(MODELS_DIR, 'feature_columns.pkl'))

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.2, random_state=42, stratify=y)

# Impute missing values
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='median')
X_train[numeric_cols] = imputer.fit_transform(X_train[numeric_cols])
X_test[numeric_cols] = imputer.transform(X_test[numeric_cols])
joblib.dump(imputer, os.path.join(MODELS_DIR, 'imputer.pkl'))

# Scale numeric features
scaler = StandardScaler()
X_train[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
X_test[numeric_cols] = scaler.transform(X_test[numeric_cols])
joblib.dump(scaler, os.path.join(MODELS_DIR, 'scaler.pkl'))

# 3. Handle Imbalance (SMOTE)
print("\n[3/7] Applying SMOTE for class imbalance...")
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
print(f"Resampled train shape: {X_train_res.shape}")

# 4. Model Definition & Training
print("\n[4/7] Training Models...")

models = {
    'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
    'Decision Tree': DecisionTreeClassifier(random_state=42),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
    'XGBoost': XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)
}

results = []
best_model = None
best_f1 = 0
best_model_name = ""

for name, model in models.items():
    print(f"  Training {name}...")
    model.fit(X_train_res, y_train_res)
    y_pred = model.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted')
    rec = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # Needs probabilities for ROC-AUC
    try:
        y_prob = model.predict_proba(X_test)
        auc = roc_auc_score(y_test, y_prob, multi_class='ovr')
    except:
        auc = np.nan
        
    results.append({
        'Model': name, 'Accuracy': acc, 'Precision': prec,
        'Recall': rec, 'F1 Score': f1, 'ROC-AUC': auc
    })
    
    if f1 > best_f1:
        best_f1 = f1
        best_model = model
        best_model_name = name

results_df = pd.DataFrame(results).sort_values(by='F1 Score', ascending=False)
print("\nModel Evaluation Results:")
print(results_df.to_string(index=False))

# 5. Save Best Model
print(f"\n[5/7] Saving best model ({best_model_name})...")
joblib.dump(best_model, os.path.join(MODELS_DIR, 'best_model.pkl'))

# 6. Feature Importance (Best Model)
print("\n[6/7] Extracting Feature Importance...")
if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    feat_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
    feat_df = feat_df.sort_values(by='Importance', ascending=False).head(20)
    
    plt.figure(figsize=(10, 8))
    sns.barplot(x='Importance', y='Feature', data=feat_df)
    plt.title(f"Top 20 Features ({best_model_name})")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'feature_importance.png'))
    plt.close()
    print("  Feature importance plot saved to reports/feature_importance.png")
else:
    print("  Best model does not support native feature_importances_.")

# 7. Generate ML Report
print("\n[7/7] Generating ML Report...")
y_pred_best = best_model.predict(X_test)
report = classification_report(y_test, y_pred_best, target_names=le_target.classes_)
cm = confusion_matrix(y_test, y_pred_best)

html_report = f"""
<!DOCTYPE html>
<html>
<head>
<style>
body{{font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f9;}}
.card{{background: #fff; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);}}
table{{border-collapse: collapse; width: 100%;}}
th, td{{padding: 10px; border: 1px solid #ddd; text-align: left;}}
th{{background-color: #007bff; color: white;}}
pre{{background: #f8f9fa; padding: 15px; border-radius: 5px;}}
</style>
</head>
<body>
<h1>Machine Learning Model Report</h1>
<div class='card'>
<h2>Model Comparison</h2>
{results_df.to_html(classes='table', index=False)}
</div>
<div class='card'>
<h2>Best Model: {best_model_name}</h2>
<h3>Classification Report</h3>
<pre>{report}</pre>
<h3>Confusion Matrix</h3>
<pre>{cm}</pre>
</div>
</body>
</html>
"""
with open(os.path.join(REPORTS_DIR, 'model_report.html'), 'w', encoding='utf-8') as f:
    f.write(html_report)

print("  Model report saved to reports/model_report.html")
print("\n✅ ML Pipeline complete!")
