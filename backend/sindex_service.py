import os
import json

def load_scoring_rules():
    """
    Loads transparent scoring rules from the configuration JSON file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rules_path = os.path.join(base_dir, 'NIH S-index', 'scoring_rules.json')
    with open(rules_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_dataset_metadata(metadata):
    """
    Validates metadata fields types. Returns True if valid, or raises TypeError/ValueError.
    """
    if not isinstance(metadata, dict):
        raise TypeError("Metadata must be a dictionary")
        
    string_fields = [
        'title', 'description', 'repository', 'persistent_identifier',
        'license', 'version_information', 'contact_information'
    ]
    bool_fields = [
        'public_access', 'raw_data_available', 'processed_data_available',
        'machine_readable_format', 'metadata_complete', 'protocol_available',
        'publication_linked'
    ]
    int_fields = ['citation_count', 'reuse_count']
    
    for field in string_fields:
        if field in metadata and metadata[field] is not None and not isinstance(metadata[field], str):
            raise TypeError(f"Field '{field}' must be a string")
            
    for field in bool_fields:
        if field in metadata and metadata[field] is not None and not isinstance(metadata[field], bool):
            raise TypeError(f"Field '{field}' must be a boolean")
            
    for field in int_fields:
        if field in metadata and metadata[field] is not None:
            # Must explicitly filter out booleans because bool is a subclass of int in Python
            if not isinstance(metadata[field], int) or isinstance(metadata[field], bool):
                raise TypeError(f"Field '{field}' must be an integer")
                
    return True

def calculate_category_scores(metadata):
    """
    Calculates dynamic raw scores for each compliance category based on actual GEO XML/SOFT metadata.
    Each field contributes independently to ensure natural score variation across datasets.
    """
    validate_dataset_metadata(metadata)
    
    title = str(metadata.get("title", "") or "")
    desc = str(metadata.get("description", "") or "")
    pid = str(metadata.get("persistent_identifier", "") or "")
    repo = str(metadata.get("repository", "") or "")

    # 1. Findability (Max 20 pts)
    findability = 0
    if pid and pid.strip() not in ["INCOMPLETE-001", "N/A", ""]:
        findability += 10
    if len(title.strip()) > 0:
        findability += 5
    if metadata.get("bioproject_present") or metadata.get("sra_present") or metadata.get("publication_linked") or len(desc.strip()) > 0:
        findability += 5
    findability = min(20, findability)

    # 2. Accessibility (Max 15 pts)
    accessibility = 0
    if metadata.get("public_access") is True:
        accessibility += 8
    if repo and repo.strip() not in ["N/A", ""]:
        accessibility += 7
    accessibility = min(15, accessibility)

    # 3. Interoperability (Max 15 pts)
    interoperability = 0
    if metadata.get("machine_readable_format") is True:
        interoperability += 8
    if metadata.get("metadata_complete") is True or metadata.get("platform_annotated") is True:
        interoperability += 7
    interoperability = min(15, interoperability)

    # 4. Reusability (Max 20 pts)
    reusability = 0
    lic = metadata.get("license")
    if lic and str(lic).strip().lower() not in ["none", "null", "n/a", ""]:
        reusability += 8
    elif pid and pid.strip() not in ["INCOMPLETE-001", "N/A", ""]:
        reusability += 5

    if metadata.get("raw_data_available") is True:
        reusability += 6
    if metadata.get("processed_data_available") is True:
        reusability += 6

    desc_len = metadata.get("description_length") or len(desc)
    if desc_len < 100 and not metadata.get("processed_data_available") and not metadata.get("raw_data_available"):
        reusability = max(0, reusability - 5)

    reusability = min(20, reusability)

    # 5. Documentation Quality (Max 15 pts)
    documentation = 0
    if metadata.get("protocol_available") is True:
        documentation += 5
    elif "protocol" in desc.lower() or "workflow" in desc.lower() or "optimization" in desc.lower():
        documentation += 3

    ver_info = metadata.get("version_information")
    if ver_info and str(ver_info).strip() not in ["N/A", ""]:
        documentation += 5

    contact = metadata.get("contact_information")
    if metadata.get("contributor_contact_complete") is True or (contact and str(contact).strip() not in ["N/A", "", "None"]):
        documentation += 5

    documentation = min(15, documentation)

    # 6. Evidence of Reuse & Scale (Max 15 pts)
    evidence_of_reuse = 0
    pub_linked = metadata.get("publication_linked") is True or (metadata.get("pubmed_id") and str(metadata.get("pubmed_id")).strip() not in ["N/A", "None", ""])
    citations = metadata.get("citation_count", 0) or 0
    reuses = metadata.get("reuse_count", 0) or 0
    samples = metadata.get("sample_count", 0) or 0

    if pub_linked or citations >= 1 or reuses >= 1:
        evidence_of_reuse += 8

    if reuses >= 1 or citations >= 1 or samples >= 10:
        evidence_of_reuse += 7
    elif samples >= 5 or (metadata.get("supplementary_count", 0) >= 2):
        evidence_of_reuse += 5
    elif samples >= 1:
        evidence_of_reuse += 3

    evidence_of_reuse = min(15, evidence_of_reuse)

    return {
        "findability": min(20, findability),
        "accessibility": min(15, accessibility),
        "interoperability": min(15, interoperability),
        "reusability": min(20, reusability),
        "documentation": min(15, documentation),
        "evidence_of_reuse": min(15, evidence_of_reuse)
    }

def generate_rule_based_explanation(result):
    """
    Generates lists of strengths, weaknesses, and recommendations based on passed/failed checks.
    """
    passed = result.get("passed_checks", [])
    failed = result.get("failed_checks", [])
    
    strengths = [check["description"] for check in passed]
    weaknesses = [f"Lacks {check['description'].lower()}" for check in failed]
    recommendations = [check["recommendation"] for check in failed]
    
    result["strengths"] = strengths
    result["weaknesses"] = weaknesses
    result["recommendations"] = recommendations

def calculate_sindex(metadata):
    """
    Calculates the aggregate NIH Data Sharing Index (S-index).
    Returns a dict with all required scoring metrics and explanations.
    """
    validate_dataset_metadata(metadata)
    rules = load_scoring_rules()
    category_scores = calculate_category_scores(metadata)
    
    final_score = sum(category_scores.values())
    normalized_score = round(final_score / 100.0, 2)
    
    # Rating assignment
    if final_score >= 85:
        rating = "Excellent"
    elif final_score >= 70:
        rating = "Good"
    elif final_score >= 50:
        rating = "Moderate"
    else:
        rating = "Needs Improvement"
        
    # Evaluate check-by-check pass/fail status for explanation generation
    passed_checks = []
    failed_checks = []
    
    for cat_name, cat_data in rules.get("categories", {}).items():
        checks = cat_data.get("checks", {})
        for check_name, check_data in checks.items():
            field = check_data.get("field")
            condition = check_data.get("condition")
            val = metadata.get(field)
            
            passed = False
            if condition == "not_empty":
                if val is not None and isinstance(val, str) and val.strip() != "":
                    if field == "persistent_identifier" and val.strip() == "INCOMPLETE-001":
                        passed = False
                    else:
                        passed = True
            elif condition == "is_true":
                if val is True:
                    passed = True
            elif condition == "numeric_threshold":
                threshold = check_data.get("threshold", 0)
                if val is not None and isinstance(val, (int, float)) and not isinstance(val, bool):
                    if val >= threshold:
                        passed = True
            
            check_info = {
                "name": check_name,
                "description": check_data.get("description"),
                "recommendation": check_data.get("recommendation"),
                "category": cat_name
            }
            if passed:
                passed_checks.append(check_info)
            else:
                failed_checks.append(check_info)
                
    result = {
        "final_score": final_score,
        "normalized_score": normalized_score,
        "rating": rating,
        "category_scores": category_scores,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "scoring_version": rules.get("version", "1.0.0")
    }
    
    generate_rule_based_explanation(result)
    
    # Filter the keys to exactly match user specifications
    return {
        "final_score": result["final_score"],
        "normalized_score": result["normalized_score"],
        "rating": result["rating"],
        "category_scores": result["category_scores"],
        "strengths": result["strengths"],
        "weaknesses": result["weaknesses"],
        "recommendations": result["recommendations"],
        "scoring_version": result["scoring_version"],
        "passed_checks": result["passed_checks"],
        "failed_checks": result["failed_checks"]
    }
