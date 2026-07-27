import unittest
from unittest.mock import patch, MagicMock
import os
import json
import time
import shutil
import sys
import urllib.error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.geo_service import (
    fetch_geo_metadata,
    parse_miniml_xml,
    parse_soft_text,
    CACHE_DIR,
    get_cache_path,
    detect_license
)
from backend.sindex_service import calculate_sindex
from backend.app import get_dataset_by_id

MOCK_MINIML_XML = """<?xml version="1.0" encoding="UTF-8"?>
<MINiML xmlns="http://www.ncbi.nlm.nih.gov/geo/info/MINiML">
  <Contributor iid="contrib1">
    <Person><First>John</First><Last>Doe</Last></Person>
    <Email>john@doe.com</Email>
    <Organization>Doe Org</Organization>
  </Contributor>
  <Platform iid="GPL24676">
    <Title>Illumina NovaSeq 6000 (Homo sapiens)</Title>
  </Platform>
  <Platform iid="GPL11111">
    <Title>Some Other Platform</Title>
  </Platform>
  <Sample iid="GSM1">
    <Accession>GSM1</Accession>
    <Organism>Homo sapiens</Organism>
  </Sample>
  <Sample iid="GSM2">
    <Accession>GSM2</Accession>
    <Organism>Mus musculus</Organism>
  </Sample>
  <Series iid="GSE214617">
    <Title>Test Study Title</Title>
    <Summary>This summary describes the study of protocol and license CC0.</Summary>
    <Overall-Design>Overall study design.</Overall-Design>
    <Status>
      <Submission-Date>2022-10-02</Submission-Date>
      <Release-Date>2022-10-05</Release-Date>
      <Last-Update-Date>2022-10-05</Last-Update-Date>
    </Status>
    <Type>Expression profiling by high throughput sequencing</Type>
    <Pubmed-ID>36200000</Pubmed-ID>
    <Relation type="BioProject" target="https://www.ncbi.nlm.nih.gov/bioproject/PRJNA886404"/>
    <Relation type="SRA" target="https://www.ncbi.nlm.nih.gov/sra/SRP400732"/>
    <Platform-Ref ref="GPL24676"/>
    <Platform-Ref ref="GPL11111"/>
    <Sample-Ref ref="GSM1"/>
    <Sample-Ref ref="GSM2"/>
    <Contact-Ref ref="contrib1"/>
    <Supplementary-Data type="XLSX">ftp://ftp.ncbi.nlm.nih.gov/geo/suppl/GSE214617_counts.xlsx</Supplementary-Data>
  </Series>
</MINiML>"""

MOCK_SOFT_TXT = """^SERIES = GSE290316
!Series_title = High-throughput screening of cortical neurons
!Series_geo_accession = GSE290316
!Series_status = Public on Jan 16 2025
!Series_submission_date = Jan 15 2025
!Series_last_update_date = Jan 16 2025
!Series_contact_name = PI,Stress
!Series_contact_email = pi_stress@institute.org
!Series_contact_institute = Stress Institute
!Series_summary = Viability profiling of primary cortical neurons.
!Series_sample_id = GSM999991
!Series_platform_id = GPL24676
!Series_type = Expression profiling
"""

MOCK_PUBMED_JSON = """{
  "result": {
    "36200000": {
      "title": "A highly cited scientific article",
      "source": "Nature Biotechnology",
      "pubdate": "2022 Oct",
      "authors": [
        {"name": "Doe J"},
        {"name": "Smith A"}
      ],
      "articleids": [
        {"idtype": "doi", "value": "10.1038/s12345"},
        {"idtype": "pubmed", "value": "36200000"}
      ]
    }
  }
}"""

class TestGeoService(unittest.TestCase):

    def setUp(self):
        # Backup existing cache files to avoid wiping actual development cache
        self.temp_cache_dir = CACHE_DIR + "_temp_test_backup"
        if os.path.exists(CACHE_DIR):
            if os.path.exists(self.temp_cache_dir):
                shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
            try:
                shutil.copytree(CACHE_DIR, self.temp_cache_dir, dirs_exist_ok=True)
                shutil.rmtree(CACHE_DIR, ignore_errors=True)
            except Exception:
                pass
        os.makedirs(CACHE_DIR, exist_ok=True)

    def tearDown(self):
        # Restore cache backup
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
        if os.path.exists(self.temp_cache_dir):
            try:
                shutil.copytree(self.temp_cache_dir, CACHE_DIR, dirs_exist_ok=True)
                shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
            except Exception:
                pass

    @patch('backend.geo_service.make_http_request')
    def test_1_valid_gse_accession(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata("GSE214617")
        self.assertNotIn("error", result)
        self.assertEqual(result["accession"], "GSE214617")
        self.assertEqual(result["source_mode"], "Live NCBI GEO Metadata")

    @patch('backend.geo_service.make_http_request')
    def test_2_lowercase_input_normalization(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata(" gse214617 ")
        self.assertNotIn("error", result)
        self.assertEqual(result["accession"], "GSE214617")

    def test_3_invalid_accession(self):
        res = fetch_geo_metadata("GSM123456")
        self.assertIn("error", res)
        self.assertIn("format", res["error"].lower())

        res2 = fetch_geo_metadata("GSEabc")
        self.assertIn("error", res2)

        res3 = fetch_geo_metadata("")
        self.assertIn("error", res3)

    @patch('backend.geo_service.make_http_request')
    def test_4_geo_record_not_found(self, mock_http):
        # Simulate 404 HTTP Error
        mock_http.side_effect = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        result = fetch_geo_metadata("GSE999999")
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_5_successful_miniml_parsing(self):
        res = parse_miniml_xml(MOCK_MINIML_XML)
        self.assertEqual(res["accession"], "GSE214617")
        self.assertEqual(res["title"], "Test Study Title")
        self.assertEqual(res["summary"], "This summary describes the study of protocol and license CC0.")
        self.assertEqual(res["bioproject_accession"], "PRJNA886404")
        self.assertEqual(res["sra_accession"], "SRP400732")

    def test_6_soft_fallback_parsing(self):
        res = parse_soft_text(MOCK_SOFT_TXT)
        self.assertEqual(res["accession"], "GSE290316")
        self.assertEqual(res["title"], "High-throughput screening of cortical neurons")
        self.assertEqual(res["sample_count"], 1)

    def test_7_multiple_organisms(self):
        res = parse_miniml_xml(MOCK_MINIML_XML)
        self.assertEqual(res["organism"], "Homo sapiens, Mus musculus")

    def test_8_multiple_platforms(self):
        res = parse_miniml_xml(MOCK_MINIML_XML)
        self.assertEqual(res["platform_accession"], "GPL24676, GPL11111")

    def test_9_sample_count(self):
        res = parse_miniml_xml(MOCK_MINIML_XML)
        self.assertEqual(res["sample_count"], 2)

    @patch('backend.geo_service.make_http_request')
    def test_10_linked_pubmed_record(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata("GSE214617")
        self.assertEqual(result["doi"], "10.1038/s12345")
        self.assertIn("A highly cited scientific article", result["publication_title"])
        self.assertIn("Nature Biotechnology", result["publication_title"])
        self.assertIn("2022", result["publication_title"])
        self.assertIn("Doe J, Smith A", result["publication_title"])

    @patch('backend.geo_service.make_http_request')
    def test_11_no_pubmed_record(self, mock_http):
        # Simulate SOFT record with no pubmed_id
        mock_http.side_effect = [Exception("XML not found"), MOCK_SOFT_TXT]
        result = fetch_geo_metadata("GSE290316")
        self.assertEqual(result["doi"], "No linked publication found")
        self.assertEqual(result["publication_title"], "No linked publication found")

    def test_12_missing_license_remains_unavailable(self):
        # SOFT mock has no license keyword
        res = parse_soft_text(MOCK_SOFT_TXT)
        self.assertIsNone(detect_license(res["summary"]))

    @patch('backend.geo_service.make_http_request')
    def test_13_raw_data_detection(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata("GSE214617")
        self.assertTrue(result["raw_data_available"])
        self.assertTrue(result["normalized"]["raw_data_available"])

    @patch('backend.geo_service.make_http_request')
    def test_14_processed_data_detection(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata("GSE214617")
        self.assertTrue(result["processed_data_available"])
        self.assertTrue(result["normalized"]["processed_data_available"])

    @patch('backend.geo_service.make_http_request')
    def test_15_timeout_with_cache_fallback(self, mock_http):
        # Save a record into cache manually first
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        fetch_geo_metadata("GSE214617")
        
        # Make subsequent request raise a timeout exception
        mock_http.side_effect = Exception("NCBI Connection Timeout")
        result = fetch_geo_metadata("GSE214617")
        
        self.assertNotIn("error", result)
        self.assertEqual(result["accession"], "GSE214617")
        # Ensure it notes it came from cache fallback
        self.assertEqual(result["source_mode"], "Cached NCBI GEO Metadata")

    @patch('backend.geo_service.make_http_request')
    def test_16_timeout_without_cache(self, mock_http):
        mock_http.side_effect = Exception("NCBI Connection Timeout")
        result = fetch_geo_metadata("GSE214617")
        self.assertIn("error", result)
        self.assertIn("timeout", result["error"].lower())

    def test_17_malformed_xml(self):
        with self.assertRaises(Exception):
            parse_miniml_xml("<invalid><xml>")

    def test_18_no_silent_fallback_to_sample_datasets(self):
        # Querying app for live-only GSE214617 bypasses sample_datasets.json
        # get_dataset_by_id returns a result indicating Live/Cached GEO Metadata instead of local config
        with patch('backend.geo_service.fetch_geo_metadata') as mock_fetch:
            mock_fetch.return_value = {
                "accession": "GSE214617",
                "normalized": {
                    "title": "Live Title",
                    "description": "Live Desc",
                    "repository": "Gene Expression Omnibus (GEO)",
                    "persistent_identifier": "GSE214617",
                    "public_access": True,
                    "raw_data_available": True,
                    "processed_data_available": True,
                    "machine_readable_format": True,
                    "metadata_complete": True,
                    "license": None,
                    "protocol_available": True,
                    "publication_linked": False,
                    "citation_count": 0,
                    "reuse_count": 0,
                    "version_information": "2022-10-05",
                    "contact_information": "Some contact"
                },
                "provenance": {"title": {"source": "NCBI GEO"}},
                "source_mode": "Live NCBI GEO Metadata"
            }
            res = get_dataset_by_id("GSE214617")
            self.assertIsNotNone(res)
            self.assertEqual(res["source_mode"], "Live NCBI GEO Metadata")
            # Verify it did not load the local mockup title which is "Single-cell transcriptome profiling..."
            self.assertEqual(res["metadata"]["title"], "Live Title")

    @patch('backend.geo_service.make_http_request')
    def test_19_sindex_calculation_using_normalized_live_metadata(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata("GSE214617")
        scores = calculate_sindex(result["normalized"])
        self.assertIn("final_score", scores)
        self.assertGreaterEqual(scores["final_score"], 0)
        self.assertLessEqual(scores["final_score"], 100)

    @patch('backend.geo_service.make_http_request')
    def test_20_provenance_for_every_normalized_field(self, mock_http):
        mock_http.side_effect = [MOCK_MINIML_XML, MOCK_PUBMED_JSON]
        result = fetch_geo_metadata("GSE214617")
        prov = result["provenance"]
        normalized_keys = [
            "title", "description", "repository", "persistent_identifier",
            "public_access", "raw_data_available", "processed_data_available",
            "machine_readable_format", "metadata_complete", "license",
            "protocol_available", "publication_linked", "citation_count",
            "reuse_count", "version_information", "contact_information"
        ]
        for key in normalized_keys:
            self.assertIn(key, prov)
            self.assertIn("value", prov[key])
            self.assertIn("source_name", prov[key])
            self.assertIn("source_url", prov[key])
            self.assertIn("source_format", prov[key])
            self.assertIn("retrieval_timestamp_utc", prov[key])
            self.assertIn("confidence", prov[key])
            self.assertIn("raw_source_value", prov[key])
            self.assertIn("transformation_note", prov[key])

if __name__ == '__main__':
    unittest.main()
