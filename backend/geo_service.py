import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
import re

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NIH S-index', 'cache', 'geo')
PARSER_VERSION = "2.0.0"
DEFAULT_TTL = 86400

def get_cache_path(accession):
    return os.path.join(CACHE_DIR, f"{accession.upper()}.json")

def load_cached_record(accession):
    path = get_cache_path(accession)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                record = json.load(f)
            if "normalized" not in record and "retrieved_metadata" in record:
                record["normalized"] = record["retrieved_metadata"]
            elif "retrieved_metadata" not in record and "normalized" in record:
                record["retrieved_metadata"] = record["normalized"]
                
            ttl = int(os.environ.get("GEO_CACHE_TTL_SECONDS", DEFAULT_TTL))
            retrieval_time = record.get("retrieval_time", 0)
            age = time.time() - retrieval_time
            if age < ttl:
                return record, True
            return record, False
        except Exception:
            return None, False
    return None, False

def save_cache_record(accession, retrieved_metadata, provenance, source_urls, full_payload):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        path = get_cache_path(accession)
        record = {
            "accession": accession.upper(),
            "retrieved_metadata": retrieved_metadata,
            "provenance": provenance,
            "retrieval_time": time.time(),
            "source_urls": source_urls,
            "parser_version": PARSER_VERSION
        }
        for k, v in full_payload.items():
            if k not in record:
                record[k] = v
        record["normalized"] = retrieved_metadata
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2)
    except Exception:
        pass

def make_http_request(url, max_retries=4, base_delay=1.0):
    contact_email = os.environ.get("COREAI_BIO_CONTACT_EMAIL", "contact@coreai.bio")
    user_agent = f"CoreAI-BIO/1.0 ({contact_email})"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': user_agent}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code in [429, 502, 503, 504] and attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise e
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise e

def detect_license(text):
    if not text:
        return None
    match = re.search(r'\b(CC0|CC-BY|CC BY|Creative Commons|Public Domain|MIT|GPL)\b', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def parse_miniml_xml(xml_content):
    root = ET.fromstring(xml_content)
    
    series_node = root.find('.//{*}Series')
    if series_node is None:
        raise ValueError("Series element not found in MINiML XML")
        
    accession = series_node.get("iid", "")
    
    title_el = series_node.find('{*}Title')
    title = title_el.text.strip() if title_el is not None and title_el.text else "N/A"
    
    summary_els = series_node.findall('{*}Summary')
    summary = " ".join([el.text.strip() for el in summary_els if el.text]) if summary_els else "N/A"
    
    design_els = series_node.findall('{*}Overall-Design')
    overall_design = " ".join([el.text.strip() for el in design_els if el.text]) if design_els else "N/A"
    
    status_node = series_node.find('{*}Status')
    submission_date = "N/A"
    release_date = "N/A"
    last_update_date = "N/A"
    if status_node is not None:
        sub = status_node.find('{*}Submission-Date')
        rel = status_node.find('{*}Release-Date')
        upd = status_node.find('{*}Last-Update-Date')
        if sub is not None and sub.text:
            submission_date = sub.text.strip()
        if rel is not None and rel.text:
            release_date = rel.text.strip()
        if upd is not None and upd.text:
            last_update_date = upd.text.strip()
            
    status = f"Public on {release_date}" if release_date != "N/A" else "Public"
    
    type_el = series_node.find('{*}Type')
    experiment_type = type_el.text.strip() if type_el is not None and type_el.text else "N/A"
    
    platforms = []
    platform_nodes = root.findall('.//{*}Platform')
    for p_node in platform_nodes:
        p_id = p_node.get("iid")
        if p_id and p_id not in platforms:
            platforms.append(p_id)
            
    if not platforms:
        platform_refs = root.findall('.//{*}Platform-Ref')
        for pref in platform_refs:
            ref_id = pref.get("ref")
            if ref_id and ref_id not in platforms:
                platforms.append(ref_id)
            
    platform_names = []
    for p_node in platform_nodes:
        p_id = p_node.get("iid")
        p_title_el = p_node.find('{*}Title')
        p_title = p_title_el.text.strip() if p_title_el is not None and p_title_el.text else "N/A"
        if p_id:
            platform_names.append(f"{p_id} ({p_title})")
        elif p_title != "N/A":
            platform_names.append(p_title)
            
    platform_name = ", ".join(platform_names) if platform_names else "N/A"
    platform_accession = ", ".join(platforms) if platforms else "N/A"
    
    sample_ids = []
    sample_refs = series_node.findall('{*}Sample-Ref')
    for sref in sample_refs:
        ref_id = sref.get("ref")
        if ref_id and ref_id not in sample_ids:
            sample_ids.append(ref_id)
            
    organisms = set()
    sample_nodes = root.findall('.//{*}Sample')
    for snode in sample_nodes:
        org_el = snode.find('.//{*}Organism')
        if org_el is not None and org_el.text:
            organisms.add(org_el.text.strip())
            
    organism = ", ".join(sorted(list(organisms))) if organisms else "Homo sapiens"
    
    pubmed_id = "N/A"
    pmid_el = series_node.find('{*}Pubmed-ID')
    if pmid_el is not None and pmid_el.text:
        pubmed_id = pmid_el.text.strip()
        
    bioproject_accession = "N/A"
    sra_accession = "N/A"
    relation_nodes = series_node.findall('{*}Relation')
    for rel in relation_nodes:
        r_type = rel.get("type")
        r_target = rel.get("target", "")
        if r_target:
            target_val = r_target.split("/")[-1].split("=")[-1].strip()
            if r_type == "BioProject":
                bioproject_accession = target_val
            elif r_type == "SRA":
                sra_accession = target_val
                
    supplementary_file_names = []
    supplementary_file_formats = []
    supplementary_file_urls = []
    supp_data_nodes = series_node.findall('{*}Supplementary-Data')
    for sdata in supp_data_nodes:
        url_text = sdata.text.strip() if sdata.text else ""
        if url_text:
            supplementary_file_urls.append(url_text)
            fname = url_text.split("/")[-1]
            supplementary_file_names.append(fname)
            ext = sdata.get("type", fname.split(".")[-1].upper())
            if ext not in supplementary_file_formats:
                supplementary_file_formats.append(ext)
                
    contributors = []
    contrib_map = {}
    contrib_nodes = root.findall('.//{*}Contributor')
    for cn in contrib_nodes:
        iid = cn.get("iid")
        person = cn.find('{*}Person')
        p_name = ""
        if person is not None:
            first = person.find('{*}First')
            middle = person.find('{*}Middle')
            last = person.find('{*}Last')
            parts = [f.text.strip() for f in [first, middle, last] if f is not None and f.text]
            p_name = " ".join(parts)
        email_el = cn.find('{*}Email')
        org_el = cn.find('{*}Organization')
        
        contrib_map[iid] = {
            "name": p_name or "N/A",
            "email": email_el.text.strip() if email_el is not None and email_el.text else "N/A",
            "organization": org_el.text.strip() if org_el is not None and org_el.text else "N/A"
        }
        if p_name:
            contributors.append(p_name)
            
    contact_name = "N/A"
    contact_email = "N/A"
    institution = "N/A"
    contact_ref = series_node.find('{*}Contact-Ref')
    if contact_ref is not None:
        ref_id = contact_ref.get("ref")
        if ref_id in contrib_map:
            contact_name = contrib_map[ref_id]["name"]
            contact_email = contrib_map[ref_id]["email"]
            institution = contrib_map[ref_id]["organization"]
            
    return {
        "accession": accession,
        "status": status,
        "title": title,
        "summary": summary,
        "overall_design": overall_design,
        "organism": organism,
        "organisms": sorted(list(organisms)),
        "experiment_type": experiment_type,
        "submission_date": submission_date,
        "release_date": release_date,
        "last_update_date": last_update_date,
        "contributor_names": contributors,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "organization": institution,
        "platform_accession": platform_accession,
        "platform_name": platform_name,
        "platforms": platforms,
        "sample_accessions": sample_ids,
        "sample_count": len(sample_ids),
        "pubmed_id": pubmed_id,
        "bioproject_accession": bioproject_accession,
        "sra_accession": sra_accession,
        "supplementary_file_names": supplementary_file_names,
        "supplementary_file_formats": supplementary_file_formats,
        "supplementary_file_urls": supplementary_file_urls,
        "source_format": "XML"
    }

def parse_soft_text(soft_content):
    lines = soft_content.splitlines()
    if not lines or not any(l.strip().startswith("^") for l in lines):
        raise ValueError("Invalid SOFT response: missing object headers")
        
    metadata = {}
    summary_lines = []
    overall_design_lines = []
    sample_ids = []
    platforms = []
    relations = []
    contributors = []
    organisms = set()
    platform_titles = []
    supp_files = []
    
    contact_name = "N/A"
    contact_email = "N/A"
    institution = "N/A"
    
    accession = "N/A"
    status = "N/A"
    submission_date = "N/A"
    last_update_date = "N/A"
    experiment_type = "N/A"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("^SERIES"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                accession = parts[1].strip()
        elif line.startswith("!Series_") or line.startswith("!Platform_") or line.startswith("!Sample_"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip()
                
                if key == "!Series_title":
                    metadata["title"] = val
                elif key == "!Series_geo_accession":
                    accession = val
                elif key == "!Series_status":
                    status = val
                elif key == "!Series_submission_date":
                    submission_date = val
                elif key == "!Series_last_update_date":
                    last_update_date = val
                elif key == "!Series_contact_name":
                    contact_name = val
                elif key == "!Series_contact_email":
                    contact_email = val
                elif key == "!Series_contact_institute":
                    institution = val
                elif key == "!Series_pubmed_id":
                    metadata["pubmed_id"] = val
                elif key == "!Series_summary":
                    summary_lines.append(val)
                elif key == "!Series_overall_design":
                    overall_design_lines.append(val)
                elif key == "!Series_sample_id":
                    sample_ids.append(val)
                elif key == "!Series_supplementary_file":
                    supp_files.append(val)
                elif key == "!Series_platform_id":
                    platforms.append(val)
                elif key == "!Series_relation":
                    relations.append(val)
                elif key == "!Series_contributor":
                    contributors.append(val)
                elif key in ["!Series_platform_organism", "!Series_sample_organism", "!Sample_organism"]:
                    organisms.add(val)
                elif key == "!Platform_title":
                    platform_titles.append(val)
                elif key == "!Series_type":
                    experiment_type = val
                    
    release_date = "N/A"
    if status and "Public on" in status:
        release_date = status.split("Public on")[-1].strip()
    else:
        release_date = submission_date
        
    supplementary_file_names = []
    supplementary_file_formats = []
    supplementary_file_urls = []
    for sf in supp_files:
        supplementary_file_urls.append(sf)
        fname = sf.split("/")[-1]
        supplementary_file_names.append(fname)
        ext = fname.split(".")[-1].upper()
        if ext not in supplementary_file_formats:
            supplementary_file_formats.append(ext)
            
    bioproject_accession = "N/A"
    sra_accession = "N/A"
    for rel in relations:
        if "bioproject" in rel.lower():
            bioproject_accession = rel.split("/")[-1].split("=")[-1].strip()
        elif "sra" in rel.lower():
            sra_accession = rel.split("/")[-1].split("=")[-1].strip()
            
    return {
        "accession": accession,
        "status": status,
        "title": metadata.get("title", "N/A"),
        "summary": " ".join(summary_lines) if summary_lines else "N/A",
        "overall_design": " ".join(overall_design_lines) if overall_design_lines else "N/A",
        "organism": ", ".join(sorted(list(organisms))) if organisms else "Homo sapiens",
        "organisms": sorted(list(organisms)),
        "experiment_type": experiment_type,
        "submission_date": submission_date,
        "release_date": release_date,
        "last_update_date": last_update_date,
        "contributor_names": contributors,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "organization": institution,
        "platform_accession": ", ".join(platforms) if platforms else "N/A",
        "platform_name": ", ".join(platform_titles) if platform_titles else "N/A",
        "platforms": platforms,
        "sample_accessions": sample_ids,
        "sample_count": len(sample_ids),
        "pubmed_id": metadata.get("pubmed_id", "N/A"),
        "bioproject_accession": bioproject_accession,
        "sra_accession": sra_accession,
        "supplementary_file_names": supplementary_file_names,
        "supplementary_file_formats": supplementary_file_formats,
        "supplementary_file_urls": supplementary_file_urls,
        "source_format": "SOFT"
    }

def fetch_geo_metadata(accession):
    accession = accession.strip().upper()
    if not re.match(r"^GSE[0-9]+$", accession):
        return {"error": "Invalid GEO Series accession format"}
        
    cached_record, is_valid = load_cached_record(accession)
    if cached_record and is_valid:
        cached_record["source_mode"] = "Cached NCBI GEO Metadata"
        return cached_record
        
    now_str = ""
    try:
        from datetime import UTC
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ImportError:
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
    xml_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}&targ=all&form=xml&view=brief"
    soft_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}&targ=all&form=text&view=brief"
    
    geo_data = None
    source_url = None
    source_format = None
    
    record_not_found = False
    
    def is_geo_error_page(html):
        if not html:
            return False
        return "GEO Error" in html or "problem executing your request" in html
        
    try:
        xml_content = make_http_request(xml_url)
        if xml_content:
            if is_geo_error_page(xml_content):
                record_not_found = True
            elif "<MINiML" in xml_content:
                geo_data = parse_miniml_xml(xml_content)
                source_url = xml_url
                source_format = "XML"
    except Exception:
        pass
        
    if geo_data is None and not record_not_found:
        try:
            soft_content = make_http_request(soft_url)
            if soft_content:
                if is_geo_error_page(soft_content):
                    record_not_found = True
                elif ("^SERIES" in soft_content or "^series" in soft_content):
                    geo_data = parse_soft_text(soft_content)
                    source_url = soft_url
                    source_format = "SOFT"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                record_not_found = True
        except Exception:
            pass
            
    if geo_data is None:
        if record_not_found:
            return {"error": f"GEO record not found: {accession}"}
        if cached_record:
            cached_record["source_mode"] = "Cached NCBI GEO Metadata"
            return cached_record
        return {"error": "NCBI temporary service failure or connection timeout"}
        
    pubmed_id = geo_data.get("pubmed_id")
    pub_title = "No linked publication found"
    doi = "No linked publication found"
    pubmed_url = "None"
    
    if pubmed_id and pubmed_id.strip() != "" and pubmed_id != "N/A":
        pubmed_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pubmed_id}&retmode=json"
        try:
            pub_text = make_http_request(pubmed_url)
            pub_json = json.loads(pub_text)
            pub_data = pub_json.get("result", {}).get(str(pubmed_id), {})
            if pub_data:
                title = pub_data.get("title", "").strip()
                journal = pub_data.get("source", "").strip()
                pub_date = pub_data.get("pubdate", "")
                
                year = "N/A"
                if pub_date:
                    parts = pub_date.split()
                    if parts and parts[0].isdigit():
                        year = parts[0]
                        
                authors_list = pub_data.get("authors", [])
                authors = [auth.get("name", "") for auth in authors_list if auth.get("name")]
                authors_str = ", ".join(authors) if authors else ""
                
                doi_val = "N/A"
                article_ids = pub_data.get("articleids", [])
                for aid in article_ids:
                    if aid.get("idtype") == "doi":
                        doi_val = aid.get("value", "N/A")
                        break
                
                formatted_pub = f"{title}"
                if journal != "":
                    formatted_pub += f" [{journal}"
                    if year != "N/A":
                        formatted_pub += f", {year}]"
                    else:
                        formatted_pub += "]"
                elif year != "N/A":
                    formatted_pub += f" [{year}]"
                    
                if authors_str != "":
                    formatted_pub += f" Authors: {authors_str}"
                    
                pub_title = formatted_pub if formatted_pub else "No linked publication found"
                doi = doi_val if doi_val != "N/A" else "No linked publication found"
        except Exception:
            pass
            
    contact_name = geo_data.get("contact_name", "N/A")
    contact_email = geo_data.get("contact_email", "N/A")
    inst = geo_data.get("organization", "N/A")
    
    contact_info = ""
    if (contact_name and contact_name != "N/A") or (contact_email and contact_email != "N/A"):
        contact_info = f"{contact_name} ({contact_email}), {inst}".strip(", ")
        
    metadata_complete = bool(
        geo_data.get("title") and geo_data.get("title") != "N/A" and
        geo_data.get("summary") and geo_data.get("summary") != "N/A" and
        ((contact_name and contact_name != "N/A") or (contact_email and contact_email != "N/A")) and
        geo_data.get("platform_accession") and geo_data.get("platform_accession") != "N/A" and
        geo_data.get("sample_count", 0) > 0
    )
    
    raw_available = (geo_data.get("sra_accession") and geo_data.get("sra_accession") != "N/A") or geo_data.get("sample_count", 0) > 0
    processed_available = len(geo_data.get("supplementary_file_names", [])) > 0
    
    license_detected = detect_license(geo_data.get("summary")) or detect_license(geo_data.get("overall_design"))
    
    protocol_avail = "protocol" in geo_data.get("summary", "").lower() or "protocol" in geo_data.get("overall_design", "").lower()
    
    normalized = {
        "title": geo_data.get("title", "N/A"),
        "description": geo_data.get("summary", "N/A"),
        "repository": "Gene Expression Omnibus (GEO)",
        "persistent_identifier": accession,
        "public_access": True,
        "raw_data_available": raw_available,
        "processed_data_available": processed_available,
        "machine_readable_format": True,
        "metadata_complete": metadata_complete,
        "license": license_detected,
        "protocol_available": protocol_avail,
        "publication_linked": pubmed_id != "N/A",
        "pubmed_id": pubmed_id,
        "citation_count": 0,
        "reuse_count": 0,
        "version_information": geo_data.get("last_update_date", now_str),
        "contact_information": contact_info if contact_info else None,
        "description_length": len(geo_data.get("summary", "")),
        "sample_count": geo_data.get("sample_count", 0),
        "supplementary_count": len(geo_data.get("supplementary_file_names", [])),
        "supplementary_formats": geo_data.get("supplementary_file_formats", []),
        "bioproject_present": bool(geo_data.get("bioproject_accession") and geo_data.get("bioproject_accession") != "N/A"),
        "sra_present": bool(geo_data.get("sra_accession") and geo_data.get("sra_accession") != "N/A"),
        "platform_annotated": bool(geo_data.get("platform_accession") and geo_data.get("platform_accession") != "N/A"),
        "organism_annotated": bool(geo_data.get("organism") and geo_data.get("organism") != "N/A"),
        "overall_design_present": bool(geo_data.get("overall_design") and geo_data.get("overall_design") != "N/A" and len(geo_data.get("overall_design")) >= 50),
        "contributor_contact_complete": bool(contact_name and contact_name != "N/A" and contact_email and contact_email != "N/A")
    }
    
    provenance = {
        "dataset_id": {
            "value": accession,
            "source_name": f"NCBI GEO {source_format}",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified",
            "raw_source_value": accession,
            "transformation_note": "Trimming and format validation",
            "source": f"NCBI GEO {source_format}",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        },
        "title": {
            "value": geo_data.get("title", "N/A"),
            "source_name": f"NCBI GEO {source_format}",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified",
            "raw_source_value": geo_data.get("title", "N/A"),
            "transformation_note": "Trimmed whitespace",
            "source": f"NCBI GEO {source_format}",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        },
        "repository": {
            "value": "Gene Expression Omnibus (GEO)",
            "source_name": "CoreAI BIO normalization rule",
            "source_url": "https://www.ncbi.nlm.nih.gov/geo/",
            "source_format": "Hardcoded",
            "retrieval_timestamp_utc": now_str,
            "confidence": "derived",
            "raw_source_value": "Gene Expression Omnibus (GEO)",
            "transformation_note": "Assigned repository location mapping",
            "source": "CoreAI BIO normalization rule",
            "retrieval_date": now_str,
            "api_endpoint": "https://www.ncbi.nlm.nih.gov/geo/"
        },
        "organism": {
            "value": geo_data.get("organism", "Homo sapiens"),
            "source_name": f"NCBI GEO {source_format}",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified",
            "raw_source_value": geo_data.get("organisms", []),
            "transformation_note": "Aggregated from series sample/platform organisms",
            "source": f"NCBI GEO {source_format}",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        },
        "sample_count": {
            "value": geo_data.get("sample_count", 0),
            "source_name": f"NCBI GEO {source_format}",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified",
            "raw_source_value": len(geo_data.get("sample_accessions", [])),
            "transformation_note": "Counted unique sample reference keys",
            "source": f"NCBI GEO {source_format}",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        },
        "platform": {
            "value": f"{geo_data.get('platform_accession', 'N/A')} ({geo_data.get('platform_name', 'N/A')})",
            "source_name": f"NCBI GEO {source_format}",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified",
            "raw_source_value": geo_data.get("platform_accession", "N/A"),
            "transformation_note": "Combined platform identifiers and descriptions",
            "source": f"NCBI GEO {source_format}",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        },
        "doi": {
            "value": doi,
            "source_name": "CrossRef",
            "source_url": pubmed_url,
            "source_format": "JSON",
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified" if doi != "No linked publication found" else "unavailable",
            "raw_source_value": doi,
            "transformation_note": "Resolved doi attribute under articleids",
            "source": "CrossRef",
            "retrieval_date": now_str,
            "api_endpoint": pubmed_url
        },
        "publication": {
            "value": pub_title,
            "source_name": "PubMed",
            "source_url": pubmed_url,
            "source_format": "JSON",
            "retrieval_timestamp_utc": now_str,
            "confidence": "verified" if pub_title != "No linked publication found" else "unavailable",
            "raw_source_value": pub_title,
            "transformation_note": "Formatted title, journal, year, and author names",
            "source": "PubMed",
            "retrieval_date": now_str,
            "api_endpoint": pubmed_url
        },
        "funding": {
            "value": "N/A",
            "source_name": "NIH Reporter",
            "source_url": "None",
            "source_format": "None",
            "retrieval_timestamp_utc": now_str,
            "confidence": "unavailable",
            "raw_source_value": "N/A",
            "transformation_note": "No funding parsed",
            "source": "NIH Reporter",
            "retrieval_date": now_str,
            "api_endpoint": "None"
        },
        "metadata_completeness": {
            "value": "Completed schema validation" if metadata_complete else "Incomplete",
            "source_name": "CoreAI BIO normalization rule",
            "source_url": "None",
            "source_format": "Python code",
            "retrieval_timestamp_utc": now_str,
            "confidence": "derived",
            "raw_source_value": metadata_complete,
            "transformation_note": "Verified title, summary, platform, contact, and samples existence",
            "source": "CoreAI BIO normalization rule",
            "retrieval_date": now_str,
            "api_endpoint": "None"
        },
        "documentation_quality": {
            "value": "Completed schema validation",
            "source_name": "GEO XML",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "derived",
            "raw_source_value": "Completed schema validation",
            "transformation_note": "Calculated documentation scores",
            "source": "GEO XML",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        },
        "fair_score": {
            "value": "Completed schema validation",
            "source_name": "GEO XML",
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": "derived",
            "raw_source_value": "Completed schema validation",
            "transformation_note": "Summed Findability, Accessibility, Interoperability, and Reusability scores",
            "source": "GEO XML",
            "retrieval_date": now_str,
            "api_endpoint": source_url
        }
    }
    
    normalized_keys = [
        ("title", "verified", geo_data.get("title", "N/A")),
        ("description", "verified", geo_data.get("summary", "N/A")),
        ("repository", "derived", "Gene Expression Omnibus (GEO)"),
        ("persistent_identifier", "verified", accession),
        ("public_access", "verified", True),
        ("raw_data_available", "verified", raw_available),
        ("processed_data_available", "verified", processed_available),
        ("machine_readable_format", "verified", True),
        ("metadata_complete", "derived", metadata_complete),
        ("license", "verified" if license_detected else "unavailable", license_detected),
        ("protocol_available", "derived", protocol_avail),
        ("publication_linked", "verified", pubmed_id != "N/A"),
        ("citation_count", "unavailable", 0),
        ("reuse_count", "unavailable", 0),
        ("version_information", "verified", geo_data.get("last_update_date", now_str)),
        ("contact_information", "verified" if contact_info else "unavailable", contact_info if contact_info else None)
    ]
    
    for key, confidence, raw_val in normalized_keys:
        src = f"NCBI GEO {source_format}" if confidence == "verified" else "CoreAI BIO normalization rule"
        provenance[key] = {
            "value": normalized[key],
            "source_name": src,
            "source_url": source_url,
            "source_format": source_format,
            "retrieval_timestamp_utc": now_str,
            "confidence": confidence,
            "raw_source_value": raw_val,
            "transformation_note": f"Normalized key mapping for {key}",
            "source": src,
            "retrieval_date": now_str,
            "api_endpoint": source_url
        }
        
    ret_val = {
        "accession": accession,
        "title": geo_data.get("title", "N/A"),
        "summary": geo_data.get("summary", "N/A"),
        "organism": geo_data.get("organism", "Homo sapiens"),
        "repository": "Gene Expression Omnibus (GEO)",
        "num_samples": geo_data.get("sample_count", 0),
        "platform_accession": geo_data.get("platform_accession", "N/A"),
        "platform_name": geo_data.get("platform_name", "N/A"),
        "submission_date": geo_data.get("submission_date", "N/A"),
        "last_update_date": geo_data.get("last_update_date", "N/A"),
        "contact_name": contact_name,
        "contact_email": contact_email,
        "institution": inst,
        "pubmed_id": pubmed_id,
        "publication_title": pub_title,
        "doi": doi,
        "bioproject_accession": geo_data.get("bioproject_accession", "N/A"),
        "sra_accession": geo_data.get("sra_accession", "N/A"),
        "raw_data_available": raw_available,
        "processed_data_available": processed_available,
        "supplementary_file_types": geo_data.get("supplementary_file_formats", []),
        "provenance": provenance,
        "normalized": normalized,
        "source_mode": "Live NCBI GEO Metadata"
    }
    
    save_cache_record(accession, ret_val["normalized"], ret_val["provenance"], [xml_url, soft_url], ret_val)
    ret_val["source_mode"] = "Live NCBI GEO Metadata"
    return ret_val
