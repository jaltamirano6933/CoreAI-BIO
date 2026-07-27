# Cell Fate Analyzer (Beta) — Module Documentation

**Module:** CoreAI BIO — Phase 5: Cell Fate Analyzer (Beta)  
**Service Component:** `backend/cell_fate_service.py`  
**Dataset:** `dataset/cell_fate/GSE290316_hypo_TPM.csv.gz`  
**Date:** July 2026  

---

## 1. Executive Summary

The **Cell Fate Analyzer (Beta)** is a high-performance exploratory analysis subsystem within CoreAI BIO designed specifically for TPM-normalized RNA-seq gene expression profiling. It processes compressed `.csv.gz` expression matrices, performs rigorous gene symbol validation, detects and applies $\log_2(\text{TPM}+1)$ transformations, extracts top variable genes, computes sample-to-sample correlation matrices, and projects sample relationships into 2D Principal Component space.

---

## 2. Dataset Specification

- **File Path:** `dataset/cell_fate/GSE290316_hypo_TPM.csv.gz`
- **Data Type:** Transcripts Per Million (TPM) pre-normalized RNA-seq expression matrix.
- **Dimensions:** $32,650$ unique validated genes across $6$ RNA-seq sample replicates.
- **Sample Replicates:**
  1. `hypoTOs-1`
  2. `hypoTOs-2`
  3. `hypoTOs-3`
  4. `hypo-2`
  5. `hypo-2.1`
  6. `hypo-2.2`

---

## 3. Data Processing Pipeline

```text
[ GSE290316_hypo_TPM.csv.gz ]
             │
             ▼ (Gzip CSV Decompression)
[ Validate Gene Symbols & Remove Nulls ]
             │
             ▼ (Group & Average Duplicate Genes)
[ Check Un-logged Raw TPM vs Log Transformed ]
             │  (If max(TPM) > 50 -> Apply log2(TPM + 1))
             ▼
[ Expression Matrix E in R^(32650 x 6) ]
    ├──► Summary Statistics (Mean: 1.5078, Median: 0.1916, Variance: 4.3787)
    ├──► Variance Ranking (Top 50 Most Variable Genes)
    ├──► 2D PCA Decomposition (PCA fit on 6 sample vectors)
    └──► Pearson Correlation Matrix (6 x 6 Pairwise Correlations)
```

---

## 4. Key Assumptions & Safeguards

1. **TPM Pre-Normalization:** The dataset contains TPM-normalized transcript abundances. Count-based normalization algorithms (DESeq2, edgeR, CPM, RPM) are **strictly prohibited** and were not applied.
2. **Log Transformation Rule:** Un-logged TPM values span several orders of magnitude (e.g. $0.0$ to $110.95$). Applying $\log_2(\text{TPM} + 1)$ stabilizes variance and reduces skewness without distorting zero-expression values.
3. **Duplicate Symbol Handling:** In instances where multiple rows share identical gene symbols, expression values are aggregated via group-wise mean averaging.
4. **Scope Boundaries:** UMAP, unsupervised clustering, differential expression, and machine learning classification were intentionally excluded per Phase 5 design specifications.

---

## 5. Differential Gene Expression (DGE) & Pathway Enrichment Workflow (Phase 5B)

Phase 5B performs an exploratory differential expression contrast between two detected biological sample replicate groups:
- **Group A (hypoTOs):** `['hypoTOs-1', 'hypoTOs-2', 'hypoTOs-3']` ($N_A=3$)
- **Group B (hypo):** `['hypo-2', 'hypo-2.1', 'hypo-2.2']` ($N_B=3$)

```text
[ Input: GSE290316_hypo_TPM.csv.gz (32650 Validated Genes x 6 Samples) ]
               │
               ▼
[ Transformation: Expression E_i,j = log2(TPM_i,j + 1.0) ]
               │
               ├──► Mean Group A: \bar{x}_A = mean(log2(TPM+1) in hypoTOs)
               └──► Mean Group B: \bar{x}_B = mean(log2(TPM+1) in hypo)
                       │
                       ▼
               [ log2 Fold Change: log2FC = \bar{x}_A - \bar{x}_B ]
                       │
                       ▼
               [ Welch's Two-Sample t-test (equal_var=False) ]
                       │
                       ▼
               [ Benjamini-Hochberg FDR Adjustment across 32,650 genes ]
                       │
                       ├──► Upregulated: log2FC >= 0.5 & p_adj <= 0.05 (34 Genes)
                       └──► Downregulated: log2FC <= -0.5 & p_adj <= 0.05 (51 Genes)
```

### 5.1 Fold Change Formulations & Scientific Validation
1. **Primary Log-Transformed Fold Change (Used in Analysis):**
   $$\text{log2FC} = \bar{x}_A - \bar{x}_B = \frac{1}{3} \sum_{i \in A} \log_2(\text{TPM}_i + 1) - \frac{1}{3} \sum_{j \in B} \log_2(\text{TPM}_j + 1)$$
   *Defined as the difference between group arithmetic means on the $\log_2(\text{TPM}+1)$ scale.*

2. **Reference Raw TPM Fold Change (Calculated for Audit):**
   $$\text{log2FC}_{\text{raw}} = \log_2 \left( \frac{\text{mean}(\text{raw TPM}_A) + \epsilon}{\text{mean}(\text{raw TPM}_B) + \epsilon} \right)$$
   *Note:* The log-difference of means ($\text{log2FC}$) dampens extreme high-expression outliers compared to the log ratio of raw means ($\text{log2FC}_{\text{raw}}$), providing greater variance stability across small sample sizes ($N=3$).

### 5.2 Statistical Testing & Multiple-Testing Correction
- **Welch's $t$-test:** Calculated per gene using unequal variance assumptions:
  $$t = \frac{\bar{x}_A - \bar{x}_B}{\sqrt{\frac{s_A^2}{3} + \frac{s_B^2}{3}}}$$
  *Zero-variance genes ($s_A^2 = s_B^2 = 0$) are assigned $t=0.0, p=1.0, p_{\text{adj}}=1.0$ safely.*
- **Benjamini-Hochberg FDR:** Applied simultaneously across all $32,650$ tested genes to bound false discovery rates:
  $$p_{(i)}^{\text{adj}} = \min_{j \ge i} \left( \frac{32650 \cdot p_{(j)}}{j} \right) \in [0.0, 1.0]$$

### 5.3 Over-Representation Analysis (ORA) Methodology
Functional pathway enrichment evaluates over-representation of significant DE genes ($k = 85$) against the full background universe ($N = 32,650$) via **Fisher's Exact Right-Tailed Test**:
$$\text{p-value} = \sum_{i=x}^{\min(k, m)} \frac{\binom{m}{i} \binom{N-m}{k-i}}{\binom{N}{k}}$$
Where $m$ is the pathway gene set size, $x$ is the DE gene overlap, $k$ is total DE genes, and $N$ is total background universe. Benjamini-Hochberg FDR correction is applied across all evaluated pathway terms.

### 5.4 Methodological Scope & Limitations
> ⚠️ **Notice:** This analysis is exploratory and is based on log-transformed TPM values with three biological replicates per group ($N=3$). Welch’s t-test serves as an approximate statistical comparison. For confirmatory RNA-seq differential expression, raw counts and dedicated negative binomial count-based models (e.g. DESeq2 or edgeR) are strongly recommended.

---

## 6. Reproducibility & CSV Result Export

Complete statistical test results are automatically exported upon processing to:
`static/results/cell_fate/dge_complete_results.csv`

### 6.1 Export Schema Specifications
- `Gene Symbol`: Official HGNC gene symbol
- `Mean hypoTOs`: Mean expression in Group A ($\log_2(\text{TPM}+1)$)
- `Mean hypo`: Mean expression in Group B ($\log_2(\text{TPM}+1)$)
- `log2FC`: Log2 Fold Change ($\bar{x}_A - \bar{x}_B$)
- `t-statistic`: Welch's $t$-test statistic
- `raw p-value`: Unadjusted two-tailed p-value
- `adjusted p-value`: Benjamini-Hochberg FDR adjusted p-value
- `significance classification`: Classification (`Upregulated`, `Downregulated`, `Not Significant`)
- `regulation direction`: Direction (`Upregulated`, `Downregulated`, `Unchanged`)

*Sorting Order:* Primary sort by `adjusted p-value` ascending, secondary sort by $|\text{log2FC}|$ descending.

---

## 7. Gene Annotation Architecture & Biological Interpretation

The **Biological Interpretation Module** is managed by `backend/gene_annotation_service.py`. It enriches the Top Variable & DE Genes matrices with functional biological metadata, cellular localizations, pathway mappings, Gene Ontology terms, and direct external links.

---

## 8. API Endpoints

| Endpoint | Method | Response Description | Status |
| :--- | :---: | :--- | :---: |
| `/api/fate/summary` | `GET` | Gene count ($32,650$), sample count ($6$), mean, median, variance | `200 OK` |
| `/api/fate/pca` | `GET` | 2D PCA sample coordinates and explained variance ratios | `200 OK` |
| `/api/fate/correlation` | `GET` | 6x6 Pearson sample correlation matrix | `200 OK` |
| `/api/fate/top-variable-genes` | `GET` | Top 50 most variable genes enriched with full biological annotations | `200 OK` |
| `/api/fate/gene/<gene_symbol>` | `GET` | Specific gene functional annotation, GO terms, and external links | `200 OK` |
| `/api/fate/dge/summary` | `GET` | DGE group breakdown, sample counts, up/down-regulated statistics | `200 OK` |
| `/api/fate/dge/genes` | `GET` | Enriched lists of top upregulated and downregulated DE genes | `200 OK` |
| `/api/fate/dge/pathways` | `GET` | Over-represented GO terms, KEGG, and Reactome functional pathways | `200 OK` |

## 10. Machine Learning Preview (Unsupervised Discovery — Phase 5C)

The **Machine Learning Preview** provides exploratory, unsupervised pattern discovery across sample expression profiles. It evaluates non-linear manifold embeddings and cluster partitioning without supervised training.

```text
[ Log2-Transformed Expression Matrix E (32650 x 6) ]
                         │
                         ▼
[ Select Top 500 Most Variable Genes (Ranked by Variance) ]
                         │
                         ├──► UMAP 2D Projection: (n_neighbors=3, min_dist=0.3)
                         └──► K-Means Clustering: (K=2, n_init=10, random_state=42)
                                 │
                                 ▼
                         [ Cluster 0: hypoTOs-1, hypoTOs-2, hypoTOs-3 ]
                         [ Cluster 1: hypo-2, hypo-2.1, hypo-2.2 ]
```

### 10.1 Variable Gene Selection & Model Parameters
* **Feature Dimension:** Top $500$ most variable genes across samples selected to mitigate noise and high-dimensional variance instability.
* **UMAP Projection:** $n\_components=2, n\_neighbors=3, min\_dist=0.3, \text{metric}=\text{'euclidean'}$.
* **K-Means Configuration:** $K=2, \text{n\_init}=10, \text{random\_state}=42$.

### 10.2 Sample Size Limitation & Omission of Supervised Classification
> ℹ️ **Exploratory ML Notice:** *“This is an exploratory unsupervised visualization based on six samples. It is not a validated cell fate prediction model. Supervised machine learning requires a substantially larger labeled dataset.”*
* **Rationale:** Supervised algorithms (e.g. Random Forest, XGBoost, Neural Networks, SHAP) require dozens to hundreds of independent biological samples to prevent severe overfitting. Supervised classification was intentionally omitted for Phase 5 to preserve scientific integrity.

---

## 11. Generated Visualizations (`static/results/cell_fate/`)

1. **`pca_plot.png`**: 2D Principal Component Analysis scatter plot displaying sample replicate clustering in PC1/PC2 space.
2. **`sample_correlation_heatmap.png`**: Heatmap displaying pairwise Pearson correlation values ($r \ge 0.80$).
3. **`expression_distribution.png`**: Histogram distribution of $\log_2(\text{TPM}+1)$ expression levels.
4. **`top_variable_genes.png`**: Horizontal bar plot highlighting top 20 most variable gene symbols.
5. **`volcano_plot.png`**: Volcano plot displaying $\text{log2FC}$ vs. $-\log_{10}(p_{\text{adj}})$.
6. **`dge_heatmap.png`**: Z-Score standardized expression heatmap of top DE genes across sample replicates.
7. **`top_upregulated_genes.png`**: Bar chart of top 15 upregulated genes ($\text{log2FC} \uparrow$).
8. **`top_downregulated_genes.png`**: Bar chart of top 15 downregulated genes ($\text{log2FC} \downarrow$).
9. **`umap_preview.png`**: 2D UMAP manifold projection scatter plot colored by K-Means cluster assignments ($K=2$).

---

## 8. Limitations & Future Roadmap

- **Annotation Fallback Strategy:** If an uncharacterized novel transcript or non-standard gene symbol cannot be resolved online, the system returns `"Annotation currently unavailable."` without interrupting or crashing the web application.
- **Phase 6 Roadmap:**
  - Implement UMAP non-linear dimensionality reduction.
  - Hierarchical clustering & sample dendrograms.
  - Differential Gene Expression (DGE) statistical testing.
  - Cell fate lineage state classification models.
