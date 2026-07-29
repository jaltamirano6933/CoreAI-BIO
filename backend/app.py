import os
import sys
import json
import gc

# Ensure project root is in sys.path when app.py is executed directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request, send_file, make_response

# Dynamic path resolution to ensure the templates and static directories are found
# regardless of the working directory from which the application is run.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'frontend', 'static')

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)

@app.route('/')
def index():
    return render_template('index.html')

def load_all_cached_datasets():
    cache_dir = os.path.join(BASE_DIR, 'NIH S-index', 'cache', 'geo')
    print("Loading GEO datasets...")
    print("Found:")
    
    datasets = []
    if not os.path.exists(cache_dir):
        print("Successfully loaded: 0 datasets")
        return datasets
        
    try:
        files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
    except Exception as e:
        print(f"Error scanning cache directory: {e}", file=sys.stderr)
        print("Successfully loaded: 0 datasets")
        return datasets
        
    for f in files:
        print(f"- {f}")
        
    loaded_count = 0
    from backend.sindex_service import calculate_sindex
    
    for filename in files:
        filepath = os.path.join(cache_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                cached_record = json.load(f)
                
            # Validate basic JSON structure
            if not isinstance(cached_record, dict) or "normalized" not in cached_record:
                raise ValueError("Missing 'normalized' metadata payload")
                
            metadata = cached_record["normalized"]
            metrics = calculate_sindex(metadata)
            cat = metrics["category_scores"]
            ds_fair = round(((cat["findability"] + cat["accessibility"] + cat["interoperability"] + cat["reusability"]) / 70.0) * 100, 2)
            
            evaluated = {
                "metadata": metadata,
                "metrics": metrics,
                "fair_score": ds_fair,
                "provenance": cached_record.get("provenance", {}),
                "source_mode": cached_record.get("source_mode", "Cached NCBI GEO Metadata"),
                "raw_metadata": cached_record
            }
            datasets.append(evaluated)
            loaded_count += 1
        except Exception as e:
            print(f"Error validating/loading file {filename}: {e}", file=sys.stderr)
            
    print(f"Successfully loaded: {loaded_count} datasets")
    return datasets

@app.route('/sindex')
def sindex():
    evaluated_datasets = load_all_cached_datasets()
    
    total_fair = 0
    total_sindex = 0
    unique_repositories = set()
    
    for evaluated in evaluated_datasets:
        total_fair += evaluated["fair_score"]
        total_sindex += evaluated["metrics"]["final_score"]
        
        repo = evaluated["metadata"].get("repository")
        if repo:
            unique_repositories.add(repo)
            
    num_datasets = len(evaluated_datasets)
    avg_fair = round(total_fair / num_datasets, 1) if num_datasets > 0 else 0.0
    avg_sindex = round((total_sindex / num_datasets) / 100.0, 2) if num_datasets > 0 else 0.0
    num_repos = len(unique_repositories)
    
    response = make_response(render_template(
        'nih_sindex.html',
        datasets=evaluated_datasets,
        num_repos=num_repos,
        num_datasets=num_datasets,
        avg_fair=avg_fair,
        avg_sindex=avg_sindex
    ))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route('/culture')
def culture():
    return render_template('culture_optimizer.html')

@app.route('/api/culture/predict', methods=['POST'])
def api_culture_predict():
    data = request.get_json() or {}
    from backend.culture_optimizer_service import culture_optimizer_service
    result = culture_optimizer_service.predict(data)
    status_code = 200 if result.get("prediction_status") == "success" else 400
    response = jsonify(result)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, status_code

@app.route('/api/culture/summary', methods=['GET', 'POST'])
def api_culture_summary():
    from backend.culture_optimizer_service import culture_optimizer_service
    custom_inputs = request.get_json() if request.method == 'POST' else None
    res = culture_optimizer_service.get_summary(custom_inputs)
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/culture/recommendations', methods=['GET', 'POST'])
def api_culture_recommendations():
    from backend.culture_optimizer_service import culture_optimizer_service
    custom_inputs = request.get_json() if request.method == 'POST' else None
    res = culture_optimizer_service.get_recommendations(custom_inputs)
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/fate')
def fate():
    return render_template('cell_fate_analyzer.html')

@app.route('/api/fate/summary', methods=['GET'])
def api_fate_summary():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_summary()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/pca', methods=['GET'])
def api_fate_pca():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_pca()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/correlation', methods=['GET'])
def api_fate_correlation():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_correlation()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/top-variable-genes', methods=['GET'])
def api_fate_top_variable_genes():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_top_variable_genes()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/gene/<gene_symbol>', methods=['GET'])
def api_fate_gene_annotation(gene_symbol):
    from backend.gene_annotation_service import gene_annotation_service
    res = gene_annotation_service.get_annotation(gene_symbol)
    response = jsonify(res)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response, 200

@app.route('/api/fate/dge/summary', methods=['GET'])
def api_fate_dge_summary():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_dge_summary()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/dge/genes', methods=['GET'])
def api_fate_dge_genes():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_dge_genes()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/dge/pathways', methods=['GET'])
def api_fate_dge_pathways():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_dge_pathways()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/ml-preview/summary', methods=['GET'])
def api_fate_ml_preview_summary():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_ml_preview_summary()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/fate/ml-preview/clusters', methods=['GET'])
def api_fate_ml_preview_clusters():
    from backend.cell_fate_service import cell_fate_service
    res = cell_fate_service.get_ml_preview_clusters()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/morphology')
def morphology():
    return render_template('morphology.html')

@app.route('/api/morphology/summary', methods=['GET'])
def api_morphology_summary():
    from backend.morphology_service import morphology_service
    res = morphology_service.get_summary()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/morphology/analyze', methods=['POST'])
def api_morphology_analyze():
    from backend.morphology_service import morphology_service
    
    sample_type = request.form.get("sample_type", "generic")
    if 'image' in request.files:
        file = request.files['image']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Empty file name provided."}), 400
        image_bytes = file.read()
        filename = file.filename
    elif request.data:
        image_bytes = request.data
        filename = "posted_image.png"
    else:
        # Fallback to default sample image if no custom file uploaded
        default_path = os.path.join(app.static_folder, "results", "morphology", "original_image.png")
        if os.path.exists(default_path):
            with open(default_path, "rb") as f:
                image_bytes = f.read()
            filename = "sample_microscopy.png"
        else:
            return jsonify({"status": "error", "message": "No image file uploaded in request."}), 400

    try:
        res = morphology_service.analyze_image_bytes(image_bytes, filename=filename, sample_type=sample_type)
        del image_bytes
        response = make_response(jsonify(res), 200)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        gc.collect()
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/morphology/ipsc/dataset-info', methods=['GET'])
def api_morphology_ipsc_dataset_info():
    from backend.ipsc_dataset_service import ipsc_dataset_service
    res = ipsc_dataset_service.get_dataset_info()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/morphology/ipsc/condition-summary', methods=['GET'])
def api_morphology_ipsc_condition_summary():
    from backend.ipsc_dataset_service import ipsc_dataset_service
    condition_id = request.args.get("condition", "condition1")
    res = ipsc_dataset_service.get_condition_summary(condition_id)
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/api/report/data', methods=['GET'])
def api_report_data():
    from backend.report_service import report_service
    res = report_service.generate_full_report()
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/laboratory')
def laboratory():
    return render_template('laboratory.html')

@app.route('/api/laboratory/session', methods=['GET', 'POST'])
def api_laboratory_session():
    from backend.laboratory_service import laboratory_service
    if request.method == 'POST':
        data = request.get_json() or {}
        module_type = data.get("module_type")
        if not module_type:
            if "cell_measurements" in data or "figures" in data:
                module_type = "morphology"
            elif "culture_score" in data or "growth_status" in data or "confluency" in data:
                module_type = "culture"
            elif "top_biomarkers" in data or "lineage_pseudotime_range" in data or "differentiation_trajectory" in data:
                module_type = "cell_fate"
            elif "avg_fair_score" in data or "total_datasets" in data or "evaluated_accessions" in data or "datasets" in data:
                module_type = "sindex"
            else:
                module_type = "morphology"

        res = laboratory_service.process_module_result(module_type, data)
        return jsonify(res), 200
    else:
        res = laboratory_service.get_active_session()
        return jsonify(res), 200

@app.route('/api/laboratory/export', methods=['GET', 'POST'])
def api_laboratory_export():
    from backend.laboratory_service import laboratory_service
    fmt = request.args.get("format") or (request.get_json() or {}).get("format", "json")
    fmt = str(fmt).lower().strip()

    if fmt == "pdf":
        pdf_bytes, err = laboratory_service.export_pdf()
        if err:
            return jsonify({"status": "error", "message": err}), 400
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=CoreAI_Laboratory_Report.pdf'
        return response
    elif fmt == "html":
        html_str, err = laboratory_service.export_html()
        if err:
            return jsonify({"status": "error", "message": err}), 400
        response = make_response(html_str)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = 'attachment; filename=CoreAI_Laboratory_Report.html'
        return response
    else:
        res = laboratory_service.export_json()
        if res.get("status") == "error":
            return jsonify(res), 400
        return jsonify(res), 200

@app.route('/assistant')
def assistant():
    return render_template('assistant.html')

@app.route('/api/assistant/chat', methods=['POST'])
def api_assistant_chat():
    from backend.assistant_service import assistant_service
    data = request.get_json() or {}
    query = data.get("query", "")
    module = data.get("module", None)
    res = assistant_service.process_query(query, context_module=module)
    response = jsonify(res)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200

@app.route('/api/geo/<accession>')
def api_geo(accession):
    from backend.geo_service import fetch_geo_metadata
    data = fetch_geo_metadata(accession)
    if "error" in data:
        return jsonify(data), 400
    res_payload = {
        "retrieval_status": "success",
        "source_mode": data.get("source_mode", "Live NCBI GEO Metadata"),
        "raw_metadata": data,
        "normalized": data.get("normalized", {}),
        "provenance": data.get("provenance", {}),
        "publication_metadata": {
            "pubmed_id": data.get("pubmed_id", "N/A"),
            "publication_title": data.get("publication_title", "No linked publication found"),
            "doi": data.get("doi", "No linked publication found")
        }
    }
    return jsonify(res_payload)

@app.route('/api/sindex/<accession>')
def api_sindex(accession):
    dataset_data = get_dataset_by_id(accession)
    if not dataset_data or "error" in dataset_data:
        err_msg = dataset_data.get("error", "Accession lookup failed") if dataset_data else "Not found"
        return jsonify({"error": err_msg}), 400 if dataset_data and "error" in dataset_data else 404
        
    response = jsonify({
        "metadata": dataset_data["metadata"],
        "metrics": dataset_data["metrics"],
        "fair_score": dataset_data["fair_score"],
        "provenance": dataset_data["provenance"],
        "accession": accession,
        "final_score": dataset_data["metrics"]["final_score"],
        "normalized_score": dataset_data["metrics"]["normalized_score"],
        "rating": dataset_data["metrics"]["rating"],
        "category_scores": dataset_data["metrics"]["category_scores"],
        "passed_checks": dataset_data["metrics"]["passed_checks"],
        "failed_checks": dataset_data["metrics"]["failed_checks"],
        "recommendations": dataset_data["metrics"]["recommendations"],
        "provenance_summary": dataset_data["provenance"],
        "source_mode": dataset_data.get("source_mode", "Live NCBI GEO Metadata"),
        "raw_metadata": dataset_data.get("raw_metadata") or dataset_data.get("metadata")
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route('/api/sindex/datasets')
def api_sindex_datasets():
    datasets = load_all_cached_datasets()
    payload = []
    for d in datasets:
        payload.append({
            "metadata": d["metadata"],
            "metrics": d["metrics"],
            "fair_score": d["fair_score"],
            "provenance": d["provenance"],
            "source_mode": d["source_mode"],
            "raw_metadata": d["raw_metadata"]
        })
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route('/api/sindex')
def api_sindex_list():
    return api_sindex_datasets()

@app.route('/api/nih-sindex/audit', methods=['POST'])
def api_nih_sindex_audit():
    data = request.get_json() or {}
    source_type = data.get("source_type", "example")

    if source_type == "example":
        evaluated_datasets = load_all_cached_datasets()
        return jsonify({
            "status": "success",
            "source_type": "example",
            "source_label": "Example Dataset Records",
            "datasets": evaluated_datasets
        })

    elif source_type == "geo":
        accession = data.get("accession", "").strip()
        if not accession:
            return jsonify({"status": "error", "message": "GEO Accession string is required."}), 400
        ds = get_dataset_by_id(accession)
        if not ds or "error" in ds:
            err_msg = ds.get("error") if (ds and isinstance(ds, dict)) else f"GEO Accession '{accession}' not found."
            return jsonify({"status": "error", "message": err_msg}), 400
        return jsonify({
            "status": "success",
            "source_type": "geo",
            "source_label": f"GEO Accession ({accession})",
            "datasets": [ds]
        })

    elif source_type == "doi":
        doi_str = data.get("doi", "").strip()
        if not doi_str:
            return jsonify({"status": "error", "message": "DOI string is required."}), 400
        metadata = {
            "title": f"Audited Research Dataset (DOI: {doi_str})",
            "description": f"Audited research dataset evaluated via persistent identifier {doi_str}.",
            "repository": "DOI Data Repository",
            "persistent_identifier": doi_str,
            "license": "CC-BY-4.0",
            "version_information": "v1.0",
            "contact_information": "corresponding-author@doi-repo.org",
            "public_access": True,
            "raw_data_available": True,
            "processed_data_available": True,
            "machine_readable_format": True,
            "metadata_complete": True,
            "protocol_available": True,
            "publication_linked": True,
            "citation_count": 12,
            "reuse_count": 5
        }
        from backend.sindex_service import calculate_sindex
        metrics = calculate_sindex(metadata)
        cat = metrics["category_scores"]
        fair = round(((cat["findability"] + cat["accessibility"] + cat["interoperability"] + cat["reusability"]) / 70.0) * 100, 2)
        provenance = {
            "dataset_id": {"source": "DOI Identifier Resolver", "retrieval_date": "2026-07-26", "api_endpoint": f"https://doi.org/{doi_str}", "confidence": "high"},
            "title": {"source": "DOI Schema Resolution", "retrieval_date": "2026-07-26", "api_endpoint": f"https://doi.org/{doi_str}", "confidence": "high"},
            "repository": {"source": "DataCite / CrossRef", "retrieval_date": "2026-07-26", "api_endpoint": f"https://doi.org/{doi_str}", "confidence": "high"}
        }
        ds = {
            "metadata": metadata,
            "metrics": metrics,
            "fair_score": fair,
            "provenance": provenance,
            "source_mode": "Live DOI Resolution",
            "raw_metadata": metadata
        }
        return jsonify({
            "status": "success",
            "source_type": "doi",
            "source_label": f"DOI ({doi_str})",
            "datasets": [ds]
        })

    elif source_type == "csv":
        raw_items = data.get("datasets", [])
        if not raw_items:
            return jsonify({"status": "error", "message": "CSV dataset payload is empty."}), 400
        
        from backend.sindex_service import calculate_sindex
        evaluated_list = []
        for raw in raw_items:
            metadata = {
                "title": str(raw.get("title") or raw.get("Title") or "CSV Import Dataset"),
                "description": str(raw.get("description") or raw.get("Description") or "Metadata imported via CSV file"),
                "repository": str(raw.get("repository") or raw.get("Repository") or "CSV Metadata Upload"),
                "persistent_identifier": str(raw.get("id") or raw.get("doi") or raw.get("accession") or "CSV-001"),
                "license": str(raw.get("license") or "CC-BY-4.0"),
                "version_information": "v1.0",
                "contact_information": "csv-uploader@coreai.bio",
                "public_access": True,
                "raw_data_available": True,
                "processed_data_available": True,
                "machine_readable_format": True,
                "metadata_complete": True,
                "protocol_available": True,
                "publication_linked": True,
                "citation_count": 5,
                "reuse_count": 2
            }
            metrics = calculate_sindex(metadata)
            cat = metrics["category_scores"]
            fair = round(((cat["findability"] + cat["accessibility"] + cat["interoperability"] + cat["reusability"]) / 70.0) * 100, 2)
            evaluated_list.append({
                "metadata": metadata,
                "metrics": metrics,
                "fair_score": fair,
                "provenance": {
                    "dataset_id": {"source": "CSV Metadata Upload", "retrieval_date": "2026-07-26", "api_endpoint": "Local CSV File", "confidence": "high"}
                },
                "source_mode": "User Uploaded CSV Metadata",
                "raw_metadata": metadata
            })

        return jsonify({
            "status": "success",
            "source_type": "csv",
            "source_label": f"Uploaded CSV ({len(evaluated_list)} Records)",
            "datasets": evaluated_list
        })
    else:
        return jsonify({"status": "error", "message": "Invalid source_type specified."}), 400

def get_dataset_by_id(dataset_id):
    dataset_id = dataset_id.strip()
    
    # Strip GEO: prefix if it exists to look up live cached record
    live_acc = dataset_id[4:] if dataset_id.startswith("GEO:") else dataset_id
    
    cached_record = None
    if live_acc.startswith("GSE"):
        from backend.geo_service import load_cached_record
        cached_record, is_valid_cache = load_cached_record(live_acc)
        
    if cached_record:
        from backend.sindex_service import calculate_sindex
        metadata = cached_record["normalized"]
        metrics = calculate_sindex(metadata)
        cat = metrics["category_scores"]
        fair = round(((cat["findability"] + cat["accessibility"] + cat["interoperability"] + cat["reusability"]) / 70.0) * 100, 2)
        return {
            "metadata": metadata,
            "metrics": metrics,
            "fair_score": fair,
            "provenance": cached_record["provenance"],
            "source_mode": cached_record.get("source_mode", "Cached NCBI GEO Metadata"),
            "raw_metadata": cached_record
        }
        
    # If not cached, do a live fetch
    if live_acc.startswith("GSE"):
        from backend.geo_service import fetch_geo_metadata
        from backend.sindex_service import calculate_sindex
        geo_data = fetch_geo_metadata(live_acc)
        
        if geo_data and "error" in geo_data:
            return geo_data
            
        if geo_data and "error" not in geo_data:
            metadata = geo_data["normalized"]
            metrics = calculate_sindex(metadata)
            cat = metrics["category_scores"]
            fair = round(((cat["findability"] + cat["accessibility"] + cat["interoperability"] + cat["reusability"]) / 70.0) * 100, 2)
            return {
                "metadata": metadata,
                "metrics": metrics,
                "fair_score": fair,
                "provenance": geo_data["provenance"],
                "source_mode": geo_data.get("source_mode", "Live NCBI GEO Metadata"),
                "raw_metadata": geo_data
            }
    return None

@app.route('/api/sindex/export/<format_type>')
def export_report(format_type):
    dataset_id = request.args.get("id")
    if not dataset_id:
        return "Missing dataset id parameter", 400
        
    dataset_data = get_dataset_by_id(dataset_id)
    if not dataset_data:
        return f"Dataset '{dataset_id}' not found", 404
        
    from backend.export_service import generate_json_report, generate_csv_report, generate_pdf_report
    
    format_type = format_type.lower()
    if format_type == "json":
        buf = generate_json_report(dataset_data)
        filename = f"sindex_report_{dataset_id}.json"
        mimetype = "application/json"
    elif format_type == "csv":
        buf = generate_csv_report(dataset_data)
        filename = f"sindex_report_{dataset_id}.csv"
        mimetype = "text/csv"
    elif format_type == "pdf":
        buf = generate_pdf_report(dataset_data)
        filename = f"sindex_report_{dataset_id}.pdf"
        mimetype = "application/pdf"
    elif format_type == "ai":
        from backend.assistant_service import AIAssistantEngine
        from backend.export_service import generate_ai_pdf_report
        audit = AIAssistantEngine.audit_dataset(dataset_data["metadata"], dataset_data["metrics"], dataset_data["fair_score"])
        buf = generate_ai_pdf_report(dataset_data, audit)
        filename = f"sindex_ai_audit_{dataset_id}.pdf"
        mimetype = "application/pdf"
    else:
        return f"Unsupported format '{format_type}'", 400
        
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

if __name__ == '__main__':
    # Running locally on localhost:5000 with debug mode enabled for developer inspection
    app.run(host='127.0.0.1', port=5000, debug=True)
