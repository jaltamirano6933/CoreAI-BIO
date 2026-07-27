import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.culture_optimizer_service import culture_optimizer_service
from backend.app import app

class TestCultureOptimizer(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_summary_endpoint(self):
        res = self.app.get('/api/culture/summary')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data["confluency"], 85.0)
        self.assertEqual(data["quality_indicators"]["overall_culture_score"], 88)
        self.assertEqual(data["quality_indicators"]["risk_level"], "Low")
        self.assertIn("density_chart", data["figures"])

    def test_recommendations_endpoint(self):
        res = self.app.get('/api/culture/recommendations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertGreater(data.get("recommendations_count"), 0)
        recs = data.get("recommendations", [])
        actions = [r["action"] for r in recs]
        self.assertIn("Passage cells soon", actions)

    def test_rule_engine_logic(self):
        recs_data = culture_optimizer_service.get_recommendations()
        recs = recs_data["recommendations"]
        passage_rule = next((r for r in recs if r["rule_id"] == "R1_PASSAGE"), None)
        self.assertIsNotNone(passage_rule)
        self.assertEqual(passage_rule["priority"], "High")

    def test_chart_generation_files_exist(self):
        culture_optimizer_service.get_summary()
        base_dir = culture_optimizer_service.static_dirs[0]
        self.assertTrue(os.path.exists(os.path.join(base_dir, "density_over_time.png")))
        self.assertTrue(os.path.exists(os.path.join(base_dir, "confluency_over_time.png")))
        self.assertTrue(os.path.exists(os.path.join(base_dir, "culture_score_trend.png")))

    def test_dashboard_rendering_html(self):
        res = self.app.get('/culture')
        self.assertEqual(res.status_code, 200)
        html_str = res.get_data(as_text=True)
        self.assertIn("This module provides research-oriented culture monitoring recommendations and is not intended to replace laboratory protocols or expert judgment.", html_str)

    def test_formulation_prediction_post(self):
        payload = {"Glucose": 5.6, "FBS": 0.05}
        res = self.app.post('/api/culture/predict', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("prediction_status"), "success")
        self.assertIn("predicted_mean_A450_168h", data)

    def test_manual_input_summary_and_recommendations(self):
        payload = {
            "data_source": "manual",
            "cell_density": 2.50,
            "confluency": 92.0,
            "passage_number": 5,
            "incubator_temperature_c": 38.5,
            "co2_percent": 6.5,
            "relative_humidity_percent": 88.0,
            "culture_age_days": 5.0
        }
        res_sum = self.app.post('/api/culture/summary', json=payload)
        self.assertEqual(res_sum.status_code, 200)
        data_sum = res_sum.get_json()
        self.assertEqual(data_sum["data_source_label"], "Manual User Input")
        self.assertEqual(data_sum["confluency"], 92.0)
        self.assertEqual(data_sum["passage_number"], "P5")

        res_rec = self.app.post('/api/culture/recommendations', json=payload)
        self.assertEqual(res_rec.status_code, 200)
        data_rec = res_rec.get_json()
        self.assertEqual(data_rec["data_source_label"], "Manual User Input")
        actions = [r["action"] for r in data_rec["recommendations"]]
        self.assertIn("Verify incubator settings", actions)

if __name__ == '__main__':
    unittest.main()
