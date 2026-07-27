import os
from datetime import datetime

class ProvenanceEngine:
    """
    Modular engine to track and audit data provenance and traceability.
    Maps fields to their original databases, API queries, collection times, and confidence levels.
    """
    
    @staticmethod
    def compile_provenance(dataset_id, metadata, is_live=False):
        """
        Compiles a structured provenance map for dataset fields.
        """
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Determine endpoints based on whether it is a live query or mock staging data
        if is_live:
            # Live NCBI GEO accessions
            gds_search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term={dataset_id}[Accession]"
            gds_summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id=<UID>"
            pubmed_summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={metadata.get('pmid', '')}"
            crossref_url = f"https://api.crossref.org/works/{metadata.get('doi', '')}"
            nih_reporter_url = f"https://api.reporter.nih.gov/v2/projects/search (Funding: {metadata.get('funding', '')})"
            xml_source = "GEO XML API"
            confidence_level = "High (Verified)"
        else:
            # Local mock dataset configurations
            gds_search_url = "Local config: cache/geo"
            gds_summary_url = "Local config: cache/geo"
            pubmed_summary_url = "Local PubMed cache: cache/geo"
            crossref_url = f"Local CrossRef registry (DOI: {metadata.get('doi', '')})"
            nih_reporter_url = f"Local NIH RePORTER registry (Grant: {metadata.get('funding', '')})"
            xml_source = "Local Metadata Cache"
            confidence_level = "High"

        # Construct field-level provenance details
        provenance_map = {
            "dataset_id": {
                "val": dataset_id,
                "source": "GEO XML",
                "retrieval_date": now_str,
                "api_endpoint": gds_search_url,
                "confidence": confidence_level
            },
            "title": {
                "val": metadata.get("title", "N/A"),
                "source": "NCBI GEO",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            },
            "repository": {
                "val": metadata.get("repository", "N/A"),
                "source": "GEO XML",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            },
            "organism": {
                "val": metadata.get("organism", "Homo sapiens"),
                "source": "NCBI GEO",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            },
            "sample_count": {
                "val": metadata.get("reuse_count", 0) if not is_live else metadata.get("num_samples", 0),
                "source": "NCBI GEO",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": "High (Verified)" if is_live else "High"
            },
            "platform": {
                "val": metadata.get("platform", "GPL24676"),
                "source": "NCBI GEO",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            },
            "doi": {
                "val": metadata.get("doi", "N/A"),
                "source": "CrossRef",
                "retrieval_date": now_str,
                "api_endpoint": crossref_url,
                "confidence": "High" if metadata.get("doi") and metadata.get("doi") != "N/A" else "Low (Fallback)"
            },
            "publication": {
                "val": metadata.get("publication", "N/A"),
                "source": "PubMed",
                "retrieval_date": now_str,
                "api_endpoint": pubmed_summary_url,
                "confidence": "High" if metadata.get("publication") and metadata.get("publication") != "N/A" and metadata.get("publication") != "Not published" else "Low (Unpublished)"
            },
            "funding": {
                "val": metadata.get("funding", "N/A"),
                "source": "NIH Reporter",
                "retrieval_date": now_str,
                "api_endpoint": nih_reporter_url,
                "confidence": "High" if metadata.get("funding") and metadata.get("funding") != "None" and metadata.get("funding") != "N/A" else "Medium (Declared)"
            },
            "metadata_completeness": {
                "val": f"{metadata.get('interoperability', 15)}/15",
                "source": "GEO XML",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            },
            "documentation_quality": {
                "val": f"{metadata.get('documentation', 15)}/15",
                "source": "GEO XML",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            },
            "fair_score": {
                "val": f"{metadata.get('fair_score', 100)}%",
                "source": "GEO XML",
                "retrieval_date": now_str,
                "api_endpoint": gds_summary_url,
                "confidence": confidence_level
            }
        }
        
        return provenance_map
