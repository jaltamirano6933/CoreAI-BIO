# AI Culture Optimizer — Exploratory Data Analysis (EDA) Report

**Project Module:** CoreAI BIO — Phase 4: AI Culture Optimizer  
**Dataset Path:** `dataset/culture_optimizer/Data.xlsx`  
**Report Date:** July 2026  
**Document Status:** Complete Exploratory Data Analysis (Pre-Model Training)

---

## 1. Executive Summary

This report delivers a comprehensive exploratory data analysis (EDA) of the culture medium optimization dataset for **Phase 4 (AI Culture Optimizer)** of the CoreAI BIO platform. The dataset contains quantitative experimental measurements evaluating the growth response of cell cultures across various formulations of culture medium components (amino acids, vitamins, inorganic salts, energy sources, and serum).

No data modifications, feature engineering, or model training were performed during this analysis. The findings herein provide the structural, statistical, and correlation baseline needed to configure data preprocessing pipelines and select target variables for subsequent AI model training.

---

## 2. Dataset Overview

The Excel workbook `dataset/culture_optimizer/Data.xlsx` consists of two distinct worksheets:
1. `regular`: Initial experimental dataset measuring cell proliferation after a fixed incubation period.
2. `time-saving`: Expanded longitudinal dataset measuring cell proliferation across multiple timepoints ($96\text{h}$ and $168\text{h}$).

### 2.1 Summary Metrics by Worksheet

| Worksheet Metric | `regular` Worksheet | `time-saving` Worksheet |
| :--- | :---: | :---: |
| **Total Rows (Observations)** | $308$ | $403$ |
| **Total Columns** | $32$ | $34$ |
| **Input Features** | $30$ | $30$ |
| **Candidate Target Variables** | $2$ (`mean_A450`, `sd_A450`) | $4$ (`mean_A450_96h`, `mean_A450_168h`, `sd_A450_96h`, `sd_A450_168h`) |
| **Missing Values (Nulls)** | $0$ ($0.0\%$) | $0$ ($0.0\%$) |
| **Duplicate Rows** | $0$ ($0.0\%$) | $0$ ($0.0\%$) |
| **Index / Identifier Column** | `Unnamed: 0` (`int64`) | `Unnamed: 0` (`int64`) |
| **Numeric Component Features** | $30$ (`float64`) | $30$ (`float64`) |

---

## 3. Feature Breakdown & Classification

The $30$ input features represent chemical and biological components added to the culture medium. They fall into 4 major biochemical categories:

### 3.1 Biochemical Classification of Input Features

| Category | Chemical / Nutrient Components | Count |
| :--- | :--- | :---: |
| **Essential & Non-Essential Amino Acids** | L-Arginine, L-Glutamine, L-Histidine, L-Isoleucine, L-Leucine, L-Lysine, L-Methionine, L-Phenylalanine, L-Threonine, L-Tryptophan, L-Tyrosine, L-Valine, L-Cystine | $13$ |
| **Vitamins & Co-factors** | Choline chloride, D-Calcium pantothenate, Folic acid, Niacinamide, Pyridoxal hydrochloride, Riboflavin, Thiamine hydrochloride, i-Inositol | $8$ |
| **Inorganic Salts** | $\text{CaCl}_2$, $\text{MgSO}_4$, $\text{KCl}$, $\text{NaHCO}_3$, $\text{NaCl}$, $\text{NaH}_2\text{PO}_4$ | $6$ |
| **Carbon/Energy & Serum** | D-Glucose, FBS (Fetal Bovine Serum) | $2$ |
| **Index Identifier** | `Unnamed: 0` (Row / Experiment ID) | $1$ |

> **Note on Naming Conventions:** The `regular` worksheet uses full chemical names with salt forms (e.g., `L-Arginine hydrochloride `, `Choline chloride`, `D-Glucose`), whereas the `time-saving` worksheet uses shortened compound names (e.g., `Arginine`, `Choline`, `Glucose`).

---

## 4. Detailed Worksheet Analysis

### 4.1 Worksheet 1: `regular`

#### Data Types & Missing Values
- **Row Count:** $308$ rows
- **Column Count:** $32$ columns
- **Data Types:** $1$ $\text{int64}$ (`Unnamed: 0`), $31$ $\text{float64}$
- **Missing Values:** $0$ across all columns
- **Duplicates:** $0$ duplicate rows

#### Descriptive Statistics (`regular` sheet)

| Feature / Column Name | Min | Median ($50\%$) | Mean | Max | Std Dev | Zero Count ($\%$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `L-Arginine hydrochloride ` | $0.0000$ | $0.6000$ | $0.9479$ | $16.0000$ | $1.7645$ | $1$ ($0.3\%$) |
| `L-Glutamine ` | $0.0000$ | $2.0000$ | $3.2474$ | $10.0000$ | $2.0069$ | $1$ ($0.3\%$) |
| `L-Histidine hydrochloride-H2O` | $0.0000$ | $0.2000$ | $0.2201$ | $10.0000$ | $0.5702$ | $1$ ($0.3\%$) |
| `L-Isoleucine ` | $0.0000$ | $0.4000$ | $1.6400$ | $10.0000$ | $2.1465$ | $1$ ($0.3\%$) |
| `L-Leucine ` | $0.0000$ | $0.4000$ | $1.9864$ | $10.0000$ | $2.4414$ | $1$ ($0.3\%$) |
| `L-Lysine hydrochloride ` | $0.0000$ | $0.4000$ | $0.6212$ | $16.0000$ | $1.4116$ | $1$ ($0.3\%$) |
| `L-Methionine ` | $0.0000$ | $0.1000$ | $0.1777$ | $10.0000$ | $0.6007$ | $1$ ($0.3\%$) |
| `L-Phenylalanine ` | $0.0000$ | $0.2000$ | $0.3872$ | $10.0000$ | $0.8710$ | $1$ ($0.3\%$) |
| `L-Threonine ` | $0.0000$ | $0.4000$ | $0.6403$ | $10.0000$ | $1.0421$ | $1$ ($0.3\%$) |
| `L-Tryptophan` | $0.0000$ | $0.0500$ | $0.0637$ | $5.0000$ | $0.2829$ | $1$ ($0.3\%$) |
| `L-Tyrosine disodium salt` | $0.0000$ | $0.2000$ | $0.3925$ | $10.0000$ | $0.8037$ | $1$ ($0.3\%$) |
| `L-Valine` | $0.0000$ | $0.4000$ | $2.1631$ | $10.0000$ | $3.2084$ | $13$ ($4.2\%$) |
| `L-Cystine 2HCl ` | $0.0000$ | $0.1000$ | $0.0701$ | $0.2500$ | $0.0401$ | $1$ ($0.3\%$) |
| `Choline chloride` | $0.0000$ | $0.0070$ | $0.0687$ | $0.7000$ | $0.1834$ | $46$ ($14.9\%$) |
| `D-Calcium pantothenate ` | $0.0000$ | $0.0020$ | $0.0152$ | $0.2000$ | $0.0470$ | $21$ ($6.8\%$) |
| `Folic Acid` | $0.0000$ | $0.0020$ | $0.0014$ | $0.0060$ | $0.0009$ | $1$ ($0.3\%$) |
| `Niacinamide` | $0.0000$ | $0.0080$ | $0.0272$ | $0.8000$ | $0.0543$ | $10$ ($3.2\%$) |
| `Pyridoxal hydrochloride` | $0.0000$ | $0.0050$ | $0.0208$ | $0.5000$ | $0.0441$ | $44$ ($14.3\%$) |
| `Riboflavin` | $0.0000$ | $0.0003$ | $0.0003$ | $0.0300$ | $0.0017$ | $16$ ($5.2\%$) |
| `Thiamine hydrochloride ` | $0.0000$ | $0.0030$ | $0.0269$ | $0.3000$ | $0.0703$ | $66$ ($21.4\%$) |
| `i-Inositol` | $0.0000$ | $0.0100$ | $0.0186$ | $1.0000$ | $0.0607$ | $16$ ($5.2\%$) |
| `CaCl2` | $0.0000$ | $1.8000$ | $1.7223$ | $36.0000$ | $2.1481$ | $19$ ($6.2\%$) |
| `MgSO4` | $0.0000$ | $0.8000$ | $0.6756$ | $40.0000$ | $2.2748$ | $68$ ($22.1\%$) |
| `KCl ` | $0.0000$ | $5.5000$ | $5.3554$ | $110.0000$ | $6.7592$ | $1$ ($0.3\%$) |
| `NaHCO3` | $0.0000$ | $26.0000$ | $26.5994$ | $260.0000$ | $13.3426$ | $1$ ($0.3\%$) |
| `NaCl` | $0.0000$ | $120.0000$ | $107.6922$ | $240.0000$ | $34.5028$ | $1$ ($0.3\%$) |
| `NaH2PO4` | $0.0000$ | $1.0000$ | $1.3445$ | $100.0000$ | $5.6421$ | $1$ ($0.3\%$) |
| `D-Glucose` | $0.0000$ | $5.6000$ | $5.7291$ | $56.0000$ | $2.8596$ | $1$ ($0.3\%$) |
| `FBS ` | $0.0010$ | $0.0500$ | $0.0622$ | $0.1000$ | $0.0389$ | $0$ ($0.0\%$) |
| **`mean_A450` (Target)** | **$0.0000$** | **$0.6127$** | **$0.7557$** | **$2.9077$** | **$0.5898$** | **$4$ ($1.3\%$)** |
| **`sd_A450` (Noise)** | **$0.0000$** | **$0.0604$** | **$0.0944$** | **$0.5941$** | **$0.0968$** | **$4$ ($1.3\%$)** |

---

### 4.2 Worksheet 2: `time-saving`

#### Data Types & Missing Values
- **Row Count:** $403$ rows
- **Column Count:** $34$ columns
- **Data Types:** $1$ $\text{int64}$ (`Unnamed: 0`), $33$ $\text{float64}$
- **Missing Values:** $0$ across all columns
- **Duplicates:** $0$ duplicate rows

#### Target Distributions Comparison (`time-saving` sheet)

| Target Variable | Description | Mean | Median | Min | Max | Std Dev | Skewness |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `mean_A450_96h` | Absorbance at 96 hours | $0.2671$ | $0.2413$ | $0.0000$ | $0.8297$ | $0.1524$ | $+0.7401$ |
| `mean_A450_168h` | Absorbance at 168 hours (7 days) | $0.6994$ | $0.5547$ | $0.0000$ | $2.9077$ | $0.5610$ | $+1.3819$ |
| `sd_A450_96h` | Standard deviation at 96 hours | $0.0342$ | $0.0240$ | $0.0009$ | $0.2879$ | $0.0347$ | $+2.9741$ |
| `sd_A450_168h` | Standard deviation at 168 hours | $0.0931$ | $0.0604$ | $0.0005$ | $0.5941$ | $0.0968$ | $+2.1752$ |

---

## 5. Correlation Analysis

Both Pearson ($r$, linear relationship) and Spearman ($\rho$, monotonic relationship) correlation coefficients were computed between the $30$ input features and candidate target variables.

### 5.1 Primary Growth Correlates (`mean_A450` / `mean_A450_168h`)

| Feature | Pearson $r$ (`regular`) | Spearman $\rho$ (`regular`) | Pearson $r$ (`168h`) | Spearman $\rho$ (`168h`) | Biological Interpretation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`NaCl`** | **$+0.3710$** | **$+0.4681$** | **$+0.3231$** | **$+0.4164$** | Strongest positive correlate. Ionic strength and osmolality regulation are critical for cell membrane stability. |
| **`CaCl2`** | $+0.0231$ | **$+0.3483$** | $+0.0192$ | **$+0.2939$** | High positive non-linear (Spearman) rank correlation; essential divalent cation for cell signaling and adhesion. |
| **`MgSO4`** | $+0.0231$ | **$+0.2496$** | $+0.0165$ | **$+0.1747$** | Positive non-linear rank correlation; required co-factor for ATP-dependent enzymes. |
| **`Folic Acid` / `Cystine`** | $+0.2071$ | $+0.1481$ | $+0.1844$ | $+0.1840$ | Direct growth promoters involved in DNA synthesis and reduction-oxidation balance. |
| **`FBS` (Serum)** | $+0.2035$ | $+0.1849$ | $+0.1697$ | $+0.0879$ | Growth factor source supporting proliferation. |
| **`L-Glutamine`** | **$-0.2321$** | **$-0.2457$** | **$-0.2428$** | **$-0.2536$** | Strongest negative correlate. Excess glutamine degrades into toxic ammonia in culture media over time. |
| **`L-Tyrosine`** | **$-0.2335$** | $-0.1229$ | **$-0.1870$** | $-0.0384$ | Negative linear correlation; potential solubility limits or amino acid toxicity at elevated doses. |
| **`L-Leucine` / `L-Isoleucine`** | $-0.2212$ | $-0.1272$ | $-0.1889$ | $-0.1396$ | Negative correlation when overdosed beyond physiological optimal ratios. |

### 5.2 Kinetic Comparison (96h vs 168h Targets)

- **`mean_A450_96h`:** Showed lower overall correlation magnitudes ($r_{\text{max}} = +0.3585$ for `NaCl`) due to early logarithmic growth phase variance.
- **`mean_A450_168h`:** Demonstrated stronger monotonic rank correlations ($\rho_{\text{max}} = +0.4164$ for `NaCl`, $+0.2939$ for `CaCl2`) as differences in culture saturation and longevity become fully expressed by day 7.

---

## 6. Target Variable Recommendation

### **Recommended Target Variable:** `mean_A450_168h` (or `mean_A450` for single-timepoint models)

### **Rationale:**
1. **Biological Purpose:** The primary goal of culture medium optimization is to maximize peak biomass accumulation and cell density. $A_{450}$ at 168 hours ($7$ days) represents the stationary-phase cell density, capturing total cell yield.
2. **Signal-to-Noise Ratio & Dynamic Range:**
   - `mean_A450_168h` exhibits a broad dynamic range ($0.0000$ to $2.9077$, mean $0.6994$, std $0.5610$).
   - In contrast, `mean_A450_96h` has a restricted range ($0.0000$ to $0.8297$, mean $0.2671$, std $0.1524$), making it harder for ML algorithms to distinguish high-yield formulations.
3. **Exclusion of Standard Deviation Targets (`sd_A450`):** `sd_A450` measures inter-replicate experimental variance rather than biological yield. It should not be used as an optimization target, but may be used during model evaluation as sample weights ($1 / \text{sd}^2$).

---

## 7. Recommendations for Data Preprocessing (Phase 4 Preparation)

Before training machine learning models (e.g., XGBoost, LightGBM, Random Forest, PyTorch Neural Nets) in Phase 4, the following preprocessing steps are strongly recommended:

1. **Feature Name Harmonization:**
   - Standardize column names between `regular` and `time-saving` datasets (e.g., strip trailing whitespace, convert names to a unified format like `L-Arginine_hydrochloride` or `Arginine`).
2. **Index Identifier Removal:**
   - Drop `Unnamed: 0` from feature matrices. It represents experimental row order and shows spurious negative correlations ($r \approx -0.24$) due to batch ordering.
3. **Feature Feature Scaling:**
   - Component concentrations span multiple orders of magnitude (from $0.0003 \text{ mM}$ for Riboflavin to $240 \text{ mM}$ for $\text{NaCl}$).
   - Apply `RobustScaler` or `StandardScaler` to prevent high-magnitude features from dominating distance-based models or gradient updates.
4. **Target Transformation:**
   - `mean_A450_168h` exhibits moderate right skewness ($+1.38$). Applying $\log1p(y)$ or Box-Cox transformation prior to training regression models (especially linear or neural network architectures) can stabilize residual variance.
5. **Handling Zero-Concentration Features:**
   - Certain components (e.g., $\text{MgSO}_4$, Thiamine, Pyridoxal) contain $14\%$ to $22\%$ zero values representing omission experiments. Tree-based models (XGBoost/LightGBM) natively handle zero values, but dense neural networks will benefit from explicit binary indicator flags (`is_omitted`).

---

## 8. Conclusion & Next Steps

This exploratory data analysis establishes that the dataset is **clean, complete ($0\%$ missing values), and structurally sound ($0\%$ duplicates)**. The target variable **`mean_A450_168h`** (or `mean_A450`) provides the optimal balance of dynamic range and biological relevance for training AI Culture Optimizer algorithms.

The next milestone for Phase 4 will be implementing the data preprocessing pipeline and training predictive regression models to discover optimal culture media formulations.
