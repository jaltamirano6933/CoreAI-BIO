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

if __name__ == '__main__':
    unittest.main()
