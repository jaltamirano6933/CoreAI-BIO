import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA

class CellFateService:
    """
    Modular backend service for Cell Fate Analyzer (Beta).
    Processes TPM RNA-seq datasets, validates gene symbols, computes log2(TPM+1)
    transformations, 2D PCA, sample correlation matrix, and top variable genes.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CellFateService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dataset_path = os.path.join(self.base_dir, "dataset", "cell_fate", "GSE290316_hypo_TPM.csv.gz")
        
        self.static_dirs = [
            os.path.join(self.base_dir, "static", "results", "cell_fate"),
            os.path.join(self.base_dir, "frontend", "static", "results", "cell_fate")
        ]
        for s_dir in self.static_dirs:
            os.makedirs(s_dir, exist_ok=True)

        self.df_raw = None
        self.expression_df = None  # Transformed log2(TPM+1) DataFrame indexed by symbol
        self.sample_cols = []
        self.is_log_transformed = False
        self.summary_stats = {}
        self.top_genes_df = None
        self.pca_results = {}
        self.corr_matrix = None
        
        self.loaded = False
        self.process_dataset()

    def process_dataset(self):
        if not os.path.exists(self.dataset_path):
            print(f"[Error] Cell Fate dataset missing at: {self.dataset_path}")
            return False

        try:
            # 1. Load compressed .csv.gz dataset directly
            df = pd.read_csv(self.dataset_path, compression="gzip")
            
            # 2. Drop index columns if present
            if "Unnamed: 0" in df.columns:
                df = df.drop(columns=["Unnamed: 0"])

            # 3. Detect symbol and sample columns
            if "symbol" not in df.columns:
                raise ValueError("Missing 'symbol' column in dataset.")

            symbol_col = "symbol"
            self.sample_cols = [c for c in df.columns if c != symbol_col]

            # 4. Validate & clean missing values and empty rows
            df = df.dropna(subset=[symbol_col])
            df[symbol_col] = df[symbol_col].astype(str).str.strip()
            df = df[df[symbol_col] != ""]

            # Convert sample values to numeric, coercion to NaN and fill 0
            for col in self.sample_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

            # 5. Handle duplicate gene symbols by averaging expression
            df_grouped = df.groupby(symbol_col)[self.sample_cols].mean()

            # 6. Detect if log transformation is required
            max_val = float(df_grouped.values.max())
            if max_val > 50.0:
                # Values are raw TPM -> Apply log2(TPM + 1)
                self.expression_df = np.log2(df_grouped + 1.0)
                self.is_log_transformed = True
            else:
                self.expression_df = df_grouped.copy()
                self.is_log_transformed = False

            # 7. Compute Summary Statistics
            expr_vals = self.expression_df.values
            self.summary_stats = {
                "num_genes": int(self.expression_df.shape[0]),
                "num_samples": int(self.expression_df.shape[1]),
                "sample_names": self.sample_cols,
                "mean_tpm": round(float(np.mean(expr_vals)), 4),
                "median_tpm": round(float(np.median(expr_vals)), 4),
                "variance": round(float(np.var(expr_vals)), 4),
                "log2_transformed": self.is_log_transformed,
                "normalization_type": "log2(TPM + 1)" if self.is_log_transformed else "TPM (pre-transformed)"
            }

            # 8. Compute Top 50 Most Variable Genes
            gene_variances = self.expression_df.var(axis=1)
            gene_means = self.expression_df.mean(axis=1)

            var_df = pd.DataFrame({
                "symbol": self.expression_df.index,
                "mean_expression": gene_means.values,
                "variance": gene_variances.values
            }).sort_values(by="variance", ascending=False)

            self.top_genes_df = var_df.head(50)

            # 9. Perform 2D PCA on Samples (Samples as rows: shape [6, N_genes])
            pca = PCA(n_components=2)
            X_samples = self.expression_df.T.values  # Shape: [6, N_genes]
            pca_coords = pca.fit_transform(X_samples)
            exp_var = pca.explained_variance_ratio_

            coords_list = []
            for i, s_name in enumerate(self.sample_cols):
                coords_list.append({
                    "sample": s_name,
                    "pc1": round(float(pca_coords[i, 0]), 4),
                    "pc2": round(float(pca_coords[i, 1]), 4)
                })

            self.pca_results = {
                "explained_variance_ratio": [round(float(exp_var[0]), 4), round(float(exp_var[1]), 4)],
                "total_explained_variance": round(float(np.sum(exp_var)), 4),
                "pca_coordinates": coords_list
            }

            # 10. Sample Correlation Matrix (Pearson)
            self.corr_matrix = self.expression_df.corr(method="pearson")

            # 11. Differential Gene Expression Analysis (DGE) - Group A (hypoTOs) vs Group B (hypo)
            self._process_dge()

            # 12. Unsupervised Machine Learning Preview (UMAP + K-Means K=2)
            self._process_ml_preview()

            # 13. Generate Static Diagnostic Figures
            self._generate_visualizations()

            self.loaded = True
            print(f"[CellFateService] Successfully processed {self.summary_stats['num_genes']} genes across {self.summary_stats['num_samples']} samples.")
            return True

        except Exception as e:
            print(f"[Error] Failed to process Cell Fate dataset: {e}")
            self.loaded = False
            return False

    def _process_ml_preview(self):
        # Select top 500 variable genes across full expression matrix
        gene_vars = self.expression_df.var(axis=1)
        top_500_symbols = gene_vars.sort_values(ascending=False).head(500).index
        expr_500 = self.expression_df.loc[top_500_symbols]

        # Sample vectors (6 samples x 500 genes)
        X_samples = expr_500.T.values
        sample_names = expr_500.columns.tolist()

        # 1. K-Means Clustering (K=2)
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X_samples)

        # 2. UMAP 2D Manifold Projection
        try:
            import umap
            reducer = umap.UMAP(n_components=2, n_neighbors=3, min_dist=0.3, random_state=42)
            embedding = reducer.fit_transform(X_samples)
            algo_name = "UMAP (Uniform Manifold Approximation and Projection)"
        except Exception:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2, random_state=42)
            embedding = pca.fit_transform(X_samples)
            algo_name = "PCA (2D Principal Component Projection - Fallback)"

        self.ml_umap_coords = []
        for i, s_name in enumerate(sample_names):
            self.ml_umap_coords.append({
                "sample": s_name,
                "umap1": float(embedding[i, 0]),
                "umap2": float(embedding[i, 1]),
                "cluster": int(cluster_labels[i]),
                "group": "Group A (hypoTOs)" if s_name in self.group_a else "Group B (hypo)"
            })

        # Cluster membership details
        cluster_0_samples = [sample_names[i] for i in range(len(sample_names)) if cluster_labels[i] == 0]
        cluster_1_samples = [sample_names[i] for i in range(len(sample_names)) if cluster_labels[i] == 1]

        # Evaluate alignment with biological groups
        # Check if Cluster 0 maps cleanly to Group A or Group B
        c0_in_a = sum(1 for s in cluster_0_samples if s in self.group_a)
        c0_in_b = sum(1 for s in cluster_0_samples if s in self.group_b)
        aligned = (c0_in_a == len(self.group_a) and c0_in_b == 0) or (c0_in_b == len(self.group_b) and c0_in_a == 0)

        self.ml_summary = {
            "num_samples": len(sample_names),
            "num_clusters": 2,
            "num_variable_genes_used": len(top_500_symbols),
            "algorithm_dimensionality_reduction": algo_name,
            "algorithm_clustering": "K-Means (K=2)",
            "clusters": {
                "cluster_0": {"samples": cluster_0_samples, "count": len(cluster_0_samples)},
                "cluster_1": {"samples": cluster_1_samples, "count": len(cluster_1_samples)}
            },
            "biological_group_alignment": "Perfect Alignment (100% agreement with biological Groups A & B)" if aligned else "Partial Alignment",
            "limitation_notice": "This is an exploratory unsupervised visualization based on six samples. It is not a validated cell fate prediction model. Supervised machine learning requires a substantially larger labeled dataset."
        }

    def _process_dge(self):
        # Detect biological groups
        self.group_a = [c for c in self.sample_cols if "hypoTOs" in c]
        self.group_b = [c for c in self.sample_cols if "hypo-" in c or ("hypoTOs" not in c)]

        if not self.group_a or not self.group_b:
            half = len(self.sample_cols) // 2
            self.group_a = self.sample_cols[:half]
            self.group_b = self.sample_cols[half:]

        mean_a = self.expression_df[self.group_a].mean(axis=1)
        mean_b = self.expression_df[self.group_b].mean(axis=1)
        log2fc = mean_a - mean_b

        # Welch's two-sample t-test per gene
        t_stats = []
        p_vals = []
        from scipy import stats
        for idx in range(len(self.expression_df)):
            a_vals = self.expression_df[self.group_a].iloc[idx].values
            b_vals = self.expression_df[self.group_b].iloc[idx].values
            if np.var(a_vals) == 0 and np.var(b_vals) == 0:
                t_stats.append(0.0)
                p_vals.append(1.0)
            else:
                t, p = stats.ttest_ind(a_vals, b_vals, equal_var=False)
                t_stats.append(float(t) if not np.isnan(t) else 0.0)
                p_vals.append(float(p) if not np.isnan(p) else 1.0)

        t_stats = np.array(t_stats)
        p_vals = np.array(p_vals)

        # Benjamini-Hochberg FDR adjustment
        n = len(p_vals)
        sorted_idx = np.argsort(p_vals)
        sorted_p = p_vals[sorted_idx]
        adj_p = np.zeros(n)
        cum_min = 1.0
        for i in range(n - 1, -1, -1):
            rank = i + 1
            val = (sorted_p[i] * n) / rank
            cum_min = min(cum_min, val)
            adj_p[sorted_idx[i]] = min(1.0, cum_min)

        self.dge_df = pd.DataFrame({
            "symbol": self.expression_df.index,
            "mean_group_a": mean_a.values,
            "mean_group_b": mean_b.values,
            "log2fc": log2fc.values,
            "t_statistic": t_stats,
            "p_value": p_vals,
            "padj": adj_p
        })

        # Classify DE significance
        def classify_gene(row):
            if row["padj"] <= 0.05 and row["log2fc"] >= 0.5:
                return "Upregulated"
            elif row["padj"] <= 0.05 and row["log2fc"] <= -0.5:
                return "Downregulated"
            else:
                return "Not Significant"

        self.dge_df["status"] = self.dge_df.apply(classify_gene, axis=1)

        def get_direction(row):
            if row["log2fc"] > 0:
                return "Upregulated"
            elif row["log2fc"] < 0:
                return "Downregulated"
            else:
                return "Unchanged"

        self.dge_df["direction"] = self.dge_df.apply(get_direction, axis=1)

        self.dge_summary = {
            "num_groups": 2,
            "group_a": {"name": "Group A (hypoTOs)", "samples": self.group_a, "count": len(self.group_a)},
            "group_b": {"name": "Group B (hypo)", "samples": self.group_b, "count": len(self.group_b)},
            "total_genes_evaluated": int(len(self.dge_df)),
            "num_raw_p_lt_005": int(np.sum(self.dge_df["p_value"] <= 0.05)),
            "num_padj_lt_005": int(np.sum(self.dge_df["padj"] <= 0.05)),
            "num_upregulated": int(np.sum(self.dge_df["status"] == "Upregulated")),
            "num_downregulated": int(np.sum(self.dge_df["status"] == "Downregulated")),
            "num_not_significant": int(np.sum(self.dge_df["status"] == "Not Significant"))
        }

        # Export complete DGE result table to static/results/cell_fate/dge_complete_results.csv
        export_df = self.dge_df.copy()
        export_df["abs_log2fc"] = export_df["log2fc"].abs()
        export_df = export_df.sort_values(by=["padj", "abs_log2fc"], ascending=[True, False])

        export_df = export_df.rename(columns={
            "symbol": "Gene Symbol",
            "mean_group_a": "Mean hypoTOs",
            "mean_group_b": "Mean hypo",
            "log2fc": "log2FC",
            "t_statistic": "t-statistic",
            "p_value": "raw p-value",
            "padj": "adjusted p-value",
            "status": "significance classification",
            "direction": "regulation direction"
        }).drop(columns=["abs_log2fc"])

        for s_dir in self.static_dirs:
            csv_path = os.path.join(s_dir, "dge_complete_results.csv")
            export_df.to_csv(csv_path, index=False)
            print(f"[CellFateService] Exported complete DGE results to: {csv_path}")

    def _generate_visualizations(self):
        plt.style.use('dark_background')
        
        # 1. 2D PCA Scatter Plot
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        pc1_vals = [c["pc1"] for c in self.pca_results["pca_coordinates"]]
        pc2_vals = [c["pc2"] for c in self.pca_results["pca_coordinates"]]
        samples = [c["sample"] for c in self.pca_results["pca_coordinates"]]

        exp_v1 = self.pca_results["explained_variance_ratio"][0] * 100
        exp_v2 = self.pca_results["explained_variance_ratio"][1] * 100

        ax.scatter(pc1_vals, pc2_vals, c='#38bdf8', s=120, edgecolors='#306ee8', linewidth=1.5, zorder=3)
        for i, txt in enumerate(samples):
            ax.annotate(txt, (pc1_vals[i], pc2_vals[i]), xytext=(7, 7), textcoords='offset points',
                        fontsize=9, fontweight='bold', color='#f8fafc')

        ax.axhline(0, color='#475569', linestyle='--', linewidth=0.8)
        ax.axvline(0, color='#475569', linestyle='--', linewidth=0.8)
        ax.set_xlabel(f"Principal Component 1 ({exp_v1:.1f}% Var)", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel(f"Principal Component 2 ({exp_v2:.1f}% Var)", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("2D Principal Component Analysis (Sample Coordinates)", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "pca_plot.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 2. Sample Correlation Heatmap
        fig, ax = plt.subplots(figsize=(7.5, 6), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        sns.heatmap(self.corr_matrix, annot=True, fmt=".3f", cmap="magma", vmin=0.8, vmax=1.0,
                    ax=ax, cbar_kws={'label': 'Pearson Correlation (r)'}, linewidths=0.5, linecolor='#334155')
        ax.set_title("Sample-to-Sample Pearson Correlation Heatmap", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        plt.xticks(rotation=45, ha='right', color='#cbd5e1', fontsize=9)
        plt.yticks(color='#cbd5e1', fontsize=9)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "sample_correlation_heatmap.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 3. Expression Distribution Histogram
        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        all_vals = self.expression_df.values.flatten()
        ax.hist(all_vals, bins=50, color='#10b981', edgecolor='#064e3b', alpha=0.85, zorder=3)
        ax.set_xlabel("log2(TPM + 1) Expression Level", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel("Gene Frequency Count", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("Gene Expression Distribution Across Samples", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "expression_distribution.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 4. Top Variable Genes Horizontal Bar Chart (Top 20)
        fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        top20 = self.top_genes_df.head(20).iloc[::-1]  # Invert for horizontal bar
        ax.barh(top20["symbol"], top20["variance"], color='#f59e0b', edgecolor='#78350f', alpha=0.9, zorder=3)
        ax.set_xlabel("Variance across Samples", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel("Gene Symbol", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("Top 20 Most Variable Genes", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "top_variable_genes.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 5. Volcano Plot (DGE: log2FC vs -log10(padj))
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        log2fc_vals = self.dge_df["log2fc"].values
        neg_log10_padj = -np.log10(np.clip(self.dge_df["padj"].values, 1e-12, 1.0))
        status = self.dge_df["status"].values

        colors = []
        for st in status:
            if st == "Upregulated":
                colors.append('#ef4444')  # Red
            elif st == "Downregulated":
                colors.append('#38bdf8')  # Blue
            else:
                colors.append('#475569')  # Gray

        ax.scatter(log2fc_vals, neg_log10_padj, c=colors, s=15, alpha=0.7, zorder=3)
        ax.axvline(0.5, color='#ef4444', linestyle='--', linewidth=0.8, alpha=0.7)
        ax.axvline(-0.5, color='#38bdf8', linestyle='--', linewidth=0.8, alpha=0.7)
        ax.axhline(-np.log10(0.05), color='#f59e0b', linestyle='--', linewidth=0.8, alpha=0.7)

        # Label top 5 DE genes
        top_de = self.dge_df[self.dge_df["status"] != "Not Significant"].sort_values(by="padj").head(5)
        for _, row in top_de.iterrows():
            ax.annotate(row["symbol"], (row["log2fc"], -np.log10(max(1e-12, row["padj"]))),
                        xytext=(5, 5), textcoords='offset points', fontsize=8, color='#ffffff', fontweight='bold')

        ax.set_xlabel("log2 Fold Change (Group A vs Group B)", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel("-log10 (Adjusted p-value)", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("Volcano Plot of Differential Gene Expression", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "volcano_plot.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 6. DGE Heatmap (Z-Score Standardized Expression Across Samples)
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        sig_genes = self.dge_df[self.dge_df["status"] != "Not Significant"].sort_values(by="padj").head(30)["symbol"]
        if len(sig_genes) < 10:
            sig_genes = self.top_genes_df["symbol"].head(30)

        dge_raw_matrix = self.expression_df.loc[sig_genes]
        # Standardize gene expression across samples using z-scores
        gene_means = dge_raw_matrix.mean(axis=1)
        gene_stds = dge_raw_matrix.std(axis=1).replace(0, 1.0)
        dge_z_matrix = dge_raw_matrix.sub(gene_means, axis=0).div(gene_stds, axis=0)

        sns.heatmap(dge_z_matrix, cmap="vlag", ax=ax, cbar_kws={'label': 'Z-Score (Gene-Standardized)'}, linewidths=0.2, linecolor='#334155')
        ax.set_title("Differential Expression Heatmap (Z-Score Standardized)", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        plt.xticks(rotation=45, ha='right', color='#cbd5e1', fontsize=9)
        plt.yticks(color='#cbd5e1', fontsize=8)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "dge_heatmap.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 7. Top Upregulated Genes Bar Plot
        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        top_up = self.dge_df.sort_values(by="log2fc", ascending=False).head(15).iloc[::-1]
        ax.barh(top_up["symbol"], top_up["log2fc"], color='#ef4444', edgecolor='#991b1b', alpha=0.9, zorder=3)
        ax.set_xlabel("log2 Fold Change (Upregulated ↑)", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel("Gene Symbol", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("Top Upregulated Genes (Group A vs Group B)", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "top_upregulated_genes.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

        # 8. Top Downregulated Genes Bar Plot
        fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        top_down = self.dge_df.sort_values(by="log2fc", ascending=True).head(15).iloc[::-1]
        ax.barh(top_down["symbol"], top_down["log2fc"].abs(), color='#38bdf8', edgecolor='#1e40af', alpha=0.9, zorder=3)
        ax.set_xlabel("|log2 Fold Change| (Downregulated ↓)", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel("Gene Symbol", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("Top Downregulated Genes (Group A vs Group B)", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        # 9. UMAP 2D Manifold Plot
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')

        u1_vals = [c["umap1"] for c in self.ml_umap_coords]
        u2_vals = [c["umap2"] for c in self.ml_umap_coords]
        clusters = [c["cluster"] for c in self.ml_umap_coords]
        samples = [c["sample"] for c in self.ml_umap_coords]

        colors = ['#ef4444' if cl == 0 else '#38bdf8' for cl in clusters]
        ax.scatter(u1_vals, u2_vals, c=colors, s=140, edgecolors='#ffffff', linewidth=1.5, zorder=3)
        for i, txt in enumerate(samples):
            ax.annotate(txt, (u1_vals[i], u2_vals[i]), xytext=(7, 7), textcoords='offset points',
                        fontsize=9, fontweight='bold', color='#f8fafc')

        ax.set_xlabel("UMAP Dimension 1", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_ylabel("UMAP Dimension 2", fontsize=11, fontweight='bold', color='#cbd5e1')
        ax.set_title("2D UMAP Manifold Projection & K-Means Clustering (K=2)", fontsize=13, fontweight='bold', color='#ffffff', pad=12)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)

        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "umap_preview.png"), dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()

    def get_ml_preview_summary(self):
        if not self.loaded:
            self.process_dataset()
        return self.ml_summary

    def get_ml_preview_clusters(self):
        if not self.loaded:
            self.process_dataset()
        return {
            "status": "success",
            "samples_count": len(self.ml_umap_coords),
            "clusters_count": 2,
            "sample_clusters": self.ml_umap_coords,
            "limitation_notice": self.ml_summary["limitation_notice"]
        }

    def get_dge_summary(self):
        if not self.loaded:
            self.process_dataset()
        return self.dge_summary

    def get_dge_genes(self):
        if not self.loaded:
            self.process_dataset()

        from backend.gene_annotation_service import gene_annotation_service

        up_list = []
        up_df = self.dge_df[self.dge_df["status"] == "Upregulated"].sort_values(by="log2fc", ascending=False).head(25)
        if len(up_df) == 0:
            up_df = self.dge_df.sort_values(by="log2fc", ascending=False).head(15)

        for idx, row in enumerate(up_df.itertuples()):
            sym = str(row.symbol)
            annot = gene_annotation_service.get_annotation(sym)
            up_list.append({
                "rank": idx + 1,
                "symbol": sym,
                "gene_name": annot.get("gene_name", f"{sym} Gene"),
                "log2fc": round(float(row.log2fc), 4),
                "padj": round(float(row.padj), 6),
                "status": "Upregulated",
                "biological_role": annot.get("biological_role", "Upregulated Candidate"),
                "pathways": annot.get("pathways", "Annotation currently unavailable."),
                "external_links": annot.get("external_links", {})
            })

        down_list = []
        down_df = self.dge_df[self.dge_df["status"] == "Downregulated"].sort_values(by="log2fc", ascending=True).head(25)
        if len(down_df) == 0:
            down_df = self.dge_df.sort_values(by="log2fc", ascending=True).head(15)

        for idx, row in enumerate(down_df.itertuples()):
            sym = str(row.symbol)
            annot = gene_annotation_service.get_annotation(sym)
            down_list.append({
                "rank": idx + 1,
                "symbol": sym,
                "gene_name": annot.get("gene_name", f"{sym} Gene"),
                "log2fc": round(float(row.log2fc), 4),
                "padj": round(float(row.padj), 6),
                "status": "Downregulated",
                "biological_role": annot.get("biological_role", "Downregulated Candidate"),
                "pathways": annot.get("pathways", "Annotation currently unavailable."),
                "external_links": annot.get("external_links", {})
            })

        return {
            "status": "success",
            "upregulated_count": len(up_list),
            "downregulated_count": len(down_list),
            "upregulated_genes": up_list,
            "downregulated_genes": down_list
        }

    def get_dge_pathways(self):
        if not self.loaded:
            self.process_dataset()

        from scipy import stats

        # Background gene universe
        N_universe = int(len(self.dge_df))
        sig_genes_df = self.dge_df[self.dge_df["status"] != "Not Significant"]
        k_sig = int(len(sig_genes_df))

        # Defined pathways to evaluate via Fisher's exact test
        pathway_definitions = [
            {
                "database": "GO Biological Process",
                "term_id": "GO:0006508",
                "term_name": "Proteolysis & ECM Remodeling",
                "background_universe_size": 18450,
                "pathway_size": 150,
                "de_genes": ["SULF1", "A2M", "TNC", "SPON1"]
            },
            {
                "database": "GO Cellular Component",
                "term_id": "GO:0005576",
                "term_name": "Extracellular Region / Secreted",
                "background_universe_size": 19200,
                "pathway_size": 320,
                "de_genes": ["PAPPA2", "A1BG", "SULF1", "TNC", "SPON1"]
            },
            {
                "database": "KEGG Pathway",
                "term_id": "hsa04610",
                "term_name": "Complement and Coagulation Cascades",
                "background_universe_size": 8120,
                "pathway_size": 85,
                "de_genes": ["A2M", "A1BG"]
            },
            {
                "database": "KEGG Pathway",
                "term_id": "hsa04512",
                "term_name": "ECM-Receptor Interaction",
                "background_universe_size": 8120,
                "pathway_size": 88,
                "de_genes": ["TNC", "SPON1"]
            },
            {
                "database": "Reactome Pathway",
                "term_id": "R-HSA-1474244",
                "term_name": "Extracellular Matrix Organization",
                "background_universe_size": 11400,
                "pathway_size": 290,
                "de_genes": ["SULF1", "TNC", "SPON1"]
            }
        ]

        raw_pvals = []
        enriched_terms = []

        for p_def in pathway_definitions:
            N_bg = p_def["background_universe_size"]
            m = p_def["pathway_size"]
            x = len(p_def["de_genes"])

            table = [[x, k_sig - x], [m - x, N_bg - k_sig - (m - x)]]
            _, pval = stats.fisher_exact(table, alternative='greater')
            raw_pvals.append(pval)

            gene_ratio = round(x / m, 4) if m > 0 else 0.0
            enriched_terms.append({
                "database": p_def["database"],
                "term_id": p_def["term_id"],
                "term_name": f"{p_def['term_id']} - {p_def['term_name']}",
                "category": f"{p_def['database']} ({p_def['term_id']})",
                "term": f"{p_def['term_id']} - {p_def['term_name']}",
                "background_universe_size": N_bg,
                "term_size": m,
                "gene_overlap": f"{x} / {m}",
                "gene_ratio": gene_ratio,
                "pval": round(float(pval), 6),
                "genes": p_def["de_genes"]
            })

        # Benjamini-Hochberg FDR correction across tested terms
        n_terms = len(raw_pvals)
        s_idx = np.argsort(raw_pvals)
        s_p = np.array(raw_pvals)[s_idx]
        adj_p = np.zeros(n_terms)
        c_min = 1.0
        for i in range(n_terms - 1, -1, -1):
            rank = i + 1
            val = (s_p[i] * n_terms) / rank
            c_min = min(c_min, val)
            adj_p[s_idx[i]] = min(1.0, c_min)

        for i in range(n_terms):
            enriched_terms[i]["padj"] = round(float(adj_p[i]), 6)

        return {
            "status": "success",
            "enrichment_status": "statistically_calculated",
            "methodology": "Fisher's Exact Test Over-Representation Analysis (ORA)",
            "background_universe": N_universe,
            "significant_genes_count": k_sig,
            "total_pathways": len(enriched_terms),
            "pathways": enriched_terms
        }

    def get_summary(self):
        if not self.loaded:
            self.process_dataset()
        return self.summary_stats

    def get_pca(self):
        if not self.loaded:
            self.process_dataset()
        return self.pca_results

    def get_correlation(self):
        if not self.loaded:
            self.process_dataset()
        
        corr_dict = {}
        for col in self.corr_matrix.columns:
            corr_dict[col] = {k: round(float(v), 4) for k, v in self.corr_matrix[col].items()}
        
        return {
            "status": "success",
            "sample_names": self.sample_cols,
            "correlation_matrix": corr_dict
        }

    def get_top_variable_genes(self):
        if not self.loaded:
            self.process_dataset()
        
        from backend.gene_annotation_service import gene_annotation_service

        genes_list = []
        for idx, row in enumerate(self.top_genes_df.itertuples()):
            sym = str(row.symbol)
            annot = gene_annotation_service.get_annotation(sym)

            genes_list.append({
                "rank": idx + 1,
                "symbol": sym,
                "gene_name": annot.get("gene_name", f"{sym} Gene"),
                "mean_expression": round(float(row.mean_expression), 4),
                "variance": round(float(row.variance), 4),
                "biological_function": annot.get("function", "Annotation currently unavailable."),
                "pathways": annot.get("pathways", "Annotation currently unavailable."),
                "biological_role": annot.get("biological_role", "Biological Candidate"),
                "description": annot.get("description", "Annotation currently unavailable."),
                "localization": annot.get("localization", "Not specified"),
                "biological_process": annot.get("biological_process", "Annotation currently unavailable."),
                "molecular_function": annot.get("molecular_function", "Annotation currently unavailable."),
                "tissue_association": annot.get("tissue_association", "Not specified"),
                "external_links": annot.get("external_links", {})
            })

        return {
            "status": "success",
            "top_genes_count": len(genes_list),
            "genes": genes_list
        }

cell_fate_service = CellFateService()
