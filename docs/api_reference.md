# CoreAI BIO — API Reference Specification

**System Version:** CoreAI BIO v1.0.0  
**Protocol:** HTTP / REST  
**Base URL:** `http://127.0.0.1:5000`  
**Content-Type:** `application/json` (for API requests)  

---

## Overview

The CoreAI BIO platform exposes web view routes and asynchronous RESTful API endpoints for genomic repository data auditing (NIH S-Index) and predictive culture medium optimization (AI Culture Optimizer with SHAP explainability).

---

## 1. NIH S-Index Module Endpoints

### 1.1 `GET /nih-sindex`
Renders the interactive **NIH S-Index Audit Dashboard** displaying dataset metadata, repository counts, FAIR metrics, and S-index distributions.

- **Method:** `GET`
- **Query Parameters:** None
- **Response:** `200 OK` (`text/html`)
- **Headers:** `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`

---

### 1.2 `POST /api/nih-sindex/audit`
Triggers an asynchronous live audit for an NCBI Gene Expression Omnibus (GEO) accession number (e.g. `GSE163148`, `GSE214617`, `GSE290316`). Fetches MINiML XML / SOFT metadata from NCBI, updates the cache (`NIH S-index/cache/geo/<ACCESSION>.json`), recalculates FAIR vector scores, and returns updated platform statistics.

- **Method:** `POST`
- **Headers:** `Content-Type: application/x-www-form-urlencoded` or `application/json`
- **Request Body:**
  ```json
  {
    "accession": "GSE163148"
  }
  ```

- **Success Response (`200 OK`):**
  ```json
  {
    "status": "success",
    "accession": "GSE163148",
    "message": "Dataset GSE163148 successfully fetched, evaluated, and cached.",
    "dataset": {
      "id": "GSE163148",
      "title": "High-throughput sequencing of human cardiac tissue",
      "repository": "GEO",
      "organism": "Homo sapiens",
      "samples": 24,
      "fair_score": 92.5,
      "s_index": 88.4,
      "provenance": "NCBI GEO API (Live Fetch)",
      "fair_breakdown": {
        "findable": 100.0,
        "accessible": 90.0,
        "interoperable": 90.0,
        "reusable": 90.0
      }
    },
    "summary": {
      "total_datasets": 4,
      "num_repositories": 1,
      "avg_fair": 91.2,
      "avg_sindex": 86.8
    }
  }
  ```

- **Error Codes & Responses:**
  - `400 Bad Request` — Missing or invalid accession format (must start with `GSE`).
    ```json
    {
      "status": "error",
      "message": "Invalid accession format. Please provide a valid GEO accession starting with 'GSE' (e.g., GSE163148)."
    }
    ```
  - `404 Not Found` — Accession not found on NCBI GEO servers.
  - `500 Internal Server Error` — Network failure or XML parsing error.

---

## 2. AI Culture Optimizer Endpoints

### 2.1 `GET /culture`
Renders the interactive **AI Culture Optimizer** input form, media component preset loaders, real-time prediction cards, and SHAP explainability driver panels.

- **Method:** `GET`
- **Query Parameters:** None
- **Response:** `200 OK` (`text/html`)

---

### 2.2 `POST /api/culture/predict`
Runs Machine Learning model inference (`RandomForestRegressor` baseline / `ExtraTreesRegressor` experimental) to predict cell growth absorbance ($A_{450}$ at 168 hours) from 29 culture medium components. Simultaneously computes local SHAP feature attributions.

- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Request Body Example:**
  ```json
  {
    "Arginine": 0.6,
    "Glutamine": 2.0,
    "Histidine": 0.2,
    "Isoleucine": 0.4,
    "Leucine": 0.4,
    "Lysine": 0.4,
    "Methionine": 0.1,
    "Phenylalanine": 0.2,
    "Threonine": 0.4,
    "Tryptophane": 0.05,
    "Tyrosine": 0.2,
    "Valine": 0.4,
    "Cystine": 0.1,
    "Choline": 0.007,
    "Calcium pantothenate": 0.002,
    "Folic acid": 0.002,
    "Niacinamide": 0.008,
    "Pyridoxal": 0.005,
    "Riboflavin": 0.0003,
    "Thiamine": 0.003,
    "Inositol": 0.01,
    "CaCl2": 1.8,
    "MgSO4": 0.8,
    "KCl": 5.5,
    "NaHCO3": 26.0,
    "NaCl": 120.0,
    "NaH2PO4": 1.0,
    "Glucose": 5.6,
    "FBS": 0.05
  }
  ```

- **Success Response (`200 OK`):**
  ```json
  {
    "base_value": 0.6907,
    "growth_category": "Optimal High Biomass Yield",
    "model_name": "RandomForestRegressor",
    "num_features_used": 29,
    "predicted_mean_A450_168h": 1.0686,
    "prediction_status": "success",
    "rating_badge": "Good",
    "timestamp": "2026-07-22 03:24:04 UTC",
    "top_positive_features": [
      { "feature": "Lysine", "impact": 0.1459 },
      { "feature": "NaCl", "impact": 0.0678 },
      { "feature": "Glutamine", "impact": 0.0358 }
    ],
    "top_negative_features": [
      { "feature": "Choline", "impact": -0.0670 },
      { "feature": "Calcium pantothenate", "impact": -0.0542 }
    ],
    "shap_values": {
      "Arginine": 0.0355,
      "Glutamine": 0.0358,
      "Glucose": 0.0168,
      "FBS": 0.0247
    },
    "prediction_explanation": {
      "top_positive_features": [ ... ],
      "top_negative_features": [ ... ]
    }
  }
  ```

- **Error Codes & Responses:**
  - `400 Bad Request` — Non-numeric values or negative concentration inputs.
    ```json
    {
      "error": "Input validation failed",
      "prediction_status": "invalid_input",
      "timestamp": "2026-07-22 04:00:00 UTC",
      "validation_details": [
        "Component concentration for 'Glucose' cannot be negative."
      ]
    }
    ```
  - `500 Internal Server Error` — Model binary loading error or inference crash.

---

## 3. Core Application View Routes

| Route | Method | Description | Content-Type | Status |
| :--- | :---: | :--- | :---: | :---: |
| `/` | `GET` | Main Platform Overview & Navigation Hub | `text/html` | Active |
| `/nih-sindex` | `GET` | NIH S-Index Data Audit Interface | `text/html` | Active |
| `/culture` | `GET` | AI Culture Optimizer & SHAP Interface | `text/html` | Active |
| `/fate` | `GET` | Cell Fate Analyzer Module | `text/html` | Placeholder (Phase 5) |
| `/morphology` | `GET` | Cell Morphology Analyzer Module | `text/html` | Placeholder (Phase 6) |
| `/assistant` | `GET` | AI Bio-Assistant Chat Interface | `text/html` | Placeholder |
