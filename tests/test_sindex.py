import unittest
import sys
import os

# Append the project root to sys.path so backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.sindex_service import (
    load_scoring_rules,
    validate_dataset_metadata,
    calculate_category_scores,
    calculate_sindex
)

class TestSIndexService(unittest.TestCase):

    def setUp(self):
        # Define a mock complete dataset that satisfies all compliance checks (100 points)
        self.complete_metadata = {
            "title": "A highly compliant mock research dataset",
            "description": "This is a detailed description of the compliant dataset.",
            "repository": "Zenodo",
            "persistent_identifier": "doi:10.5281/zenodo.123456",
            "public_access": True,
            "raw_data_available": True,
            "processed_data_available": True,
            "machine_readable_format": True,
            "metadata_complete": True,
            "license": "CC-BY-4.0",
            "protocol_available": True,
            "publication_linked": True,
            "citation_count": 5,
            "reuse_count": 10,
            "version_information": "v1.0.0",
            "contact_information": "contact@mockresearch.org"
        }

        # Define an incomplete dataset
        self.incomplete_metadata = {
            "title": "Minimal draft dataset",
            "description": "",
            "repository": "",
            "persistent_identifier": "",
            "public_access": False,
            "raw_data_available": False,
            "processed_data_available": False,
            "machine_readable_format": False,
            "metadata_complete": False,
            "license": "",
            "protocol_available": False,
            "publication_linked": False,
            "citation_count": 0,
            "reuse_count": 0,
            "version_information": "",
            "contact_information": ""
        }

    def test_rules_loading(self):
        """Test that scoring rules load successfully and contain all six categories."""
        rules = load_scoring_rules()
        self.assertIn("categories", rules)
        categories = rules["categories"]
        expected_categories = [
            "findability", "accessibility", "interoperability", 
            "reusability", "documentation", "evidence_of_reuse"
        ]
        for cat in expected_categories:
            self.assertIn(cat, categories)

    def test_complete_metadata_scoring(self):
        """Test that complete metadata gets a perfect score (100) and is rated Excellent."""
        result = calculate_sindex(self.complete_metadata)
        self.assertEqual(result["final_score"], 100)
        self.assertEqual(result["normalized_score"], 1.0)
        self.assertEqual(result["rating"], "Excellent")
        self.assertEqual(len(result["weaknesses"]), 0)
        self.assertEqual(len(result["recommendations"]), 0)

    def test_incomplete_metadata_scoring(self):
        """Test that incomplete metadata receives a low score and is rated Needs Improvement."""
        result = calculate_sindex(self.incomplete_metadata)
        # Findability title check passes (5 points). All others fail.
        self.assertEqual(result["final_score"], 5)
        self.assertEqual(result["normalized_score"], 0.05)
        self.assertEqual(result["rating"], "Needs Improvement")
        self.assertGreater(len(result["weaknesses"]), 0)
        self.assertGreater(len(result["recommendations"]), 0)

    def test_invalid_metadata_types(self):
        """Test that passing invalid types raises TypeErrors."""
        # 1. Non-dict metadata
        with self.assertRaises(TypeError):
            validate_dataset_metadata("not a dictionary")

        # 2. Invalid string type
        invalid_title = self.complete_metadata.copy()
        invalid_title["title"] = 12345
        with self.assertRaises(TypeError):
            validate_dataset_metadata(invalid_title)

        # 3. Invalid boolean type
        invalid_access = self.complete_metadata.copy()
        invalid_access["public_access"] = "true"  # String instead of bool
        with self.assertRaises(TypeError):
            validate_dataset_metadata(invalid_access)

        # 4. Invalid integer type (passing float)
        invalid_citations = self.complete_metadata.copy()
        invalid_citations["citation_count"] = 5.5
        with self.assertRaises(TypeError):
            validate_dataset_metadata(invalid_citations)

        # 5. Invalid integer type (passing bool - Python treats bool as subclass of int)
        invalid_citations_bool = self.complete_metadata.copy()
        invalid_citations_bool["citation_count"] = True
        with self.assertRaises(TypeError):
            validate_dataset_metadata(invalid_citations_bool)

    def test_score_boundaries(self):
        """Test that score bounds are respected even if metadata contains inflated numeric values."""
        inflated_metadata = self.complete_metadata.copy()
        # Inflating citations and reuses should not push the score past 100
        inflated_metadata["citation_count"] = 99999
        inflated_metadata["reuse_count"] = 99999
        result = calculate_sindex(inflated_metadata)
        self.assertEqual(result["final_score"], 100)
        self.assertTrue(0 <= result["final_score"] <= 100)

        # Ensure empty/zero values result in bounds within [0, 100]
        empty_metadata = {}
        result = calculate_sindex(empty_metadata)
        self.assertEqual(result["final_score"], 0)
        self.assertTrue(0 <= result["final_score"] <= 100)

    def test_category_totals(self):
        """Test that individual category scores do not exceed their defined maximums."""
        scores = calculate_category_scores(self.complete_metadata)
        self.assertEqual(scores["findability"], 20)
        self.assertEqual(scores["accessibility"], 15)
        self.assertEqual(scores["interoperability"], 15)
        self.assertEqual(scores["reusability"], 20)
        self.assertEqual(scores["documentation"], 15)
        self.assertEqual(scores["evidence_of_reuse"], 15)

    def test_summary_aggregation_two_datasets(self):
        """Test summary aggregation calculations for two distinct datasets."""
        from backend.app import app
        client = app.test_client()
        
        res = client.post('/api/nih-sindex/audit', json={"source_type": "example"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        datasets = data.get("datasets", [])
        
        if len(datasets) >= 2:
            two_ds = datasets[:2]
            num_datasets = len(two_ds)
            unique_repos = len(set(d["metadata"].get("repository") for d in two_ds))
            total_fair = sum(d["fair_score"] for d in two_ds)
            avg_fair = round(total_fair / num_datasets, 1)
            total_sindex = sum(d["metrics"]["final_score"] for d in two_ds)
            avg_sindex = round((total_sindex / num_datasets) / 100.0, 2)
            
            self.assertEqual(num_datasets, 2)
            self.assertGreaterEqual(unique_repos, 1)
            self.assertGreater(avg_fair, 0)
            self.assertGreater(avg_sindex, 0)

    def test_empty_datasets_handling(self):
        """Test empty datasets payload returns valid empty-state response without crashing."""
        from backend.app import app
        client = app.test_client()
        res = client.post('/api/nih-sindex/audit', json={"source_type": "csv", "datasets": []})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")

    def test_sindex_audit_api_sources(self):
        """Test /api/nih-sindex/audit endpoint for GEO, DOI, and CSV modes."""
        from backend.app import app
        client = app.test_client()

        # DOI audit mode
        res_doi = client.post('/api/nih-sindex/audit', json={"source_type": "doi", "doi": "10.1038/s41587-023-01800-w"})
        self.assertEqual(res_doi.status_code, 200)
        data_doi = res_doi.get_json()
        self.assertEqual(data_doi["status"], "success")
        self.assertEqual(len(data_doi["datasets"]), 1)

        # CSV audit mode
        csv_payload = {
            "source_type": "csv",
            "datasets": [
                {"title": "CSV Dataset 1", "repository": "Zenodo", "id": "CSV-101"},
                {"title": "CSV Dataset 2", "repository": "Figshare", "id": "CSV-102"}
            ]
        }
        res_csv = client.post('/api/nih-sindex/audit', json=csv_payload)
        self.assertEqual(res_csv.status_code, 200)
        data_csv = res_csv.get_json()
        self.assertEqual(data_csv["status"], "success")
        self.assertEqual(len(data_csv["datasets"]), 2)

    def test_dynamic_scoring_variation(self):
        """Test that different datasets evaluate to distinct FAIR and S-Index scores."""
        meta_rich = {
            "title": "Advanced physiological maturation of iPSC-derived human cardiomyocytes using an algorithm-directed optimization",
            "description": "Induced pluripotent stem cell-derived cardiomyocytes hold tremendous promise for in vitro modeling... " * 5,
            "repository": "Gene Expression Omnibus (GEO)",
            "persistent_identifier": "GSE214617",
            "public_access": True,
            "raw_data_available": True,
            "processed_data_available": True,
            "machine_readable_format": True,
            "metadata_complete": True,
            "license": "CC-BY-4.0",
            "protocol_available": True,
            "publication_linked": True,
            "citation_count": 10,
            "reuse_count": 5,
            "version_information": "2026-07-01",
            "contact_information": "Researcher <res@univ.edu>",
            "description_length": 1250,
            "sample_count": 12,
            "supplementary_count": 3,
            "supplementary_formats": ["CSV", "XLSX"],
            "bioproject_present": True,
            "sra_present": True,
            "platform_annotated": True,
            "organism_annotated": True,
            "overall_design_present": True,
            "contributor_contact_complete": True
        }

        meta_sparse = {
            "title": "Short title",
            "description": "Minimal description.",
            "repository": "Gene Expression Omnibus (GEO)",
            "persistent_identifier": "GSE000000",
            "public_access": True,
            "raw_data_available": False,
            "processed_data_available": False,
            "machine_readable_format": True,
            "metadata_complete": False,
            "license": None,
            "protocol_available": False,
            "publication_linked": False,
            "citation_count": 0,
            "reuse_count": 0,
            "version_information": "N/A",
            "contact_information": None,
            "description_length": 20,
            "sample_count": 2,
            "supplementary_count": 0,
            "supplementary_formats": [],
            "bioproject_present": False,
            "sra_present": False,
            "platform_annotated": False,
            "organism_annotated": True,
            "overall_design_present": False,
            "contributor_contact_complete": False
        }

        score_rich = calculate_sindex(meta_rich)
        score_sparse = calculate_sindex(meta_sparse)

        self.assertNotEqual(score_rich["final_score"], score_sparse["final_score"])
        self.assertGreater(score_rich["final_score"], score_sparse["final_score"])

if __name__ == '__main__':
    unittest.main()
