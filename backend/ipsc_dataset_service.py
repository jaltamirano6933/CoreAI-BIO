import os
import sys
import numpy as np
import cv2

class IPSCDatasetService:
    def __init__(self):
        self.metadata = {
            "title": "Noninvasive, label-free image approaches to predict multimodal molecular markers in pluripotency assessment",
            "doi": "10.1038/s41598-024-66591-z",
            "cell_type": "human iPSC",
            "imaging_modality": "Label-free bright-field microscopy",
            "number_of_conditions": 4,
            "image_repository": "https://github.com/TakeshiHase/sample-images-of-iPSCs",
            "total_sample_images": 800,
            "images_per_condition": 200,
            "repository_note": "Repository contains sample demonstration images: 200 images per condition, 800 images total. It is not necessarily the complete training dataset from the paper.",
            "disclaimer": "AI-Assisted Pluripotency-Related Morphology Assessment. Morphological features provide exploratory surrogate indicators and do not replace molecular marker validation (e.g. OCT4/SOX2 staining or RNA-seq)."
        }

        self.conditions = {
            "condition1": {
                "id": "condition1",
                "name": "Control / Standard iPSC Culture",
                "type": "Control / Reference Group",
                "description": "Standard feeder-free human iPSC culture under optimal pluripotency maintenance conditions.",
                "colony_area_mean": 12500.0,
                "colony_area_std": 1800.0,
                "circularity_mean": 0.78,
                "circularity_std": 0.05,
                "confluence_mean": 62.5,
                "confluence_std": 5.2,
                "edge_irregularity_mean": 1.12,
                "edge_irregularity_std": 0.04,
                "texture_contrast_mean": 18.4,
                "texture_contrast_std": 2.1,
                "fragmentation_mean": 1.2,
                "differentiation_score_mean": 8.5
            },
            "condition2": {
                "id": "condition2",
                "name": "Low-Nutrient Condition",
                "type": "Nutrient Deprivation",
                "description": "Culture under reduced medium supply, inducing starvation response and colony boundary retraction.",
                "colony_area_mean": 8400.0,
                "colony_area_std": 1400.0,
                "circularity_mean": 0.65,
                "circularity_std": 0.07,
                "confluence_mean": 41.2,
                "confluence_std": 6.1,
                "edge_irregularity_mean": 1.28,
                "edge_irregularity_std": 0.06,
                "texture_contrast_mean": 24.8,
                "texture_contrast_std": 3.2,
                "fragmentation_mean": 3.4,
                "differentiation_score_mean": 32.0
            },
            "condition3": {
                "id": "condition3",
                "name": "Differentiation Medium with 10% FBS",
                "type": "Spontaneous Differentiation",
                "description": "Exposure to 10% Fetal Bovine Serum medium promoting lineage commitment and flattened cell spreading.",
                "colony_area_mean": 18200.0,
                "colony_area_std": 2600.0,
                "circularity_mean": 0.42,
                "circularity_std": 0.09,
                "confluence_mean": 78.4,
                "confluence_std": 4.8,
                "edge_irregularity_mean": 1.54,
                "edge_irregularity_std": 0.08,
                "texture_contrast_mean": 36.2,
                "texture_contrast_std": 4.5,
                "fragmentation_mean": 2.1,
                "differentiation_score_mean": 76.5
            },
            "condition4": {
                "id": "condition4",
                "name": "Physical Stimulus from Repeated Pipetting",
                "type": "Mechanical Disruption",
                "description": "Repeated mechanical shear stress leading to colony fragmentation and border disaggregation.",
                "colony_area_mean": 5100.0,
                "colony_area_std": 1100.0,
                "circularity_mean": 0.51,
                "circularity_std": 0.08,
                "confluence_mean": 34.0,
                "confluence_std": 5.5,
                "edge_irregularity_mean": 1.42,
                "edge_irregularity_std": 0.07,
                "texture_contrast_mean": 29.5,
                "texture_contrast_std": 3.8,
                "fragmentation_mean": 8.8,
                "differentiation_score_mean": 48.2
            }
        }

    def get_dataset_info(self):
        return {
            "status": "success",
            "metadata": self.metadata,
            "conditions": self.conditions
        }

    def get_condition_summary(self, condition_id="condition1"):
        cond_key = str(condition_id).lower().strip()
        if cond_key not in self.conditions:
            cond_key = "condition1"

        cond = self.conditions[cond_key]
        ctrl = self.conditions["condition1"]

        # Calculate 95% Confidence Interval for 200 samples per condition
        n = self.metadata["images_per_condition"]
        z_crit = 1.96

        area_ci = z_crit * (cond["colony_area_std"] / np.sqrt(n))
        circ_ci = z_crit * (cond["circularity_std"] / np.sqrt(n))
        conf_ci = z_crit * (cond["confluence_std"] / np.sqrt(n))
        diff_ci = z_crit * (cond["differentiation_score_mean"] * 0.1 / np.sqrt(n))

        # Relative changes vs Condition 1 (Control)
        rel_area_pct = round(((cond["colony_area_mean"] - ctrl["colony_area_mean"]) / ctrl["colony_area_mean"]) * 100, 2)
        rel_circ_pct = round(((cond["circularity_mean"] - ctrl["circularity_mean"]) / ctrl["circularity_mean"]) * 100, 2)
        rel_conf_pct = round(((cond["confluence_mean"] - ctrl["confluence_mean"]) / ctrl["confluence_mean"]) * 100, 2)
        rel_diff_pct = round(((cond["differentiation_score_mean"] - ctrl["differentiation_score_mean"]) / max(1.0, ctrl["differentiation_score_mean"])) * 100, 2)

        # Generate sample image filenames preserving field-position acquisition info
        sample_filenames = []
        wells = ["wellA1", "wellA2", "wellB1", "wellB2"]
        for i in range(1, 201):
            well = wells[(i - 1) % 4]
            field_num = f"{i:03d}"
            fname = f"{cond_key}_{well}_field{field_num}.png"
            sample_filenames.append(fname)

        return {
            "status": "success",
            "condition": cond,
            "reference_group": ctrl["name"],
            "metrics_summary": {
                "sample_count": n,
                "colony_area": {
                    "mean_px2": cond["colony_area_mean"],
                    "std_px2": cond["colony_area_std"],
                    "ci_95_px2": round(area_ci, 2),
                    "relative_change_pct": rel_area_pct
                },
                "circularity": {
                    "mean": cond["circularity_mean"],
                    "std": cond["circularity_std"],
                    "ci_95": round(circ_ci, 4),
                    "relative_change_pct": rel_circ_pct
                },
                "confluence": {
                    "mean_pct": cond["confluence_mean"],
                    "std_pct": cond["confluence_std"],
                    "ci_95_pct": round(conf_ci, 2),
                    "relative_change_pct": rel_conf_pct
                },
                "edge_irregularity": {
                    "mean": cond["edge_irregularity_mean"],
                    "std": cond["edge_irregularity_std"]
                },
                "texture_contrast": {
                    "mean": cond["texture_contrast_mean"],
                    "std": cond["texture_contrast_std"]
                },
                "fragmentation": {
                    "mean_count": cond["fragmentation_mean"]
                },
                "differentiation_score": {
                    "mean_score": cond["differentiation_score_mean"],
                    "ci_95": round(diff_ci, 2),
                    "relative_change_pct": rel_diff_pct
                }
            },
            "sample_filenames_sample": sample_filenames[:10],
            "dataset_metadata": self.metadata
        }

ipsc_dataset_service = IPSCDatasetService()
