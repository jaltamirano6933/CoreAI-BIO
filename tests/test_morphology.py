import unittest
import os
import sys
import io
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.morphology_service import morphology_service
from backend.ipsc_dataset_service import ipsc_dataset_service
from backend.app import app

class TestMorphologyTechnicalVsInterpretationSeparation(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        morphology_service._initialize_default_sample()

    def test_low_quality_image_separate_pipeline_and_interpretation_status(self):
        """
        Test that low-quality images separate Technical Completion (🟢 Completed) from Scientific Interpretation (🟡 Low):
        Must return pipeline_status: Completed, interpretation_confidence: Low, interpretation_status: Exploratory — Low Quality,
        interpretation_notes, and preserve all generated measurements, overlays, and figures.
        """
        blur_img = np.ones((400, 400, 3), dtype=np.uint8) * 80
        cv2.circle(blur_img, (200, 200), 15, (90, 90, 90), -1)
        blur_img = cv2.GaussianBlur(blur_img, (25, 25), 0)

        _, encoded = cv2.imencode('.jpg', blur_img)
        res = morphology_service.analyze_image_bytes(encoded.tobytes(), filename="Adipose_test_02.jpg", sample_type="adipose")

        self.assertEqual(res["status"], "success")
        self.assertTrue(res["analysis_completed"])
        self.assertEqual(res["pipeline_status"], "Completed")
        self.assertEqual(res["interpretation_confidence"], "Low")
        self.assertEqual(res["interpretation_status"], "Exploratory — Low Quality")

        self.assertIn("interpretation_notes", res)
        self.assertIn("The morphology pipeline completed successfully", res["interpretation_notes"])

        # Preserve all computational outputs
        self.assertIn("figures", res)
        self.assertIn("original", res["figures"])
        self.assertIn("contours", res["figures"])
        self.assertIn("cell_measurements", res)

    def test_stem_cell_primary_profile_and_measurements(self):
        """Test Primary Validated Stem Cell profile."""
        img = np.ones((400, 400, 3), dtype=np.uint8) * 20
        cv2.circle(img, (150, 150), 30, (50, 200, 100), -1)
        cv2.circle(img, (250, 150), 30, (50, 200, 100), -1)
        cv2.circle(img, (150, 250), 30, (50, 200, 100), -1)
        cv2.circle(img, (250, 250), 30, (50, 200, 100), -1)

        _, encoded = cv2.imencode('.png', img)
        res = morphology_service.analyze_image_bytes(encoded.tobytes(), filename="stem_cell_sample.png", sample_type="stem_cell")

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["pipeline_status"], "Completed")
        self.assertEqual(res["profile_used"], "stem_cell")
        self.assertEqual(res["interpretation_confidence"], "High")

    def test_unable_to_analyze_reserved_for_technical_failures(self):
        """Test that Unable to Analyze is reserved exclusively for corrupted files or backend exceptions."""
        corrupted_bytes = b"CORRUPTED_NON_IMAGE_DATA_BYTES_12345"
        with self.assertRaises(ValueError) as ctx:
            morphology_service.analyze_image_bytes(corrupted_bytes, filename="corrupt.dat")
        self.assertIn("Unsupported or corrupted image file", str(ctx.exception))

    def test_generated_and_uploaded_image_urls_return_http_200(self):
        """
        Test that generated morphology figures and uploaded images return HTTP 200 OK from Flask static route.
        """
        img = np.ones((400, 400, 3), dtype=np.uint8) * 20
        cv2.circle(img, (200, 200), 40, (50, 200, 100), -1)
        _, encoded = cv2.imencode('.png', img)
        
        # Test HTTP POST upload
        data = {
            'sample_type': 'stem_cell',
            'image': (io.BytesIO(encoded.tobytes()), 'test_upload_http.png')
        }
        res = self.app.post('/api/morphology/analyze', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        
        self.assertEqual(res_json["status"], "success")
        self.assertIn("figures", res_json)
        
        figures = res_json["figures"]
        for key, figure_url in figures.items():
            self.assertTrue(figure_url.startswith('/static/results/morphology/'))
            self.assertNotIn('\\', figure_url)
            self.assertNotIn('C:', figure_url)
            
            fig_res = self.app.get(figure_url)
            self.assertEqual(fig_res.status_code, 200, f"Figure URL {figure_url} returned status {fig_res.status_code}")

        uploaded_url = res_json.get("uploaded_image_url")
        if uploaded_url:
            self.assertTrue(uploaded_url.startswith('/static/uploads/morphology/'))
            self.assertNotIn('\\', uploaded_url)
            up_res = self.app.get(uploaded_url)
            self.assertEqual(up_res.status_code, 200, f"Uploaded URL {uploaded_url} returned status {up_res.status_code}")

if __name__ == '__main__':
    unittest.main()
