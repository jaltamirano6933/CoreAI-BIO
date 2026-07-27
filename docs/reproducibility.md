# CoreAI BIO — Scientific Reproducibility Checklist & Environment Specification

**System Version:** CoreAI BIO v1.0.0  
**Document Type:** Reproducibility Standard Specification  
**Date:** July 2026  

---

## 1. Environment & Software Specifications

- **Operating System:** Windows 10/11 x64
- **Python Version:** `Python 3.13.0` (compatible with `3.10+`)
- **Shell / Terminal:** PowerShell 7.x / Command Prompt

### 1.1 Core Python Package Dependencies (`requirements.txt`)

```text
flask>=3.0.0
jinja2>=3.1.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
joblib>=1.3.0
shap>=0.44.0
openpyxl>=3.1.0
matplotlib>=3.7.0
```

---

## 2. Random Seeds & Determinism Controls

To ensure 100% bit-for-bit reproducible results across model training, dataset splitting, and cross-validation:

| Pipeline Component | Parameter Name | Fixed Seed Value | Scope |
| :--- | :--- | :---: | :--- |
| **Train/Test Holdout Split** | `random_state` | `42` | `sklearn.model_selection.train_test_split(test_size=0.2, random_state=42)` |
| **Repeated K-Fold CV** | `random_state` | `42` | `RepeatedKFold(n_splits=5, n_repeats=5, random_state=42)` |
| **Randomized Search CV** | `random_state` | `42` | `RandomizedSearchCV(n_iter=15, cv=5, random_state=42)` |
| **RandomForestRegressor** | `random_state` | `42` | `RandomForestRegressor(n_estimators=100, random_state=42)` |
| **ExtraTreesRegressor** | `random_state` | `42` | `ExtraTreesRegressor(n_estimators=100, random_state=42)` |
| **XGBRegressor** | `random_state` | `42` | `XGBRegressor(n_estimators=100, random_state=42)` |

---

## 3. Dataset Specifications

- **File Path:** `dataset/culture_optimizer/Data.xlsx`
- **Sheet Name:** `time-saving`
- **Row Count:** $403$ samples
- **Feature Column Count:** $29$ numeric culture medium components
- **Target Column:** `mean_A450_168h` (cell absorbance at 168 hours post-inoculation)
- **Excluded Columns:** `Unnamed: 0`, `mean_A450_96h`, `sd_A450_96h`, `sd_A450_168h`

---

## 4. Model Versioning & Artifact Paths

| Model Role | File Path | Version Tag | Model Class |
| :--- | :--- | :---: | :--- |
| **Deployed Baseline Model** | `models/culture_optimizer_model.joblib` | `v1.0.0` | `sklearn.ensemble.RandomForestRegressor` |
| **Feature List** | `models/culture_optimizer_features.json` | `v1.0.0` | $29$ Feature Strings |
| **Baseline Metrics** | `models/culture_optimizer_metrics.json` | `v1.0.0` | JSON Metrics File |
| **Top Experimental Model** | `models/experiments/culture_optimizer/best_experimental_model.joblib` | `v1.0.0` | `sklearn.ensemble.ExtraTreesRegressor` |
| **Experimental Metrics** | `models/experiments/culture_optimizer/experimental_metrics.json` | `v1.0.0` | JSON Metrics File |

---

## 5. Step-by-Step Training & Reproducibility Procedure

### Step 1: Install Dependencies
```bash
py -m pip install -r requirements.txt
```

### Step 2: Reproduce Baseline Model Training
```bash
py backend/training/train_culture_optimizer.py
```
*Expected Output:*
- Serializes `models/culture_optimizer_model.joblib`
- Generates `models/culture_optimizer_metrics.json` ($R^2 = 0.3171$)
- Saves plots in `static/results/culture_optimizer/`

### Step 3: Reproduce Experimental Hyperparameter & CV Pipeline
```bash
py backend/training/improve_culture_optimizer.py
```
*Expected Output:*
- Executes 25-fold Repeated CV
- Serializes `models/experiments/culture_optimizer/best_experimental_model.joblib` ($R^2 = 0.3541$)
- Generates `docs/culture_optimizer_improvement_report.md`

### Step 4: Reproduce SHAP Visualizations
```bash
py backend/training/generate_shap_plots.py
```
*Expected Output:*
- Saves `shap_summary.png` and `shap_waterfall.png`

### Step 5: Execute Automated Test Suite
```bash
py -m unittest discover tests
```
*Expected Output:* `Ran 30 tests in ~0.5s OK`
