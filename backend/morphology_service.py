import os
import sys
import uuid
import time
import hashlib
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

class MorphologyService:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.root_dir = os.path.dirname(self.base_dir)
        self.static_dirs = [
            os.path.join(self.root_dir, "static", "results", "morphology"),
            os.path.join(self.root_dir, "frontend", "static", "results", "morphology")
        ]
        self.upload_dirs = [
            os.path.join(self.root_dir, "static", "uploads", "morphology"),
            os.path.join(self.root_dir, "frontend", "static", "uploads", "morphology")
        ]
        for d in self.static_dirs + self.upload_dirs:
            os.makedirs(d, exist_ok=True)
            
        self.current_analysis = None
        self._initialize_default_sample()

    def _initialize_default_sample(self):
        # Synthetic microscopy sample image with 12 discrete cells
        height, width = 512, 512
        img = np.ones((height, width, 3), dtype=np.uint8) * 20  # Dark background
        
        noise = np.random.normal(0, 5, (height, width, 3)).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        cell_centers = [
            (90, 100, 35, 30), (220, 90, 42, 38), (380, 110, 30, 32),
            (110, 250, 40, 35), (260, 240, 36, 40), (410, 260, 38, 36),
            (80, 410, 34, 34), (230, 390, 45, 40), (390, 420, 32, 35),
            (180, 170, 30, 35), (320, 330, 38, 34), (290, 460, 28, 30)
        ]

        for cx, cy, rx, ry in cell_centers:
            cv2.ellipse(img, (cx, cy), (rx, ry), angle=0, startAngle=0, endAngle=360, color=(40, 160, 80), thickness=-1)
            cv2.ellipse(img, (cx, cy), (rx, ry), angle=0, startAngle=0, endAngle=360, color=(60, 210, 110), thickness=2)
            cv2.ellipse(img, (cx, cy), (int(rx*0.4), int(ry*0.4)), angle=0, startAngle=0, endAngle=360, color=(200, 100, 30), thickness=-1)

        sample_path = os.path.join(self.static_dirs[0], "default_microscopy_sample.png")
        cv2.imwrite(sample_path, img)
        self.analyze_image_bytes(cv2.imencode('.png', img)[1].tobytes(), filename="sample_microscopy.png")

    def _detect_microscope_fov(self, img_gray):
        """
        Detects circular field-of-view (FOV) eyepiece vignette or uses a conservative centered-circle fallback.
        Reduces detected radius by 12.5% (10-15%) to remove the entire eyepiece ring and border artifacts.
        """
        height, width = img_gray.shape
        min_dim = min(height, width)
        
        blur = cv2.GaussianBlur(img_gray, (9, 9), 0)
        _, thresh = cv2.threshold(blur, 15, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fov_circle = None
        if contours:
            largest_cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_cnt)
            if area > (0.15 * width * height):
                (cx, cy), r = cv2.minEnclosingCircle(largest_cnt)
                if r >= (0.20 * min_dim):
                    fov_circle = (int(cx), int(cy), int(r))

        # Conservative centered-circle fallback if detection is uncertain
        if fov_circle is None:
            cx, cy = width // 2, height // 2
            r = int(min_dim * 0.44)
            fov_circle = (cx, cy, r)

        cx, cy, r = fov_circle
        fov_mask = np.zeros((height, width), dtype=np.uint8)
        safe_fov_mask = np.zeros((height, width), dtype=np.uint8)

        # Full circular FOV mask
        cv2.circle(fov_mask, (cx, cy), int(r), 255, -1)
        
        # Safe inner FOV mask (radius reduced by 12.5% to remove eyepiece ring entirely)
        safe_r = max(10, int(r * 0.875))
        cv2.circle(safe_fov_mask, (cx, cy), safe_r, 255, -1)

        return fov_mask, (cx, cy, r), safe_fov_mask

    def _create_background_subtracted_mask(self, img_rgb, blurred, safe_fov_mask):
        """
        Illumination normalization inside safe FOV, CLAHE, Otsu vs Adaptive Gaussian evaluation,
        mask selection minimizing border touch & oversized regions, and morphological filtering.
        """
        height, width = blurred.shape
        
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        norm_bgr = cv2.normalize(img_bgr, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        norm_gray = cv2.cvtColor(norm_bgr, cv2.COLOR_BGR2GRAY)
        
        bg_est = cv2.GaussianBlur(norm_gray, (51, 51), 0)
        subtracted = cv2.absdiff(norm_gray, bg_est)
        
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(subtracted)
        enhanced = cv2.bitwise_and(enhanced, enhanced, mask=safe_fov_mask)
        
        smooth = cv2.GaussianBlur(enhanced, (5, 5), 0)
        
        # Compare Otsu and Adaptive Gaussian thresholding
        _, otsu_mask = cv2.threshold(smooth, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adapt_mask = cv2.adaptiveThreshold(
            smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 25, 3
        )
        
        otsu_mask = cv2.bitwise_and(otsu_mask, otsu_mask, mask=safe_fov_mask)
        adapt_mask = cv2.bitwise_and(adapt_mask, adapt_mask, mask=safe_fov_mask)

        # Choose mask with lowest border contact & lowest oversized region ratio
        def evaluate_mask_quality(mask):
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            safe_area = float(np.sum(safe_fov_mask > 0))
            oversized_count = 0
            border_touch_count = 0
            for c in cnts:
                c_area = cv2.contourArea(c)
                if c_area > (0.30 * safe_area):
                    oversized_count += 1
                for px, py in c.reshape(-1, 2):
                    if safe_fov_mask[py, px] == 0:
                        border_touch_count += 1
                        break
            return oversized_count, border_touch_count

        otsu_over, otsu_touch = evaluate_mask_quality(otsu_mask)
        adapt_over, adapt_touch = evaluate_mask_quality(adapt_mask)

        if (otsu_over + otsu_touch) <= (adapt_over + adapt_touch):
            binary_raw = otsu_mask
        else:
            binary_raw = adapt_mask
            
        binary_raw = cv2.bitwise_and(binary_raw, binary_raw, mask=safe_fov_mask)
        
        # Morphological opening (remove small noise) and closing (reconnect internal boundaries)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        opened = cv2.morphologyEx(binary_raw, cv2.MORPH_OPEN, kernel_open, iterations=1)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close, iterations=1)
        closed = cv2.bitwise_and(closed, closed, mask=safe_fov_mask)
        
        return closed

    def analyze_image_bytes(self, image_bytes, filename="uploaded_image.png", sample_type="generic", um_per_pixel=None, calibration_source=None, microscope_objective=None, image_source=None):
        sample_type_norm = str(sample_type).lower().strip()
        
        profile_map = {
            "stem_cell": "stem_cell",
            "stem_cells": "stem_cell",
            "ipsc": "stem_cell",
            "esc": "stem_cell",
            "ipsc_pluripotency": "stem_cell",
            "generic": "generic",
            "adipose": "adipose",
            "muscle": "skeletal_muscle",
            "skeletal_muscle": "skeletal_muscle",
            "thyroid": "thyroid",
            "pancreas": "pancreas",
            "spinal_cord": "spinal_cord",
            "myocardium": "myocardium",
            "testis": "testis",
            "ovary": "ovary"
        }
        profile_name = profile_map.get(sample_type_norm, "stem_cell")

        parsed_um_per_pixel = None
        if um_per_pixel is not None:
            try:
                val = float(um_per_pixel)
                if val > 0:
                    parsed_um_per_pixel = val
            except (ValueError, TypeError):
                parsed_um_per_pixel = None

        is_calibrated = (parsed_um_per_pixel is not None)
        calib_source_str = str(calibration_source).strip() if calibration_source else ("Manual Input" if is_calibrated else "Uncalibrated")
        objective_str = str(microscope_objective).strip() if microscope_objective else "Unspecified"
        img_source_str = str(image_source).strip() if image_source else "Unknown"
        if img_source_str not in ["Real microscopy image", "Synthetic test image", "Prepared slide image", "Unknown"]:
            img_source_str = "Unknown"

        # Structure label mapping - Stem Cell & Generic are Primary Validated Profiles
        structure_label_map = {
            "stem_cell": "Stem Cell Colony Regions",
            "generic": "Segmented Morphological Regions",
            "adipose": "Segmented Morphological Regions (Experimental)",
            "skeletal_muscle": "Segmented Morphological Regions (Experimental)",
            "thyroid": "Segmented Morphological Regions (Experimental)",
            "pancreas": "Segmented Morphological Regions (Experimental)",
            "spinal_cord": "Segmented Morphological Regions (Experimental)",
            "myocardium": "Segmented Morphological Regions (Experimental)",
            "testis": "Segmented Morphological Regions (Experimental)",
            "ovary": "Segmented Morphological Regions (Experimental)"
        }
        structure_label = structure_label_map.get(profile_name, "Stem Cell Colony Regions")

        profile_status_map = {
            "stem_cell": "Validated (Primary Workflow)",
            "generic": "Validated (Primary Workflow)",
            "adipose": "Experimental Pipeline",
            "skeletal_muscle": "Experimental Pipeline",
            "thyroid": "Experimental Pipeline",
            "pancreas": "Experimental Pipeline",
            "spinal_cord": "Experimental Pipeline",
            "myocardium": "Experimental Pipeline",
            "testis": "Experimental Pipeline",
            "ovary": "Experimental Pipeline"
        }
        profile_status = profile_status_map.get(profile_name, "Validated (Primary Workflow)")

        sha256_hash = hashlib.sha256(image_bytes).hexdigest()

        ext = os.path.splitext(filename)[1]
        if not ext or len(ext) > 5:
            ext = ".png"
        saved_filename = f"upload_{uuid.uuid4().hex[:8]}_{int(time.time())}{ext}"
        abs_file_path = os.path.abspath(os.path.join(self.upload_dirs[0], saved_filename))

        for u_dir in self.upload_dirs:
            p = os.path.join(u_dir, saved_filename)
            with open(p, "wb") as f:
                f.write(image_bytes)

        img_bgr = cv2.imread(abs_file_path, cv2.IMREAD_COLOR)
        if img_bgr is None:
            try:
                nparr = np.frombuffer(image_bytes, np.uint8)
                img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                raise ValueError(f"Unsupported or corrupted image file: {e}")
        if img_bgr is None:
            raise ValueError("Unsupported or corrupted image file: Failed to decode image format.")

        height, width, channels = img_bgr.shape
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 4. Shared Preprocessing & Safe FOV Detection
        fov_mask, fov_circle, safe_fov_mask = self._detect_microscope_fov(img_gray)
        fov_area = float(np.sum(fov_mask > 0))

        valid_pixels = img_gray[safe_fov_mask > 0]
        brightness = float(np.mean(valid_pixels)) if len(valid_pixels) > 0 else float(np.mean(img_gray))
        contrast = float(np.std(valid_pixels)) if len(valid_pixels) > 0 else float(np.std(img_gray))
        
        laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
        sharpness = float(laplacian[safe_fov_mask > 0].var()) if np.sum(safe_fov_mask > 0) > 100 else float(laplacian.var())
        
        blur_gray = cv2.medianBlur(img_gray, 3)
        residual = img_gray.astype(np.float64) - blur_gray.astype(np.float64)
        noise = float(np.std(residual[safe_fov_mask > 0])) if np.sum(safe_fov_mask > 0) > 100 else float(np.std(residual))
        fov_coverage_pct = round(float(fov_area / (width * height)) * 100, 2)

        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(img_gray)
        blurred = cv2.GaussianBlur(enhanced_gray, (5, 5), 0)

        # 5. Dispatch to Primary Validated (Stem Cell / Generic) or Experimental Profile
        if profile_name == "stem_cell" or profile_name == "ipsc":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_stem_cell(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "adipose":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_adipose(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "skeletal_muscle":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_skeletal_muscle(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "thyroid":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_thyroid(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "pancreas":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_pancreas(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "spinal_cord":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_spinal_cord(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "myocardium":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_myocardium(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "testis":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_testis(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        elif profile_name == "ovary":
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_ovary(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )
        else:  # generic validated v1
            binary_mask, cell_metrics, contour_overlay, diag_meta, extra_meta = self._profile_generic(
                img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height
            )

        cell_count = len(cell_metrics)
        if cell_count > 0:
            mean_area = float(np.mean([m["area"] for m in cell_metrics]))
            mean_perimeter = float(np.mean([m["perimeter"] for m in cell_metrics]))
            mean_circularity = float(np.mean([m["circularity"] for m in cell_metrics]))
            mean_aspect_ratio = float(np.mean([m["aspect_ratio"] for m in cell_metrics]))
            mean_solidity = float(np.mean([m["solidity"] for m in cell_metrics]))
        else:
            mean_area, mean_perimeter, mean_circularity, mean_aspect_ratio, mean_solidity = 0.0, 0.0, 0.0, 0.0, 0.0

        # Explicit Quality Checks & Failure Reason Construction
        raw_count = diag_meta.get("raw_contour_count", 0)
        accepted_count = diag_meta.get("accepted_contour_count", 0)
        rejected_count = diag_meta.get("rejected_contour_count", 0)
        rel_candidate_area = diag_meta.get("relative_candidate_area_pct", 0.0)

        failure_reasons = []
        detailed_failure_messages = []

        if sharpness < 15.0:
            failure_reasons.append("low_sharpness")
            detailed_failure_messages.append(f"Very low sharpness: {round(sharpness, 2)}")
        if contrast < 10.0:
            failure_reasons.append("low_contrast")
            detailed_failure_messages.append(f"Low contrast: {round(contrast, 2)}")
        if brightness < 15.0 or brightness > 245.0:
            failure_reasons.append("poor_illumination")
            detailed_failure_messages.append(f"Poor illumination: mean brightness {round(brightness, 2)}")
        if rel_candidate_area < 10.0:
            failure_reasons.append("low_candidate_coverage")
            detailed_failure_messages.append(f"Low relative candidate area: {round(rel_candidate_area, 2)}%")
        if rejected_count > accepted_count and raw_count > 10:
            failure_reasons.append("high_rejection_ratio")
            detailed_failure_messages.append(f"{rejected_count} of {raw_count} raw contours rejected")

        if profile_name == "adipose" and (sharpness < 20.0 or contrast < 12.0 or rel_candidate_area < 10.0):
            failure_reasons.append("indistinct_boundaries")
            detailed_failure_messages.append("Adipocyte boundaries are not sufficiently distinct")
        elif sharpness < 20.0 or contrast < 12.0:
            failure_reasons.append("indistinct_boundaries")
            detailed_failure_messages.append(f"{profile_name.capitalize()} boundaries are not sufficiently distinct")

        analysis_completed = True
        pipeline_status = "Completed"
        
        if len(failure_reasons) >= 2 or sharpness < 15.0 or contrast < 8.0:
            quality_status = "poor"
            classification_status = "inconclusive"
            interpretation_confidence = "Low"
            interpretation_status = "Exploratory — Low Quality"
            table_header_title = "Segmented Candidate Regions"
            classification_result = "Completed (Low Interpretation Confidence)"
            confidence = "Low"
            class_reason = f"The morphology pipeline completed successfully and segmented candidate regions. However, image quality did not satisfy recommended criteria for reliable {profile_name} biological interpretation."
        elif len(failure_reasons) == 1 or cell_count < 3 or rel_candidate_area < 0.50:
            quality_status = "moderate"
            classification_status = "conclusive"
            interpretation_confidence = "Moderate"
            interpretation_status = "Exploratory — Moderate Quality"
            table_header_title = "Segmented Individual Cell Measurements"
            classification_result = "Completed (Moderate Interpretation Confidence)"
            confidence = "Medium"
            class_reason = f"The morphology pipeline completed successfully and resolved {cell_count} candidate region(s) covering {rel_candidate_area}% of safe inner field of view."
        else:
            quality_status = "good"
            classification_status = "conclusive"
            interpretation_confidence = "High"
            interpretation_status = "Validated Quality"
            table_header_title = "Segmented Individual Cell Measurements"
            classification_result = "Completed"
            confidence = "High"
            class_reason = f"The morphology pipeline completed successfully and resolved {cell_count} candidate regions covering {rel_candidate_area}% of safe inner field of view."

        interpretation_notes = (
            "The morphology pipeline completed successfully. Candidate regions were segmented and quantitative morphometric measurements were generated. "
            "However, this image did not satisfy the recommended quality criteria for reliable biological interpretation. "
            "The reported measurements remain available as exploratory quantitative results and should not be interpreted as validated biological conclusions."
        ) if (interpretation_confidence == "Low") else (
            "The morphology pipeline completed successfully. Candidate regions were segmented and quantitative morphometric measurements are reported."
        )

        inconclusive_recommendations = [
            "Refocus the microscope to increase boundary sharpness and Laplacian variance",
            "Improve illumination and contrast to highlight membrane boundaries",
            "Avoid glare, shadows, and uneven shading across the field of view",
            "Capture clearly defined candidate cavities with sharp perimeter contrast",
            "Use a higher-resolution image for precise morphological segmentation"
        ]

        if is_calibrated:
            area_unit = "µm²"
            length_unit = "µm"
            mean_area_val = round(mean_area * (parsed_um_per_pixel ** 2), 2)
            mean_perimeter_val = round(mean_perimeter * parsed_um_per_pixel, 2)
            unit_notice = f"Measurements are calibrated and reported in µm and µm² ({parsed_um_per_pixel} µm/pixel via {calib_source_str})."
        else:
            area_unit = "px²"
            length_unit = "px"
            mean_area_val = round(mean_area, 2)
            mean_perimeter_val = round(mean_perimeter, 2)
            unit_notice = "Measurements are reported in pixels because this image is not spatially calibrated."

        calibrated_cell_metrics = []
        for m in cell_metrics:
            c_copy = dict(m)
            c_copy["area_px"] = round(m["area"], 2)
            c_copy["perimeter_px"] = round(m["perimeter"], 2)
            if is_calibrated:
                c_copy["area_um2"] = round(m["area"] * (parsed_um_per_pixel ** 2), 2)
                c_copy["perimeter_um"] = round(m["perimeter"] * parsed_um_per_pixel, 2)
                c_copy["area_display"] = f"{c_copy['area_um2']} µm²"
                c_copy["perimeter_display"] = f"{c_copy['perimeter_um']} µm"
            else:
                c_copy["area_display"] = f"{round(m['area'], 2)} px²"
                c_copy["perimeter_display"] = f"{round(m['perimeter'], 2)} px"
            calibrated_cell_metrics.append(c_copy)

        self._save_figures(img_rgb, img_gray, binary_mask, contour_overlay)

        analysis_id = f"MORPH-{uuid.uuid4().hex[:8].upper()}"

        cell_measurements_payload = {
            "cell_count": cell_count,
            "region_count": cell_count,
            "structure_label": structure_label,
            "is_calibrated": is_calibrated,
            "um_per_pixel": parsed_um_per_pixel,
            "area_unit": area_unit,
            "length_unit": length_unit,
            "unit_notice": unit_notice,
            "mean_area": mean_area_val,
            "mean_perimeter": mean_perimeter_val,
            "mean_area_px": round(mean_area, 2),
            "mean_perimeter_px": round(mean_perimeter, 2),
            "mean_area_um2": round(mean_area * (parsed_um_per_pixel ** 2), 2) if is_calibrated else None,
            "mean_perimeter_um": round(mean_perimeter * parsed_um_per_pixel, 2) if is_calibrated else None,
            "mean_circularity": round(mean_circularity, 4),
            "mean_aspect_ratio": round(mean_aspect_ratio, 4),
            "mean_solidity": round(mean_solidity, 4),
            "individual_cells": calibrated_cell_metrics[:30]
        }
        cell_measurements_payload.update(extra_meta)

        disclaimer_msg = "Version 1 Proof-of-Concept: Reports descriptive geometric region measurements. Does not determine biological identities, tissue health, or clinical diagnosis."

        self.current_analysis = {
            "status": "success",
            "analysis_completed": analysis_completed,
            "pipeline_status": pipeline_status,
            "interpretation_confidence": interpretation_confidence,
            "interpretation_status": interpretation_status,
            "interpretation_notes": interpretation_notes,
            "quality_status": quality_status,
            "classification_status": classification_status,
            "failure_reasons": failure_reasons,
            "detailed_failure_messages": detailed_failure_messages,
            "inconclusive_recommendations": inconclusive_recommendations,
            "table_header_title": table_header_title,
            "analysis_id": analysis_id,
            "sha256": sha256_hash,
            "sample_type": sample_type_norm,
            "profile_used": profile_name,
            "profile_status": profile_status,
            "structure_label": structure_label,
            "filename": filename,
            "saved_filename": saved_filename,
            "abs_file_path": abs_file_path,
            "dimensions": {"width": width, "height": height, "channels": channels},
            "spatial_calibration": {
                "is_calibrated": is_calibrated,
                "um_per_pixel": parsed_um_per_pixel,
                "calibration_source": calib_source_str,
                "microscope_objective": objective_str,
                "area_unit": area_unit,
                "length_unit": length_unit,
                "unit_notice": unit_notice
            },
            "image_source": img_source_str,
            "quality_metrics": {
                "brightness": round(brightness, 2),
                "contrast": round(contrast, 2),
                "sharpness": round(sharpness, 2),
                "noise_estimate": round(noise, 2),
                "fov_area_px": int(fov_area),
                "fov_coverage_pct": fov_coverage_pct
            },
            "contour_diagnostics": diag_meta,
            "cell_measurements": cell_measurements_payload,
            "classification": {
                "result": classification_result,
                "confidence": confidence,
                "reason": class_reason,
                "notice": disclaimer_msg
            },
            "research_disclaimer": disclaimer_msg,
            "figures": {
                "original": "/static/results/morphology/original_image.png",
                "grayscale": "/static/results/morphology/grayscale_image.png",
                "binary": "/static/results/morphology/binary_threshold.png",
                "contours": "/static/results/morphology/cell_contour_overlay.png"
            }
        }
        return self.current_analysis

    # Shared Contour Extraction & Explicit Rejection Diagnostics Engine
    def _extract_and_filter_contours(
        self, contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
        min_area=20.0, max_area_ratio=0.30, min_circ=0.05, min_solidity=0.15,
        min_aspect_ratio=0.05, max_aspect_ratio=6.0, show_area_label=False
    ):
        cell_metrics = []
        contour_overlay = img_rgb.copy()

        if fov_circle is not None:
            fcx, fcy, fr = fov_circle
            # Draw outer circular FOV in cyan and inner 12.5% safe FOV boundary
            cv2.circle(contour_overlay, (fcx, fcy), fr, (56, 189, 248), 2)
            safe_r = max(10, int(fr * 0.875))
            cv2.circle(contour_overlay, (fcx, fcy), safe_r, (16, 185, 129), 1)

        raw_count = len(contours)
        accepted_count = 0
        rejected_count = 0
        rejection_reasons = {
            "FOV_BORDER_TOUCH": 0,
            "OVERSIZED_MERGED_ROI": 0,
            "UNDERSIZED_NOISE": 0,
            "LOW_CIRCULARITY": 0,
            "LOW_SOLIDITY": 0,
            "ASPECT_RATIO_OUT_OF_BOUNDS": 0
        }

        raw_areas = [float(cv2.contourArea(c)) for c in contours]
        min_raw_area = round(float(np.min(raw_areas)), 2) if raw_areas else 0.0
        median_raw_area = round(float(np.median(raw_areas)), 2) if raw_areas else 0.0
        max_raw_area = round(float(np.max(raw_areas)), 2) if raw_areas else 0.0

        rel_min_area = max(20.0, min_area if min_area > 1.0 else (min_area * fov_area))
        safe_area = float(np.sum(safe_fov_mask > 0))

        accepted_area_sum = 0.0
        cell_id = 1

        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            
            if area < rel_min_area:
                rejected_count += 1
                rejection_reasons["UNDERSIZED_NOISE"] += 1
                cv2.drawContours(contour_overlay, [cnt], -1, (239, 68, 68), 1)
                continue
            if area > (max_area_ratio * safe_area):
                rejected_count += 1
                rejection_reasons["OVERSIZED_MERGED_ROI"] += 1
                cv2.drawContours(contour_overlay, [cnt], -1, (239, 68, 68), 2)
                continue

            pts = cnt.reshape(-1, 2)
            touches_border = False
            for px, py in pts:
                if px <= 4 or py <= 4 or px >= width - 4 or py >= height - 4:
                    touches_border = True
                    break
                if safe_fov_mask[py, px] == 0:
                    touches_border = True
                    break

            if touches_border:
                rejected_count += 1
                rejection_reasons["FOV_BORDER_TOUCH"] += 1
                cv2.drawContours(contour_overlay, [cnt], -1, (239, 68, 68), 1)
                continue

            perimeter = float(cv2.arcLength(cnt, True))
            if perimeter == 0:
                rejected_count += 1
                rejection_reasons["UNDERSIZED_NOISE"] += 1
                continue

            circularity = float(4.0 * np.pi * area / (perimeter ** 2))
            circularity = min(1.0, circularity)

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w / h) if h > 0 else 1.0

            hull = cv2.convexHull(cnt)
            hull_area = float(cv2.contourArea(hull))
            solidity = float(area / hull_area) if hull_area > 0 else 1.0

            if circularity < min_circ:
                rejected_count += 1
                rejection_reasons["LOW_CIRCULARITY"] += 1
                cv2.drawContours(contour_overlay, [cnt], -1, (239, 68, 68), 1)
                continue

            if solidity < min_solidity:
                rejected_count += 1
                rejection_reasons["LOW_SOLIDITY"] += 1
                cv2.drawContours(contour_overlay, [cnt], -1, (239, 68, 68), 1)
                continue

            if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
                rejected_count += 1
                rejection_reasons["ASPECT_RATIO_OUT_OF_BOUNDS"] += 1
                cv2.drawContours(contour_overlay, [cnt], -1, (239, 68, 68), 1)
                continue

            accepted_count += 1
            accepted_area_sum += area

            angle_deg = 0.0
            if len(cnt) >= 5:
                (rect_cx, rect_cy), (rect_w, rect_h), angle_deg = cv2.minAreaRect(cnt)

            equivalent_diam = 2.0 * np.sqrt(area / np.pi)
            feret_diam = np.sqrt(w**2 + h**2)

            cell_metrics.append({
                "cell_id": cell_id,
                "area": round(area, 2),
                "perimeter": round(perimeter, 2),
                "circularity": round(circularity, 4),
                "aspect_ratio": round(aspect_ratio, 4),
                "solidity": round(solidity, 4),
                "width_px": round(w, 2),
                "height_px": round(h, 2),
                "length_px": round(max(w, h), 2),
                "equivalent_diameter_px": round(equivalent_diam, 2),
                "feret_diameter_px": round(feret_diam, 2),
                "angle_deg": round(angle_deg, 1)
            })

            cv2.drawContours(contour_overlay, [cnt], -1, (16, 185, 129), 2)
            label_text = f"#{cell_id} ({int(area)}px²)" if show_area_label else f"#{cell_id}"
            cv2.putText(contour_overlay, label_text, (x, max(14, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (245, 158, 11), 1)
            cell_id += 1

        rel_area_pct = round(float(accepted_area_sum / safe_area * 100), 2) if safe_area > 0 else 0.0

        diag_meta = {
            "raw_contour_count": raw_count,
            "accepted_contour_count": accepted_count,
            "rejected_contour_count": rejected_count,
            "min_contour_area_raw": min_raw_area,
            "median_contour_area_raw": median_raw_area,
            "max_contour_area_raw": max_raw_area,
            "rejection_reasons_breakdown": rejection_reasons,
            "relative_candidate_area_pct": rel_area_pct,
            "fov_boundary_excluded": True
        }

        return cell_metrics, contour_overlay, diag_meta

    # 1. Profile: Generic Tissue (Validated v1 Primary Workflow)
    def _profile_generic(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=20.0, max_area_ratio=0.30, min_circ=0.05, min_solidity=0.15, max_aspect_ratio=6.0
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    # Experimental Profiles (Marked Experimental — Not Validated in Version 1)
    def _profile_adipose(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=30.0, max_area_ratio=0.30, min_circ=0.08, min_solidity=0.20, max_aspect_ratio=5.0
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_skeletal_muscle(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=25.0, max_area_ratio=0.30, min_circ=0.03, min_solidity=0.15, min_aspect_ratio=0.1, max_aspect_ratio=8.0
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_thyroid(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=30.0, max_area_ratio=0.30, min_circ=0.10, min_solidity=0.25
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_pancreas(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=25.0, max_area_ratio=0.30, min_circ=0.08, min_solidity=0.20
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_spinal_cord(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=25.0, max_area_ratio=0.30, min_circ=0.05, min_solidity=0.15
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_myocardium(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=25.0, max_area_ratio=0.30, min_circ=0.03, min_solidity=0.15, min_aspect_ratio=0.1, max_aspect_ratio=8.0
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_testis(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=35.0, max_area_ratio=0.30, min_circ=0.10, min_solidity=0.25
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    def _profile_ovary(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height):
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=35.0, max_area_ratio=0.30, min_circ=0.10, min_solidity=0.30
        )
        return closed, cell_metrics, contour_overlay, diag_meta, {}

    # Primary Validated Profile: Stem Cells (iPSC / ESC) (Stem Cell Colony Morphometry)
    def _profile_stem_cell(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height, condition_id="condition1"):
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        valid_px = img_gray[safe_fov_mask > 0]
        
        brightness_mean = float(np.mean(valid_px)) if len(valid_px) > 0 else float(np.mean(img_gray))
        brightness_std = float(np.std(valid_px)) if len(valid_px) > 0 else float(np.mean(img_gray))
        
        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        
        colony_px = float(np.sum((closed > 0) & (safe_fov_mask > 0)))
        safe_area = float(np.sum(safe_fov_mask > 0))
        colony_coverage_pct = round(float(colony_px / safe_area * 100), 2) if safe_area > 0 else 0.0

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        colony_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=25.0, max_area_ratio=0.35, min_circ=0.05, min_solidity=0.15, max_aspect_ratio=6.0, show_area_label=True
        )

        colony_count = len(colony_metrics)
        colony_density = round(float(colony_count / max(1.0, safe_area / 100000.0)), 2)

        areas = [m["area"] for m in colony_metrics] if colony_metrics else []
        small_colonies = sum(1 for a in areas if a < 150.0)
        med_colonies = sum(1 for a in areas if 150.0 <= a <= 800.0)
        large_colonies = sum(1 for a in areas if a > 800.0)

        border_irregularity_vals = []
        compactness_vals = []
        for m in colony_metrics:
            circ = max(0.01, m["circularity"])
            sol = max(0.01, m["solidity"])
            border_irregularity_vals.append(round(1.0 / circ, 4))
            compactness_vals.append(round(sol / circ, 4))

        mean_border_irregularity = float(np.mean(border_irregularity_vals)) if border_irregularity_vals else 1.0
        mean_compactness = float(np.mean(compactness_vals)) if compactness_vals else 1.0

        extra_meta = {
            "colony_count": colony_count,
            "colony_coverage_pct": colony_coverage_pct,
            "colony_density": colony_density,
            "mean_border_irregularity": round(mean_border_irregularity, 3),
            "mean_colony_compactness": round(mean_compactness, 3),
            "colony_size_distribution": {
                "small": small_colonies,
                "medium": med_colonies,
                "large": large_colonies
            }
        }

        return closed, colony_metrics, contour_overlay, diag_meta, extra_meta

    # Dedicated Profile: human iPSC (Pluripotency Assessment - DOI: 10.1038/s41598-024-66591-z)
    def _profile_ipsc(self, img_rgb, blurred, fov_mask, safe_fov_mask, fov_area, fov_circle, width, height, condition_id="condition1"):
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        valid_px = img_gray[safe_fov_mask > 0]
        
        brightness_mean = float(np.mean(valid_px)) if len(valid_px) > 0 else float(np.mean(img_gray))
        brightness_std = float(np.std(valid_px)) if len(valid_px) > 0 else float(np.std(img_gray))
        
        if brightness_std > 0 and len(valid_px) > 0:
            brightness_skew = float(np.mean(((valid_px - brightness_mean) / brightness_std) ** 3))
        else:
            brightness_skew = 0.0

        laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
        focus_sharpness = float(laplacian[safe_fov_mask > 0].var()) if np.sum(safe_fov_mask > 0) > 100 else float(laplacian.var())

        # Quality Control Flags
        qc_reasons = []
        if focus_sharpness < 18.0:
            qc_reasons.append("Out of Focus / Blurry Image")
        if brightness_mean < 15.0 or brightness_mean > 245.0 or brightness_std < 8.0:
            qc_reasons.append("Poor Illumination / Low Contrast")

        closed = self._create_background_subtracted_mask(img_rgb, blurred, safe_fov_mask)
        
        colony_px = float(np.sum((closed > 0) & (safe_fov_mask > 0)))
        safe_area = float(np.sum(safe_fov_mask > 0))
        confluence_pct = round(float(colony_px / safe_area * 100), 2) if safe_area > 0 else 0.0

        if confluence_pct < 0.5:
            qc_reasons.append("Empty Field - No iPSC Colonies Detected")

        qc_status = "PASSED" if len(qc_reasons) == 0 else f"WARNING: {', '.join(qc_reasons)}"

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cell_metrics, contour_overlay, diag_meta = self._extract_and_filter_contours(
            contours, img_rgb, safe_fov_mask, fov_area, fov_circle, width, height,
            min_area=25.0, max_area_ratio=0.35, min_circ=0.05, min_solidity=0.15, max_aspect_ratio=6.0, show_area_label=True
        )

        colony_count = len(cell_metrics)
        fragmentation_count = sum(1 for m in cell_metrics if m["area"] < 150.0)
        fragmentation_index = round(float(fragmentation_count / max(1, colony_count)), 3)

        texture_contrast = round(brightness_std, 2)
        texture_homogeneity = round(1.0 / (1.0 + brightness_std), 4)

        edge_irregularity_vals = []
        compactness_vals = []
        for m in cell_metrics:
            circ = max(0.01, m["circularity"])
            sol = max(0.01, m["solidity"])
            compactness_vals.append(round(sol / circ, 4))
            edge_irregularity_vals.append(round(1.0 / circ, 4))

        mean_compactness = float(np.mean(compactness_vals)) if compactness_vals else 1.0
        mean_edge_irregularity = float(np.mean(edge_irregularity_vals)) if edge_irregularity_vals else 1.0

        diff_score = 0.0
        if colony_count > 0:
            mean_circ = float(np.mean([m["circularity"] for m in cell_metrics]))
            diff_score = max(0.0, min(100.0, (1.0 - mean_circ) * 60.0 + (mean_edge_irregularity - 1.0) * 30.0 + (brightness_std / 50.0) * 10.0))
        diff_score = round(diff_score, 2)

        from backend.ipsc_dataset_service import ipsc_dataset_service
        cond_info = ipsc_dataset_service.get_condition_summary(condition_id)

        extra_meta = {
            "qc_status": qc_status,
            "qc_reasons": qc_reasons,
            "confluence_pct": confluence_pct,
            "colony_count": colony_count,
            "fragmentation_count": fragmentation_count,
            "fragmentation_index": fragmentation_index,
            "mean_edge_sharpness": round(focus_sharpness, 2),
            "edge_irregularity_index": round(mean_edge_irregularity, 3),
            "mean_compactness": round(mean_compactness, 3),
            "texture_contrast": texture_contrast,
            "texture_homogeneity": texture_homogeneity,
            "brightness_distribution": {
                "mean": round(brightness_mean, 2),
                "std": round(brightness_std, 2),
                "skewness": round(brightness_skew, 3)
            },
            "differentiation_likelihood_score": diff_score,
            "condition_comparison": cond_info["metrics_summary"],
            "dataset_metadata": ipsc_dataset_service.metadata
        }

        return closed, cell_metrics, contour_overlay, diag_meta, extra_meta

    def _save_figures(self, img_rgb, img_gray, closed, contour_overlay):
        plt.style.use('dark_background')

        def save_img(matrix, filename, is_gray=False):
            fig, ax = plt.subplots(figsize=(6, 6), dpi=300)
            fig.patch.set_facecolor('#0f172a')
            ax.set_facecolor('#1e293b')

            if is_gray:
                ax.imshow(matrix, cmap='gray')
            else:
                ax.imshow(matrix)

            ax.axis('off')
            plt.tight_layout()

            for s_dir in self.static_dirs:
                out_path = os.path.join(s_dir, filename)
                plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close()

        save_img(img_rgb, "original_image.png")
        save_img(img_gray, "grayscale_image.png", is_gray=True)
        save_img(closed, "binary_threshold.png", is_gray=True)
        save_img(contour_overlay, "cell_contour_overlay.png")

    def get_summary(self):
        if self.current_analysis is None:
            self._initialize_default_sample()
        return self.current_analysis

morphology_service = MorphologyService()
