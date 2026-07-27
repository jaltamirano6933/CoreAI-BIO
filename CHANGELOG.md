# Changelog

All notable changes to **CoreAI BIO** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-26

### Added
- **Stem Cell Colony Morphometry**: Dedicated primary validated workflow for analyzing human iPSC/ESC stem cell colonies, computing colony coverage %, density, circularity, border irregularity, compactness, and size distributions.
- **Generic Tissue Morphometry**: Standardized computer vision pipeline for automated boundary segmentation and morphometric feature extraction across circular microscope fields of view.
- **Status & Confidence Separation**: Independent reporting of Technical Pipeline Status (🟢 `Completed`) vs. Scientific Interpretation Confidence (🟡 `Low` / 🟢 `High`).
- **Image Quality Diagnostics**: Quantitative measurement of Laplacian focus variance, intensity contrast, brightness, noise estimation, and contour rejection ratios.
- **AI Laboratory Integration**: Central Interpretation Workspace accepting multi-module experiment sessions from Cell Morphology, Research Culture Optimizer, Cell Fate Analyzer, and FAIR S-Index modules.
- **Multi-Format Export Service**: One-click generation of PDF summary reports, CSV per-region datasets, JSON session archives, and Markdown research walkthroughs.
- **FAIR Data Sharing Index (S-Index)**: NIH/FAIR data governance audit engine with GEO XML/SOFT parser, metadata completeness auditing, and dynamic score calculation.
- **Cell Fate & DGE Analyzer**: Differential Gene Expression analysis pipeline with Volcanoplot visualizations, UMAP clustering, and biomarker candidate ranking.
- **Research Culture Optimizer**: Bayesian culture media parameter optimization with SHAP feature importance interpretation and yield prediction.
- **Automated Test Suite**: 89 automated unit tests verifying core algorithms, API contracts, image processing pipelines, and data serialization.

---

## [0.1.0-alpha] - Initial Prototype
- Basic morphology pipeline prototype with single threshold segmentation.
- Initial Flask web app shell.
