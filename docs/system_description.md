# CoreAI BIO: Integrated Computational Infrastructure for Genomic Repository Data Auditing and Cell Culture Medium Optimization

**Authors:** CoreAI BIO Research Group  
**System Release:** v1.0.0  
**Repository Document:** System Description & Technical Architecture Paper  
**Date:** July 2026  

---

## Abstract

We present **CoreAI BIO** (v1.0.0), an open-source, modular web application and computational framework designed to address two persistent bottlenecks in modern biotechnology and systems biology: (1) assessing and auditing the Findability, Accessibility, Interoperability, and Reusability (FAIR) of publicly deposited genomic datasets, and (2) optimizing multi-component cell culture medium formulations using interpretable machine learning. CoreAI BIO integrates a real-time NCBI GEO repository auditor (**NIH S-Index Subsystem**) with an explainable Machine Learning regression pipeline (**AI Culture Optimizer Subsystem**). Evaluated across $403$ experimental formulations, our tuned `ExtraTreesRegressor` model achieved a test-set holdout $R^2$ score of $0.3541$ ($\text{RMSE} = 0.4655$), outperforming standard baselines. Explainable AI (SHAP) TreeExplainer integration decomposes single-sample predictions into actionable biochemical driver attributions ($\phi_i$). CoreAI BIO provides an end-to-end reproducible platform ready for bioprocess demonstration and peer-reviewed research.

---

## 1. Motivation & Background

High-throughput genomic sequencing and cell bioprocessing generate massive volumes of biomedical data. However, secondary re-use of deposited data is severely bottlenecked by incomplete metadata, non-standardized annotations, and lack of automated quality auditing tools. Concurrently, in mammalian and microbial cell culture engineering, formulation of 30+ nutrient components (amino acids, vitamins, inorganic salts, energy sources) traditionally relies on trial-and-error design of experiments (DOE).

**CoreAI BIO** bridges these domains by providing:
1. Automated, reproducible scoring of genomic metadata quality (NIH S-Index).
2. Machine learning optimization of culture formulations with real-time SHAP explainability.

---

## 2. Problem Statement

### 2.1 NIH S-Index Metadata Auditing
Public repositories such as NCBI GEO host hundreds of thousands of datasets. Evaluating dataset FAIR compliance requires automated parsing of heterogeneous XML MINiML and SOFT flat-file schemas without relying on hardcoded static sample lists.

### 2.2 Culture Medium Growth Prediction & Explainability
Given a 29-dimensional vector of nutrient concentrations $X = [x_1, x_2, \dots, x_{29}]^T$, predict cell biomass absorbance $y = A_{450}$ at 168 hours post-inoculation while providing game-theoretic feature attributions ($\phi_i$) to inform biological experimental design.

---

## 3. Methods & Computational Pipeline

### 3.1 NIH S-Index Subsystem Architecture
- **Dynamic File Discovery:** Searches `NIH S-index/cache/geo/*.json` dynamically without code modification.
- **Robust Schema Parsing:** Extracts sample counts, taxonomic organisms, platform titles, and contributor metadata from MINiML XML (`http://www.ncbi.nlm.nih.gov/geo/info/MINiML`) with fallback to SOFT flat-text format.
- **FAIR Vector Engine:** Calculates a 4-vector score ($F, A, I, R \in [0, 100]$) and composite NIH S-Index score:
  $$S = 0.30 \cdot F + 0.25 \cdot A + 0.20 \cdot I + 0.25 \cdot R$$

### 3.2 AI Culture Optimizer ML Pipeline
- **Dataset Preprocessing:** Dataset derived from `dataset/culture_optimizer/Data.xlsx` (`time-saving` sheet, $403$ samples). Feature vector $X \in \mathbb{R}^{29}$ excludes index markers, 96h intermediate targets, and standard deviation columns.
- **Model Selection & CV Protocol:** Evaluated across Repeated 5-Fold Cross-Validation ($5 \text{ splits} \times 5 \text{ repeats} = 25 \text{ runs}$, `random_state=42`) on a $322$-sample training set, reserving an untouched $81$-sample ($20\%$) holdout test set.
- **Compared Architectures:**
  - `DummyRegressor` (baseline mean predictor)
  - `RandomForestRegressor` (deployed default)
  - `ExtraTreesRegressor` (tuned top experimental candidate)
  - `HistGradientBoostingRegressor`
  - `XGBoostRegressor`

### 3.3 Explainable AI (SHAP) Engine
Integrates `shap.TreeExplainer` to compute exact TreeSHAP values for single-sample predictions:
$$\hat{y}(x) = \phi_0 + \sum_{i=1}^{29} \phi_i(x)$$
Positive ($\phi_i > 0$) and negative ($\phi_i < 0$) attributions are formatted as structured JSON responses and rendered visually as green $\uparrow$ and red $\downarrow$ badges on the web interface.

---

## 4. Experimental Validation & Results

### 4.1 AI Culture Optimizer Model Performance
Evaluated on the $20\%$ untouched holdout set ($81$ samples) on the original $A_{450}$ scale:

| Model Architecture | Holdout MAE | Holdout RMSE | Holdout $R^2$ Score | Deployment Status |
| :--- | :---: | :---: | :---: | :---: |
| **DummyRegressor** | $0.4207$ | $0.5504$ | $-0.0241$ | Reference |
| **Baseline RandomForestRegressor** | $0.3342$ | $0.4787$ | $0.3171$ | Deployed v1.0.0 |
| **Tuned ExtraTreesRegressor** 🏆 | **$0.3165$** | **$0.4655$** | **$0.3541$** | **Top Experimental (+0.0370 $R^2$)** |
| **Weighted Ensemble (ET + XGB)** | $0.3298$ | $0.4753$ | $0.3266$ | Experimental |
| **Tuned XGBoostRegressor** | $0.3472$ | $0.5028$ | $0.2466$ | Experimental |

### 4.2 System Verification
- **Automated Test Suite:** 30/30 unit tests passing (`py -m unittest discover tests`).
- **Live HTTP Endpoint Verification:** End-to-end verified via `POST /api/culture/predict` and `POST /api/nih-sindex/audit`.

---

## 5. Current Limitations

1. **Dataset Size & Scope:** Culture optimizer training data is derived from $403$ observations of a specific cell line; generalization to alternative cell types requires transfer learning.
2. **Static Cache Invalidation:** GEO audits cache records locally in `cache/geo/`; periodic automated cache invalidation remains a future feature.

---

## 6. Future Work & Phase 5 Roadmap

1. **Phase 5: Cell Fate Analyzer:** Implement deep learning classification models for cell fate determination (differentiation, apoptosis, senescence).
2. **Phase 6: Cell Morphology Analyzer:** Integrate computer vision pipelines for microscopic cell image segmentation and morphometric profiling.
