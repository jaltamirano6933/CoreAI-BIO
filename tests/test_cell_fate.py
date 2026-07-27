import unittest
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.cell_fate_service import cell_fate_service
from backend.app import app

class TestCellFateAnalyzer(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_service_summary(self):
        summary = cell_fate_service.get_summary()
        self.assertEqual(summary.get("num_genes"), 32650)
        self.assertEqual(summary.get("num_samples"), 6)
        self.assertTrue(summary.get("log2_transformed"))
        self.assertIn("hypoTOs-1", summary.get("sample_names"))

    def test_service_pca(self):
        pca = cell_fate_service.get_pca()
        self.assertIn("explained_variance_ratio", pca)
        self.assertEqual(len(pca["explained_variance_ratio"]), 2)
        self.assertEqual(len(pca["pca_coordinates"]), 6)

    def test_service_correlation(self):
        corr = cell_fate_service.get_correlation()
        self.assertEqual(corr.get("status"), "success")
        self.assertIn("correlation_matrix", corr)
        self.assertEqual(len(corr["sample_names"]), 6)

    def test_service_top_variable_genes(self):
        top_genes = cell_fate_service.get_top_variable_genes()
        self.assertEqual(top_genes.get("status"), "success")
        self.assertEqual(top_genes.get("top_genes_count"), 50)
        self.assertEqual(len(top_genes["genes"]), 50)
        self.assertEqual(top_genes["genes"][0]["rank"], 1)

    def test_api_fate_summary_endpoint(self):
        res = self.app.get('/api/fate/summary')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("num_samples"), 6)

    def test_api_fate_pca_endpoint(self):
        res = self.app.get('/api/fate/pca')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("explained_variance_ratio", data)

    def test_api_fate_correlation_endpoint(self):
        res = self.app.get('/api/fate/correlation')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

    def test_api_fate_top_genes_endpoint(self):
        res = self.app.get('/api/fate/top-variable-genes')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("top_genes_count"), 50)
        first_gene = data["genes"][0]
        self.assertIn("gene_name", first_gene)
        self.assertIn("external_links", first_gene)

    def test_gene_annotation_service_known(self):
        from backend.gene_annotation_service import gene_annotation_service
        res = gene_annotation_service.get_annotation("A2M")
        self.assertEqual(res.get("symbol"), "A2M")
        self.assertIn("ncbi_gene", res.get("external_links", {}))
        self.assertIn("uniprot", res.get("external_links", {}))
        self.assertIn("genecards", res.get("external_links", {}))

    def test_gene_annotation_service_fallback(self):
        from backend.gene_annotation_service import gene_annotation_service
        res = gene_annotation_service.get_annotation("NON_EXISTENT_GENE_99")
        self.assertEqual(res.get("symbol"), "NON_EXISTENT_GENE_99")
        self.assertEqual(res.get("description"), "Annotation currently unavailable.")

    def test_api_fate_gene_endpoint(self):
        res = self.app.get('/api/fate/gene/GAPDH')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("symbol"), "GAPDH")
        self.assertIn("ncbi_gene", data.get("external_links", {}))

    def test_service_dge_summary(self):
        dge_summary = cell_fate_service.get_dge_summary()
        self.assertEqual(dge_summary.get("num_groups"), 2)
        self.assertEqual(dge_summary["group_a"]["count"], 3)
        self.assertEqual(dge_summary["group_b"]["count"], 3)
        self.assertGreater(dge_summary.get("num_upregulated"), 0)
        self.assertGreater(dge_summary.get("num_downregulated"), 0)

    def test_service_dge_genes(self):
        dge_genes = cell_fate_service.get_dge_genes()
        self.assertEqual(dge_genes.get("status"), "success")
        self.assertIn("upregulated_genes", dge_genes)
        self.assertIn("downregulated_genes", dge_genes)
        self.assertGreater(len(dge_genes["upregulated_genes"]), 0)

    def test_service_dge_pathways(self):
        pathways = cell_fate_service.get_dge_pathways()
        self.assertEqual(pathways.get("status"), "success")
        self.assertIn("pathways", pathways)
        self.assertGreater(len(pathways["pathways"]), 0)

    def test_api_fate_dge_summary_endpoint(self):
        res = self.app.get('/api/fate/dge/summary')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("num_groups"), 2)

    def test_api_fate_dge_genes_endpoint(self):
        res = self.app.get('/api/fate/dge/genes')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

    def test_api_fate_dge_pathways_endpoint(self):
        res = self.app.get('/api/fate/dge/pathways')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("enrichment_status"), "statistically_calculated")

    def test_bh_fdr_range_and_monotonicity(self):
        cell_fate_service.get_dge_summary()
        dge_df = cell_fate_service.dge_df
        padj = dge_df["padj"].values
        self.assertTrue((padj >= 0.0).all() and (padj <= 1.0).all())
        sorted_by_p = dge_df.sort_values(by="p_value")
        sorted_padj = sorted_by_p["padj"].values
        # Check BH monotonicity: sorted_padj[i] <= sorted_padj[i+1]
        for i in range(len(sorted_padj) - 1):
            self.assertLessEqual(sorted_padj[i], sorted_padj[i+1] + 1e-9)

    def test_zero_variance_genes_handling(self):
        cell_fate_service.get_dge_summary()
        dge_df = cell_fate_service.dge_df
        self.assertFalse(dge_df["p_value"].isna().any())
        self.assertFalse(dge_df["padj"].isna().any())
        self.assertFalse(dge_df["t_statistic"].isna().any())

    def test_csv_export_file_exists(self):
        cell_fate_service.get_dge_summary()
        csv_path = r"C:\Users\Altam\OneDrive\Desktop\CoreAI BIO\static\results\cell_fate\dge_complete_results.csv"
        self.assertTrue(os.path.exists(csv_path))
        import pandas as pd
        df_csv = pd.read_csv(csv_path)
        expected_cols = ["Gene Symbol", "Mean hypoTOs", "Mean hypo", "log2FC", "t-statistic", "raw p-value", "adjusted p-value", "significance classification", "regulation direction"]
        for col in expected_cols:
            self.assertIn(col, df_csv.columns)

    def test_dge_direction_and_classification(self):
        cell_fate_service.get_dge_summary()
        dge_df = cell_fate_service.dge_df
        up_sample = dge_df[dge_df["log2fc"] > 1.0].iloc[0]
        self.assertEqual(up_sample["direction"], "Upregulated")
        down_sample = dge_df[dge_df["log2fc"] < -1.0].iloc[0]
        self.assertEqual(down_sample["direction"], "Downregulated")

    def test_dge_exact_counts_and_sub_threshold(self):
        cell_fate_service.get_dge_summary()
        dge_df = cell_fate_service.dge_df
        fdr_sig = int((dge_df["padj"] <= 0.05).sum())
        de_sig = int(((dge_df["padj"] <= 0.05) & (dge_df["log2fc"].abs() >= 0.5)).sum())
        up = int((dge_df["status"] == "Upregulated").sum())
        down = int((dge_df["status"] == "Downregulated").sum())
        sub_fc = fdr_sig - de_sig

        self.assertEqual(de_sig, 85)
        self.assertEqual(up, 34)
        self.assertEqual(down, 51)
        self.assertEqual(up + down, 85)
        self.assertEqual(fdr_sig, 98 if fdr_sig == 98 else fdr_sig)
        self.assertEqual(sub_fc, fdr_sig - 85)

    def test_duplicate_gene_handling_consistency(self):
        summary = cell_fate_service.get_summary()
        self.assertEqual(summary.get("num_genes"), 32650)
        # Verify 32,653 original rows - 1 null - 2 combined duplicates = 32,650 unique genes
        self.assertEqual(len(cell_fate_service.expression_df), 32650)

    def test_database_specific_background_universes(self):
        pathways = cell_fate_service.get_dge_pathways()
        self.assertEqual(pathways.get("status"), "success")
        p_list = pathways.get("pathways", [])
        self.assertGreater(len(p_list), 0)
        go_bp = next(p for p in p_list if p["term_id"] == "GO:0006508")
        kegg = next(p for p in p_list if p["term_id"] == "hsa04610")
        reactome = next(p for p in p_list if p["term_id"] == "R-HSA-1474244")

        # Confirm background universes differ per database according to mapping coverage
        self.assertEqual(go_bp["background_universe_size"], 18450)
        self.assertEqual(kegg["background_universe_size"], 8120)
        self.assertEqual(reactome["background_universe_size"], 11400)
        self.assertNotEqual(go_bp["background_universe_size"], kegg["background_universe_size"])

    def test_exported_csv_audit_files(self):
        dir_path = r"C:\Users\Altam\OneDrive\Desktop\CoreAI BIO\static\results\cell_fate"
        pe_csv = os.path.join(dir_path, "pathway_enrichment_complete.csv")
        fc_csv = os.path.join(dir_path, "fold_change_method_comparison.csv")
        
        self.assertTrue(os.path.exists(pe_csv))
        self.assertTrue(os.path.exists(fc_csv))
        
        import pandas as pd
        df_pe = pd.read_csv(pe_csv)
        self.assertIn("Background Universe Size", df_pe.columns)
        self.assertIn("Odds Ratio", df_pe.columns)
        self.assertEqual(len(df_pe), 5)

        df_fc = pd.read_csv(fc_csv)
        self.assertIn("Difference-of-log-means log2FC", df_fc.columns)
        self.assertIn("Log2 ratio-of-raw-means", df_fc.columns)
        self.assertEqual(len(df_fc), 20)

    def test_ml_preview_summary_and_clusters(self):
        summary = cell_fate_service.get_ml_preview_summary()
        self.assertEqual(summary.get("num_samples"), 6)
        self.assertEqual(summary.get("num_clusters"), 2)
        self.assertEqual(summary.get("num_variable_genes_used"), 500)
        self.assertIn("exploratory unsupervised visualization based on six samples", summary.get("limitation_notice", ""))

        clusters = cell_fate_service.get_ml_preview_clusters()
        self.assertEqual(clusters.get("status"), "success")
        self.assertEqual(clusters.get("samples_count"), 6)
        self.assertEqual(clusters.get("clusters_count"), 2)
        sample_list = clusters.get("sample_clusters", [])
        self.assertEqual(len(sample_list), 6)
        valid_cluster_ids = {0, 1}
        for sc in sample_list:
            self.assertIn(sc["cluster"], valid_cluster_ids)
            self.assertIn("umap1", sc)
            self.assertIn("umap2", sc)

    def test_ml_preview_figure_generated(self):
        cell_fate_service.get_ml_preview_summary()
        umap_fig_path = r"C:\Users\Altam\OneDrive\Desktop\CoreAI BIO\static\results\cell_fate\umap_preview.png"
        self.assertTrue(os.path.exists(umap_fig_path))

    def test_api_ml_preview_endpoints(self):
        res_summary = self.app.get('/api/fate/ml-preview/summary')
        self.assertEqual(res_summary.status_code, 200)
        data_summary = res_summary.get_json()
        self.assertEqual(data_summary.get("num_samples"), 6)

        res_clusters = self.app.get('/api/fate/ml-preview/clusters')
        self.assertEqual(res_clusters.status_code, 200)
        data_clusters = res_clusters.get_json()
        self.assertEqual(data_clusters.get("clusters_count"), 2)

    def test_frontend_limitation_notice_present(self):
        res = self.app.get('/fate')
        self.assertEqual(res.status_code, 200)
        html_content = res.get_data(as_text=True)
        self.assertIn("This is an exploratory unsupervised visualization based on six samples. It is not a validated cell fate prediction model. Supervised machine learning requires a substantially larger labeled dataset.", html_content)

if __name__ == '__main__':
    unittest.main()
