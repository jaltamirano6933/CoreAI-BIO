# Culture Optimizer Module — Documentation

**Module:** CoreAI BIO — Research Culture Optimizer  
**Backend Component:** `backend/culture_optimizer_service.py`  
**Frontend View:** `/culture` ([frontend/templates/culture_optimizer.html](file:///C:/Users/Altam/OneDrive/Desktop/CoreAI%20BIO/frontend/templates/culture_optimizer.html))  
**Date:** July 2026  

---

## 1. Overview

The **Research Culture Optimizer** provides stem cell culture telemetry monitoring, environmental quality scoring, and deterministic rule-based recommendations. It enables research labs to track cell density, confluency, incubator parameters, and growth phases with actionable guidance for subculture timing, media changes, and environmental verifications.

---

## 2. Quality Metrics & Dashboard Indicators

| Metric | Measured Value | Target Range | Status / Quality Impact |
| :--- | :---: | :---: | :--- |
| **Culture Status** | `Near Confluent` | `Optimal Growth` | Confluency approaching passage threshold ($85.0\%$). |
| **Cell Density** | $1.25 \times 10^5 \text{ cells/cm}^2$ | $0.2 - 3.5 \times 10^5$ | Logarithmic growth phase. |
| **Confluency** | $85.0\%$ | $30.0\% - 80.0\%$ | Passage recommended to prevent contact inhibition. |
| **Passage Number** | `P4` | $\le P10$ | Early passage stem cell stability. |
| **Incubator Temperature** | $37.0^\circ\text{C}$ | $36.5^\circ\text{C} - 37.5^\circ\text{C}$ | Optimal mammalian cell culture temperature. |
| **$\text{CO}_2$ Level** | $5.0\%$ | $4.5\% - 5.5\%$ | Standard bicarbonate buffer pH equilibrium. |
| **Relative Humidity** | $95.0\%$ | $\ge 90.0\%$ | Prevents evaporation and hyperosmolality. |
| **Culture Age** | $4\text{ Days}$ | $1 - 7\text{ Days}$ | Post-passage incubation duration. |
| **Overall Culture Score** | $88 / 100$ | $80 - 100$ | `Low` Risk, `Exponential Growth`. |

---

## 3. Deterministic Recommendation Rules & Threshold Definitions

The recommendation engine executes deterministic threshold rules:

```text
[ Telemetry & Culture Parameters ]
               │
               ├──► Confluency >= 85.0% ───────► Rule R1: Passage cells soon (High Priority)
               ├──► Culture Age >= 3 Days ─────► Rule R2: Change medium (Medium Priority)
               ├──► Temp outside [36.5, 37.5] ──► Rule R3: Verify incubator settings (High Priority)
               ├──► CO2 outside [4.5, 5.5] ────► Rule R4: Check CO2 cylinder & regulator (High Priority)
               └──► Humidity < 90.0% ──────────► Rule R5: Replenish water pan (Medium Priority)
```

1. **Subculture Rule (`R1_PASSAGE`):** Triggered when Confluency $\ge 85.0\%$. Action: *Passage cells soon to prevent contact inhibition and cell senescence.*
2. **Nutrient Feeding Rule (`R2_FEEDING`):** Triggered when Culture Age $\ge 3\text{ days}$ and Confluency $< 90.0\%$. Action: *Change medium to replenish glucose and amino acids.*
3. **Temperature Control Rule (`R3_TEMP`):** Triggered if Temp $< 36.5^\circ\text{C}$ or $> 37.5^\circ\text{C}$. Action: *Verify incubator temperature settings.*
4. **$\text{CO}_2$ Gas Control Rule (`R4_CO2`):** Triggered if $\text{CO}_2 < 4.5\%$ or $> 5.5\%$. Action: *Check incubator CO2 cylinder and gas regulator.*
5. **Humidity Evaporation Rule (`R5_HUMIDITY`):** Triggered if Relative Humidity $< 90.0\%$. Action: *Replenish incubator water pan.*
6. **Routine Monitoring Rule (`R6_MONITOR`):** Triggered when parameters are within optimal ranges. Action: *Maintain routine monitoring.*

---

## 4. Trend Charts (`static/results/culture_optimizer/`)

1. **`density_over_time.png`**: Plot of Cell Density ($10^5 \text{ cells/cm}^2$) over Days 1–7.
2. **`confluency_over_time.png`**: Plot of Confluency ($0-100\%$) over Days 1–7 with $85\%$ passage threshold line.
3. **`culture_score_trend.png`**: Plot of Overall Culture Health Score over Days 1–7.

---

## 5. API Reference

| Endpoint | Method | Response Payload | Status |
| :--- | :---: | :--- | :---: |
| `/api/culture/summary` | `GET` | Dashboard metrics, quality indicators, figure paths | `200 OK` |
| `/api/culture/recommendations` | `GET` | Actionable rule-based recommendations list | `200 OK` |
| `/api/culture/predict` | `POST` | Media formulation yield prediction ($A_{450}$ at 168h) & SHAP attributions | `200 OK` |

---

## 6. Scientific Scope & Laboratory Limitation Notice

> ℹ️ **Research Guidance Notice:** This module provides research-oriented culture monitoring recommendations and is not intended to replace laboratory protocols or expert judgment.
