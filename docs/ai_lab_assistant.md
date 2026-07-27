# AI Laboratory Assistant — Documentation

**Module:** CoreAI BIO — AI Laboratory Assistant  
**Backend Component:** `backend/assistant_service.py`  
**Frontend View:** `/assistant` ([frontend/templates/assistant.html](file:///C:/Users/Altam/OneDrive/Desktop/CoreAI%20BIO/frontend/templates/assistant.html))  
**Date:** July 2026  

---

## 1. Architecture & Intent Routing Engine

The **AI Laboratory Assistant** functions as an integrated research knowledge engine across the CoreAI BIO stem cell platform.

```text
[ User Query (Web Chat / API) ]
              │
              ▼
[ Safety & Compliance Filter ] ──(Medical/Treatment Detected)──► [ Medical Safety Disclaimer Notice ]
              │
              ▼ (Scientific Research Topic Match)
[ Module Intent Routing Engine ]
              ├──► Cell Fate Analyzer (Volcano plots, DGE, Pathways, PCA, UMAP)
              ├──► Cell Morphology (Circularity, Aspect Ratio, Solidity, Contour overlay)
              ├──► Culture Optimizer (Confluency, Density, Incubator, Rules)
              ├──► NIH S-Index (FAIR Data reproducibility scores)
              └──► Generic / Out-of-Scope (Data Limitation & Validation Notice)
```

---

## 2. Supported CoreAI BIO Modules

1. **NIH S-Index Dashboard:** FAIR data evaluation, repository provenance, metadata completeness.
2. **Culture Optimizer:** Cell density, confluency ($85\%$), passage rules ($P4$), incubator telemetry ($37.0^\circ\text{C}, 5.0\% \text{ CO}_2$).
3. **Cell Morphology:** Contour extraction, circularity ($C = 4\pi A / P^2$), aspect ratio, solidity, Otsu thresholding.
4. **Cell Fate Analyzer:**
   * **Exploratory Analysis:** 2D PCA, sample correlation heatmaps, top 50 variable gene annotations.
   * **Differential Expression (DGE):** Log2 Fold Change ($\text{log2FC}$), Welch's t-test, BH FDR correction, Volcano plots.
   * **Pathway Analysis:** Fisher's Exact Test ORA over GO:BP ($18,450$), GO:CC ($19,200$), KEGG ($8,120$), Reactome ($11,400$).
   * **Machine Learning Preview:** 2D UMAP projection, K-Means ($K=2$) clustering, sample size limitations ($N=6$).

---

## 3. Safety Rules & Compliance Safeguards

* **No Clinical Medical Diagnosis:** Requests for medical diagnosis or patient treatment are intercepted and answered with an explicit safety notice.
* **No Result Fabrication:** Explanations rely strictly on verified platform outputs and scientific literature definitions.
* **Evidence Insufficiency Statements:** When queries exceed platform data, the engine explicitly indicates that available evidence is insufficient and additional experimental validation is required.

---

## 4. API Reference

| Endpoint | Method | Input Payload | Response Payload | Status |
| :--- | :---: | :--- | :--- | :---: |
| `/api/assistant/chat` | `POST` | `{"query": "What does a volcano plot mean?"}` | Topic, module tag, scientific explanation response, follow-up suggestions, disclaimer | `200 OK` |

---

## 5. Example Supported Questions

* *"What does this volcano plot mean?"*
* *"Explain this pathway."*
* *"What is Circularity?"*
* *"Why is this culture classified as Near Confluent?"*
* *"What is PCA?"*
* *"What does UMAP show?"*
* *"Explain the Differential Expression results."*
* *"What is NIH S-Index?"*
* *"Can you prescribe treatment for a patient?"* (Triggers Safety Disclaimer)

---

## 6. Scientific & Clinical Limitation Notice

> ℹ️ **Scientific Notice:** This assistant provides educational and research-oriented explanations only. It does not replace scientific review or clinical judgment.
