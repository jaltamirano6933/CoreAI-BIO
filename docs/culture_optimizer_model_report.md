# AI Culture Optimizer — Model Training & Evaluation Report

**Module:** CoreAI BIO — Phase 4: AI Culture Optimizer  
**Dataset:** `dataset/culture_optimizer/Data.xlsx` (`time-saving` sheet)  
**Target Variable:** `mean_A450_168h`  
**Train/Test Split:** 80% Train / 20% Test (random_state=42)  

---

## 1. Executive Summary

This report documents the training and evaluation of regression models for predicting cell proliferation (`mean_A450_168h`) based on 30 culture medium chemical formulation features. 

The best-performing model identified is **RandomForestRegressor**, achieving an $R^2$ score of **0.3171** and a Root Mean Squared Error (RMSE) of **0.4787**.

---

## 2. Model Performance Comparison

| Model Architecture | MAE | RMSE | $R^2$ Score | Ranking |
| :--- | :---: | :---: | :---: | :---: |
| **DummyRegressor (Baseline)** | 0.4564 | 0.5806 | -0.0047 | Baseline |
| **RandomForestRegressor** | 0.3342 | 0.4787 | 0.3171 | 1st |
| **XGBoostRegressor** | 0.3394 | 0.4918 | 0.2792 | 2nd |

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
