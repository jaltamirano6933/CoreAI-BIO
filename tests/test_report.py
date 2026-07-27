import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.report_service import report_service
from backend.app import app

class TestResearchReportGenerator(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_report_api_endpoint(self):
        res = self.app.get('/api/report/data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("cell_morphology", data)
        self.assertIn("culture_optimizer", data)
        self.assertIn("cell_fate", data)
        self.assertIn("ai_assistant_summary", data)

    def test_report_rendering_html(self):
        res = self.app.get('/report')
        self.assertEqual(res.status_code, 200)
        html_str = res.get_data(as_text=True)
        self.assertIn("Research Report Generator", html_str)
        self.assertIn("Export HTML Report", html_str)
        self.assertIn("Print / Export PDF", html_str)
        self.assertIn("This report provides automated research-oriented analytical summaries", html_str)

    def test_missing_data_graceful_handling(self):
        # Service call should complete cleanly and return valid payload structure
        report = report_service.generate_full_report()
        self.assertEqual(report.get("status"), "success")
        self.assertIn("metadata", report)
        self.assertEqual(len(report["ai_assistant_summary"]["paragraphs"]), 5)

    def test_export_functionality_structure(self):
        report = report_service.generate_full_report()
        self.assertIn("scientific_limitations", report)
        self.assertIn("disclaimer", report["scientific_limitations"])

if __name__ == '__main__':
    unittest.main()
