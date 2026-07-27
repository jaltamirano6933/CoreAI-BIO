import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app
from backend.laboratory_service import laboratory_service

class TestMultiModuleLaboratoryIntegration(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        laboratory_service.active_session = None

        self.mock_morphology_payload = {
            "module_type": "morphology",
            "experiment_id": "EXP-2026-8492",
            "analysis_id": "MORPH-TEST-1234",
            "filename": "thyroid_sample.png",
            "sample_type": "thyroid",
            "profile_used": "thyroid",
            "image_source": "Prepared slide image",
            "classification": {"result": "Segmentation Quality: High"},
            "cell_measurements": {
                "cell_count": 12,
                "mean_area": 450.2,
                "mean_perimeter": 78.5,
                "mean_circularity": 0.894,
                "mean_solidity": 0.982,
                "area_unit": "µm²"
            }
        }

        self.mock_culture_payload = {
            "module_type": "culture",
            "experiment_id": "EXP-2026-8492",
            "source_mode": "Manual Entry",
            "cell_density": "1.5e5 cells/mL",
            "confluency": "85.0 %",
            "passage_number": "P5",
            "temperature": "37.0 °C",
            "co2": "5.0 %",
            "humidity": "95.0 %",
            "culture_score": "92 / 100",
            "growth_status": "Exponential Growth Phase",
            "risk_level": "Low Risk",
            "biomass_prediction": "Optimal High Yield"
        }

        self.mock_cell_fate_payload = {
            "module_type": "cell_fate",
            "experiment_id": "EXP-2026-8492",
            "dataset_name": "Cardiomyocyte Differentiation (scRNA-seq)",
            "cell_count": 32650,
            "sample_count": 6,
            "clustering_method": "Leiden Graph Clustering & UMAP",
            "top_biomarkers": ["TNNT2", "MYH6", "NKX2-5", "TNNI3"],
            "lineage_pseudotime_range": "0.00 - 1.00",
            "differentiation_trajectory": "Pluripotent Stem Cell → Cardiac Progenitor → Mature Cardiomyocyte"
        }

        self.mock_sindex_payload = {
            "module_type": "sindex",
            "experiment_id": "EXP-2026-8492",
            "source_type": "Example Dataset Records",
            "total_repositories": 2,
            "total_datasets": 5,
            "avg_fair_score": "88.2%",
            "avg_sindex": "0.85",
            "evaluated_accessions": ["GSE214617", "GSE290316"]
        }

    def test_send_results_from_each_module(self):
        """Test sending results from each of the 4 modules independently."""
        # 1. Morphology
        res_m = self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        self.assertEqual(res_m.status_code, 200)
        self.assertIn("morphology", res_m.get_json()["session"]["modules"])

        # 2. Culture
        res_c = self.app.post('/api/laboratory/session', json=self.mock_culture_payload)
        self.assertEqual(res_c.status_code, 200)
        self.assertIn("culture", res_c.get_json()["session"]["modules"])

        # 3. Cell Fate
        res_f = self.app.post('/api/laboratory/session', json=self.mock_cell_fate_payload)
        self.assertEqual(res_f.status_code, 200)
        self.assertIn("cell_fate", res_f.get_json()["session"]["modules"])

        # 4. S-Index
        res_s = self.app.post('/api/laboratory/session', json=self.mock_sindex_payload)
        self.assertEqual(res_s.status_code, 200)
        self.assertIn("sindex", res_s.get_json()["session"]["modules"])

    def test_writing_all_modules_to_one_experiment_id(self):
        """Verify all 4 modules write to the same single Experiment ID."""
        self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        self.app.post('/api/laboratory/session', json=self.mock_culture_payload)
        self.app.post('/api/laboratory/session', json=self.mock_cell_fate_payload)
        self.app.post('/api/laboratory/session', json=self.mock_sindex_payload)

        get_res = self.app.get('/api/laboratory/session')
        self.assertEqual(get_res.status_code, 200)
        session = get_res.get_json()["session"]

        self.assertEqual(session["experiment_id"], "EXP-2026-8492")
        self.assertEqual(len(session["modules"]), 4)
        self.assertEqual(session["status_matrix"]["morphology"], "Completed")
        self.assertEqual(session["status_matrix"]["culture"], "Completed")
        self.assertEqual(session["status_matrix"]["cell_fate"], "Completed")
        self.assertEqual(session["status_matrix"]["sindex"], "Completed")

    def test_updating_existing_module_without_duplication(self):
        """Verify updating an existing module updates that block without creating duplicate keys."""
        # First send
        self.app.post('/api/laboratory/session', json=self.mock_culture_payload)
        
        # Updated send
        updated_culture = dict(self.mock_culture_payload)
        updated_culture["culture_score"] = "98 / 100"
        self.app.post('/api/laboratory/session', json=updated_culture)

        session = self.app.get('/api/laboratory/session').get_json()["session"]
        self.assertEqual(len(session["modules"]), 1)
        self.assertEqual(session["modules"]["culture"]["culture_score"], "98 / 100")
        self.assertEqual(session["status_matrix"]["culture"], "Updated")

    def test_export_json(self):
        """Verify JSON export returns complete structured experiment session."""
        self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        res = self.app.get('/api/laboratory/export?format=json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("export_format"), "JSON")
        self.assertIn("session", data)

    def test_export_pdf(self):
        """Verify PDF export returns valid PDF binary content starting with %PDF-."""
        self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        self.app.post('/api/laboratory/session', json=self.mock_culture_payload)

        res = self.app.get('/api/laboratory/export?format=pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'application/pdf')
        self.assertTrue(res.data.startswith(b'%PDF-'))

    def test_export_html(self):
        """Verify HTML export returns browser-readable HTML report."""
        self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        self.app.post('/api/laboratory/session', json=self.mock_cell_fate_payload)

        res = self.app.get('/api/laboratory/export?format=html')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content_type.startswith('text/html'))
        html_str = res.get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("CoreAI BIO — Multi-Module AI Laboratory Report", html_str)
        self.assertIn("EXP-2026-8492", html_str)

    def test_handling_incomplete_experiments(self):
        """Verify incomplete experiments with some Not Started modules are handled gracefully."""
        self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        session = self.app.get('/api/laboratory/session').get_json()["session"]

        self.assertEqual(session["status_matrix"]["morphology"], "Completed")
        self.assertEqual(session["status_matrix"]["culture"], "Not Started")
        self.assertEqual(session["status_matrix"]["cell_fate"], "Not Started")
        self.assertEqual(session["status_matrix"]["sindex"], "Not Started")
        self.assertIn("Cell Morphology", session["integrated_synthesis"])

    def test_preventing_unsupported_biological_causal_claims(self):
        """Verify unlinked module transfers contain the mandatory scientific independence guardrail."""
        self.app.post('/api/laboratory/session', json=self.mock_morphology_payload)
        self.app.post('/api/laboratory/session', json=self.mock_culture_payload)

        session = self.app.get('/api/laboratory/session').get_json()["session"]
        synthesis = session.get("integrated_synthesis", "")

        self.assertIn("Scientific Independence Guardrail", synthesis)
        self.assertIn("No biological causal relationship", synthesis)

if __name__ == '__main__':
    unittest.main()
