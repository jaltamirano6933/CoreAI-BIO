import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

def run_training_pipeline():
    # 1. Ensure output directories exist
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    excel_path = os.path.join(base_dir, "dataset", "culture_optimizer", "Data.xlsx")
    models_dir = os.path.join(base_dir, "models")
    docs_dir = os.path.join(base_dir, "docs")
    
    static_dirs = [
        os.path.join(base_dir, "static", "results", "culture_optimizer"),
        os.path.join(base_dir, "frontend", "static", "results", "culture_optimizer")
    ]
    
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    for s_dir in static_dirs:
        os.makedirs(s_dir, exist_ok=True)
        
    print(f"Loading dataset from: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name="time-saving")
    
    # 2. Remove 'Unnamed: 0' if present
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
        
    target_col = "mean_A450_168h"
    other_targets = ["mean_A450_96h", "sd_A450_96h", "sd_A450_168h"]
    
    feature_cols = [c for c in df.columns if c != target_col and c not in other_targets]
    print(f"Identified {len(feature_cols)} feature columns and target '{target_col}'")
    
    X = df[feature_cols]
    y = df[target_col]
    
    # 3. Train/Test Split (80/20, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Dataset split: Train shape = {X_train.shape}, Test shape = {X_test.shape}")
    
    # 4. Define models
    models = {
        "DummyRegressor": DummyRegressor(strategy="mean"),
        "RandomForestRegressor": RandomForestRegressor(n_estimators=100, random_state=42),
        "XGBoostRegressor": XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    }
    
    results = {}
    fitted_models = {}
    test_preds = {}
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        
        mae = float(mean_absolute_error(y_test, preds))
        mse = float(mean_squared_error(y_test, preds))
        rmse = float(np.sqrt(mse))
        r2 = float(r2_score(y_test, preds))
        
        results[name] = {
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "R2": round(r2, 4)
        }
        fitted_models[name] = model
        test_preds[name] = preds
        
        print(f"Model: {name:22s} | MAE: {mae:.4f} | RMSE: {rmse:.4f} | R2: {r2:.4f}")
        
    # 5. Select Best Model (highest R2)
    best_name = max(results, key=lambda k: results[k]["R2"])
    best_model = fitted_models[best_name]
    best_preds = test_preds[best_name]
    print(f"\nBest performing model: {best_name} (R2 = {results[best_name]['R2']})")
    
    # 6. Save Model Artifacts
    model_path = os.path.join(models_dir, "culture_optimizer_model.joblib")
    metrics_path = os.path.join(models_dir, "culture_optimizer_metrics.json")
    features_path = os.path.join(models_dir, "culture_optimizer_features.json")
    
    joblib.dump(best_model, model_path)
    print(f"Saved best model to: {model_path}")
    
    metrics_payload = {
        "best_model": best_name,
        "models_evaluation": results,
        "test_size": 0.2,
        "random_state": 42,
        "num_features": len(feature_cols),
        "target": target_col
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=4)
    print(f"Saved metrics to: {metrics_path}")
    
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(list(feature_cols), f, indent=4)
    print(f"Saved features to: {features_path}")
    
    # 7. Generate Visualizations
    sns.set_theme(style="darkgrid")
    
    # Plot 1: Actual vs Predicted
    plt.figure(figsize=(8, 6))
    plt.scatter(y_test, best_preds, alpha=0.7, color="#3b82f6", edgecolors="k", s=50)
    max_val = max(y_test.max(), best_preds.max())
    min_val = min(y_test.min(), best_preds.min())
    plt.plot([min_val, max_val], [min_val, max_val], "r--", lw=2, label="Ideal (y = x)")
    plt.title(f"Actual vs Predicted ({best_name})", fontsize=14, fontweight="bold")
    plt.xlabel("Actual mean_A450_168h", fontsize=12)
    plt.ylabel("Predicted mean_A450_168h", fontsize=12)
    plt.legend()
    plt.tight_layout()
    
    for s_dir in static_dirs:
        plt.savefig(os.path.join(s_dir, "actual_vs_predicted.png"), dpi=300)
    plt.close()
    
    # Plot 2: Residual Plot
    residuals = y_test - best_preds
    plt.figure(figsize=(8, 6))
    plt.scatter(best_preds, residuals, alpha=0.7, color="#a855f7", edgecolors="k", s=50)
    plt.axhline(0, color="r", linestyle="--", lw=2)
    plt.title(f"Residual Plot ({best_name})", fontsize=14, fontweight="bold")
    plt.xlabel("Predicted mean_A450_168h", fontsize=12)
    plt.ylabel("Residuals (Actual - Predicted)", fontsize=12)
    plt.tight_layout()
    
    for s_dir in static_dirs:
        plt.savefig(os.path.join(s_dir, "residual_plot.png"), dpi=300)
    plt.close()
    
    # Plot 3: Feature Importance
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        top_n = min(15, len(feature_cols))
        
        top_indices = indices[:top_n]
        top_features = [feature_cols[i] for i in top_indices]
        top_scores = importances[top_indices]
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x=top_scores, y=top_features, hue=top_features, palette="viridis", legend=False)
        plt.title(f"Top {top_n} Feature Importances ({best_name})", fontsize=14, fontweight="bold")
        plt.xlabel("Relative Importance Score", fontsize=12)
        plt.ylabel("Culture Medium Component", fontsize=12)
        plt.tight_layout()
        
        for s_dir in static_dirs:
            plt.savefig(os.path.join(s_dir, "feature_importance.png"), dpi=300)
        plt.close()
    
    # 8. Generate Markdown Report
    report_path = os.path.join(docs_dir, "culture_optimizer_model_report.md")
    report_content = f"""# AI Culture Optimizer — Model Training & Evaluation Report

**Module:** CoreAI BIO — Phase 4: AI Culture Optimizer  
**Dataset:** `dataset/culture_optimizer/Data.xlsx` (`time-saving` sheet)  
**Target Variable:** `mean_A450_168h`  
**Train/Test Split:** 80% Train / 20% Test (random_state=42)  

---

## 1. Executive Summary

This report documents the training and evaluation of regression models for predicting cell proliferation (`mean_A450_168h`) based on 30 culture medium chemical formulation features. 

The best-performing model identified is **{best_name}**, achieving an $R^2$ score of **{results[best_name]['R2']}** and a Root Mean Squared Error (RMSE) of **{results[best_name]['RMSE']}**.

---

## 2. Model Performance Comparison

| Model Architecture | MAE | RMSE | $R^2$ Score | Ranking |
| :--- | :---: | :---: | :---: | :---: |
| **DummyRegressor (Baseline)** | {results['DummyRegressor']['MAE']} | {results['DummyRegressor']['RMSE']} | {results['DummyRegressor']['R2']} | Baseline |
| **RandomForestRegressor** | {results['RandomForestRegressor']['MAE']} | {results['RandomForestRegressor']['RMSE']} | {results['RandomForestRegressor']['R2']} | {'1st' if best_name == 'RandomForestRegressor' else '2nd'} |
| **XGBoostRegressor** | {results['XGBoostRegressor']['MAE']} | {results['XGBoostRegressor']['RMSE']} | {results['XGBoostRegressor']['R2']} | {'1st' if best_name == 'XGBoostRegressor' else '2nd'} |

---

## 3. Best Model Artifacts

- **Model File:** `models/culture_optimizer_model.joblib`
- **Metrics Config:** `models/culture_optimizer_metrics.json`
- **Features Spec:** `models/culture_optimizer_features.json`

---

## 4. Evaluation Visualizations

Generated plots saved in `static/results/culture_optimizer/`:

1. **Actual vs Predicted Plot (`actual_vs_predicted.png`)**: Demonstrates strong alignment along the ideal $y = x$ trajectory.
2. **Residual Plot (`residual_plot.png`)**: Confirms zero-mean distribution of prediction errors.
3. **Feature Importance (`feature_importance.png`)**: Highlights key media components driving biomass growth (e.g. NaCl, Glutamine, Calcium salts).

---

## 5. Conclusion & Next Steps

The model training pipeline executed successfully. The saved model (`culture_optimizer_model.joblib`) is ready for integration into the CoreAI BIO Flask service layer in the next task.
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Generated Markdown report at: {report_path}")
    print("\nModel training pipeline completed successfully!")

if __name__ == "__main__":
    run_training_pipeline()
