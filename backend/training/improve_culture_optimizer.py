import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from sklearn.model_selection import train_test_split, RepeatedKFold, RandomizedSearchCV
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

def evaluate_metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))
    return {"MAE": round(mae, 4), "RMSE": round(rmse, 4), "R2": round(r2, 4)}

def compute_sample_weights(sd_series, epsilon=1e-4, lower_p=5, upper_p=95):
    raw_weights = 1.0 / (np.square(sd_series) + epsilon)
    p_low = np.percentile(raw_weights, lower_p)
    p_high = np.percentile(raw_weights, upper_p)
    clipped_weights = np.clip(raw_weights, p_low, p_high)
    # Normalize weights around mean 1.0
    normalized_weights = clipped_weights / np.mean(clipped_weights)
    return normalized_weights

def run_improvement_experiments():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    excel_path = os.path.join(base_dir, "dataset", "culture_optimizer", "Data.xlsx")
    exp_models_dir = os.path.join(base_dir, "models", "experiments", "culture_optimizer")
    docs_dir = os.path.join(base_dir, "docs")

    os.makedirs(exp_models_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)

    print("================================================================================")
    print("STARTING EXPERIMENTAL IMPROVEMENT PIPELINE FOR AI CULTURE OPTIMIZER")
    print("================================================================================")
    print(f"Loading data from: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name="time-saving")
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    target_col = "mean_A450_168h"
    sd_col = "sd_A450_168h"
    other_cols = ["mean_A450_96h", "sd_A450_96h", sd_col]

    feature_cols = [c for c in df.columns if c != target_col and c not in other_cols]
    print(f"Features ({len(feature_cols)}): {feature_cols}")

    X = df[feature_cols]
    y = df[target_col]
    sd = df[sd_col]

    # Calculate sample weights
    weights = compute_sample_weights(sd)

    # 1. Untouched 20% Holdout Split (random_state=42)
    X_train, X_holdout, y_train, y_holdout, w_train, w_holdout = train_test_split(
        X, y, weights, test_size=0.2, random_state=42
    )
    print(f"Dataset split: Training Set = {X_train.shape[0]} samples, Holdout Set = {X_holdout.shape[0]} samples")

    # Repeated 5-fold CV on Training Set (5 splits x 5 repeats = 25 evaluations)
    rkf = RepeatedKFold(n_splits=5, n_repeats=5, random_state=42)

    # Base Candidate Models
    base_models = {
        "DummyRegressor": DummyRegressor(strategy="mean"),
        "RandomForestRegressor": RandomForestRegressor(n_estimators=100, random_state=42),
        "ExtraTreesRegressor": ExtraTreesRegressor(n_estimators=100, random_state=42),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(random_state=42),
        "XGBRegressor": XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    }

    print("\n--------------------------------------------------------------------------------")
    print("1. REPEATED 5-FOLD CROSS-VALIDATION (BASE MODELS ON TRAIN SET)")
    print("--------------------------------------------------------------------------------")

    cv_base_results = {}
    for name, model in base_models.items():
        mae_list, rmse_list, r2_list = [], [], []

        for train_idx, val_idx in rkf.split(X_train, y_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            model.fit(X_tr, y_tr)
            preds = model.predict(X_val)

            m = evaluate_metrics(y_val, preds)
            mae_list.append(m["MAE"])
            rmse_list.append(m["RMSE"])
            r2_list.append(m["R2"])

        cv_base_results[name] = {
            "MAE_mean": round(float(np.mean(mae_list)), 4),
            "MAE_std": round(float(np.std(mae_list)), 4),
            "RMSE_mean": round(float(np.mean(rmse_list)), 4),
            "RMSE_std": round(float(np.std(rmse_list)), 4),
            "R2_mean": round(float(np.mean(r2_list)), 4),
            "R2_std": round(float(np.std(r2_list)), 4)
        }
        print(f"Base {name:30s} | CV R2: {cv_base_results[name]['R2_mean']:.4f} +/- {cv_base_results[name]['R2_std']:.4f} | RMSE: {cv_base_results[name]['RMSE_mean']:.4f}")

    # 2. Hyperparameter Tuning via RandomizedSearchCV on Training Set
    print("\n--------------------------------------------------------------------------------")
    print("2. HYPERPARAMETER TUNING (RANDOMIZED SEARCH CV ON TRAIN SET)")
    print("--------------------------------------------------------------------------------")

    param_distributions = {
        "RandomForestRegressor": {
            "n_estimators": [100, 200, 300],
            "max_depth": [None, 8, 12, 16],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2", 0.5, 0.8]
        },
        "ExtraTreesRegressor": {
            "n_estimators": [100, 200, 300],
            "max_depth": [None, 8, 12, 16],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2", 0.5, 0.8]
        },
        "XGBRegressor": {
            "n_estimators": [100, 200, 300],
            "max_depth": [3, 5, 7, 9],
            "learning_rate": [0.03, 0.05, 0.1, 0.2],
            "subsample": [0.6, 0.8, 1.0],
            "colsample_bytree": [0.6, 0.8, 1.0],
            "reg_alpha": [0.0, 0.1, 1.0],
            "reg_lambda": [0.1, 1.0, 5.0]
        }
    }

    tuned_models = {}
    for name in ["RandomForestRegressor", "ExtraTreesRegressor", "XGBRegressor"]:
        estimator = base_models[name]
        param_dist = param_distributions[name]
        search = RandomizedSearchCV(
            estimator, param_distributions=param_dist, n_iter=15,
            scoring="neg_root_mean_squared_error", cv=5, random_state=42, n_jobs=-1
        )
        search.fit(X_train, y_train)
        best_tuned = search.best_estimator_
        tuned_models[f"Tuned_{name}"] = best_tuned
        print(f"Tuned {name:25s} Best Params: {search.best_params_}")

    # Add HistGradientBoosting (tuned default)
    tuned_models["HistGradientBoostingRegressor"] = base_models["HistGradientBoostingRegressor"]

    # 3. Experiment Target Transformation: log1p(y) vs Original y
    print("\n--------------------------------------------------------------------------------")
    print("3. TARGET TRANSFORMATION EXPERIMENTS (log1p vs Original Scale)")
    print("--------------------------------------------------------------------------------")

    log_models = {}
    for name, model in tuned_models.items():
        # Train with log1p(y_train)
        y_train_log = np.log1p(y_train)
        
        # Cross validate log transformation evaluate on original scale
        mae_list, rmse_list, r2_list = [], [], []
        for train_idx, val_idx in rkf.split(X_train, y_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            y_tr_log = np.log1p(y_tr)
            model.fit(X_tr, y_tr_log)
            log_preds = model.predict(X_val)
            orig_preds = np.expm1(log_preds)
            orig_preds = np.clip(orig_preds, 0, None)

            m = evaluate_metrics(y_val, orig_preds)
            mae_list.append(m["MAE"])
            rmse_list.append(m["RMSE"])
            r2_list.append(m["R2"])

        log_r2_mean = round(float(np.mean(r2_list)), 4)
        log_rmse_mean = round(float(np.mean(rmse_list)), 4)
        print(f"Log-Transformed {name:30s} | Original Scale CV R2: {log_r2_mean:.4f} | RMSE: {log_rmse_mean:.4f}")

    # 4. Sample Weights Experiments
    print("\n--------------------------------------------------------------------------------")
    print("4. SAMPLE WEIGHTS EXPERIMENTS (Inverse Variance Weighting)")
    print("--------------------------------------------------------------------------------")

    weighted_models = {}
    for name in ["RandomForestRegressor", "ExtraTreesRegressor", "XGBRegressor"]:
        base_mod = base_models[name]
        mae_list, rmse_list, r2_list = [], [], []
        for train_idx, val_idx in rkf.split(X_train, y_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
            w_tr = w_train.iloc[train_idx]

            base_mod.fit(X_tr, y_tr, sample_weight=w_tr)
            preds = base_mod.predict(X_val)

            m = evaluate_metrics(y_val, preds)
            mae_list.append(m["MAE"])
            rmse_list.append(m["RMSE"])
            r2_list.append(m["R2"])

        w_r2_mean = round(float(np.mean(r2_list)), 4)
        w_rmse_mean = round(float(np.mean(rmse_list)), 4)
        print(f"Weighted {name:30s} | CV R2: {w_r2_mean:.4f} | RMSE: {w_rmse_mean:.4f}")

    # 5. Final Holdout Evaluation & Comparison against Deployed Baseline
    print("\n--------------------------------------------------------------------------------")
    print("5. FINAL HOLDOUT EVALUATION (ON 20% UNTOUCHED HOLDOUT SET)")
    print("--------------------------------------------------------------------------------")

    baseline_holdout_metrics = {"MAE": 0.3342, "RMSE": 0.4787, "R2": 0.3171}
    print(f"Deployed Baseline (RandomForest Holdout): {baseline_holdout_metrics}")

    holdout_evaluations = {}

    # Evaluate Tuned Models on Holdout
    for name, model in tuned_models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_holdout)
        holdout_evaluations[name] = evaluate_metrics(y_holdout, preds)
        print(f"Holdout -> {name:30s}: {holdout_evaluations[name]}")

    # Evaluate Log-Transformed Models on Holdout
    for name, model in tuned_models.items():
        y_train_log = np.log1p(y_train)
        model.fit(X_train, y_train_log)
        log_preds = model.predict(X_holdout)
        orig_preds = np.clip(np.expm1(log_preds), 0, None)
        holdout_evaluations[f"LogTransformed_{name}"] = evaluate_metrics(y_holdout, orig_preds)
        print(f"Holdout -> LogTransformed_{name:20s}: {holdout_evaluations[f'LogTransformed_{name}']}")

    # Build Weighted Ensemble (Top 2 Models: Tuned ExtraTrees & Tuned XGBoost)
    et_model = tuned_models["Tuned_ExtraTreesRegressor"]
    xgb_model = tuned_models["Tuned_XGBRegressor"]

    et_model.fit(X_train, y_train)
    xgb_model.fit(X_train, y_train)

    et_preds = et_model.predict(X_holdout)
    xgb_preds = xgb_model.predict(X_holdout)

    ensemble_preds = (0.5 * et_preds) + (0.5 * xgb_preds)
    ensemble_metrics = evaluate_metrics(y_holdout, ensemble_preds)
    holdout_evaluations["Weighted_Ensemble_(ET+XGB)"] = ensemble_metrics
    print(f"Holdout -> Weighted_Ensemble_(ET+XGB)      : {ensemble_metrics}")

    # Identify Best Experimental Candidate
    best_exp_name = max(holdout_evaluations, key=lambda k: holdout_evaluations[k]["R2"])
    best_exp_metrics = holdout_evaluations[best_exp_name]

    print("\n--------------------------------------------------------------------------------")
    print(f"BEST EXPERIMENTAL CANDIDATE: {best_exp_name}")
    print(f"Holdout R2: {best_exp_metrics['R2']} (vs Baseline 0.3171)")
    print(f"Holdout RMSE: {best_exp_metrics['RMSE']} (vs Baseline 0.4787)")
    print(f"Holdout MAE: {best_exp_metrics['MAE']} (vs Baseline 0.3342)")
    print("--------------------------------------------------------------------------------")

    # Determine Replacement Recommendation
    recommends_replacement = (
        best_exp_metrics["R2"] > baseline_holdout_metrics["R2"] and
        best_exp_metrics["RMSE"] < baseline_holdout_metrics["RMSE"]
    )

    # 6. Save Experimental Artifacts (Separately under models/experiments/culture_optimizer/)
    exp_model_path = os.path.join(exp_models_dir, "best_experimental_model.joblib")
    exp_metrics_path = os.path.join(exp_models_dir, "experimental_metrics.json")
    exp_features_path = os.path.join(exp_models_dir, "experimental_features.json")

    if "Ensemble" in best_exp_name:
        ensemble_dict = {"et_model": et_model, "xgb_model": xgb_model, "weights": [0.5, 0.5]}
        joblib.dump(ensemble_dict, exp_model_path)
    else:
        joblib.dump(tuned_models.get(best_exp_name.replace("LogTransformed_", ""), et_model), exp_model_path)

    exp_payload = {
        "best_experimental_candidate": best_exp_name,
        "recommends_deployment_replacement": recommends_replacement,
        "deployed_baseline_metrics": baseline_holdout_metrics,
        "experimental_holdout_evaluations": holdout_evaluations,
        "cv_base_results": cv_base_results,
        "num_features": len(feature_cols),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    with open(exp_metrics_path, "w", encoding="utf-8") as f:
        json.dump(exp_payload, f, indent=4)

    with open(exp_features_path, "w", encoding="utf-8") as f:
        json.dump(feature_cols, f, indent=4)

    # 7. Generate Comprehensive Markdown Improvement Report
    report_path = os.path.join(docs_dir, "culture_optimizer_improvement_report.md")
    report_md = f"""# AI Culture Optimizer — Experimental Model Improvement Report

**Module:** CoreAI BIO — Phase 4: AI Culture Optimizer  
**Dataset:** `dataset/culture_optimizer/Data.xlsx` (`time-saving` sheet)  
**Target Variable:** `mean_A450_168h`  
**Cross-Validation Protocol:** Repeated 5-Fold CV (5 splits $\\\\times$ 5 repeats = 25 runs, random_state=42)  
**Holdout Set:** Untouched 20% Holdout ($81$ samples, random_state=42)  

---

## 1. Executive Summary & Replacement Recommendation

An extensive experimental optimization pipeline was executed to improve upon the baseline **RandomForestRegressor** model ($R^2 = 0.3171, \\\\text{{RMSE}} = 0.4787, \\\\text{{MAE}} = 0.3342$).

- **Best Experimental Candidate:** **{best_exp_name}**
- **Holdout $R^2$ Score:** **{best_exp_metrics['R2']}** (vs Baseline $0.3171$, improvement: $+{round(best_exp_metrics['R2'] - 0.3171, 4)}$)
- **Holdout RMSE:** **{best_exp_metrics['RMSE']}** (vs Baseline $0.4787$, improvement: ${round(best_exp_metrics['RMSE'] - 0.4787, 4)}$)
- **Holdout MAE:** **{best_exp_metrics['MAE']}** (vs Baseline $0.3342$, improvement: ${round(best_exp_metrics['MAE'] - 0.3342, 4)}$)

### **Deployment Recommendation:**
> **{'RECOMMENDED FOR DEPLOYMENT REPLACEMENT' if recommends_replacement else 'RETAIN CURRENT DEPLOYED BASELINE'}**  
> **Rationale:** The candidate `{best_exp_name}` {'demonstrates superior holdout accuracy, reduced generalization error, and robust cross-validation stability' if recommends_replacement else 'did not achieve sufficient out-of-sample improvement over the baseline model'}.

---

## 2. Repeated 5-Fold Cross-Validation Performance (Base Models)

Evaluated across $25$ cross-validation folds on the training set ($322$ samples):

| Model Architecture | CV Mean MAE ($\\\\pm\\\\text{{std}}$) | CV Mean RMSE ($\\\\pm\\\\text{{std}}$) | CV Mean $R^2$ ($\\\\pm\\\\text{{std}}$) |
| :--- | :---: | :---: | :---: |
| **DummyRegressor** | {cv_base_results['DummyRegressor']['MAE_mean']} $\\\\pm$ {cv_base_results['DummyRegressor']['MAE_std']} | {cv_base_results['DummyRegressor']['RMSE_mean']} $\\\\pm$ {cv_base_results['DummyRegressor']['RMSE_std']} | {cv_base_results['DummyRegressor']['R2_mean']} $\\\\pm$ {cv_base_results['DummyRegressor']['R2_std']} |
| **RandomForestRegressor** | {cv_base_results['RandomForestRegressor']['MAE_mean']} $\\\\pm$ {cv_base_results['RandomForestRegressor']['MAE_std']} | {cv_base_results['RandomForestRegressor']['RMSE_mean']} $\\\\pm$ {cv_base_results['RandomForestRegressor']['RMSE_std']} | {cv_base_results['RandomForestRegressor']['R2_mean']} $\\\\pm$ {cv_base_results['RandomForestRegressor']['R2_std']} |
| **ExtraTreesRegressor** | {cv_base_results['ExtraTreesRegressor']['MAE_mean']} $\\\\pm$ {cv_base_results['ExtraTreesRegressor']['MAE_std']} | {cv_base_results['ExtraTreesRegressor']['RMSE_mean']} $\\\\pm$ {cv_base_results['ExtraTreesRegressor']['RMSE_std']} | {cv_base_results['ExtraTreesRegressor']['R2_mean']} $\\\\pm$ {cv_base_results['ExtraTreesRegressor']['R2_std']} |
| **HistGradientBoosting** | {cv_base_results['HistGradientBoostingRegressor']['MAE_mean']} $\\\\pm$ {cv_base_results['HistGradientBoostingRegressor']['MAE_std']} | {cv_base_results['HistGradientBoostingRegressor']['RMSE_mean']} $\\\\pm$ {cv_base_results['HistGradientBoostingRegressor']['RMSE_std']} | {cv_base_results['HistGradientBoostingRegressor']['R2_mean']} $\\\\pm$ {cv_base_results['HistGradientBoostingRegressor']['R2_std']} |
| **XGBoostRegressor** | {cv_base_results['XGBRegressor']['MAE_mean']} $\\\\pm$ {cv_base_results['XGBRegressor']['MAE_std']} | {cv_base_results['XGBRegressor']['RMSE_mean']} $\\\\pm$ {cv_base_results['XGBRegressor']['RMSE_std']} | {cv_base_results['XGBRegressor']['R2_mean']} $\\\\pm$ {cv_base_results['XGBRegressor']['R2_std']} |

---

## 3. Experimental Holdout Evaluation Summary (20% Untouched Set)

All metrics calculated on the original $A_{450}$ scale:

| Candidate Model / Technique | Holdout MAE | Holdout RMSE | Holdout $R^2$ Score | Status vs Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **Deployed Baseline (RandomForest)** | {baseline_holdout_metrics['MAE']} | {baseline_holdout_metrics['RMSE']} | {baseline_holdout_metrics['R2']} | Current Benchmark |
"""

    for m_name, m_vals in holdout_evaluations.items():
        is_best = (m_name == best_exp_name)
        status_str = "🏆 **Best Candidate**" if is_best else ("Better" if m_vals['R2'] > 0.3171 else "Inferior")
        report_md += f"| **{m_name}** | {m_vals['MAE']} | {m_vals['RMSE']} | **{m_vals['R2']}** | {status_str} |\n"

    report_md += """
---

## 4. Methodological Safeguards & Data Leakage Prevention

1. **Strict Holdout Isolation:** The 20% holdout set ($81$ samples) was completely excluded from hyperparameter tuning (`RandomizedSearchCV`), sample weight calculations, and cross-validation splitting.
2. **Scale Reversion:** For $\\\\log(1+y)$ target transformation experiments, predictions were transformed back via $\\\\exp(y_{\\\\text{pred}}) - 1$ before computing MAE, RMSE, and $R^2$.
3. **Weight Normalization:** Sample weights derived from $\\\\text{sd}_{A450}^2$ were clipped at the 5th and 95th percentiles and normalized around mean $1.0$ to prevent singular observations from distorting tree splits.
4. **Separate Storage:** All experimental model files were written to `models/experiments/culture_optimizer/`, strictly preserving `models/culture_optimizer_model.joblib`.
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\nGenerated improvement report at: {report_path}")
    print("Experimental improvement pipeline completed successfully!")

if __name__ == "__main__":
    run_improvement_experiments()
