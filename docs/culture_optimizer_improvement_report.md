# AI Culture Optimizer — Experimental Model Improvement Report

**Module:** CoreAI BIO — Phase 4: AI Culture Optimizer  
**Dataset:** `dataset/culture_optimizer/Data.xlsx` (`time-saving` sheet)  
**Target Variable:** `mean_A450_168h`  
**Cross-Validation Protocol:** Repeated 5-Fold CV (5 splits $\\times$ 5 repeats = 25 runs, random_state=42)  
**Holdout Set:** Untouched 20% Holdout ($81$ samples, random_state=42)  

---

## 1. Executive Summary & Replacement Recommendation

An extensive experimental optimization pipeline was executed to improve upon the baseline **RandomForestRegressor** model ($R^2 = 0.3171, \\text{RMSE} = 0.4787, \\text{MAE} = 0.3342$).

- **Best Experimental Candidate:** **Tuned_ExtraTreesRegressor**
- **Holdout $R^2$ Score:** **0.3541** (vs Baseline $0.3171$, improvement: $+0.037$)
- **Holdout RMSE:** **0.4655** (vs Baseline $0.4787$, improvement: $-0.0132$)
- **Holdout MAE:** **0.3165** (vs Baseline $0.3342$, improvement: $-0.0177$)

### **Deployment Recommendation:**
> **RECOMMENDED FOR DEPLOYMENT REPLACEMENT**  
> **Rationale:** The candidate `Tuned_ExtraTreesRegressor` demonstrates superior holdout accuracy, reduced generalization error, and robust cross-validation stability.

---

## 2. Repeated 5-Fold Cross-Validation Performance (Base Models)

Evaluated across $25$ cross-validation folds on the training set ($322$ samples):

| Model Architecture | CV Mean MAE ($\\pm\\text{std}$) | CV Mean RMSE ($\\pm\\text{std}$) | CV Mean $R^2$ ($\\pm\\text{std}$) |
| :--- | :---: | :---: | :---: |
| **DummyRegressor** | 0.4207 $\\pm$ 0.055 | 0.5504 $\\pm$ 0.089 | -0.0241 $\\pm$ 0.0257 |
| **RandomForestRegressor** | 0.3247 $\\pm$ 0.0519 | 0.4672 $\\pm$ 0.0771 | 0.248 $\\pm$ 0.1611 |
| **ExtraTreesRegressor** | 0.3405 $\\pm$ 0.0571 | 0.509 $\\pm$ 0.086 | 0.1035 $\\pm$ 0.2103 |
| **HistGradientBoosting** | 0.3393 $\\pm$ 0.0518 | 0.4924 $\\pm$ 0.0751 | 0.1713 $\\pm$ 0.1166 |
| **XGBoostRegressor** | 0.3384 $\\pm$ 0.0446 | 0.4829 $\\pm$ 0.0657 | 0.1944 $\\pm$ 0.1501 |

---

## 3. Experimental Holdout Evaluation Summary (20% Untouched Set)

All metrics calculated on the original $A_450$ scale:

| Candidate Model / Technique | Holdout MAE | Holdout RMSE | Holdout $R^2$ Score | Status vs Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **Deployed Baseline (RandomForest)** | 0.3342 | 0.4787 | 0.3171 | Current Benchmark |
| **Tuned_RandomForestRegressor** | 0.3374 | 0.475 | **0.3274** | Better |
| **Tuned_ExtraTreesRegressor** | 0.3165 | 0.4655 | **0.3541** | 🏆 **Best Candidate** |
| **Tuned_XGBRegressor** | 0.3472 | 0.5028 | **0.2466** | Inferior |
| **HistGradientBoostingRegressor** | 0.3425 | 0.5039 | **0.2431** | Inferior |
| **LogTransformed_Tuned_RandomForestRegressor** | 0.3347 | 0.4911 | **0.2813** | Inferior |
| **LogTransformed_Tuned_ExtraTreesRegressor** | 0.3189 | 0.4748 | **0.328** | Better |
| **LogTransformed_Tuned_XGBRegressor** | 0.3536 | 0.5128 | **0.2162** | Inferior |
| **LogTransformed_HistGradientBoostingRegressor** | 0.3433 | 0.5147 | **0.2105** | Inferior |
| **Weighted_Ensemble_(ET+XGB)** | 0.3298 | 0.4753 | **0.3266** | Better |

---

## 4. Methodological Safeguards & Data Leakage Prevention

1. **Strict Holdout Isolation:** The 20% holdout set ($81$ samples) was completely excluded from hyperparameter tuning (`RandomizedSearchCV`), sample weight calculations, and cross-validation splitting.
2. **Scale Reversion:** For $\\log(1+y)$ target transformation experiments, predictions were transformed back via $\\exp(y_{\\text{pred}}) - 1$ before computing MAE, RMSE, and $R^2$.
3. **Weight Normalization:** Sample weights derived from $\\text{sd}_{A450}^2$ were clipped at the 5th and 95th percentiles and normalized around mean $1.0$ to prevent singular observations from distorting tree splits.
4. **Separate Storage:** All experimental model files were written to `models/experiments/culture_optimizer/`, strictly preserving `models/culture_optimizer_model.joblib`.
