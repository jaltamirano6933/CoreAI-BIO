# Cell Morphology Module — Documentation

**Module:** CoreAI BIO — Cell Morphology Analyzer  
**Backend Component:** `backend/morphology_service.py`  
**Frontend View:** `/morphology` ([frontend/templates/morphology.html](file:///C:/Users/Altam/OneDrive/Desktop/CoreAI%20BIO/frontend/templates/morphology.html))  
**Date:** July 2026  

---

## 1. Overview

The **Cell Morphology Analyzer** provides automated computer-vision processing for cellular microscopy images (PNG, JPG, JPEG, TIFF). It analyzes image quality metrics, extracts segmented cell contour boundaries, calculates morphometric feature descriptors, and classifies overall cellular state using a transparent rule-based classifier.

---

## 2. Image Processing & Quality Diagnostics

```text
[ Input Image (PNG / JPG / TIFF) ]
               │
               ▼
[ Conversion: BGR -> RGB & Grayscale ]
               │
               ├──► Brightness: mean(I_gray)
               ├──► Contrast: std(I_gray)
               ├──► Sharpness: Var(Laplacian(I_gray))
               └──► Noise Estimate: std(I_gray - MedianBlur(I_gray))
```

### Metrics & Formulas
1. **Brightness:** $\mu = \frac{1}{W \cdot H} \sum_{x,y} I(x,y) \in [0, 255]$
2. **Contrast:** $\sigma = \sqrt{\frac{1}{W \cdot H} \sum_{x,y} (I(x,y) - \mu)^2}$
3. **Sharpness:** $\text{Var}(\nabla^2 I) = \text{Var}\left( \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2} \right)$
4. **Noise Estimate:** $\sigma_{\text{residual}} = \text{std}\left( I - \text{MedianBlur}(I, k=3) \right)$

---

## 3. Cell Segmentation & Morphometric Measurements

```text
[ Grayscale Image ]
        │
        ▼ (Gaussian Blur, k=5)
[ Otsu Thresholding -> Binary Matrix ]
        │
        ▼ (Morphological Closing, Ellipse Kernel 3x3)
[ Find Contours: cv2.findContours ]
        │
        ▼ (Filter Noise Speckles: Area >= 50 px²)
[ Extract Individual & Summary Morphometric Features ]
```

### Morphometric Feature Definitions
* **Cell Area ($A$):** Polygon area enclosed by contour boundary ($\text{px}^2$).
* **Cell Perimeter ($P$):** Total arc length of closed contour ($\text{px}$).
* **Circularity ($C$):** Isoperimetric quotient quantifying boundary roundness:
  $$C = \frac{4 \pi \cdot A}{P^2} \in (0, 1.0]$$
* **Aspect Ratio ($AR$):** Ratio of bounding rectangle width to height ($W / H$).
* **Solidity ($S$):** Ratio of cell area to its convex hull area:
  $$S = \frac{A}{A_{\text{ConvexHull}}} \in (0, 1.0]$$

---

## 4. Rule-Based Classification Logic

The module implements a deterministic rule-based classifier evaluating morphometric shape uniformity and image quality:

| Category | Rules & Thresholds | Confidence | Interpretation |
| :--- | :--- | :---: | :--- |
| **Low Quality Image** | $\text{Sharpness} < 25.0$ OR $\text{Contrast} < 10.0$ | `Low` | Image blur or insufficient contrast prevents reliable segmentation. |
| **Healthy** | $\bar{C} \ge 0.75$ AND $\bar{S} \ge 0.85$ AND $N_{\text{cells}} \ge 3$ | `High` | High circularity and smooth convex cell boundaries. |
| **Differentiating** | $0.50 \le \bar{C} < 0.75$ OR $1.3 \le \overline{AR} \le 2.2$ | `Medium` | Elongated cell processes indicative of lineage differentiation. |
| **Irregular** | $\bar{C} < 0.50$ OR $\bar{S} < 0.70$ OR $\overline{AR} > 2.2$ | `Medium` | Distorted cell boundaries or irregular membrane protrusions. |

---

## 5. API Reference

| Endpoint | Method | Input | Response Payload | Status |
| :--- | :---: | :--- | :--- | :---: |
| `/api/morphology/summary` | `GET` | None | Default / current sample morphology analysis | `200 OK` |
| `/api/morphology/analyze` | `POST` | `multipart/form-data` (`image`) | Dimensions, quality diagnostics, cell measurements, classification, figures | `200 OK` |

---

## 6. Generated Visualizations (`static/results/morphology/`)

1. **`original_image.png`**: Original input microscopy image.
2. **`grayscale_image.png`**: Grayscale intensity conversion.
3. **`binary_threshold.png`**: Otsu binary thresholding after morphological closing.
4. **`cell_contour_overlay.png`**: RGB image overlay with green cell boundaries and yellow cell IDs (`#1`, `#2`, ...).

---

## 7. Scientific & Clinical Limitation Notice

> ⚠️ **Scientific Notice:** This module provides exploratory morphology measurements for research purposes only. It is not intended for clinical diagnosis. Deep learning neural networks (CNNs, U-Nets, YOLO) were intentionally omitted per design specifications.
