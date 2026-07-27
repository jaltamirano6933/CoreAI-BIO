import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.assistant_service import assistant_service
from backend.app import app

class TestAILaboratoryAssistant(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_chat_endpoint(self):
        res = self.app.post('/api/assistant/chat', json={"query": "What does a volcano plot mean?"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("Volcano Plot", data.get("topic", ""))
        self.assertIn("suggested_followups", data)

    def test_question_routing_volcano(self):
        res = assistant_service.process_query("What does this volcano plot mean?")
        self.assertEqual(res["topic"], "Volcano Plot Interpretation")
        self.assertIn("Statistical Significance", res["response"])

    def test_question_routing_circularity(self):
        res = assistant_service.process_query("What is Circularity?")
        self.assertEqual(res["topic"], "Cell Morphology Measurements & Circularity")
        self.assertIn("Perimeter", res["response"])

    def test_question_routing_umap(self):
        res = assistant_service.process_query("What does UMAP show?")
        self.assertEqual(res["topic"], "2D UMAP Manifold Projection")
        self.assertIn("K-Means", res["response"])

    def test_question_routing_culture(self):
        res = assistant_service.process_query("Why is this culture classified as Near Confluent?")
        self.assertEqual(res["topic"], "Culture Optimization & Confluency Monitoring")
        self.assertIn("85%", res["response"])

    def test_unknown_question(self):
        res = assistant_service.process_query("What is quantum entanglement?")
        self.assertEqual(res["topic"], "Research Information Query")
        self.assertIn("Additional experimental validation is required", res["response"])

    def test_safety_medical_response(self):
        res = assistant_service.process_query("How do I treat a patient with this disease?")
        self.assertEqual(res["topic"], "Medical Safety Notice")
        self.assertIn("Medical Safety Policy", res["response"])
        self.assertIn("cannot recommend patient treatments", res["response"])

    def test_assistant_html_rendering(self):
        res = self.app.get('/assistant')
        self.assertEqual(res.status_code, 200)
        html_str = res.get_data(as_text=True)
        self.assertIn("This assistant provides educational and research-oriented explanations only.", html_str)

if __name__ == '__main__':
    unittest.main()
