import os
import time
import json
import uuid
import io

class LaboratoryService:
    def __init__(self):
        self.active_session = None

    def _get_or_create_session(self, target_exp_id=None, is_same_exp=False):
        if not self.active_session:
            exp_id = target_exp_id or f"EXP-2026-{uuid.uuid4().hex[:4].upper()}"
            now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            self.active_session = {
                "experiment_id": exp_id,
                "created_timestamp": now_str,
                "last_updated_timestamp": now_str,
                "is_same_experiment_matched": is_same_exp,
                "status_matrix": {
                    "morphology": "Not Started",
                    "culture": "Not Started",
                    "cell_fate": "Not Started",
                    "sindex": "Not Started"
                },
                "modules": {},
                "integrated_synthesis": "",
                "research_disclaimer": "This analysis is exploratory and does not determine tissue health or clinical diagnosis."
            }
        elif target_exp_id and target_exp_id != self.active_session["experiment_id"]:
            # Switch session ID if explicitly requested
            self.active_session["experiment_id"] = target_exp_id

        return self.active_session

    def process_module_result(self, module_type, data):
        if not data or not isinstance(data, dict):
            return {"status": "error", "message": f"Invalid {module_type} payload"}

        module_type = str(module_type).lower().strip()
        if module_type not in ["morphology", "culture", "cell_fate", "sindex"]:
            return {"status": "error", "message": f"Unsupported module type: {module_type}"}

        exp_id_req = data.get("experiment_id")
        is_same_exp = bool(data.get("is_same_experiment_matched", False))
        session = self._get_or_create_session(exp_id_req, is_same_exp)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        # Update module status
        current_status = session["status_matrix"].get(module_type, "Not Started")
        new_status = "Updated" if current_status in ["Completed", "Updated"] else "Completed"
        session["status_matrix"][module_type] = new_status
        session["last_updated_timestamp"] = now_str

        # Format module block
        if module_type == "morphology":
            m = data.get("cell_measurements", {})
            cls = data.get("classification", {})
            calib = data.get("spatial_calibration", {})

            area_unit = m.get("area_unit") or calib.get("area_unit") or "px²"
            len_unit = m.get("length_unit") or calib.get("length_unit") or "px"

            mean_area_val = m.get("mean_area") if m.get("mean_area") is not None else m.get("mean_area_px", 0)
            mean_perim_val = m.get("mean_perimeter") if m.get("mean_perimeter") is not None else m.get("mean_perimeter_px", 0)

            session["modules"]["morphology"] = {
                "module_name": "Cell Morphology",
                "tissue_profile": str(data.get("profile_used") or data.get("sample_type") or "generic").capitalize(),
                "image_source": str(data.get("image_source") or "Unknown"),
                "segmentation_quality": str(cls.get("result") or "Segmentation Quality: High"),
                "candidate_structures": m.get("cell_count", 0),
                "mean_area": f"{mean_area_val} {area_unit}",
                "mean_perimeter": f"{mean_perim_val} {len_unit}",
                "mean_circularity": m.get("mean_circularity", 0),
                "mean_solidity": m.get("mean_solidity", 0),
                "aspect_ratio": m.get("mean_aspect_ratio", 0),
                "measurement_units": area_unit,
                "calibration": calib.get("unit_notice") or m.get("unit_notice") or "Uncalibrated",
                "processing_pipeline": [
                    "Grayscale Conversion",
                    "Otsu Binary Thresholding",
                    "Morphological Closing",
                    "Contour Detection & Geometric Measurement"
                ],
                "provenance": {
                    "analysis_id": data.get("analysis_id", "MORPH-001"),
                    "uploaded_filename": data.get("filename", "microscopy_sample.png"),
                    "calibration_source": calib.get("calibration_source", "Uncalibrated"),
                    "pipeline_version": "v1.3.0"
                }
            }

        elif module_type == "culture":
            session["modules"]["culture"] = {
                "module_name": "Research Culture Optimizer",
                "source_mode": data.get("source_mode") or data.get("source_type") or "Example Culture",
                "cell_density": data.get("cell_density", "1.2e5 cells/mL"),
                "confluency": data.get("confluency", "82.5 %"),
                "passage_number": data.get("passage_number", "P4"),
                "temperature": data.get("temperature", "37.0 °C"),
                "co2": data.get("co2", "5.0 %"),
                "humidity": data.get("humidity", "95.0 %"),
                "culture_score": data.get("culture_score", "88 / 100"),
                "growth_status": data.get("growth_status", "Exponential Growth Phase"),
                "risk_level": data.get("risk_level", "Low Risk"),
                "biomass_prediction": data.get("biomass_prediction", "Optimal High Yield"),
                "processing_pipeline": [
                    "Environmental Sensor Telemetry",
                    "Random Forest Growth Predictor",
                    "SHAP Attribution Engine",
                    "Risk & Score Optimization Rules"
                ],
                "provenance": {
                    "source_mode": data.get("source_mode", "Example Culture"),
                    "analysis_timestamp": now_str,
                    "pipeline_version": "v1.3.0"
                }
            }

        elif module_type == "cell_fate":
            session["modules"]["cell_fate"] = {
                "module_name": "Cell Fate Analyzer",
                "dataset_name": data.get("dataset_name", "Cardiomyocyte Differentiation (scRNA-seq)"),
                "cell_count": data.get("cell_count", 32650),
                "sample_count": data.get("sample_count", 6),
                "clustering_method": data.get("clustering_method", "Leiden Graph Clustering & UMAP"),
                "top_biomarkers": data.get("top_biomarkers", ["TNNT2", "MYH6", "NKX2-5", "TNNI3"]),
                "lineage_pseudotime_range": data.get("lineage_pseudotime_range", "0.00 - 1.00"),
                "differentiation_trajectory": data.get("differentiation_trajectory", "Pluripotent Stem Cell → Cardiac Progenitor → Mature Cardiomyocyte"),
                "processing_pipeline": [
                    "Single-Cell Matrix Normalization",
                    "PCA Dimension Reduction & UMAP",
                    "Leiden Community Detection",
                    "Differential Gene Expression (DGE)"
                ],
                "provenance": {
                    "dge_results_file": data.get("dge_file", "dge_complete_results.csv"),
                    "pipeline_version": "v1.3.0"
                }
            }

        elif module_type == "sindex":
            session["modules"]["sindex"] = {
                "module_name": "CoreAI Experimental S-Index",
                "source_type": data.get("source_type", "Example Dataset Records"),
                "total_repositories": data.get("total_repositories", 2),
                "total_datasets": data.get("total_datasets", 5),
                "avg_fair_score": data.get("avg_fair_score", "85.4%"),
                "avg_sindex": data.get("avg_sindex", "0.82"),
                "evaluated_accessions": data.get("evaluated_accessions", ["GSE214617", "GSE290316"]),
                "processing_pipeline": [
                    "NCBI GEO XML / SOFT Parsing",
                    "Metadata Field Extraction",
                    "FAIR Compliance Check",
                    "S-Index Score Aggregation"
                ],
                "provenance": {
                    "audit_timestamp": data.get("audit_timestamp", now_str),
                    "scoring_formula": "CoreAI Experimental S-Index (v1.3.0)",
                    "pipeline_version": "v1.3.0"
                }
            }

        # Update integrated research synthesis with causal guardrails
        self._update_integrated_synthesis()
        return {"status": "success", "session": self.active_session}

    def _update_integrated_synthesis(self):
        if not self.active_session:
            return

        mods = self.active_session.get("modules", {})
        active_count = len(mods)

        parts = []
        parts.append(f"AI Laboratory Session {self.active_session['experiment_id']} contains results from {active_count} active module(s): {', '.join([v['module_name'] for v in mods.values()])}.")

        if "morphology" in mods:
            m_mod = mods["morphology"]
            parts.append(f"Cell Morphology segmented {m_mod['candidate_structures']} candidate structures in {m_mod['tissue_profile']} tissue ({m_mod['segmentation_quality']}).")

        if "culture" in mods:
            c_mod = mods["culture"]
            parts.append(f"Culture Optimizer recorded {c_mod['growth_status']} with culture score {c_mod['culture_score']} ({c_mod['risk_level']}).")

        if "cell_fate" in mods:
            f_mod = mods["cell_fate"]
            parts.append(f"Cell Fate Analyzer resolved {f_mod['cell_count']} single cells across {f_mod['sample_count']} samples, identifying top biomarkers ({', '.join(f_mod['top_biomarkers'][:3])}).")

        if "sindex" in mods:
            s_mod = mods["sindex"]
            parts.append(f"S-Index audit evaluated {s_mod['total_datasets']} dataset records achieving average FAIR score {s_mod['avg_fair_score']} (S-Index {s_mod['avg_sindex']}).")

        # Mandatory Causal Safety Guardrail (Directive #5)
        if not self.active_session.get("is_same_experiment_matched", False):
            parts.append("Scientific Independence Guardrail: These analytical modules were transferred independently. No biological causal relationship (e.g., culture condition directly causing specific gene expression or cell shape changes) is assumed or inferred across unlinked dataset records.")
        else:
            parts.append("Matched Biological Experiment: Records originate from an explicitly matched biological experiment ID.")

        parts.append("This analysis is exploratory and intended for research decision support only.")
        self.active_session["integrated_synthesis"] = " ".join(parts)

    def get_active_session(self):
        if not self.active_session:
            return {
                "status": "success",
                "has_session": False,
                "message": "No active laboratory session. Perform an analysis in any module to transfer results."
            }
        return {
            "status": "success",
            "has_session": True,
            "session": self.active_session
        }

    def export_json(self):
        session = self._get_or_create_session()
        return {
            "status": "success",
            "export_format": "JSON",
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "session": session
        }

    def export_pdf(self):
        session = self._get_or_create_session()

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor('#0f172a'),
                fontName='Helvetica-Bold'
            )
            h2_style = ParagraphStyle(
                'DocHeading2',
                parent=styles['Heading2'],
                fontSize=13,
                leading=16,
                textColor=colors.HexColor('#1e293b'),
                fontName='Helvetica-Bold',
                spaceBefore=10,
                spaceAfter=6
            )
            body_style = ParagraphStyle(
                'DocBody',
                parent=styles['Normal'],
                fontSize=9,
                leading=13,
                textColor=colors.HexColor('#334155'),
                fontName='Helvetica'
            )
            disclaimer_style = ParagraphStyle(
                'DocDisclaimer',
                parent=styles['Normal'],
                fontSize=8,
                leading=11,
                textColor=colors.HexColor('#9a3412'),
                fontName='Helvetica-Oblique'
            )

            story = []
            session = self.active_session

            # Title & Metadata
            story.append(Paragraph("CoreAI BIO — Multi-Module AI Laboratory Report", title_style))
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Experiment ID:</b> {session['experiment_id']} | <b>Generated:</b> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}", body_style))
            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=4, spaceAfter=12))

            # Status Matrix Table
            story.append(Paragraph("1. Experiment Workspace Status Matrix", h2_style))
            matrix_data = [["Module", "Status"]]
            for mod_k, mod_v in session["status_matrix"].items():
                matrix_data.append([mod_k.replace("_", " ").title(), mod_v])
            
            t_matrix = Table(matrix_data, colWidths=[240, 240])
            t_matrix.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(t_matrix)
            story.append(Spacer(1, 12))

            # Integrated Synthesis
            story.append(Paragraph("2. Integrated Research Synthesis", h2_style))
            story.append(Paragraph(session.get("integrated_synthesis", ""), body_style))
            story.append(Spacer(1, 12))

            # Module Summaries
            mods = session.get("modules", {})
            if mods:
                story.append(Paragraph("3. Module Analytics Summaries", h2_style))
                for mk, mv in mods.items():
                    story.append(Paragraph(f"<b>{mv.get('module_name', mk.title())}</b>", body_style))
                    mod_table_data = [["Attribute", "Value"]]
                    for k, v in mv.items():
                        if k not in ["processing_pipeline", "provenance"]:
                            val_str = ", ".join(v) if isinstance(v, list) else str(v)
                            mod_table_data.append([k.replace("_", " ").title(), val_str])
                    
                    t_mod = Table(mod_table_data, colWidths=[200, 280])
                    t_mod.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 8),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                        ('PADDING', (0,0), (-1,-1), 5),
                    ]))
                    story.append(t_mod)
                    story.append(Spacer(1, 10))

            # Disclaimer
            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=4, spaceAfter=10))
            story.append(Paragraph(f"<b>Research Disclaimer:</b> {session.get('research_disclaimer')}", disclaimer_style))

            doc.build(story)
            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()
            return pdf_bytes, None
        except Exception as e:
            return None, f"PDF Generation Error: {str(e)}"

    def export_html(self):
        session = self._get_or_create_session()
        mods = session.get("modules", {})
        matrix = session.get("status_matrix", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CoreAI BIO - AI Laboratory Report ({session['experiment_id']})</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 2rem; }}
        .container {{ max-width: 960px; margin: 0 auto; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2rem; }}
        h1 {{ color: #f8fafc; font-size: 1.8rem; margin-top: 0; }}
        h2 {{ color: #38bdf8; font-size: 1.2rem; border-bottom: 1px solid #334155; padding-bottom: 0.4rem; margin-top: 1.5rem; }}
        .meta-bar {{ background: rgba(15,23,42,0.6); padding: 0.85rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1.5rem; border: 1px solid #334155; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 1rem; font-size: 0.85rem; }}
        th, td {{ border: 1px solid #334155; padding: 0.6rem 0.8rem; text-align: left; }}
        th {{ background: #0f172a; color: #94a3b8; font-weight: 700; }}
        .badge {{ padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
        .completed {{ background: rgba(16,185,129,0.2); color: #10b981; }}
        .updated {{ background: rgba(56,189,248,0.2); color: #38bdf8; }}
        .not-started {{ background: rgba(148,163,184,0.1); color: #94a3b8; }}
        .disclaimer {{ background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); border-radius: 8px; padding: 0.85rem; font-size: 0.8rem; color: #f59e0b; margin-top: 2rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔬 CoreAI BIO — Multi-Module AI Laboratory Report</h1>
        <div class="meta-bar">
            <strong>Experiment ID:</strong> {session['experiment_id']} | 
            <strong>Created:</strong> {session['created_timestamp']} | 
            <strong>Last Updated:</strong> {session['last_updated_timestamp']}
        </div>

        <h2>1. Workspace Status Matrix</h2>
        <table>
            <thead>
                <tr><th>Module</th><th>Status</th></tr>
            </thead>
            <tbody>
"""
        for mk, mv in matrix.items():
            badge_cls = "completed" if mv == "Completed" else ("updated" if mv == "Updated" else "not-started")
            html += f"<tr><td>{mk.replace('_', ' ').title()}</td><td><span class=\"badge {badge_cls}\">{mv}</span></td></tr>"

        html += f"""
            </tbody>
        </table>

        <h2>2. Integrated Research Synthesis</h2>
        <div style="background: #0f172a; padding: 1rem; border-radius: 8px; font-size: 0.9rem; line-height: 1.5; border: 1px solid #334155;">
            {session.get('integrated_synthesis', '')}
        </div>

        <h2>3. Active Module Summaries</h2>
"""
        if not mods:
            html += "<p style=\"color: #94a3b8;\">No active module results transferred yet.</p>"
        else:
            for mk, mv in mods.items():
                html += f"<h3>{mv.get('module_name', mk.title())}</h3><table><tbody>"
                for k, v in mv.items():
                    if k not in ["processing_pipeline", "provenance"]:
                        val_str = ", ".join(v) if isinstance(v, list) else str(v)
                        html += f"<tr><td style=\"width: 35%; color: #94a3b8;\">{k.replace('_', ' ').title()}</td><td><strong>{val_str}</strong></td></tr>"
                html += "</tbody></table>"

        html += f"""
        <div class="disclaimer">
            ⚠️ <strong>Research Disclaimer:</strong> {session.get('research_disclaimer')}
        </div>
    </div>
</body>
</html>
"""
        return html, None

laboratory_service = LaboratoryService()
