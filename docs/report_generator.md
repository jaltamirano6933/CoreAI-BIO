# Research Report Generator — Documentation

**Module:** CoreAI BIO — Research Report Generator  
**Backend Component:** `backend/report_service.py`  
**Frontend View:** `/report` ([frontend/templates/report.html](file:///C:/Users/Altam/OneDrive/Desktop/CoreAI%20BIO/frontend/templates/report.html))  
**Date:** July 2026  

---

## 1. Overview

The **Research Report Generator** provides a one-click automated synthesis engine combining analytical outputs from all five CoreAI BIO platform modules into a unified, publication-ready research report.

---

## 2. Combined Module Integration Pipeline

```text
[ CoreAI BIO Modules ]
       │
       ├──► Cell Morphology (Contour Overlay, Cell Count, Circularity, Sharpness)
       ├──► Culture Optimizer (Culture Score, Confluency 85%, Incubator Telemetry, Rules)
       ├──► Cell Fate Analyzer (2D PCA, Volcano Plot, Heatmap, UMAP, DGE, ORA Pathways)
       ├──► AI Laboratory Assistant (5-Paragraph Scientific Synthesis)
       └──► Metadata (Timestamp, Sample Name, System Version)
               │
               ▼
[ Report Service Aggregator: backend/report_service.py ]
               │
               ├──► Interactive HTML Report (/report)
               ├──► Export Self-Contained HTML (.html)
               └──► Export / Print PDF (window.print())
```

---

## 3. Report Sections & Contents

1. **Header & Provenance:** System version (`CoreAI BIO v1.0`), Date/Time UTC, Sample Name (`GSE290316 / Hypothalamic Organoids`), Project Name.
2. **Cell Morphology Summary:** Original microscopy image, contour segmentation overlay (`cell_contour_overlay.png`), cell count ($12$), circularity ($0.8944$), aspect ratio ($1.0204$), solidity ($0.9885$), classification (`Healthy`), sharpness ($1104.79$).
3. **Culture Optimizer Summary:** Overall Culture Score ($88/100$), Growth Status (`Exponential Growth`), Risk Level (`Low`), density trend chart (`density_over_time.png`), confluency trend chart (`confluency_over_time.png`), deterministic recommendations.
4. **Cell Fate Multi-Omics Summary:** 4-Grid Diagnostic Plots (2D PCA, Volcano Plot, Heatmap, 2D UMAP), DGE counts ($98$ FDR significant, $85$ DE, $34$ up, $51$ down), top enriched GO/KEGG pathways.
5. **AI Assistant Scientific Synthesis:** Concise 5-paragraph synthesis integrating morphology, culture status, transcriptomic findings, biological pathways, and ML preview, strictly utilizing existing platform outputs.
6. **Scientific Limitations Notice:** Explaining that results are for research purposes only, require experimental validation, and are not intended for clinical medical diagnosis.

---

## 4. API Reference

| Endpoint | Method | Response Payload | Status |
| :--- | :---: | :--- | :---: |
| `/api/report/data` | `GET` | Aggregated JSON report data from all modules + AI Assistant synthesis | `200 OK` |
| `/report` | `GET` | HTML rendered report dashboard view | `200 OK` |

---

## 5. Export Instructions

* **Export HTML:** Click `"Export HTML Report"` on the `/report` toolbar to download a self-contained `.html` report file.
* **Export PDF:** Click `"Print / Export PDF"` or press `Ctrl + P` in your browser, selecting `"Save as PDF"` as the destination printer.
