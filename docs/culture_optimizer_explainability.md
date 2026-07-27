# AI Culture Optimizer — Explainable AI (SHAP) Documentation

**Module:** CoreAI BIO — Phase 4: AI Culture Optimizer  
**Service Component:** `backend/explainability_service.py`  
**API Integration:** `POST /api/culture/predict`  
**Report Date:** July 2026  

---

## 1. Introduction to SHAP in Culture Medium Optimization

In biological culture medium optimization, black-box predictions of cell growth are insufficient for cell biologists and bioprocess engineers. Understanding **why** a specific nutrient combination produces a predicted biomass absorbance ($A_{450}$ at 168h) is vital for identifying nutrient bottlenecks, preventing amino acid toxicity, and fine-tuning formulation concentrations.

The **AI Culture Optimizer** implements **SHAP (SHapley Additive exPlanations)** via `shap.TreeExplainer` to provide local feature attributions for every single prediction request.

---

## 2. How SHAP Works

SHAP is grounded in cooperative game theory. It calculates the marginal contribution of each culture medium component across all possible feature subsets (coalitions):

$$\hat{y}(x) = \phi_0 + \sum_{i=1}^{M} \phi_i(x)$$

Where:
- $\hat{y}(x)$ is the final model prediction ($A_{450}$ absorbance at 168 hours).
- $\phi_0$ is the base value (expected average prediction $E[f(X)]$ across the dataset, approx. $0.6907$).
- $\phi_i(x)$ is the SHAP value (impact score) attributable to nutrient component $i$.
- $M$ is the total number of features ($29$ culture components).

---

## 3. Interpretation of Positive and Negative Contributions

Each SHAP value represents the directional effect of a component's concentration relative to the baseline expectation:

- **Green $\uparrow$ Positive Contribution ($\phi_i > 0$):**
  - Indicates that the specific concentration of component $i$ **increases** predicted cell biomass above the dataset baseline.
  - *Example:* Optimal doses of Niacinamide or Choline boost biomass proliferation ($\phi \approx +0.36$).

- **Red $\downarrow$ Negative Contribution ($\phi_i < 0$):**
  - Indicates that the specific concentration of component $i$ **suppresses** predicted cell biomass below the baseline expectation.
  - *Example:* Overdosing or underdosing components like $\text{NaCl}$ or Glutamine can cause osmotic stress or toxic metabolite build-up, reducing yield ($\phi \approx -0.76$).

---

## 4. Methodological Limitations

1. **Correlation vs. Causation:** SHAP values measure feature importance within the learned model trees, reflecting statistical associations rather than direct biochemical mechanisms.
2. **Feature Interdependence:** Highly correlated components (e.g. total amino acid nitrogen load vs. osmotic salt concentration) can distribute SHAP values across co-dependent features.
3. **Local Scope:** Individual prediction SHAP attributions represent local feature effects for that specific media formulation, which may differ for alternative media formulations.

---

## 5. Example API Prediction Request & Explanation Response

### 5.1 Request (`POST /api/culture/predict`)

```json
{
  "Glucose": 10.0,
  "FBS": 0.1,
  "Glutamine": 4.0,
  "NaCl": 140.0
}
```

### 5.2 Response Payload with Embedded SHAP Explanation

```json
{
  "base_value": 0.6907,
  "growth_category": "Optimal High Biomass Yield",
  "model_name": "RandomForestRegressor",
  "num_features_used": 29,
  "predicted_mean_A450_168h": 1.1191,
  "prediction_status": "success",
  "rating_badge": "Good",
  "timestamp": "2026-07-22 03:22:45 UTC",
  "prediction_explanation": {
    "top_positive_features": [
      { "feature": "Niacinamide", "impact": 0.3637 },
      { "feature": "Choline", "impact": 0.151 },
      { "feature": "Calcium pantothenate", "impact": 0.0827 }
    ],
    "top_negative_features": [
      { "feature": "NaCl", "impact": -0.7602 },
      { "feature": "NaHCO3", "impact": -0.1381 },
      { "feature": "Tryptophane", "impact": -0.0498 }
    ]
  },
  "top_positive_features": [
    { "feature": "Niacinamide", "impact": 0.3637 },
    { "feature": "Choline", "impact": 0.151 },
    { "feature": "Calcium pantothenate", "impact": 0.0827 }
  ],
  "top_negative_features": [
    { "feature": "NaCl", "impact": -0.7602 },
    { "feature": "NaHCO3", "impact": -0.1381 },
    { "feature": "Tryptophane", "impact": -0.0498 }
  ]
}
```

---

## 6. Generated SHAP Visualizations

The explainability engine outputs two static diagnostic charts available in `static/results/culture_optimizer/`:

1. **`shap_summary.png`**: Beeswarm summary plot displaying global feature impact across all dataset samples.
2. **`shap_waterfall.png`**: Sample waterfall plot illustrating step-by-step additive decomposition from baseline $\phi_0$ to final prediction $\hat{y}$.
