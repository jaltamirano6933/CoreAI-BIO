import re

class AssistantService:
    def __init__(self):
        self.disclaimer = "This assistant provides educational and research-oriented explanations only. It does not replace scientific review or clinical judgment."

    def process_query(self, query: str, context_module: str = None) -> dict:
        if not query or not query.strip():
            return {
                "status": "error",
                "message": "Empty query provided.",
                "disclaimer": self.disclaimer
            }

        q_clean = query.strip().lower()

        # Safety Check: Medical Diagnosis or Patient Treatment requests
        if any(word in q_clean for word in ["patient", "treat", "treatment", "cure", "diagnose", "diagnosis", "prescribe", "therapy"]):
            return {
                "status": "success",
                "query": query,
                "topic": "Medical Safety Notice",
                "module": "Safety Engine",
                "response": "⚠️ **Medical Safety Policy:** CoreAI BIO and the AI Laboratory Assistant provide educational and research-oriented analytical tools only. They cannot recommend patient treatments, prescribe therapy, or provide clinical medical diagnoses. Please consult a qualified healthcare professional or clinical protocols for medical guidance.",
                "suggested_followups": [
                    "What are the differential expression results in the dataset?",
                    "How does cell circularity evaluate morphology?",
                    "What does UMAP represent in unsupervised clustering?"
                ],
                "disclaimer": self.disclaimer
            }

        # 1. Cell Fate Analyzer — Volcano Plot
        if "volcano" in q_clean:
            return {
                "status": "success",
                "query": query,
                "topic": "Volcano Plot Interpretation",
                "module": "Cell Fate Analyzer (Differential Expression)",
                "response": "🌋 **Volcano Plot Overview:**\n"
                            r"A volcano plot displays Statistical Significance ($-\log_{10}(p_{\text{adj}})$) on the y-axis against Effect Size ($\log_2 \text{Fold Change}$) on the x-axis for all evaluated genes." "\n\n"
                            r"• **Red Dots (Upregulated):** Genes in top-right with $\log_2\text{FC} \ge 0.5$ and $p_{\text{adj}} \le 0.05$." "\n"
                            r"• **Blue Dots (Downregulated):** Genes in top-left with $\log_2\text{FC} \le -0.5$ and $p_{\text{adj}} \le 0.05$." "\n"
                            "• **Gray Dots (Not Significant):** Genes failing statistical significance thresholds.\n\n"
                            r"*In our dataset, 98 genes reached FDR significance ($p_{\text{adj}} \le 0.05$), with 85 satisfying fold-change cutoffs (34 upregulated, 51 downregulated).*",
                "suggested_followups": [
                    "Explain the Differential Expression results.",
                    "What pathways are enriched in the top DE genes?",
                    "Explain the difference between raw p-value and FDR."
                ],
                "disclaimer": self.disclaimer
            }

        # 2. Cell Fate Analyzer — Pathway Analysis (GO, KEGG, Reactome)
        if any(w in q_clean for w in ["pathway", "go", "kegg", "reactome", "enrichment", "ora"]):
            return {
                "status": "success",
                "query": query,
                "topic": "Functional Pathway & Over-Representation Analysis",
                "module": "Cell Fate Analyzer (Pathway Analysis)",
                "response": "🧬 **Biological Pathway & Functional Annotation:**\n"
                            "Pathway enrichment evaluates whether sets of differentially expressed (DE) genes are disproportionately involved in specific biological processes compared to background gene universes using Fisher's Exact Test.\n\n"
                            "• **Gene Ontology (GO:BP / GO:CC):** Hierarchical terms describing biological processes and cellular components.\n"
                            "• **KEGG:** Manually curated metabolic and signaling pathways.\n"
                            "• **Reactome:** Biomolecular reaction networks.\n\n"
                            r"*Enriched pathways are evaluated over database-specific background universes (e.g. $N_{\text{GO:BP}} = 18,450$). Statistically significant terms reflect activated cell fate mechanisms.*",
                "suggested_followups": [
                    "What does a volcano plot mean?",
                    "Explain top variable gene annotations.",
                    "What is UMAP?"
                ],
                "disclaimer": self.disclaimer
            }

        # 3. Cell Fate Analyzer — UMAP Projection
        if "umap" in q_clean:
            return {
                "status": "success",
                "query": query,
                "topic": "2D UMAP Manifold Projection",
                "module": "Cell Fate Analyzer (ML Preview)",
                "response": "🗺️ **UMAP (Uniform Manifold Approximation and Projection):**\n"
                            "UMAP is a non-linear dimension reduction technique that models local and global topological structure to project high-dimensional gene expression vectors into 2D space.\n\n"
                            "• **Clustering:** K-Means ($K=2$) on the top 500 variable genes cleanly partitions sample replicates into Cluster 0 (`hypoTOs`) and Cluster 1 (`hypo`).\n"
                            "• **Exploratory Scope:** This visualization shows unsupervised sample grouping ($N=6$). Supervised cell fate prediction requires substantially larger labeled cohorts.",
                "suggested_followups": [
                    "What is PCA?",
                    "Why are the sample groups different?",
                    "Explain the ML preview limitations."
                ],
                "disclaimer": self.disclaimer
            }

        # 4. Cell Fate Analyzer — PCA (Principal Component Analysis)
        if "pca" in q_clean:
            return {
                "status": "success",
                "query": query,
                "topic": "Principal Component Analysis (PCA)",
                "module": "Cell Fate Analyzer (Exploratory Analysis)",
                "response": "📉 **PCA (2D Principal Component Analysis):**\n"
                            "PCA is a linear orthogonal transformation that projects high-dimensional gene expression data onto uncorrelated axes (PC1 and PC2) capturing maximum variance.\n\n"
                            "• **PC1 Axis:** Captures primary variance between organoid replicates (`hypoTOs`) and standard tissue cultures (`hypo`).\n"
                            "• **PC2 Axis:** Captures secondary biological/technical variance across replicates.",
                "suggested_followups": [
                    "What does UMAP show?",
                    "Explain sample correlation heatmap.",
                    "What are the top variable genes?"
                ],
                "disclaimer": self.disclaimer
            }

        # 5. Cell Fate Analyzer — DGE / Differential Expression
        if any(w in q_clean for w in ["differential expression", "dge", "log2fc", "fold change"]):
            return {
                "status": "success",
                "query": query,
                "topic": "Differential Expression Analysis",
                "module": "Cell Fate Analyzer (DGE)",
                "response": "⚖️ **Differential Gene Expression (DGE):**\n"
                            "DGE quantifies changes in gene expression between biological conditions (Group A: `hypoTOs` vs Group B: `hypo`).\n\n"
                            r"• **Log2 Fold Change ($\log_2\text{FC}$):** Difference between mean $\log_2(\text{TPM}+1)$ expression levels." "\n"
                            r"• **Statistical Test:** Welch's two-sample t-test ($df \approx 3.75$) with Benjamini-Hochberg FDR correction." "\n"
                            r"• **Dataset Counts:** 85 DE genes ($p_{\text{adj}} \le 0.05, |\text{log2FC}| \ge 0.5$), including 34 upregulated and 51 downregulated genes.",
                "suggested_followups": [
                    "What does a volcano plot mean?",
                    "Explain pathway enrichment.",
                    "Explain top downregulated genes."
                ],
                "disclaimer": self.disclaimer
            }

        # 6. Cell Morphology — Circularity & Morphology Metrics
        if any(w in q_clean for w in ["circularity", "morphology", "solidity", "aspect ratio", "perimeter", "contour"]):
            return {
                "status": "success",
                "query": query,
                "topic": "Cell Morphology Measurements & Circularity",
                "module": "Cell Morphology",
                "response": "🔬 **Cell Morphometric Descriptors:**\n"
                            "Computer vision contour extraction calculates key shape parameters for segmented cells:\n\n"
                            "• **Circularity ($C$):** $C = \\frac{4 \\pi \\cdot \\text{Area}}{\\text{Perimeter}^2} \\in (0, 1.0]$. Values near 1.0 indicate perfect circular boundaries; lower values indicate elongation or irregular membrane ruffling.\n"
                            "• **Aspect Ratio ($AR$):** Ratio of bounding rectangle width to height ($W/H$).\n"
                            "• **Solidity ($S$):** Ratio of cell area to its convex hull area (quantifies boundary roughness).\n"
                            "• **Classification:** Rules classify cells into `Healthy` ($C \\ge 0.75, S \\ge 0.85$), `Differentiating`, `Irregular`, or `Low Quality Image`.",
                "suggested_followups": [
                    "Interpret the morphology measurements.",
                    "How is image quality assessed?",
                    "What is image sharpness?"
                ],
                "disclaimer": self.disclaimer
            }

        # 7. Culture Optimizer — Confluency & Incubator Metrics
        if any(w in q_clean for w in ["culture", "confluent", "confluency", "density", "incubator", "passage"]):
            return {
                "status": "success",
                "query": query,
                "topic": "Culture Optimization & Confluency Monitoring",
                "module": "Culture Optimizer",
                "response": "🌱 **Stem Cell Culture Telemetry & Status:**\n"
                            "The Culture Optimizer tracks culture health indicators to generate deterministic laboratory recommendations:\n\n"
                            "• **Near Confluent (85% Confluency):** Indicates cells occupy 85% of culture dish surface. Subculture (passage) is recommended to prevent contact inhibition and senescence.\n"
                            "• **Incubator Telemetry:** Maintains optimal $37.0^\\circ\\text{C}$ temperature, $5.0\\% \\text{ CO}_2$ buffer, and $\\ge 90\\%$ relative humidity to prevent evaporation.\n"
                            "• **Culture Score (88/100):** Reflects high viability, exponential growth, and low risk status.",
                "suggested_followups": [
                    "What recommendations are generated?",
                    "What is cell circularity?",
                    "Explain NIH S-Index."
                ],
                "disclaimer": self.disclaimer
            }

        # 8. NIH S-Index Dashboard
        if any(w in q_clean for w in ["s-index", "sindex", "nih", "fair", "reproducibility", "provenance"]):
            return {
                "status": "success",
                "query": query,
                "topic": "NIH S-Index & FAIR Data Evaluation",
                "module": "NIH S-Index Dashboard",
                "response": "📊 **NIH S-Index Data Quality & FAIR Score:**\n"
                            "The NIH Scientific Index (S-Index) evaluates dataset compliance with FAIR principles (Findable, Accessible, Interoperable, Reusable).\n\n"
                            "• **FAIR Score (87.5/100):** Measures metadata completeness, stable accession IDs, and open formats.\n"
                            "• **NIH S-Index (0.88):** Standardized reproducibility composite metric for biomedical repositories (GEO, SRA, BioStudies).",
                "suggested_followups": [
                    "What is Cell Fate Analyzer?",
                    "Why is this culture classified as Near Confluent?",
                    "What is a volcano plot?"
                ],
                "disclaimer": self.disclaimer
            }

        # 9. Generic / Out-of-Scope Query Fallback
        return {
            "status": "success",
            "query": query,
            "topic": "Research Information Query",
            "module": "CoreAI BIO Information Engine",
            "response": "💡 **Scientific Overview:**\n"
                        f"Thank you for your question regarding *\"{query}\"*.\n\n"
                        "CoreAI BIO is an integrated stem cell intelligence platform supporting five primary modules:\n"
                        "1. **NIH S-Index:** Evaluates FAIR data reproducibility.\n"
                        "2. **Culture Optimizer:** Monitors culture density, confluency, and rule-based feeding protocols.\n"
                        "3. **Cell Morphology:** Computer vision segmentation of cell circularity, area, and quality.\n"
                        "4. **Cell Fate Analyzer:** RNA-seq TPM analysis, PCA, DGE (volcano plots), pathway enrichment (GO/KEGG), and UMAP.\n"
                        "5. **AI Assistant:** Explains analytical outputs and metrics.\n\n"
                        "*Note: Available experimental evidence may be insufficient to answer out-of-scope inquiries. Additional experimental validation is required.*",
            "suggested_followups": [
                "What does a volcano plot mean?",
                "What is Circularity?",
                "What does UMAP show?",
                "Why is this culture classified as Near Confluent?"
            ],
            "disclaimer": self.disclaimer
        }

assistant_service = AssistantService()
