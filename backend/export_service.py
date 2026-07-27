import io
import json
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Line

APP_VERSION = "1.0.0"

def generate_json_report(dataset_data):
    """
    Generates a JSON representation of the S-index compliance report.
    """
    report = {
        "export_metadata": {
            "application": "CoreAI BIO S-index scoring engine",
            "version": APP_VERSION,
            "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        },
        "dataset": {
            "id": dataset_data["metadata"].get("persistent_identifier", "N/A"),
            "title": dataset_data["metadata"].get("title", "N/A"),
            "repository": dataset_data["metadata"].get("repository", "N/A"),
            "organism": dataset_data["metadata"].get("organism", "N/A"),
            "platform": dataset_data["metadata"].get("platform", "N/A"),
            "funding": dataset_data["metadata"].get("funding", "N/A"),
            "raw_metadata": dataset_data["metadata"]
        },
        "compliance_summary": {
            "sindex_score": dataset_data["metrics"].get("final_score", 0),
            "normalized_score": dataset_data["metrics"].get("normalized_score", 0.0),
            "rating": dataset_data["metrics"].get("rating", "Needs Improvement"),
            "fair_score_pct": dataset_data.get("fair_score", 0.0)
        },
        "category_breakdown": dataset_data["metrics"].get("category_scores", {}),
        "checklists": {
            "passed_checks": dataset_data["metrics"].get("passed_checks", []),
            "failed_checks": dataset_data["metrics"].get("failed_checks", [])
        },
        "recommendations": dataset_data["metrics"].get("recommendations", [])
    }
    
    # Write to a string buffer
    buf = io.BytesIO()
    buf.write(json.dumps(report, indent=2).encode('utf-8'))
    buf.seek(0)
    return buf

def generate_csv_report(dataset_data):
    """
    Generates a CSV representation of the S-index compliance report.
    """
    # Write to a string buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Title & Metadata block
    writer.writerow(["CoreAI BIO - NIH Data Sharing Index (S-Index) Report"])
    writer.writerow(["Export Date", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
    writer.writerow(["Application Version", APP_VERSION])
    writer.writerow([])
    
    writer.writerow(["DATASET METADATA"])
    writer.writerow(["Field", "Value"])
    meta = dataset_data["metadata"]
    writer.writerow(["Dataset ID", meta.get("persistent_identifier", "N/A")])
    writer.writerow(["Title", meta.get("title", "N/A")])
    writer.writerow(["Repository", meta.get("repository", "N/A")])
    writer.writerow(["Organism", meta.get("organism", "N/A")])
    writer.writerow(["Platform", meta.get("platform", "N/A")])
    writer.writerow(["Funding", meta.get("funding", "N/A")])
    writer.writerow([])
    
    writer.writerow(["COMPLIANCE METRICS"])
    writer.writerow(["Metric", "Score", "Rating / Context"])
    writer.writerow(["S-index Score", dataset_data["metrics"].get("final_score", 0), dataset_data["metrics"].get("rating", "N/A")])
    writer.writerow(["FAIR Score (%)", f"{dataset_data.get('fair_score', 0.0)}%", "Findability + Accessibility + Interoperability + Reusability"])
    writer.writerow([])
    
    writer.writerow(["CATEGORY BREAKDOWN"])
    writer.writerow(["Category", "Score", "Max Points"])
    cat_scores = dataset_data["metrics"].get("category_scores", {})
    categories = [
        ("Findability", 20),
        ("Accessibility", 15),
        ("Interoperability", 15),
        ("Reusability", 20),
        ("Documentation", 15),
        ("Evidence of Reuse", 15)
    ]
    for cat_name, max_pts in categories:
        key = cat_name.lower().replace(" ", "_")
        writer.writerow([cat_name, cat_scores.get(key, 0), max_pts])
    writer.writerow([])
    
    writer.writerow(["COMPLIANCE CHECKLISTS"])
    writer.writerow(["Check Name", "Status", "Category", "Recommendation"])
    for check in dataset_data["metrics"].get("passed_checks", []):
        writer.writerow([check.get("name"), "PASSED", check.get("category"), ""])
    for check in dataset_data["metrics"].get("failed_checks", []):
        writer.writerow([check.get("name"), "FAILED", check.get("category"), check.get("recommendation")])
        
    # Prepare bytes buffer
    buf = io.BytesIO()
    buf.write(output.getvalue().encode('utf-8'))
    buf.seek(0)
    return buf

def create_pdf_compliance_chart(category_scores):
    """
    Renders a custom vector compliance bar chart using ReportLab shapes.
    """
    d = Drawing(460, 140)
    # Background card panel
    d.add(Rect(0, 0, 460, 140, fillColor=colors.HexColor('#111622'), strokeColor=colors.HexColor('#1e293b'), rx=5, ry=5))
    
    categories = [
        ("Findability", category_scores.get("findability", 0), 20, '#3b82f6'),
        ("Accessibility", category_scores.get("accessibility", 0), 15, '#10b981'),
        ("Interoperability", category_scores.get("interoperability", 0), 15, '#a855f7'),
        ("Reusability", category_scores.get("reusability", 0), 20, '#f97316'),
        ("Documentation", category_scores.get("documentation", 0), 15, '#14b8a6'),
        ("Evidence of Reuse", category_scores.get("evidence_of_reuse", 0), 15, '#ef4444')
    ]
    
    y = 110
    for label, score, max_score, color_hex in categories:
        pct = score / max_score
        bar_width = int(pct * 240)
        
        # Label
        d.add(String(15, y + 2, label, fontSize=8, fillColor=colors.HexColor('#94a3b8'), fontName='Helvetica-Bold'))
        # Background bar
        d.add(Rect(140, y, 240, 8, fillColor=colors.HexColor('#1e293b'), strokeColor=None, rx=2, ry=2))
        # Filled bar
        if bar_width > 0:
            d.add(Rect(140, y, bar_width, 8, fillColor=colors.HexColor(color_hex), strokeColor=None, rx=2, ry=2))
        # Score label
        d.add(String(400, y + 2, f"{score} / {max_score}", fontSize=8, fillColor=colors.HexColor('#f8fafc'), fontName='Helvetica'))
        
        y -= 18
        
    return d

def generate_pdf_report(dataset_data):
    """
    Generates a beautifully styled, print-friendly PDF S-index Compliance Report.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    # Stylesheet configuration
    styles = getSampleStyleSheet()
    
    # Modify default styles safely
    styles['Normal'].textColor = colors.HexColor('#334155')
    styles['Normal'].fontSize = 9
    styles['Normal'].leading = 13
    
    # Custom heading style
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#475569')
    )
    
    meta_value = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#0f172a')
    )
    
    check_passed = ParagraphStyle(
        'CheckPassed',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#047857') # Dark green
    )
    
    check_failed = ParagraphStyle(
        'CheckFailed',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#b91c1c') # Dark red
    )
    
    rec_text = ParagraphStyle(
        'RecText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#64748b'),
        leftIndent=10
    )
    
    summary_para = ParagraphStyle(
        'SummaryText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#1e293b')
    )

    story = []
    
    # 1. Document Header
    story.append(Paragraph("NIH Data Sharing Index (S-Index) Compliance Report", title_style))
    story.append(Paragraph(
        f"Generated by CoreAI BIO on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Platform v{APP_VERSION}",
        subtitle_style
    ))
    
    # 2. Executive Score Highlights Table
    score = dataset_data["metrics"].get("final_score", 0)
    rating = dataset_data["metrics"].get("rating", "Needs Improvement")
    fair = dataset_data.get("fair_score", 0.0)
    
    kpi_data = [
        [
            Paragraph("<b>S-index Score</b>", meta_label),
            Paragraph(f"<font size=14 color='#f97316'><b>{score} / 100</b></font>", meta_value),
            Paragraph("<b>FAIR Compliance Score</b>", meta_label),
            Paragraph(f"<font size=14 color='#3b82f6'><b>{fair}%</b></font>", meta_value)
        ],
        [
            Paragraph("<b>Compliance Rating</b>", meta_label),
            Paragraph(f"<b>{rating}</b>", meta_value),
            Paragraph("<b>Evaluation Standard</b>", meta_label),
            Paragraph("NIH DMSP (2023) Guidelines", meta_value)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[120, 150, 120, 150])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))
    
    # 3. Dataset Profile Info Block
    story.append(Paragraph("Dataset Profile Metadata", section_heading))
    meta = dataset_data["metadata"]
    meta_table_data = [
        [Paragraph("Dataset ID", meta_label), Paragraph(meta.get("persistent_identifier", "N/A"), meta_value)],
        [Paragraph("Dataset Title", meta_label), Paragraph(meta.get("title", "N/A"), meta_value)],
        [Paragraph("Repository", meta_label), Paragraph(meta.get("repository", "N/A"), meta_value)],
        [Paragraph("Organism", meta_label), Paragraph(meta.get("organism", "N/A"), meta_value)],
        [Paragraph("Platform", meta_label), Paragraph(meta.get("platform", "N/A"), meta_value)],
        [Paragraph("Funding Agency", meta_label), Paragraph(meta.get("funding", "N/A"), meta_value)]
    ]
    meta_table = Table(meta_table_data, colWidths=[120, 420])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    
    # 4. Compliance Vector Charts
    story.append(Paragraph("Category Compliance Breakdown", section_heading))
    story.append(create_pdf_compliance_chart(dataset_data["metrics"].get("category_scores", {})))
    story.append(Spacer(1, 15))
    
    # 5. Natural Language S-index Summary
    story.append(Paragraph("S-index Compliance Summary", section_heading))
    summary_text = ""
    idStr = meta.get("persistent_identifier", "N/A")
    scoreStr = f"{score}/100"
    if rating == "Excellent":
        summary_text = f"This dataset ({idStr}) received an S-index rating of <b>Excellent</b> ({scoreStr}) because it satisfies all baseline criteria defined under the NIH Data Management and Sharing Policy. Strengths include complete schema compliance, full raw/processed files availability under CC licensing, experimental protocol linking, and excellent evidence of downstream scientific reuse."
    elif rating == "Good":
        missing_list = ", ".join([c.get("description", "").lower() for c in dataset_data["metrics"].get("failed_checks", [])[:2]])
        summary_text = f"This dataset ({idStr}) received a <b>Good</b> rating ({scoreStr}). It demonstrates robust searchability and repository hosting. However, S-index compliance is currently bottlenecked by the absence of {missing_list or 'minor parameters'}. Rectifying these documentation details will help maximize its reuse index."
    else:
        summary_text = f"This dataset ({idStr}) received a <b>Needs Improvement</b> rating ({scoreStr}) due to significant compliance gaps. It fails to meet multiple mandatory sharing principles, lacking public access controls, repository documentation, machine-readable formats, or contact credentials. Immediate updates are recommended to align the metadata with NIH data sharing regulations."
        
    summary_table = Table([[Paragraph(summary_text, summary_para)]], colWidths=[540])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#fff7ed') if rating == 'Needs Improvement' else colors.HexColor('#f0fdf4') if rating == 'Excellent' else colors.HexColor('#eff6ff')),
        ('PADDING', (0,0), (0,0), 10),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#fed7aa') if rating == 'Needs Improvement' else colors.HexColor('#bbf7d0') if rating == 'Excellent' else colors.HexColor('#bfdbfe')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    
    # 6. Detailed Checklist: Passed & Failed Checks
    story.append(Paragraph("Compliance Checklists & Recommendations", section_heading))
    
    # Process Passed Checks
    for check in dataset_data["metrics"].get("passed_checks", []):
        check_desc = f"<b>[PASSED]</b> {check.get('description')} ({check.get('category').capitalize()})"
        story.append(Paragraph(f"<font color='#047857'>&#x2713;</font> {check_desc}", check_passed))
        story.append(Spacer(1, 4))
        
    # Process Failed Checks & Recommendations
    for check in dataset_data["metrics"].get("failed_checks", []):
        check_desc = f"<b>[FAILED]</b> {check.get('description')} ({check.get('category').capitalize()})"
        rec_desc = f"Recommendation: {check.get('recommendation')}"
        story.append(KeepTogether([
            Paragraph(f"<font color='#b91c1c'>&#x2717;</font> {check_desc}", check_failed),
            Spacer(1, 2),
            Paragraph(rec_desc, rec_text),
            Spacer(1, 4)
        ]))
        
    if not dataset_data["metrics"].get("passed_checks") and not dataset_data["metrics"].get("failed_checks"):
        story.append(Paragraph("No evaluation checks recorded.", styles['Normal']))
        
    story.append(Spacer(1, 15))
    
    # 7. Regulatory Disclaimer Block
    disclaimer_text = (
        "<b>Regulatory Disclaimer:</b> For research and educational use only. "
        "Not for clinical diagnosis or treatment decisions."
    )
    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1 # Center
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))
    
    # Build Document
    doc.build(story)
    buf.seek(0)
    return buf

def generate_ai_pdf_report(dataset_data, audit_results):
    """
    Generates a beautifully styled PDF report specifically for AI Compliance Recommendations.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Modify default styles safely
    styles['Normal'].textColor = colors.HexColor('#334155')
    styles['Normal'].fontSize = 9
    styles['Normal'].leading = 13
    
    title_style = ParagraphStyle(
        'AITitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'AISubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    
    section_heading = ParagraphStyle(
        'AISectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True
    )
    
    item_style = ParagraphStyle(
        'AIItemText',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1e293b'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    meta_label = ParagraphStyle(
        'AIMetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=colors.HexColor('#475569')
    )
    
    meta_value = ParagraphStyle(
        'AIMetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor('#0f172a')
    )

    story = []
    
    # Title
    story.append(Paragraph("AI Compliance Audit & Recommendations", title_style))
    story.append(Paragraph(
        f"Generated by CoreAI BIO Assistant on {audit_results['audit_timestamp']} | Engine v{APP_VERSION}",
        subtitle_style
    ))
    
    # KPI block
    score = audit_results["score"]
    rating = audit_results["rating"]
    fair = audit_results["fair_score"]
    kpi_data = [
        [
            Paragraph("<b>S-index Score</b>", meta_label),
            Paragraph(f"<font size=12 color='#f97316'><b>{score} / 100</b></font>", meta_value),
            Paragraph("<b>FAIR Score</b>", meta_label),
            Paragraph(f"<font size=12 color='#3b82f6'><b>{fair}%</b></font>", meta_value)
        ],
        [
            Paragraph("<b>Compliance Rating</b>", meta_label),
            Paragraph(f"<b>{rating}</b>", meta_value),
            Paragraph("<b>Audit Standard</b>", meta_label),
            Paragraph("NIH DMSP Guidelines", meta_value)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[120, 150, 120, 150])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))
    
    # NIH DMSP Comparison
    story.append(Paragraph("NIH Recommendations Comparison", section_heading))
    summary_table = Table([[Paragraph(audit_results["nih_comparison"], styles['Normal'])]], colWidths=[540])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#fff7ed') if rating == 'Needs Improvement' else colors.HexColor('#f0fdf4') if rating == 'Excellent' else colors.HexColor('#eff6ff')),
        ('PADDING', (0,0), (0,0), 8),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#fed7aa') if rating == 'Needs Improvement' else colors.HexColor('#bbf7d0') if rating == 'Excellent' else colors.HexColor('#bfdbfe')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    
    # Category compliance chart
    story.append(Paragraph("Category Compliance Breakdown", section_heading))
    story.append(create_pdf_compliance_chart(dataset_data["metrics"].get("category_scores", {})))
    story.append(Spacer(1, 10))

    # Missing Information
    story.append(Paragraph("Identified Gaps (Missing Information)", section_heading))
    for item in audit_results["missing_information"]:
        desc = f"<b>{item['field']}</b>: {item['description']}"
        bullet = f"<font color='#ef4444'>&#x2022;</font> {desc}"
        story.append(Paragraph(bullet, item_style))
    story.append(Spacer(1, 10))
        
    # FAIR Compliance Actions
    story.append(Paragraph("FAIR Compliance Optimization Strategy", section_heading))
    for action in audit_results["fair_compliance_actions"]:
        bullet = f"<font color='#3b82f6'>&#x2022;</font> {action}"
        story.append(Paragraph(bullet, item_style))
    story.append(Spacer(1, 10))
        
    # S-index Strategy Checklist
    story.append(Paragraph("S-index Rectification Roadmap", section_heading))
    for step in audit_results["sindex_strategy"]:
        bullet = f"<font color='#10b981'>&#x2713;</font> {step}"
        story.append(Paragraph(bullet, item_style))
    story.append(Spacer(1, 10))
        
    # Regulatory Disclaimer Block
    disclaimer_text = (
        "<b>Regulatory Disclaimer:</b> For research and educational use only. "
        "Not for clinical diagnosis or treatment decisions."
    )
    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1 # Center
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))
    
    doc.build(story)
    buf.seek(0)
    return buf

