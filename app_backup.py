"""
BoviSense – Intelligent Dairy Management System
Smart Reproduction. Healthy Herds. Better Dairy Management.

A comprehensive web-based dairy cattle management and decision-support system.
Integrates cow registry, rule-based estrus prediction, health monitoring,
preliminary disease risk screening, THI heat-stress analytics, milk tracking,
centralized CSV processing, and professional reporting.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import os
import sqlite3

# Import our database module
import database

# ReportLab for PDF report generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# Application Configuration & Theming
# ==========================================
st.set_page_config(
    page_title="BoviSense – Intelligent Dairy Management",
    page_icon="🐄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database on startup
database.init_db()

# Custom CSS for Forest Green / Agricultural Aesthetic
st.markdown("""
<style>
    /* Main branding colors */
    :root {
        --forest-green: #1b4332;
        --accent-green: #2d6a4f;
        --light-green: #52b788;
        --soft-bg: #f8f9fa;
        --gold: #d4af37;
        --text-dark: #212529;
    }
    
    /* Top Bar / Header */
    .brand-header {
        background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%);
        padding: 22px 28px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .brand-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        color: #ffffff;
    }
    .brand-tagline {
        font-size: 0.95rem;
        color: #b7e4c7;
        margin-top: 4px;
        font-weight: 400;
    }
    .demo-badge {
        background-color: #d4af37;
        color: #1b4332;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border: 1px solid #fae588;
    }
    
    /* Metric / KPI Cards */
    .kpi-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 16px 18px;
        border-left: 5px solid #2d6a4f;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .kpi-title {
        font-size: 0.85rem;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #1b4332;
        line-height: 1.2;
    }
    .kpi-subtitle {
        font-size: 0.8rem;
        color: #52b788;
        font-weight: 500;
        margin-top: 4px;
    }
    
    /* Alert cards */
    .alert-card-warning {
        background-color: #fff8e6;
        border-left: 5px solid #d4af37;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 14px;
        color: #7a5800;
    }
    .alert-card-danger {
        background-color: #fdf2f2;
        border-left: 5px solid #e53e3e;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 14px;
        color: #9b2c2c;
    }
    .alert-card-success {
        background-color: #f0fff4;
        border-left: 5px solid #38a169;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 14px;
        color: #22543d;
    }

    /* Section container styling */
    .section-box {
        background: #ffffff;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* Buttons and tabs polish */
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# Core Decision-Support & Prediction Logic
# ==========================================

REPRODUCTIVE_MARKERS = [
    "Standing to Be Mounted",
    "Mounting Other Cows",
    "Clear Vaginal Mucus Discharge",
    "Increased Activity / Restlessness",
    "Vulval Swelling and Redness"
]

REPRODUCTIVE_MARKER_WEIGHTS = {
    "Standing to Be Mounted": 30.0,
    "Mounting Other Cows": 20.0,
    "Clear Vaginal Mucus Discharge": 20.0,
    "Increased Activity / Restlessness": 15.0,
    "Vulval Swelling and Redness": 15.0
}


def calculate_estrus_score(
    selected_markers=None,
    # Optional parameters for backward compatibility:
    standing_to_be_mounted=False,
    mounting_behaviour=False,
    clear_mucus_discharge=False,
    restlessness=False,
    increased_activity=False,
    frequent_vocalization=False,
    swollen_vulva=False,
    reduced_feed_intake=False,
    reduced_milk_yield=False,
    days_since_last_estrus=None,
    days_since_calving=None
):
    """
    Transparent rule-based weighted scoring system for dairy estrus detection.
    Connects the 5 core reproductive markers to evidence scoring:
    - Standing to Be Mounted: 30 pts
    - Mounting Other Cows: 20 pts
    - Clear Vaginal Mucus Discharge: 20 pts
    - Increased Activity / Restlessness: 15 pts
    - Vulval Swelling and Redness: 15 pts
    Maximum evidence score: 100.
    Screening categories:
        0–34: Low evidence
        35–64: Moderate evidence
        65–100: High evidence
    """
    # If selected_markers is None, reconstruct from boolean flags for backward compatibility
    if selected_markers is None:
        selected_markers = []
        if standing_to_be_mounted:
            selected_markers.append("Standing to Be Mounted")
        if mounting_behaviour:
            selected_markers.append("Mounting Other Cows")
        if clear_mucus_discharge:
            selected_markers.append("Clear Vaginal Mucus Discharge")
        if increased_activity or restlessness:
            selected_markers.append("Increased Activity / Restlessness")
        if swollen_vulva:
            selected_markers.append("Vulval Swelling and Redness")

    if isinstance(selected_markers, str):
        selected_markers = [m.strip() for m in selected_markers.split(",") if m.strip()]

    # Deduplicate so each marker contributes only once
    unique_selected = list(dict.fromkeys(selected_markers))

    score = 0.0
    contributions = []

    for marker in unique_selected:
        if marker in REPRODUCTIVE_MARKER_WEIGHTS:
            pts = REPRODUCTIVE_MARKER_WEIGHTS[marker]
            score += pts
            contributions.append(f"{marker} (+{int(pts)} pts)")

    # Score capped at 100
    score = min(100.0, score)

    # Screening categories
    if score >= 65.0:
        category = "High"
    elif score >= 35.0:
        category = "Moderate"
    else:
        category = "Low"

    # Cycle stage estimation
    if "Standing to Be Mounted" in unique_selected or score >= 65.0:
        stage = "Estrus (Standing Heat)"
    elif len(unique_selected) > 0 and score >= 35.0:
        stage = "Proestrus (Coming into Heat)"
    elif len(unique_selected) > 0:
        stage = "Proestrus / Mild Expression"
    elif days_since_last_estrus is not None and 1 <= days_since_last_estrus <= 4:
        stage = "Metestrus (Post-Heat)"
    elif days_since_last_estrus is not None and 5 <= days_since_last_estrus <= 17:
        stage = "Diestrus (Luteal Phase)"
    else:
        stage = "Diestrus / Baseline"

    # Brief explanation
    if score >= 65.0:
        explanation = "High estrus evidence observed. Strong combination of definitive primary standing heat and secondary physiological markers. High likelihood of receptivity for artificial insemination (A.M.–P.M. protocol)."
    elif score >= 35.0:
        explanation = "Moderate estrus evidence observed. Active secondary signs present without definitive standing heat or early proestrus progression. Intensify visual observation over the next 12 hours."
    elif score > 0.0:
        explanation = "Low estrus evidence observed. Isolated secondary or mild restlessness signs detected. Continue routine herd surveillance."
    else:
        explanation = "No behavioural or physiological reproductive markers selected. Baseline observation."

    if days_since_last_estrus is not None and 18 <= days_since_last_estrus <= 24:
        explanation += f" (Timeline aligns with expected ~21-day cycle window: {days_since_last_estrus} days elapsed)."

    return round(score, 1), category, stage, contributions, explanation


def evaluate_disease_risk(
    body_temp,
    milk_drop_pct,
    udder_swelling,
    udder_pain,
    abnormal_udder,
    abnormal_milk,
    digestive_symptoms,
    reproductive_symptoms,
    appetite_state
):
    """
    Rule-based preliminary health and disease risk assessment.
    Screening categories: Low concern, Moderate concern, High concern.
    Decision-support only; never a veterinary diagnosis.
    """
    mastitis_points = 0
    systemic_points = 0
    digestive_points = 0
    reproductive_points = 0
    reasons = []

    # 1. Mastitis screening
    if udder_swelling:
        mastitis_points += 2
        reasons.append("Quarter or udder swelling observed")
    if udder_pain:
        mastitis_points += 2
        reasons.append("Udder tenderness / flinching on touch")
    if abnormal_udder:
        mastitis_points += 2
        reasons.append("Visible redness or localized heat on udder")
    if abnormal_milk:
        mastitis_points += 3
        reasons.append("Visible clots, flakes, or watery milk secretion")
    if milk_drop_pct and milk_drop_pct >= 20.0:
        mastitis_points += 1
        reasons.append(f"Marked milk yield decline ({milk_drop_pct:.1f}%)")

    # 2. Systemic / Fever screening
    if body_temp >= 39.6:
        systemic_points += 3
        mastitis_points += 1
        reasons.append(f"Significant fever detected: {body_temp:.1f} °C (threshold > 39.5 °C)")
    elif body_temp >= 39.3:
        systemic_points += 1
        reasons.append(f"Mild pyrexia: {body_temp:.1f} °C")
    elif body_temp < 38.0:
        systemic_points += 2
        reasons.append(f"Hypothermia alert: {body_temp:.1f} °C (physiological lower bound < 38.0 °C)")

    # 3. Digestive screening
    if appetite_state in ["Anorexic", "Severely Reduced"]:
        digestive_points += 2
        systemic_points += 1
        reasons.append("Severe appetite depression / anorexia")
    elif appetite_state == "Reduced":
        digestive_points += 1
    if digestive_symptoms and str(digestive_symptoms).lower() not in ["none", "", "nan"]:
        digestive_points += 2
        reasons.append(f"Reported digestive signs: {digestive_symptoms}")

    # 4. Reproductive screening
    if reproductive_symptoms and str(reproductive_symptoms).lower() not in ["none", "", "nan"]:
        reproductive_points += 2
        reasons.append(f"Reported reproductive signs: {reproductive_symptoms}")

    # Classify each category
    def to_concern(pts):
        if pts >= 3:
            return "High concern"
        elif pts >= 1:
            return "Moderate concern"
        return "Low concern"

    mast_risk = to_concern(mastitis_points)
    sys_risk = to_concern(systemic_points)
    dig_risk = to_concern(digestive_points)
    rep_risk = to_concern(reproductive_points)

    # Overall concern
    if "High concern" in [mast_risk, sys_risk, dig_risk, rep_risk]:
        overall = "High concern"
        vet_rec = 1
    elif "Moderate concern" in [mast_risk, sys_risk, dig_risk, rep_risk]:
        overall = "Moderate concern"
        vet_rec = 0
    else:
        overall = "Low concern"
        vet_rec = 0

    rationale_str = "; ".join(reasons) if reasons else "All screened health parameters within normal physiological reference ranges."
    return mast_risk, sys_risk, dig_risk, rep_risk, overall, rationale_str, vet_rec


# ==========================================
# PDF Report Generation Utility (ReportLab)
# ==========================================

def create_pdf_report(report_title, summary_dict, table_df, notes_text=""):
    """
    Generate a clean, styled, multi-page PDF document using ReportLab.
    Returns bytes of the compiled PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1b4332'),
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#52b788'),
        spaceAfter=15,
        fontName='Helvetica'
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2d6a4f'),
        spaceBefore=10,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#212529'),
        spaceAfter=4,
        fontName='Helvetica'
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontSize=8,
        textColor=colors.HexColor('#6c757d'),
        spaceBefore=12,
        fontName='Helvetica-Oblique'
    )

    story = []

    # Title & Header
    story.append(Paragraph("BOVISENSE – Intelligent Dairy Cow Management", title_style))
    story.append(Paragraph(f"{report_title} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2d6a4f'), spaceAfter=12))

    # Summary KPI Table
    if summary_dict:
        story.append(Paragraph("Executive Summary & Operational Metrics", heading_style))
        kpi_data = []
        row = []
        for i, (k, v) in enumerate(summary_dict.items()):
            row.extend([Paragraph(f"<b>{k}</b>", body_style), Paragraph(str(v), body_style)])
            if len(row) == 4:
                kpi_data.append(row)
                row = []
        if row:
            while len(row) < 4:
                row.extend(["", ""])
            kpi_data.append(row)

        kpi_table = Table(kpi_data, colWidths=[120, 150, 120, 150])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

    # Data Table
    if table_df is not None and not table_df.empty:
        story.append(Paragraph("Detailed Records (Top 25)", heading_style))
        # Limit columns if too wide
        display_df = table_df.head(25).copy()
        if len(display_df.columns) > 7:
            display_df = display_df.iloc[:, :7]

        # Table data
        header = [Paragraph(f"<b>{col.replace('_', ' ').title()}</b>", body_style) for col in display_df.columns]
        rows = [header]
        for _, r in display_df.iterrows():
            row_vals = []
            for val in r:
                text_val = str(val)[:24] if pd.notna(val) else "-"
                row_vals.append(Paragraph(text_val, body_style))
            rows.append(row_vals)

        col_w = 540 / len(display_df.columns)
        table = Table(rows, colWidths=[col_w] * len(display_df.columns))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d6a4f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ced4da')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    if notes_text:
        story.append(Paragraph("Clinical & Technical Notes", heading_style))
        story.append(Paragraph(notes_text, body_style))

    # Regulatory & Decision-Support Disclaimer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ced4da'), spaceAfter=8))
    story.append(Paragraph(
        "<b>DISCLAIMER:</b> BoviSense decision-support outputs, estrus scores, and disease risk screening are "
        "indicative screening tools designed to assist herd managers. They do NOT constitute confirmed clinical or "
        "veterinary diagnoses. Always consult a licensed veterinarian for medical diagnosis and prescription treatment.",
        disclaimer_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==========================================
# CSV Import Templates and Validation Engine
# ==========================================

CSV_SCHEMAS = {
    "cows": {
        "required": ["cow_id", "name", "breed"],
        "optional": ["dob", "age", "weight", "lactation_number", "daily_milk_production", "last_calving_date", "last_observed_estrus_date", "last_insemination_date", "pregnancy_status", "health_status", "reproductive_status", "remarks"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-201", "name": "Clara", "breed": "Holstein Friesian", "dob": "2022-03-15", "age": 4.0, "weight": 570.0, "lactation_number": 2, "daily_milk_production": 27.5, "last_calving_date": "2025-11-10", "last_observed_estrus_date": "2026-01-05", "last_insemination_date": "2026-01-06", "pregnancy_status": "Pregnant", "health_status": "Healthy", "reproductive_status": "Confirmed Pregnant", "remarks": "High yield"},
            {"cow_id": "COW-202", "name": "Freya", "breed": "Jersey", "dob": "2023-05-20", "age": 3.0, "weight": 420.0, "lactation_number": 1, "daily_milk_production": 19.0, "last_calving_date": "2025-12-01", "last_observed_estrus_date": "2026-01-20", "last_insemination_date": "", "pregnancy_status": "Open", "health_status": "Healthy", "reproductive_status": "Open", "remarks": "Good butterfat"}
        ])
    },
    "estrus_observations": {
        "required": ["cow_id", "observation_date"],
        "optional": ["selected_markers", "increased_activity", "restlessness", "mounting_behaviour", "standing_to_be_mounted", "frequent_vocalization", "reduced_feed_intake", "clear_mucus_discharge", "swollen_vulva", "reduced_milk_yield", "notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "observation_date": "2026-02-01", "selected_markers": "Standing to Be Mounted, Clear Vaginal Mucus Discharge", "increased_activity": 1, "restlessness": 1, "mounting_behaviour": 1, "standing_to_be_mounted": 1, "frequent_vocalization": 1, "reduced_feed_intake": 1, "clear_mucus_discharge": 1, "swollen_vulva": 1, "reduced_milk_yield": 1, "notes": "Active morning standing heat"},
            {"cow_id": "COW-102", "observation_date": "2026-02-01", "selected_markers": "Increased Activity / Restlessness", "increased_activity": 1, "restlessness": 1, "mounting_behaviour": 0, "standing_to_be_mounted": 0, "frequent_vocalization": 1, "reduced_feed_intake": 0, "clear_mucus_discharge": 0, "swollen_vulva": 0, "reduced_milk_yield": 0, "notes": "Early proestrus signs"}
        ])
    },
    "health_records": {
        "required": ["cow_id", "observation_date", "body_temperature"],
        "optional": ["milk_production", "appetite", "feed_intake", "water_intake", "activity_level", "behaviour", "symptoms", "health_notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "observation_date": "2026-02-01", "body_temperature": 38.6, "milk_production": 26.5, "appetite": "Normal", "feed_intake": 18.0, "water_intake": 80.0, "activity_level": "Normal", "behaviour": "Normal", "symptoms": "None", "health_notes": "Healthy morning screening"},
            {"cow_id": "COW-102", "observation_date": "2026-02-01", "body_temperature": 39.8, "milk_production": 14.0, "appetite": "Reduced", "feed_intake": 10.0, "water_intake": 50.0, "activity_level": "Lethargic", "behaviour": "Dull", "symptoms": "Fever, mild nasal discharge", "health_notes": "Needs veterinary check"}
        ])
    },
    "disease_assessments": {
        "required": ["cow_id", "assessment_date"],
        "optional": ["udder_swelling", "udder_pain", "abnormal_udder_appearance", "abnormal_milk", "elevated_temp", "reduced_yield", "digestive_symptoms", "reproductive_symptoms", "screening_notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "assessment_date": "2026-02-01", "udder_swelling": 0, "udder_pain": 0, "abnormal_udder_appearance": 0, "abnormal_milk": 0, "elevated_temp": 0, "reduced_yield": 0, "digestive_symptoms": "None", "reproductive_symptoms": "None", "screening_notes": "Routine inspection normal"},
            {"cow_id": "COW-111", "assessment_date": "2026-02-01", "udder_swelling": 1, "udder_pain": 1, "abnormal_udder_appearance": 1, "abnormal_milk": 1, "elevated_temp": 1, "reduced_yield": 1, "digestive_symptoms": "None", "reproductive_symptoms": "None", "screening_notes": "Severe clinical mastitis signs"}
        ])
    },
    "thi_records": {
        "required": ["observation_date", "observation_time", "ambient_temp", "relative_humidity"],
        "optional": ["notes"],
        "sample": pd.DataFrame([
            {"observation_date": "2026-02-01", "observation_time": "08:00", "ambient_temp": 22.5, "relative_humidity": 65.0, "notes": "Morning reading"},
            {"observation_date": "2026-02-01", "observation_time": "14:00", "ambient_temp": 32.0, "relative_humidity": 75.0, "notes": "Afternoon peak heat"}
        ])
    },
    "milk_records": {
        "required": ["cow_id", "production_date"],
        "optional": ["morning_yield", "evening_yield", "total_yield", "notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "production_date": "2026-02-01", "morning_yield": 15.0, "evening_yield": 12.5, "total_yield": 27.5, "notes": "Standard milking"},
            {"cow_id": "COW-102", "production_date": "2026-02-01", "morning_yield": 11.0, "evening_yield": 9.5, "total_yield": 20.5, "notes": "Evening milking"}
        ])
    },
    "reproductive_history": {
        "required": ["cow_id", "event_date", "event_type"],
        "optional": ["details", "technician_or_sire", "outcome"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "event_date": "2026-01-05", "event_type": "Estrus Observed", "details": "Standing heat expression", "technician_or_sire": "Staff", "outcome": "Logged"},
            {"cow_id": "COW-101", "event_date": "2026-01-06", "event_type": "Artificial Insemination", "details": "Straw HF-9042", "technician_or_sire": "Dr. Sharma", "outcome": "Success"}
        ])
    },
    "sensor_records": {
        "required": ["cow_id", "timestamp", "activity_index", "rumination_minutes"],
        "optional": ["notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "timestamp": "2026-02-01 00:00", "activity_index": 32.5, "rumination_minutes": 58.0},
            {"cow_id": "COW-101", "timestamp": "2026-02-01 02:00", "activity_index": 28.0, "rumination_minutes": 62.0},
            {"cow_id": "COW-101", "timestamp": "2026-02-01 04:00", "activity_index": 35.0, "rumination_minutes": 55.0},
            {"cow_id": "COW-101", "timestamp": "2026-02-01 06:00", "activity_index": 62.0, "rumination_minutes": 30.0},
            {"cow_id": "COW-101", "timestamp": "2026-02-01 08:00", "activity_index": 70.0, "rumination_minutes": 25.0},
            {"cow_id": "COW-101", "timestamp": "2026-02-01 10:00", "activity_index": 54.0, "rumination_minutes": 42.0},
            {"cow_id": "COW-102", "timestamp": "2026-02-01 00:00", "activity_index": 30.0, "rumination_minutes": 52.0},
            {"cow_id": "COW-102", "timestamp": "2026-02-01 02:00", "activity_index": 27.5, "rumination_minutes": 60.0}
        ])
    }
}


def validate_csv_dataframe(df, category, existing_cow_ids):
    """
    Validates CSV records with comprehensive integrity checks:
    - Required columns
    - Data type and numerical ranges
    - Date format validity
    - Foreign key / Unknown Cow ID detection
    - Duplicate detection
    Returns: valid_rows (list of dicts), rejected_rows (list of dicts with error_reason)
    """
    schema = CSV_SCHEMAS.get(category)
    if not schema:
        return [], [{"error_reason": f"Unknown category: {category}"}]

    # Check required columns
    missing_cols = [c for c in schema["required"] if c not in df.columns]
    if missing_cols:
        return [], [{"error_reason": f"Missing mandatory columns: {', '.join(missing_cols)}"}]

    valid_rows = []
    rejected_rows = []
    seen_csv_keys = set()

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        errors = []

        # 1. Check Cow ID existence if applicable
        if "cow_id" in schema["required"]:
            cid = str(row_dict.get("cow_id", "")).strip()
            if not cid or cid.lower() in ["nan", "none"]:
                errors.append("Empty Cow ID")
            elif category != "cows" and cid not in existing_cow_ids:
                errors.append(f"Unknown Cow ID '{cid}' – please register cow in Cow Management first")

        # 2. Check Dates
        for date_col in ["observation_date", "production_date", "event_date", "assessment_date", "dob", "last_calving_date"]:
            if date_col in row_dict and pd.notna(row_dict[date_col]) and str(row_dict[date_col]).strip():
                val = str(row_dict[date_col]).strip()[:10]
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                    row_dict[date_col] = val
                except ValueError:
                    errors.append(f"Invalid date format in '{date_col}' (expected YYYY-MM-DD, got '{val}')")

        # 3. Specific Category Bounds
        if category == "health_records":
            try:
                temp = float(row_dict.get("body_temperature"))
                if not (35.0 <= temp <= 45.0):
                    errors.append(f"Body temperature {temp}°C out of physiological range (35.0–45.0°C)")
                row_dict["body_temperature"] = temp
            except (ValueError, TypeError):
                errors.append("Invalid or missing numerical body_temperature")

        elif category == "thi_records":
            try:
                temp = float(row_dict.get("ambient_temp"))
                if not (-20.0 <= temp <= 60.0):
                    errors.append(f"Ambient temperature {temp}°C out of realistic range")
                row_dict["ambient_temp"] = temp
            except (ValueError, TypeError):
                errors.append("Invalid numerical ambient_temp")

            try:
                rh = float(row_dict.get("relative_humidity"))
                if not (0.0 <= rh <= 100.0):
                    errors.append(f"Relative humidity {rh}% must be between 0 and 100%")
                row_dict["relative_humidity"] = rh
            except (ValueError, TypeError):
                errors.append("Invalid numerical relative_humidity")

        elif category == "milk_records":
            try:
                m_yield = float(row_dict.get("morning_yield", 0.0) or 0.0)
                e_yield = float(row_dict.get("evening_yield", 0.0) or 0.0)
                if m_yield < 0 or e_yield < 0:
                    errors.append("Milk yields cannot be negative")
                t_yield = row_dict.get("total_yield")
                if t_yield is None or pd.isna(t_yield) or float(t_yield) == 0.0:
                    row_dict["total_yield"] = round(m_yield + e_yield, 2)
                else:
                    t_val = float(t_yield)
                    if t_val < 0:
                        errors.append("Total milk yield cannot be negative")
                    row_dict["total_yield"] = t_val
            except (ValueError, TypeError):
                errors.append("Invalid numerical milk yield values")

        elif category == "sensor_records":
            # 1. Validate Timestamp format
            ts_raw = row_dict.get("timestamp")
            parsed_ts = None
            if pd.isna(ts_raw) or not str(ts_raw).strip():
                errors.append("Missing timestamp")
            else:
                ts_str = str(ts_raw).strip()
                try:
                    p_dt = pd.to_datetime(ts_str)
                    parsed_ts = p_dt.strftime("%Y-%m-%d %H:%M")
                    row_dict["timestamp"] = parsed_ts
                except Exception:
                    errors.append(f"Invalid timestamp '{ts_str}'. Expected 'YYYY-MM-DD HH:MM'")

            # 2. Activity index (positive numeric, preserving original sensor units)
            try:
                act = float(row_dict.get("activity_index"))
                if act < 0.0:
                    errors.append(f"Activity index ({act}) cannot be negative")
                row_dict["activity_index"] = act
            except (ValueError, TypeError):
                errors.append("Invalid or non-numeric activity_index")

            # 3. Rumination minutes (must be 0 to 120 minutes for a 2-hour interval)
            try:
                rum = float(row_dict.get("rumination_minutes"))
                if not (0.0 <= rum <= 120.0):
                    errors.append(f"Rumination minutes ({rum}) out of bounds (must be between 0 and 120 min for a 2-hr window)")
                row_dict["rumination_minutes"] = rum
            except (ValueError, TypeError):
                errors.append("Invalid or non-numeric rumination_minutes")

            # 4. Duplicate checks (within CSV and against database)
            cid = str(row_dict.get("cow_id", "")).strip()
            if parsed_ts and cid:
                pair = (cid, parsed_ts)
                if pair in seen_csv_keys:
                    errors.append(f"Duplicate record in uploaded file for Cow {cid} at {parsed_ts}")
                else:
                    seen_csv_keys.add(pair)
                    if database.check_sensor_duplicate(cid, parsed_ts):
                        errors.append(f"Duplicate record: Cow {cid} at {parsed_ts} already exists in database")

        if errors:
            row_dict["error_reason"] = " | ".join(errors)
            rejected_rows.append(row_dict)
        else:
            valid_rows.append(row_dict)

    return valid_rows, rejected_rows


# ==========================================
# Sidebar & Global Layout
# ==========================================

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0 16px 0;">
            <div style="background-color: #1b4332; color: #ffffff; padding: 12px; border-radius: 10px; font-weight: 800; font-size: 1.4rem; letter-spacing: 0.5px;">
                🐄 BOVISENSE
            </div>
            <div style="font-size: 0.8rem; color: #2d6a4f; margin-top: 5px; font-weight: 600;">
                Intelligent Dairy Platform
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Main Navigation
        nav_options = [
            "Executive Dashboard",
            "Cow Management",
            "Estrus Prediction",
            "Health Monitoring",
            "Disease Risk Assessment",
            "THI & Heat Stress",
            "Milk Production",
            "Reports & Analytics",
            "CSV Import Center",
            "CSV Export & Backup"
        ]

        selected_page = st.radio("Navigation Menu", nav_options, index=0)

        st.markdown("---")

        # Demonstration Data Management Section
        st.markdown("#### ⚙️ Data Mode & Demo")
        kpis = database.get_dashboard_kpis()
        if kpis["has_demo"]:
            st.markdown("""
            <div style="background-color: #fff9db; border: 1px solid #f08c00; border-radius: 6px; padding: 8px; font-size: 0.8rem; color: #d9480f; margin-bottom: 8px;">
                <b>DEMONSTRATION MODE ACTIVE</b><br>Fictional herd records currently loaded.
            </div>
            """, unsafe_allow_html=True)
            if st.button("🗑️ Clear Demo Records", use_container_width=True):
                ok, msg = database.clear_demo_data()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.markdown("""
            <div style="background-color: #ebfbee; border: 1px solid #40c057; border-radius: 6px; padding: 8px; font-size: 0.8rem; color: #2b8a3e; margin-bottom: 8px;">
                <b>ACTUAL FARM DATA MODE</b><br>Ready for live operations or CSV imports.
            </div>
            """, unsafe_allow_html=True)
            if st.button("✨ Load Demonstration Data", use_container_width=True):
                ok, msg = database.generate_demo_data()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.info(msg)

        st.markdown("---")
        # Quick stats footer
        st.markdown(f"""
        <div style="font-size: 0.78rem; color: #6c757d; line-height: 1.4;">
            <b>Herd Registry:</b> {kpis['total_cows']} cows<br>
            <b>Daily Milk:</b> {kpis['total_daily_milk']} L<br>
            <b>Current THI:</b> {kpis['latest_thi'] or 'N/A'}<br>
            <b>Database:</b> SQLite (bovisense.db)
        </div>
        """, unsafe_allow_html=True)

        return selected_page


# ==========================================
# MODULE 1: Executive Dashboard
# ==========================================

def render_dashboard():
    kpis = database.get_dashboard_kpis()

    # Brand Banner
    demo_tag = '<span class="demo-badge">Demo Mode Active</span>' if kpis["has_demo"] else '<span class="demo-badge" style="background:#52b788; color:#fff;">Live Farm Records</span>'
    st.markdown(f"""
    <div class="brand-header">
        <div>
            <div class="brand-title">BoviSense – Executive Dashboard</div>
            <div class="brand-tagline">Smart Reproduction. Healthy Herds. Better Dairy Management.</div>
        </div>
        <div>{demo_tag}</div>
    </div>
    """, unsafe_allow_html=True)

    # Top KPI Row (8 metrics across two 4-column rows)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Registered</div>
            <div class="kpi-value">{kpis['total_cows']}</div>
            <div class="kpi-subtitle">Cattle in Database</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #52b788;">
            <div class="kpi-title">Active Milking & Open</div>
            <div class="kpi-value">{kpis['active_cows']}</div>
            <div class="kpi-subtitle">Productive Herd</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #d4af37;">
            <div class="kpi-title">High Estrus Evidence</div>
            <div class="kpi-value">{kpis['high_estrus_count']}</div>
            <div class="kpi-subtitle">Active Insemination Candidates</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: {'#e53e3e' if kpis['health_attention_count'] > 0 else '#52b788'};">
            <div class="kpi-title">Health Attention Needed</div>
            <div class="kpi-value">{kpis['health_attention_count']}</div>
            <div class="kpi-subtitle">Requires Clinical Check</div>
        </div>
        """, unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        thi_display = f"{kpis['latest_thi']:.1f}" if kpis['latest_thi'] else "N/A"
        thi_color = "#e53e3e" if kpis['thi_stress_active'] else "#2d6a4f"
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: {thi_color};">
            <div class="kpi-title">Current THI</div>
            <div class="kpi-value">{thi_display}</div>
            <div class="kpi-subtitle">{kpis['latest_thi_category']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #2d6a4f;">
            <div class="kpi-title">Total Daily Milk</div>
            <div class="kpi-value">{kpis['total_daily_milk']} L</div>
            <div class="kpi-subtitle">Bulk Tank Estimate</div>
        </div>
        """, unsafe_allow_html=True)
    with c7:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #52b788;">
            <div class="kpi-title">Avg Milk / Cow</div>
            <div class="kpi-value">{kpis['avg_daily_milk']} L</div>
            <div class="kpi-subtitle">Per Cow / Day</div>
        </div>
        """, unsafe_allow_html=True)
    with c8:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: #d4af37;">
            <div class="kpi-title">Upcoming Estrus Windows</div>
            <div class="kpi-value">{kpis['upcoming_estrus_count']}</div>
            <div class="kpi-subtitle">Expected in Next 7 Days</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Urgent Attention Banners if conditions exist
    if kpis['health_attention_count'] > 0:
        st.markdown("""
        <div class="alert-card-danger">
            <b>⚠️ HEALTH ALERT:</b> One or more cows have elevated body temperatures, drop in appetite, or mastitis risk flags. Check <b>Health Monitoring</b> and <b>Disease Risk Assessment</b>.
        </div>
        """, unsafe_allow_html=True)
    if kpis['thi_stress_active']:
        st.markdown(f"""
        <div class="alert-card-warning">
            <b>🌡️ HEAT STRESS ADVISORY:</b> Current environmental THI ({kpis['latest_thi']}) is in <b>{kpis['latest_thi_category']}</b>. Activate cooling fans, shade, and fresh cold water.
        </div>
        """, unsafe_allow_html=True)

    # Sensor-Based Real-time Surveillance Bar
    tot_sensors = kpis.get('total_sensor_records', 0)
    high_sensor_cows = kpis.get('sensor_high_estrus_count', 0)
    if tot_sensors > 0:
        status_text = f"🚨 {high_sensor_cows} COWS IN ACTIVE ESTRUS SPIKE" if high_sensor_cows > 0 else "🟢 BASELINE STABLE"
        status_bg = "#d4af37" if high_sensor_cows > 0 else "#52b788"
        status_color = "#1b4332" if high_sensor_cows > 0 else "white"

        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1b4332 0%, #2d6a4f 100%); color: white; border-radius: 8px; padding: 12px 18px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
            <div style="font-size: 0.92rem;">
                <b>📡 2-Hourly Sensor Biometrics Surveillance:</b>
                <span style="opacity: 0.9; margin-left: 6px;">
                    <b>{tot_sensors:,}</b> intervals logged &nbsp;|&nbsp; 
                    <b>{high_sensor_cows}</b> cows with high activity/rumination divergence in last 48h
                </span>
            </div>
            <div style="background: {status_bg}; color: {status_color}; padding: 4px 12px; border-radius: 12px; font-weight: 800; font-size: 0.8rem;">
                {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Visualizations Row 1
    cows_df = database.get_all_cows()
    milk_df = database.get_milk_records()
    thi_df = database.get_thi_records()
    estrus_df = database.get_estrus_observations()

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Herd Distributions", "📈 Milk & Environmental Trends", "🔔 Actionable Worklists", "📡 Sensor & Cross-Analytics"
    ])

    with tab1:
        v1, v2, v3 = st.columns(3)
        with v1:
            if not cows_df.empty:
                breed_counts = cows_df['breed'].value_counts().reset_index()
                breed_counts.columns = ['Breed', 'Count']
                fig_breed = px.pie(
                    breed_counts, names='Breed', values='Count',
                    title="Herd Breed Distribution",
                    color_discrete_sequence=px.colors.sequential.Greens_r,
                    hole=0.45
                )
                fig_breed.update_layout(margin=dict(t=40, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig_breed, use_container_width=True)
            else:
                st.info("No cow records to display.")

        with v2:
            if not cows_df.empty:
                rep_counts = cows_df['reproductive_status'].value_counts().reset_index()
                rep_counts.columns = ['Reproductive Status', 'Count']
                fig_rep = px.bar(
                    rep_counts, x='Reproductive Status', y='Count',
                    title="Reproductive Status Distribution",
                    color='Reproductive Status',
                    color_discrete_sequence=['#2d6a4f', '#52b788', '#d4af37', '#e53e3e', '#74c69d']
                )
                fig_rep.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig_rep, use_container_width=True)
            else:
                st.info("No cow records to display.")

        with v3:
            if not estrus_df.empty:
                estrus_cat = estrus_df['evidence_category'].value_counts().reset_index()
                estrus_cat.columns = ['Category', 'Observations']
                fig_est = px.pie(
                    estrus_cat, names='Category', values='Observations',
                    title="Estrus Evidence Classification",
                    color='Category',
                    color_discrete_map={'High': '#2d6a4f', 'Moderate': '#d4af37', 'Low': '#a3b18a'},
                    hole=0.45
                )
                fig_est.update_layout(margin=dict(t=40, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig_est, use_container_width=True)
            else:
                st.info("No estrus observations to display.")

    with tab2:
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            if not milk_df.empty:
                # Group by production_date
                daily_milk = milk_df.groupby('production_date')['total_yield'].sum().reset_index()
                daily_milk = daily_milk.sort_values('production_date')
                fig_milk = px.line(
                    daily_milk, x='production_date', y='total_yield',
                    title="Herd Total Daily Milk Yield (Litres)",
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=['#2d6a4f']
                )
                fig_milk.update_layout(
                    xaxis_title="Date", yaxis_title="Total Production (L)",
                    margin=dict(t=40, b=10, l=10, r=10), height=320
                )
                st.plotly_chart(fig_milk, use_container_width=True)
            else:
                st.info("No milk records available.")

        with t_col2:
            if not thi_df.empty:
                thi_sorted = thi_df.sort_values(['observation_date', 'observation_time'])
                fig_thi = px.line(
                    thi_sorted, x='observation_date', y='thi_value',
                    title="Temperature-Humidity Index (THI) Trajectory",
                    markers=True,
                    color_discrete_sequence=['#b8860b']
                )
                # Add threshold reference lines
                fig_thi.add_hline(y=68, line_dash="dash", line_color="#52b788", annotation_text="Mild Stress (68)")
                fig_thi.add_hline(y=72, line_dash="dash", line_color="#f59f00", annotation_text="Significant Stress (72)")
                fig_thi.add_hline(y=80, line_dash="dash", line_color="#e53e3e", annotation_text="Severe Stress (80)")
                fig_thi.update_layout(
                    xaxis_title="Date", yaxis_title="THI Score",
                    margin=dict(t=40, b=10, l=10, r=10), height=320
                )
                st.plotly_chart(fig_thi, use_container_width=True)
            else:
                st.info("No THI records available.")

    with tab3:
        w1, w2 = st.columns(2)
        with w1:
            st.markdown("##### 🚨 Cows Requiring Attention")
            # Pull cows needing attention
            if not cows_df.empty:
                attention_cows = cows_df[
                    (cows_df['health_status'] != 'Healthy') |
                    (cows_df['reproductive_status'] == 'In Heat')
                ][['cow_id', 'name', 'breed', 'health_status', 'reproductive_status', 'daily_milk_production']]
                if not attention_cows.empty:
                    st.dataframe(attention_cows, use_container_width=True, hide_index=True)
                else:
                    st.success("All cows currently clear of flagged alerts.")
            else:
                st.info("No cow records.")

        with w2:
            st.markdown("##### 📅 Upcoming Estimated Estrus Windows (Next 7 Days)")
            if not estrus_df.empty:
                today_str = date.today().strftime("%Y-%m-%d")
                next_week_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
                upcoming = estrus_df[
                    (estrus_df['estimated_next_estrus'] >= today_str) &
                    (estrus_df['estimated_next_estrus'] <= next_week_str)
                ][['cow_id', 'estimated_next_estrus', 'evidence_category', 'cycle_stage']]
                if not upcoming.empty:
                    st.dataframe(upcoming.drop_duplicates(subset=['cow_id']), use_container_width=True, hide_index=True)
                else:
                    st.info("No upcoming estrus windows scheduled in the immediate 7-day forecast.")
            else:
                st.info("No estrus prediction history.")

    with tab4:
        st.markdown("#### 📡 2-Hourly Sensor Telemetry & Cross-System Analytics")
        st.write("Contextual comparison of 2-hour sensor activity/rumination biometrics with herd milk yield, environmental THI, and manual reproductive observations.")

        sensor_records_df = database.get_sensor_records()
        if not sensor_records_df.empty:
            analyzed_all = database.analyze_sensor_estrus(sensor_records_df)

            col_s1, col_s2 = st.columns([1.2, 1])
            with col_s1:
                st.markdown("##### 🚨 Active Sensor Estrus Alerts (Last 48 Hours)")
                two_days_ago_str = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
                recent_spikes = analyzed_all[
                    (analyzed_all['timestamp'] >= two_days_ago_str) &
                    (analyzed_all['evidence_category'] == 'High')
                ].sort_values('timestamp', ascending=False)

                if not recent_spikes.empty:
                    st.dataframe(
                        recent_spikes[['cow_id', 'timestamp', 'activity_index', 'activity_change_pct', 'rumination_minutes', 'rumination_change_pct', 'combined_evidence_score', 'explanation']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No high-evidence sensor estrus spikes detected in the last 48 hours.")

            with col_s2:
                st.markdown("##### 🔬 Contextual Biological Governance")
                st.markdown("""
                <div style="background: #f8fafc; border-left: 4px solid #2d6a4f; padding: 12px 14px; border-radius: 6px; font-size: 0.86rem; color: #334155;">
                    <b>Cross-System Interpretation Principles:</b>
                    <br>• <b>THI Context:</b> High environmental THI (≥72) suppresses overt behavioral activity and reduces rumination. Cross-check THI trajectory when interpreting nighttime sensor spikes.
                    <br>• <b>Milk Yield Impact:</b> Estrus restlessness frequently triggers a temporary 10–25% drop in daily milk yield on the day of peak standing heat.
                    <br>• <b>Disease Separation:</b> Sensor deviations (e.g. low rumination) are treated strictly as behavioral evidence, not automatic clinical disease diagnoses.
                </div>
                """, unsafe_allow_html=True)

            # Cross-Comparison Visualization: Herd Daily Average Activity vs Herd Daily Milk Yield vs Average THI
            st.markdown("##### Contextual Herd Trajectory: Sensor Activity vs Milk Yield vs Environmental THI")
            analyzed_all['obs_date'] = analyzed_all['timestamp_dt'].dt.strftime('%Y-%m-%d')
            daily_sensor = analyzed_all.groupby('obs_date').agg({
                'activity_index': 'mean',
                'rumination_minutes': 'mean'
            }).reset_index()

            daily_milk_summary = milk_df.groupby('production_date')['total_yield'].sum().reset_index() if not milk_df.empty else pd.DataFrame(columns=['production_date', 'total_yield'])
            daily_thi_summary = thi_df.groupby('observation_date')['thi_value'].mean().reset_index() if not thi_df.empty else pd.DataFrame(columns=['observation_date', 'thi_value'])

            merged_daily = pd.merge(daily_sensor, daily_milk_summary, left_on='obs_date', right_on='production_date', how='left')
            merged_daily = pd.merge(merged_daily, daily_thi_summary, left_on='obs_date', right_on='observation_date', how='left')
            merged_daily = merged_daily.sort_values('obs_date')

            if not merged_daily.empty:
                fig_cross = go.Figure()
                fig_cross.add_trace(go.Scatter(
                    x=merged_daily['obs_date'],
                    y=merged_daily['activity_index'],
                    name='Herd Avg Activity Index',
                    mode='lines+markers',
                    line=dict(color='#2d6a4f', width=2.5)
                ))
                if 'total_yield' in merged_daily.columns and merged_daily['total_yield'].notna().any():
                    fig_cross.add_trace(go.Scatter(
                        x=merged_daily['obs_date'],
                        y=merged_daily['total_yield'],
                        name='Herd Total Milk (L)',
                        mode='lines+markers',
                        line=dict(color='#d4af37', width=2, dash='dot'),
                        yaxis='y2'
                    ))
                if 'thi_value' in merged_daily.columns and merged_daily['thi_value'].notna().any():
                    fig_cross.add_trace(go.Scatter(
                        x=merged_daily['obs_date'],
                        y=merged_daily['thi_value'],
                        name='Mean Environmental THI',
                        mode='lines',
                        line=dict(color='#e53e3e', width=1.5, dash='dash'),
                        yaxis='y3'
                    ))

                fig_cross.update_layout(
                    title="Herd Multi-Metric Cross-Analysis (Activity, Milk Volume, THI)",
                    xaxis_title="Date",
                    yaxis=dict(title=dict(text="Activity Units", font=dict(color="#2d6a4f"))),
                    yaxis2=dict(title=dict(text="Total Milk (L)", font=dict(color="#d4af37")), overlaying="y", side="right"),
                    yaxis3=dict(title=dict(text="THI", font=dict(color="#e53e3e")), overlaying="y", side="right", anchor="free", position=0.98),
                    height=350,
                    margin=dict(t=40, b=10, l=10, r=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_cross, use_container_width=True)
        else:
            st.info("No sensor telemetry uploaded yet. Import sensor CSV in CSV Import Center or load demonstration data from sidebar.")


# ==========================================
# MODULE 2: Cow Management
# ==========================================

def render_cow_management():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Cow Management & Registry</div>
            <div class="brand-tagline">Complete cattle registration, profile tracking, lifecycle records, and search.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_list, tab_add, tab_profile, tab_edit = st.tabs([
        "📋 Herd Registry & Filter", "➕ Add New Cow", "🔍 Individual Cow Profile", "✏️ Edit / Delete Cow"
    ])

    cows_df = database.get_all_cows()

    # TAB 1: Herd Registry & Filter
    with tab_list:
        st.markdown("#### Registered Dairy Herd")
        if not cows_df.empty:
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                search_query = st.text_input("Search ID or Name", "")
            with f2:
                all_breeds = ["All"] + sorted(list(cows_df['breed'].unique()))
                sel_breed = st.selectbox("Filter by Breed", all_breeds)
            with f3:
                all_rep = ["All"] + sorted(list(cows_df['reproductive_status'].unique()))
                sel_rep = st.selectbox("Filter Reproductive Status", all_rep)
            with f4:
                all_health = ["All"] + sorted(list(cows_df['health_status'].unique()))
                sel_health = st.selectbox("Filter Health Status", all_health)

            filtered_df = cows_df.copy()
            if search_query:
                q = search_query.lower()
                filtered_df = filtered_df[
                    filtered_df['cow_id'].str.lower().str.contains(q, na=False) |
                    filtered_df['name'].str.lower().str.contains(q, na=False)
                ]
            if sel_breed != "All":
                filtered_df = filtered_df[filtered_df['breed'] == sel_breed]
            if sel_rep != "All":
                filtered_df = filtered_df[filtered_df['reproductive_status'] == sel_rep]
            if sel_health != "All":
                filtered_df = filtered_df[filtered_df['health_status'] == sel_health]

            st.write(f"Showing **{len(filtered_df)}** of **{len(cows_df)}** cows.")
            display_cols = [
                'cow_id', 'name', 'breed', 'age', 'weight', 'lactation_number',
                'daily_milk_production', 'pregnancy_status', 'health_status', 'reproductive_status'
            ]
            st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No cows currently registered. Add cows manually or load demonstration data.")

    # TAB 2: Add New Cow
    with tab_add:
        st.markdown("#### Register New Cow")
        with st.form("add_cow_form", clear_on_submit=True):
            a1, a2, a3 = st.columns(3)
            with a1:
                cid = st.text_input("Cow ID * (e.g. COW-121)", placeholder="Unique identifier")
                name = st.text_input("Cow Name *", placeholder="e.g. Buttercup")
                breed = st.selectbox("Breed *", [
                    "Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss",
                    "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred", "Other"
                ])
            with a2:
                dob = st.date_input("Date of Birth", value=date(2022, 1, 1), min_value=date(2010, 1, 1), max_value=date.today())
                weight = st.number_input("Weight (kg)", min_value=150.0, max_value=1000.0, value=520.0, step=5.0)
                lactation = st.number_input("Lactation Number", min_value=1, max_value=15, value=2, step=1)
            with a3:
                daily_milk = st.number_input("Daily Milk Yield (L)", min_value=0.0, max_value=80.0, value=22.0, step=0.5)
                preg_status = st.selectbox("Pregnancy Status", ["Open", "Inseminated", "Pregnant", "Unknown"])
                health_status = st.selectbox("Health Status", ["Healthy", "Under Observation", "Sick", "Quarantined"])

            b1, b2, b3 = st.columns(3)
            with b1:
                rep_status = st.selectbox("Reproductive Status", ["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"])
            with b2:
                last_calving = st.date_input("Last Calving Date (Optional)", value=None)
            with b3:
                last_estrus = st.date_input("Last Observed Estrus Date (Optional)", value=None)

            remarks = st.text_area("General Remarks / Pedigree Notes", placeholder="Notable background or management notes")

            submitted = st.form_submit_button("💾 Save Cow Record", use_container_width=True)
            if submitted:
                if not cid.strip() or not name.strip():
                    st.error("Please fill in both Cow ID and Cow Name.")
                else:
                    existing = database.get_cow(cid.strip())
                    if existing:
                        st.error(f"Cow ID '{cid.strip()}' already exists. Please choose a unique ID.")
                    else:
                        cow_payload = {
                            "cow_id": cid.strip(),
                            "name": name.strip(),
                            "breed": breed,
                            "dob": dob.strftime("%Y-%m-%d"),
                            "weight": weight,
                            "lactation_number": lactation,
                            "daily_milk_production": daily_milk,
                            "pregnancy_status": preg_status,
                            "health_status": health_status,
                            "reproductive_status": rep_status,
                            "last_calving_date": last_calving.strftime("%Y-%m-%d") if last_calving else None,
                            "last_observed_estrus_date": last_estrus.strftime("%Y-%m-%d") if last_estrus else None,
                            "remarks": remarks
                        }
                        database.add_cow(cow_payload)
                        st.success(f"Cow {cid.strip()} ({name.strip()}) registered successfully!")
                        st.rerun()

    # TAB 3: Individual Cow Profile
    with tab_profile:
        st.markdown("#### Comprehensive Cow Profile")
        if not cows_df.empty:
            cow_list = [f"{row['cow_id']} – {row['name']} ({row['breed']})" for _, row in cows_df.iterrows()]
            selected_cow_str = st.selectbox("Select Cow for Deep Profile Inspection", cow_list)
            selected_cow_id = selected_cow_str.split(" – ")[0]
            cow_info = database.get_cow(selected_cow_id)

            if cow_info:
                # Top Summary Card
                st.markdown(f"""
                <div class="section-box">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0; color:#1b4332;">{cow_info['name']} ({cow_info['cow_id']})</h3>
                            <div style="color:#52b788; font-weight:600;">{cow_info['breed']} | Lactation #{cow_info['lactation_number']}</div>
                        </div>
                        <div style="text-align:right;">
                            <span class="demo-badge" style="background:{'#2d6a4f' if cow_info['health_status']=='Healthy' else '#e53e3e'}; color:white;">
                                {cow_info['health_status']}
                            </span>
                            <span class="demo-badge" style="background:#52b788; color:white; margin-left:6px;">
                                {cow_info['reproductive_status']}
                            </span>
                        </div>
                    </div>
                    <hr style="margin:12px 0;">
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size:0.9rem;">
                        <div><b>Age:</b> {cow_info['age']} yrs</div>
                        <div><b>Weight:</b> {cow_info['weight']} kg</div>
                        <div><b>Daily Yield:</b> {cow_info['daily_milk_production']} L</div>
                        <div><b>Pregnancy:</b> {cow_info['pregnancy_status']}</div>
                        <div><b>Last Calved:</b> {cow_info['last_calving_date'] or 'N/A'}</div>
                        <div><b>Last Estrus:</b> {cow_info['last_observed_estrus_date'] or 'N/A'}</div>
                        <div><b>Last Inseminated:</b> {cow_info['last_insemination_date'] or 'N/A'}</div>
                        <div><b>Registered:</b> {cow_info['created_at'][:10] if cow_info['created_at'] else 'N/A'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Sub-history tabs
                h_tab1, h_tab2, h_tab3, h_tab4, h_tab5 = st.tabs([
                    "🥛 Milk History", "🎯 Estrus Observations", "📡 Sensor Telemetry", "🩺 Health History", "📜 Reproductive Events"
                ])

                with h_tab1:
                    cow_milk = database.get_milk_records(selected_cow_id)
                    if not cow_milk.empty:
                        cow_milk_sorted = cow_milk.sort_values('production_date')
                        fig_cm = px.line(
                            cow_milk_sorted, x='production_date', y=['morning_yield', 'evening_yield', 'total_yield'],
                            title=f"Milk Yield Trajectory – {cow_info['name']}",
                            markers=True,
                            color_discrete_sequence=['#52b788', '#d4af37', '#1b4332']
                        )
                        st.plotly_chart(fig_cm, use_container_width=True)
                        st.dataframe(cow_milk[['production_date', 'morning_yield', 'evening_yield', 'total_yield', 'is_drop_alert', 'notes']], use_container_width=True, hide_index=True)
                    else:
                        st.info("No milk records logged for this cow.")

                with h_tab2:
                    cow_estrus = database.get_estrus_observations(selected_cow_id)
                    if not cow_estrus.empty:
                        cols_to_show = [c for c in ['observation_date', 'selected_markers', 'estrus_score', 'evidence_category', 'cycle_stage', 'estimated_next_estrus', 'score_reasons'] if c in cow_estrus.columns]
                        st.dataframe(cow_estrus[cols_to_show], use_container_width=True, hide_index=True)
                    else:
                        st.info("No estrus observations recorded for this cow.")

                with h_tab3:
                    st.markdown(f"##### 2-Hourly Sensor Telemetry – {cow_info['name']} ({selected_cow_id})")
                    cow_sensor = database.get_sensor_records(selected_cow_id)
                    if not cow_sensor.empty:
                        c_analysis = database.analyze_sensor_estrus(cow_sensor)
                        if not c_analysis.empty:
                            total_s_int = len(c_analysis)
                            mean_s_act = round(c_analysis['activity_index'].mean(), 1)
                            mean_s_rum = round(c_analysis['rumination_minutes'].mean(), 1)
                            latest_row = c_analysis.iloc[-1]
                            latest_sc = latest_row['combined_evidence_score']
                            latest_cat = latest_row['evidence_category']

                            k_c1, k_c2, k_c3, k_c4 = st.columns(4)
                            with k_c1:
                                st.metric("2-Hr Observations", f"{total_s_int}")
                            with k_c2:
                                st.metric("Average Activity", f"{mean_s_act} units")
                            with k_c3:
                                st.metric("Avg Rumination", f"{mean_s_rum} min/2h")
                            with k_c4:
                                st.metric("Latest Sensor Estrus", f"{latest_sc}/100 ({latest_cat})")

                            # Telemetry line charts
                            c_analysis_sorted = c_analysis.sort_values('timestamp_dt')
                            fig_cow_sens = go.Figure()
                            fig_cow_sens.add_trace(go.Scatter(
                                x=c_analysis_sorted['timestamp_dt'],
                                y=c_analysis_sorted['activity_index'],
                                mode='lines+markers',
                                name='Activity Index',
                                line=dict(color='#2d6a4f', width=2),
                                marker=dict(size=4)
                            ))
                            fig_cow_sens.add_trace(go.Scatter(
                                x=c_analysis_sorted['timestamp_dt'],
                                y=c_analysis_sorted['rumination_minutes'],
                                mode='lines+markers',
                                name='Rumination Minutes',
                                line=dict(color='#2b6cb0', width=2),
                                marker=dict(size=4)
                            ))
                            high_pts = c_analysis_sorted[c_analysis_sorted['evidence_category'] == 'High']
                            if not high_pts.empty:
                                fig_cow_sens.add_trace(go.Scatter(
                                    x=high_pts['timestamp_dt'],
                                    y=high_pts['activity_index'],
                                    mode='markers',
                                    name='High Estrus Deviation',
                                    marker=dict(color='#e53e3e', size=10, symbol='star')
                                ))

                            fig_cow_sens.update_layout(
                                title=f"Telemetry Trajectory: Activity Index vs Rumination Minutes – {cow_info['name']}",
                                xaxis_title="Timeline",
                                yaxis_title="Sensor Units / Minutes",
                                height=300,
                                margin=dict(t=40, b=10, l=10, r=10),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                            )
                            st.plotly_chart(fig_cow_sens, use_container_width=True)

                            # Multi-Source Corroboration Section (Manual vs Sensor)
                            st.markdown("###### Multi-Modal Corroboration: Sensor Telemetry vs Manual Reproductive Markers")
                            cow_manual_estrus = database.get_estrus_observations(selected_cow_id)
                            has_manual_high = False
                            if not cow_manual_estrus.empty:
                                has_manual_high = len(cow_manual_estrus[cow_manual_estrus['evidence_category'] == 'High']) > 0

                            has_sensor_high = len(high_pts) > 0

                            if has_manual_high and has_sensor_high:
                                st.markdown("""
                                <div class="alert-card-success" style="margin-bottom: 12px;">
                                    <b>🎯 DUAL-SOURCE CORROBORATION CONFIRMED:</b> Both manual behavioral observation (e.g., Standing to Be Mounted) and 2-hourly sensor telemetry exhibit concurrent high estrus evidence. This represents maximum reproductive certainty for Artificial Insemination (A.M.–P.M. protocol).
                                </div>
                                """, unsafe_allow_html=True)
                            elif has_sensor_high and not has_manual_high:
                                st.markdown("""
                                <div class="alert-card-warning" style="margin-bottom: 12px;">
                                    <b>📡 SENSOR-DETECTED SUBESTRUS / SILENT HEAT:</b> Sensor telemetry detected acute activity increase and rumination drop without corresponding visual standing heat logged. Recommend direct reproductive examination.
                                </div>
                                """, unsafe_allow_html=True)
                            elif has_manual_high and not has_sensor_high:
                                st.markdown("""
                                <div class="alert-card-warning" style="margin-bottom: 12px;">
                                    <b>👀 VISUAL MARKERS OBSERVED:</b> Visual reproductive markers were recorded while 2-hour sensor baseline remained moderate. Both sources are integrated without double-counting evidence.
                                </div>
                                """, unsafe_allow_html=True)

                            # Sensor Records Table
                            s_disp_cols = ['timestamp', 'activity_index', 'baseline_activity', 'activity_change_pct', 'rumination_minutes', 'baseline_rumination', 'rumination_change_pct', 'combined_evidence_score', 'evidence_category', 'explanation']
                            st.dataframe(c_analysis[s_disp_cols].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
                        else:
                            st.info("Insufficient sensor data for baseline analysis.")
                    else:
                        st.info(f"No sensor telemetry records uploaded for {cow_info['name']}.")

                with h_tab4:
                    cow_health = database.get_health_records(selected_cow_id)
                    if not cow_health.empty:
                        st.dataframe(cow_health[['observation_date', 'body_temperature', 'milk_production', 'appetite', 'activity_level', 'health_status', 'symptoms']], use_container_width=True, hide_index=True)
                    else:
                        st.info("No health records recorded for this cow.")

                with h_tab5:
                    cow_rep = database.get_reproductive_history(selected_cow_id)
                    if not cow_rep.empty:
                        st.dataframe(cow_rep[['event_date', 'event_type', 'details', 'technician_or_sire', 'outcome']], use_container_width=True, hide_index=True)
                    else:
                        st.info("No reproductive events recorded for this cow.")
        else:
            st.info("No cows available.")

    # TAB 4: Edit / Delete Cow
    with tab_edit:
        st.markdown("#### Edit or Remove Cow Record")
        if not cows_df.empty:
            cow_edit_list = [f"{row['cow_id']} – {row['name']}" for _, row in cows_df.iterrows()]
            edit_cow_str = st.selectbox("Select Cow to Modify", cow_edit_list, key="edit_cow_select")
            edit_cow_id = edit_cow_str.split(" – ")[0]
            c_data = database.get_cow(edit_cow_id)

            if c_data:
                with st.form("edit_cow_form"):
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        new_name = st.text_input("Cow Name", value=c_data['name'])
                        new_breed = st.selectbox("Breed", [
                            "Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss",
                            "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred", "Other"
                        ], index=0 if c_data['breed'] not in ["Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss", "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred"] else ["Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss", "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred", "Other"].index(c_data['breed']))
                        new_weight = st.number_input("Weight (kg)", value=float(c_data['weight'] or 500.0), step=5.0)
                    with e2:
                        new_lactation = st.number_input("Lactation #", value=int(c_data['lactation_number'] or 1), step=1)
                        new_milk = st.number_input("Daily Yield (L)", value=float(c_data['daily_milk_production'] or 20.0), step=0.5)
                        new_preg = st.selectbox("Pregnancy Status", ["Open", "Inseminated", "Pregnant", "Unknown"], index=["Open", "Inseminated", "Pregnant", "Unknown"].index(c_data['pregnancy_status']) if c_data['pregnancy_status'] in ["Open", "Inseminated", "Pregnant", "Unknown"] else 0)
                    with e3:
                        new_health = st.selectbox("Health Status", ["Healthy", "Under Observation", "Sick", "Quarantined"], index=["Healthy", "Under Observation", "Sick", "Quarantined"].index(c_data['health_status']) if c_data['health_status'] in ["Healthy", "Under Observation", "Sick", "Quarantined"] else 0)
                        new_rep = st.selectbox("Reproductive Status", ["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"], index=["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"].index(c_data['reproductive_status']) if c_data['reproductive_status'] in ["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"] else 0)
                        new_remarks = st.text_area("Remarks", value=c_data['remarks'] or "")

                    save_changes = st.form_submit_button("💾 Update Cow Record", use_container_width=True)
                    if save_changes:
                        update_payload = {
                            "name": new_name.strip(),
                            "breed": new_breed,
                            "dob": c_data['dob'],
                            "age": c_data['age'],
                            "weight": new_weight,
                            "lactation_number": new_lactation,
                            "daily_milk_production": new_milk,
                            "last_calving_date": c_data['last_calving_date'],
                            "last_observed_estrus_date": c_data['last_observed_estrus_date'],
                            "last_insemination_date": c_data['last_insemination_date'],
                            "pregnancy_status": new_preg,
                            "health_status": new_health,
                            "reproductive_status": new_rep,
                            "remarks": new_remarks
                        }
                        database.update_cow(edit_cow_id, update_payload)
                        st.success(f"Cow {edit_cow_id} updated successfully!")
                        st.rerun()

                st.markdown("---")
                st.markdown("##### ⚠️ Danger Zone: Delete Record")
                st.warning(f"Deleting **{edit_cow_id}** will also cascade remove its associated health, milk, and estrus records.")
                confirm_del = st.checkbox(f"Yes, I confirm deleting cow {edit_cow_id}")
                if st.button(f"🗑️ Delete Cow {edit_cow_id}", type="primary"):
                    if confirm_del:
                        database.delete_cow(edit_cow_id)
                        st.success(f"Cow {edit_cow_id} deleted successfully.")
                        st.rerun()
                    else:
                        st.error("Please tick the confirmation checkbox above before deleting.")
        else:
            st.info("No cows available to edit.")


# ==========================================
# MODULE 3: Estrus Prediction
# ==========================================

def render_estrus_prediction():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Rule-Based Estrus Prediction & Reproductive Cycle Tracking</div>
            <div class="brand-tagline">Weighted multi-sign scoring, estrous cycle stage screening, and breeding window estimations.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_eval, tab_hist, tab_bulk, tab_sensor = st.tabs([
        "🎯 Record & Evaluate Observation", "📜 Estrus Observation History", "📥 Bulk CSV Estrus Screening", "📡 2-Hourly Sensor Prediction"
    ])

    cows_df = database.get_all_cows()

    # TAB 1: Evaluation
    with tab_eval:
        if cows_df.empty:
            st.warning("Please register cows first in the Cow Management module.")
            return

        c1, c2 = st.columns([1, 1.2])

        with c1:
            st.markdown("#### 1. Select Observed Reproductive Markers")
            cow_choices = [f"{r['cow_id']} – {r['name']}" for _, r in cows_df.iterrows()]
            sel_cow = st.selectbox("Select Cow", cow_choices, key="estrus_eval_cow")
            cid = sel_cow.split(" – ")[0]
            cow_data = database.get_cow(cid)

            obs_date = st.date_input("Observation Date", value=date.today())

            st.markdown("##### Reproductive Markers Selection")
            selected_markers = st.multiselect(
                "Select Reproductive Markers / Estrus Signs *",
                options=[
                    "Standing to Be Mounted",
                    "Mounting Other Cows",
                    "Clear Vaginal Mucus Discharge",
                    "Increased Activity / Restlessness",
                    "Vulval Swelling and Redness"
                ],
                default=[],
                help="Select all behavioural and physiological reproductive signs observed for this cow."
            )

            notes = st.text_area("Optional Remarks / Additional Observations", placeholder="e.g. Observed during morning paddock turnout; calm temperament")

        with c2:
            st.markdown("#### 2. Rule-Based Estrus Evidence & Cycle Analysis")

            # Calculate days since last estrus
            days_estrus = None
            if cow_data.get('last_observed_estrus_date'):
                try:
                    d_prev = datetime.strptime(str(cow_data['last_observed_estrus_date'])[:10], "%Y-%m-%d").date()
                    days_estrus = (obs_date - d_prev).days
                except Exception:
                    pass

            days_calved = None
            if cow_data.get('last_calving_date'):
                try:
                    d_calv = datetime.strptime(str(cow_data['last_calving_date'])[:10], "%Y-%m-%d").date()
                    days_calved = (obs_date - d_calv).days
                except Exception:
                    pass

            score, category, stage, contributions, explanation = calculate_estrus_score(
                selected_markers=selected_markers,
                days_since_last_estrus=days_estrus,
                days_since_calving=days_calved
            )

            # Display Score Card
            badge_color = "#2d6a4f" if category == "High" else ("#d4af37" if category == "Moderate" else "#6c757d")
            st.markdown(f"""
            <div class="section-box" style="border-top: 5px solid {badge_color};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.1rem; font-weight:700; color:#1b4332;">Estrus Evidence Score</span>
                    <span class="demo-badge" style="background:{badge_color}; color:white; font-size:1rem; padding:6px 16px;">
                        {category} Evidence ({score}/100)
                    </span>
                </div>
                <div style="margin-top:14px;">
                    <div style="background:#e9ecef; border-radius:10px; height:18px; width:100%; overflow:hidden;">
                        <div style="background:{badge_color}; height:100%; width:{min(score, 100)}%;"></div>
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.95rem;">
                    <b>Cycle Stage:</b> <span style="color:#1b4332; font-weight:700;">{stage}</span><br>
                    <b>Days Since Last Estrus:</b> {days_estrus if days_estrus is not None else 'Unknown'}<br>
                    <b>Estimated Next Window:</b> {(obs_date + timedelta(days=21)).strftime('%Y-%m-%d')} (±2 days)
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### Selected Markers & Contributions")
            if contributions:
                for c_item in contributions:
                    st.markdown(f"- ✅ **{c_item}**")
            else:
                st.markdown("- ℹ️ No reproductive markers selected. Evidence score is baseline (0/100).")

            st.markdown(f"""
            <div style="background:#f8f9fa; border-left:4px solid {badge_color}; padding:10px 14px; border-radius:6px; margin: 10px 0; font-size:0.9rem; color:#212529;">
                <b>Result Explanation:</b> {explanation}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="alert-card-warning" style="font-size:0.82rem; margin-top:8px;">
                <b>IMPORTANT DOMAIN NOTE:</b> The resulting score represents observed estrus evidence, not a scientifically calibrated probability or confirmed ovulation. Do not interpret unselected observations as negative clinical signs.
            </div>
            """, unsafe_allow_html=True)

            if st.button("💾 Save Estrus Observation Record", type="primary", use_container_width=True):
                next_estrus = (obs_date + timedelta(days=21)).strftime("%Y-%m-%d")
                record = {
                    "cow_id": cid,
                    "observation_date": obs_date.strftime("%Y-%m-%d"),
                    "selected_markers": selected_markers,
                    "standing_to_be_mounted": 1 if "Standing to Be Mounted" in selected_markers else 0,
                    "mounting_behaviour": 1 if "Mounting Other Cows" in selected_markers else 0,
                    "clear_mucus_discharge": 1 if "Clear Vaginal Mucus Discharge" in selected_markers else 0,
                    "increased_activity": 1 if "Increased Activity / Restlessness" in selected_markers else 0,
                    "restlessness": 1 if "Increased Activity / Restlessness" in selected_markers else 0,
                    "swollen_vulva": 1 if "Vulval Swelling and Redness" in selected_markers else 0,
                    "frequent_vocalization": 0,
                    "reduced_feed_intake": 0,
                    "reduced_milk_yield": 0,
                    "estrus_score": score,
                    "evidence_category": category,
                    "cycle_stage": stage,
                    "estimated_next_estrus": next_estrus,
                    "score_reasons": " | ".join(contributions) if contributions else "None observed",
                    "notes": notes
                }
                database.add_estrus_observation(record)
                st.success(f"Estrus observation saved for {cid}! Evidence: {category} ({score}/100). Estimated next window: {next_estrus}")
                st.rerun()

    # TAB 2: History
    with tab_hist:
        st.markdown("#### Historical Estrus Observations")
        estrus_df = database.get_estrus_observations()
        if not estrus_df.empty:
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                filter_cid = st.selectbox("Filter Cow", ["All"] + sorted(list(estrus_df['cow_id'].unique())), key="estrus_hist_cid")
            with f_col2:
                filter_cat = st.selectbox("Filter Evidence Category", ["All", "High", "Moderate", "Low"], key="estrus_hist_cat")

            f_df = estrus_df.copy()
            if filter_cid != "All":
                f_df = f_df[f_df['cow_id'] == filter_cid]
            if filter_cat != "All":
                f_df = f_df[f_df['evidence_category'] == filter_cat]

            cols = ['cow_id', 'observation_date', 'selected_markers', 'estrus_score', 'evidence_category', 'cycle_stage', 'estimated_next_estrus', 'score_reasons']
            st.dataframe(f_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No estrus observations logged yet.")

    # TAB 3: Bulk CSV Estrus Screening
    with tab_bulk:
        st.markdown("#### Bulk CSV Estrus Scoring & Batch Prediction")
        st.write("Upload a CSV file with manual observations to automatically compute estrus evidence scores and estimated next estrus dates.")

        sample_csv = CSV_SCHEMAS["estrus_observations"]["sample"]
        st.download_button(
            "📥 Download Estrus Observations CSV Template",
            data=sample_csv.to_csv(index=False).encode('utf-8'),
            file_name="estrus_observations_template.csv",
            mime="text/csv"
        )

        up_file = st.file_uploader("Upload Estrus Observation CSV", type=["csv"], key="bulk_estrus_uploader")
        if up_file:
            try:
                batch_df = pd.read_csv(up_file)
                st.write(f"Loaded **{len(batch_df)}** rows. Preview:")
                st.dataframe(batch_df.head(), use_container_width=True)

                if st.button("⚡ Run Batch Estrus Prediction", use_container_width=True):
                    processed = []
                    for _, r in batch_df.iterrows():
                        cid = str(r.get("cow_id", "")).strip()
                        o_date = str(r.get("observation_date", date.today().strftime("%Y-%m-%d")))
                        
                        # Parse selected_markers if provided
                        raw_markers = r.get("selected_markers")
                        if pd.notna(raw_markers) and str(raw_markers).strip() and str(raw_markers).strip().lower() != "nan":
                            markers_input = str(raw_markers).strip()
                        else:
                            markers_input = None

                        stnd = int(r.get("standing_to_be_mounted", 0)) if pd.notna(r.get("standing_to_be_mounted")) else 0
                        mnt = int(r.get("mounting_behaviour", 0)) if pd.notna(r.get("mounting_behaviour")) else 0
                        muc = int(r.get("clear_mucus_discharge", 0)) if pd.notna(r.get("clear_mucus_discharge")) else 0
                        rest = int(r.get("restlessness", 0)) if pd.notna(r.get("restlessness")) else 0
                        act = int(r.get("increased_activity", 0)) if pd.notna(r.get("increased_activity")) else 0
                        voc = int(r.get("frequent_vocalization", 0)) if pd.notna(r.get("frequent_vocalization")) else 0
                        vul = int(r.get("swollen_vulva", 0)) if pd.notna(r.get("swollen_vulva")) else 0
                        feed = int(r.get("reduced_feed_intake", 0)) if pd.notna(r.get("reduced_feed_intake")) else 0
                        m_drop = int(r.get("reduced_milk_yield", 0)) if pd.notna(r.get("reduced_milk_yield")) else 0

                        sc, cat, stg, contribs, expl = calculate_estrus_score(
                            selected_markers=markers_input,
                            standing_to_be_mounted=bool(stnd),
                            mounting_behaviour=bool(mnt),
                            clear_mucus_discharge=bool(muc),
                            restlessness=bool(rest),
                            increased_activity=bool(act),
                            frequent_vocalization=bool(voc),
                            swollen_vulva=bool(vul),
                            reduced_feed_intake=bool(feed),
                            reduced_milk_yield=bool(m_drop)
                        )
                        next_dt = (datetime.strptime(o_date[:10], "%Y-%m-%d") + timedelta(days=21)).strftime("%Y-%m-%d")
                        active_markers = ", ".join([c.split(" (+")[0] for c in contribs]) if contribs else "None"

                        processed.append({
                            "cow_id": cid,
                            "observation_date": o_date,
                            "selected_markers": active_markers,
                            "estrus_score": sc,
                            "evidence_category": cat,
                            "cycle_stage": stg,
                            "estimated_next_estrus": next_dt,
                            "score_reasons": " | ".join(contribs) if contribs else "None observed",
                            "explanation": expl
                        })

                    res_df = pd.DataFrame(processed)
                    st.success("Batch predictions computed successfully!")
                    st.dataframe(res_df, use_container_width=True)

                    st.download_button(
                        "📥 Download Calculated Predictions CSV",
                        data=res_df.to_csv(index=False).encode('utf-8'),
                        file_name="estrus_predictions_output.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.error(f"Error processing CSV: {str(e)}")

    # TAB 4: 2-Hourly Sensor Telemetry Estrus Prediction
    with tab_sensor:
        st.markdown("#### 📡 2-Hourly Sensor Telemetry Estrus Prediction")
        st.write("Analyze continuous 2-hour observation intervals of Activity Index and Rumination Minutes to identify reciprocal behavioral divergence indicative of estrus.")

        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="color: #1b4332; font-weight: 700; font-size: 0.95rem; margin-bottom: 4px;">
                🔬 Sensor Telemetry Methodology & Baseline Governance
            </div>
            <div style="font-size: 0.85rem; color: #475569; line-height: 1.5;">
                • <b>Individual Diurnal Baselines:</b> Sensor observations are evaluated against each cow's historical diurnal baseline (time-of-day median), preventing false alerts caused by normal diurnal movement patterns.
                <br>• <b>Reciprocal Estrus Divergence:</b> Highest evidence is assigned when activity increases significantly (+35% to +100%) and rumination decreases significantly (-25% to -70%) concurrently.
                <br>• <b>Multi-Interval Persistence:</b> Elevated scores persist and multiply when behavioral shifts are sustained across consecutive 2-hour observation blocks.
                <br>• <b>Missing Reading Integrity:</b> Missing sensor intervals are never imputed as zero to prevent distortion of physiological baselines.
                <br>• <b>Domain Note:</b> Evidence scores represent behavioral deviation indices, not calibrated ovulation probabilities or confirmed veterinary diagnoses.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Configurable Parameters Expander
        with st.expander("⚙️ Configurable Algorithm Thresholds & Baseline Parameters", expanded=False):
            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                cfg_act_thresh = st.slider(
                    "Activity Increase Threshold (%)",
                    min_value=15.0, max_value=80.0, value=35.0, step=5.0,
                    help="Minimum percentage increase above cow's baseline to register abnormal estrus activity."
                )
            with tc2:
                cfg_rum_thresh = st.slider(
                    "Rumination Drop Threshold (%)",
                    min_value=10.0, max_value=60.0, value=25.0, step=5.0,
                    help="Minimum percentage decrease below cow's baseline to register abnormal estrus rumination suppression."
                )
            with tc3:
                cfg_min_intervals = st.number_input(
                    "Minimum Baseline Intervals (2h blocks)",
                    min_value=6, max_value=168, value=24, step=6,
                    help="Minimum valid readings required to establish a reliable baseline (24 blocks = 2 days, recommended ~14 days)."
                )

        # Filter bar
        all_sensor_data = database.get_sensor_records()
        if all_sensor_data.empty:
            st.info("No sensor records in database. You can upload 2-hour sensor CSV files in the **CSV Import Center** or generate demonstration data from the sidebar.")
        else:
            cows_with_sensors = sorted(all_sensor_data['cow_id'].unique().tolist())
            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1])
            with f_col1:
                sel_sensor_cow = st.selectbox(
                    "Select Cow for Detailed Telemetry",
                    ["All Cows"] + cows_with_sensors,
                    key="sensor_pred_cow_filter"
                )
            with f_col2:
                date_filter = st.selectbox(
                    "Select Timeline Filter",
                    ["Last 14 Days", "Last 7 Days", "Last 30 Days", "All History"],
                    index=0,
                    key="sensor_pred_date_filter"
                )
            with f_col3:
                cat_filter = st.selectbox(
                    "Evidence Filter",
                    ["All Levels", "High Only", "Moderate & High", "Insufficient Data"],
                    key="sensor_pred_cat_filter"
                )

            # Apply cow filter to raw data
            active_df = all_sensor_data if sel_sensor_cow == "All Cows" else all_sensor_data[all_sensor_data['cow_id'] == sel_sensor_cow]

            # Run transparent rule-based algorithm
            analyzed_df = database.analyze_sensor_estrus(
                active_df,
                min_baseline_intervals=int(cfg_min_intervals),
                activity_threshold_pct=float(cfg_act_thresh),
                rumination_drop_pct=float(cfg_rum_thresh)
            )

            # Date range filtering on analyzed results
            if not analyzed_df.empty:
                max_dt = analyzed_df['timestamp_dt'].max()
                if date_filter == "Last 7 Days":
                    analyzed_df = analyzed_df[analyzed_df['timestamp_dt'] >= (max_dt - timedelta(days=7))]
                elif date_filter == "Last 14 Days":
                    analyzed_df = analyzed_df[analyzed_df['timestamp_dt'] >= (max_dt - timedelta(days=14))]
                elif date_filter == "Last 30 Days":
                    analyzed_df = analyzed_df[analyzed_df['timestamp_dt'] >= (max_dt - timedelta(days=30))]

                # Evidence level filtering
                if cat_filter == "High Only":
                    analyzed_df = analyzed_df[analyzed_df['evidence_category'] == 'High']
                elif cat_filter == "Moderate & High":
                    analyzed_df = analyzed_df[analyzed_df['evidence_category'].isin(['High', 'Moderate'])]
                elif cat_filter == "Insufficient Data":
                    analyzed_df = analyzed_df[analyzed_df['evidence_category'] == 'Insufficient Data']

            if analyzed_df.empty:
                st.warning("No sensor records match the selected timeline and evidence filters.")
            else:
                # KPI Summary Metrics
                total_intervals = len(analyzed_df)
                unique_cows = analyzed_df['cow_id'].nunique()
                high_spikes = len(analyzed_df[analyzed_df['evidence_category'] == 'High'])
                mod_spikes = len(analyzed_df[analyzed_df['evidence_category'] == 'Moderate'])
                insufficient_count = len(analyzed_df[analyzed_df['evidence_category'] == 'Insufficient Data'])

                k1, k2, k3, k4 = st.columns(4)
                with k1:
                    st.metric("Total 2-Hr Observations", f"{total_intervals:,}")
                with k2:
                    st.metric("Cows Evaluated", f"{unique_cows}")
                with k3:
                    st.metric("High Evidence Spikes (≥70)", f"{high_spikes}")
                with k4:
                    st.metric("Moderate Signals (40–69)", f"{mod_spikes}")

                if insufficient_count > 0:
                    st.markdown(f"""
                    <div class="alert-card-warning" style="margin: 12px 0;">
                        <b>⚠️ Insufficient Historical Baseline Detected:</b> {insufficient_count} observation intervals belong to cows with fewer than {cfg_min_intervals} valid readings (~{max(2, int(cfg_min_intervals)//12)} days). Reliable individual baselines cannot be established until additional 2-hour sensor records are ingested.
                    </div>
                    """, unsafe_allow_html=True)

                # Charts
                if sel_sensor_cow != "All Cows":
                    st.markdown(f"##### Telemetry Trajectory & Divergence: Cow {sel_sensor_cow}")
                    cow_disp = analyzed_df[analyzed_df['cow_id'] == sel_sensor_cow].sort_values('timestamp_dt')

                    # 1. Dual Telemetry Chart (Activity & Rumination)
                    fig_tel = go.Figure()
                    fig_tel.add_trace(go.Scatter(
                        x=cow_disp['timestamp_dt'],
                        y=cow_disp['activity_index'],
                        mode='lines+markers',
                        name='Activity Index (Observed)',
                        line=dict(color='#2d6a4f', width=2.5),
                        marker=dict(size=5)
                    ))
                    fig_tel.add_trace(go.Scatter(
                        x=cow_disp['timestamp_dt'],
                        y=cow_disp['baseline_activity'],
                        mode='lines',
                        name='Activity Baseline (Diurnal Median)',
                        line=dict(color='#52b788', width=1.5, dash='dash')
                    ))
                    high_pts = cow_disp[cow_disp['evidence_category'] == 'High']
                    if not high_pts.empty:
                        fig_tel.add_trace(go.Scatter(
                            x=high_pts['timestamp_dt'],
                            y=high_pts['activity_index'],
                            mode='markers',
                            name='High Estrus Spike',
                            marker=dict(color='#e53e3e', size=11, symbol='star', line=dict(width=1, color='white'))
                        ))

                    fig_tel.update_layout(
                        title=f"Activity Index Telemetry vs Diurnal Baseline ({sel_sensor_cow})",
                        xaxis_title="Timestamp (2-Hour Intervals)",
                        yaxis_title="Activity Units",
                        height=320,
                        margin=dict(t=40, b=10, l=10, r=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_tel, use_container_width=True)

                    # 2. Rumination Trajectory Chart
                    fig_rum = go.Figure()
                    fig_rum.add_trace(go.Scatter(
                        x=cow_disp['timestamp_dt'],
                        y=cow_disp['rumination_minutes'],
                        mode='lines+markers',
                        name='Rumination Minutes (Observed)',
                        line=dict(color='#2b6cb0', width=2.5),
                        marker=dict(size=5)
                    ))
                    fig_rum.add_trace(go.Scatter(
                        x=cow_disp['timestamp_dt'],
                        y=cow_disp['baseline_rumination'],
                        mode='lines',
                        name='Rumination Baseline (Diurnal Median)',
                        line=dict(color='#63b3ed', width=1.5, dash='dash')
                    ))
                    fig_rum.update_layout(
                        title=f"Rumination Minutes Telemetry vs Baseline ({sel_sensor_cow})",
                        xaxis_title="Timestamp (2-Hour Intervals)",
                        yaxis_title="Minutes / 2-Hour Interval (Max 120m)",
                        height=280,
                        margin=dict(t=40, b=10, l=10, r=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_rum, use_container_width=True)

                    # 3. Combined Sensor Estrus Evidence Score Timeline
                    fig_score = go.Figure()
                    fig_score.add_hrect(y0=0, y1=40, fillcolor="#2d6a4f", opacity=0.08, line_width=0, annotation_text="Low (<40)", annotation_position="top left")
                    fig_score.add_hrect(y0=40, y1=70, fillcolor="#f59f00", opacity=0.10, line_width=0, annotation_text="Moderate (40–69)", annotation_position="top left")
                    fig_score.add_hrect(y0=70, y1=100, fillcolor="#e53e3e", opacity=0.15, line_width=0, annotation_text="High (≥70)", annotation_position="top left")

                    colors_seq = [
                        '#e53e3e' if c == 'High' else ('#f59f00' if c == 'Moderate' else '#94a3b8')
                        for c in cow_disp['evidence_category']
                    ]
                    fig_score.add_trace(go.Bar(
                        x=cow_disp['timestamp_dt'],
                        y=cow_disp['combined_evidence_score'],
                        name='Combined Evidence Score',
                        marker_color=colors_seq,
                        customdata=cow_disp[['activity_change_pct', 'rumination_change_pct', 'explanation']],
                        hovertemplate="<b>Timestamp:</b> %{x|%Y-%m-%d %H:%M}<br><b>Evidence Score:</b> %{y}/100<br><b>Activity Δ:</b> %{customdata[0]:+.1f}%<br><b>Rumination Δ:</b> %{customdata[1]:+.1f}%<br><b>Details:</b> %{customdata[2]}<extra></extra>"
                    ))
                    fig_score.update_layout(
                        title=f"Combined Sensor Estrus Evidence Score Timeline ({sel_sensor_cow})",
                        xaxis_title="Observation Timeline",
                        yaxis_title="Evidence Score (0–100)",
                        yaxis=dict(range=[0, 105]),
                        height=280,
                        margin=dict(t=40, b=10, l=10, r=10)
                    )
                    st.plotly_chart(fig_score, use_container_width=True)

                else:
                    st.markdown("##### Herd-Wide Sensor Estrus Divergence Quad-Chart")
                    valid_scatter = analyzed_df[analyzed_df['evidence_category'] != 'Insufficient Data']
                    if not valid_scatter.empty:
                        fig_quad = px.scatter(
                            valid_scatter,
                            x='activity_change_pct',
                            y='rumination_change_pct',
                            color='evidence_category',
                            hover_data=['cow_id', 'timestamp', 'combined_evidence_score', 'explanation'],
                            color_discrete_map={'High': '#e53e3e', 'Moderate': '#f59f00', 'Low': '#52b788', 'Missing Reading': '#94a3b8'},
                            title="Herd Activity Deviation (%) vs Rumination Deviation (%) across 2-Hour Intervals",
                            labels={'activity_change_pct': 'Activity Change Relative to Baseline (%)', 'rumination_change_pct': 'Rumination Change Relative to Baseline (%)'}
                        )
                        fig_quad.add_vline(x=cfg_act_thresh, line_dash="dash", line_color="#e53e3e", annotation_text=f"Activity Threshold (+{cfg_act_thresh}%)")
                        fig_quad.add_hline(y=-cfg_rum_thresh, line_dash="dash", line_color="#2b6cb0", annotation_text=f"Rumination Drop Threshold (-{cfg_rum_thresh}%)")
                        fig_quad.update_layout(height=400, margin=dict(t=40, b=10, l=10, r=10))
                        st.plotly_chart(fig_quad, use_container_width=True)

                # Prediction Results Table
                st.markdown("##### 2-Hour Interval Observations & Sensor Predictions Registry")
                disp_cols = [
                    'cow_id', 'timestamp', 'activity_index', 'baseline_activity',
                    'activity_change_pct', 'rumination_minutes', 'baseline_rumination',
                    'rumination_change_pct', 'combined_evidence_score', 'evidence_category',
                    'explanation'
                ]
                st.dataframe(
                    analyzed_df[disp_cols].sort_values('timestamp', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "📥 Download Sensor Predictions CSV",
                    data=analyzed_df[disp_cols].to_csv(index=False).encode('utf-8'),
                    file_name=f"sensor_estrus_predictions_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )


# ==========================================
# MODULE 4: Health Monitoring
# ==========================================

def render_health_monitoring():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Herd Health Monitoring & Abnormality Screening</div>
            <div class="brand-tagline">Clinical parameter tracking, body temperature trends, and early abnormality detection.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_add, tab_history, tab_trends = st.tabs([
        "➕ Log Health Observation", "📋 Health Records Registry", "📈 Temperature & Health Trends"
    ])

    cows_df = database.get_all_cows()

    # TAB 1: Log Health Record
    with tab_add:
        if cows_df.empty:
            st.warning("Please register cows first in Cow Management.")
            return

        with st.form("health_log_form", clear_on_submit=True):
            h1, h2, h3 = st.columns(3)
            with h1:
                cow_choices = [f"{r['cow_id']} – {r['name']}" for _, r in cows_df.iterrows()]
                sel_cow = st.selectbox("Select Cow *", cow_choices, key="health_cow_sel")
                cid = sel_cow.split(" – ")[0]
                obs_date = st.date_input("Observation Date *", value=date.today())
                body_temp = st.number_input("Body Temperature (°C) *", min_value=35.0, max_value=44.0, value=38.6, step=0.1, help="Physiological baseline: 38.0–39.2 °C")

            with h2:
                milk_yield = st.number_input("Milk Yield Today (L)", min_value=0.0, max_value=80.0, value=22.0, step=0.5)
                appetite = st.selectbox("Appetite State", ["Normal", "Reduced", "Anorexic", "Increased"])
                feed_kg = st.number_input("Estimated Feed Intake (kg DM)", min_value=0.0, max_value=50.0, value=18.0, step=1.0)
                water_l = st.number_input("Estimated Water Intake (L)", min_value=0.0, max_value=250.0, value=80.0, step=5.0)

            with h3:
                act_level = st.selectbox("Activity Level", ["Normal", "Restless", "Lethargic", "Hyperactive"])
                behaviour = st.selectbox("General Behaviour", ["Normal", "Isolated", "Agitated", "Dull"])
                symptoms = st.text_input("Observed Symptoms", placeholder="e.g. Coughing, discharge, swollen hock")
                health_notes = st.text_area("Health Notes / Observations", placeholder="Clinical remarks")

            # Real-time screening flags
            flags = []
            status = "Healthy"
            if body_temp >= 39.6:
                flags.append("High Fever (>39.5°C)")
                status = "Critical Alert"
            elif body_temp >= 39.3:
                flags.append("Mild Pyrexia (39.3–39.5°C)")
                status = "Minor Concern"
            elif body_temp < 38.0:
                flags.append("Hypothermia (<38.0°C)")
                status = "Critical Alert"

            if appetite in ["Reduced", "Anorexic"]:
                flags.append("Appetite Drop")
                if status == "Healthy":
                    status = "Minor Concern"

            if act_level == "Lethargic" or behaviour == "Dull":
                flags.append("Depressed Sensorium")
                if status == "Healthy":
                    status = "Minor Concern"

            submitted = st.form_submit_button("💾 Save Health Record", use_container_width=True)
            if submitted:
                rec_dict = {
                    "cow_id": cid,
                    "observation_date": obs_date.strftime("%Y-%m-%d"),
                    "body_temperature": body_temp,
                    "milk_production": milk_yield,
                    "appetite": appetite,
                    "feed_intake": feed_kg,
                    "water_intake": water_l,
                    "activity_level": act_level,
                    "behaviour": behaviour,
                    "symptoms": symptoms,
                    "health_status": status,
                    "abnormality_flags": " | ".join(flags) if flags else "Normal",
                    "health_notes": health_notes
                }
                database.add_health_record(rec_dict)
                st.success(f"Health record saved for {cid}! Status assigned: {status}")
                st.rerun()

    # TAB 2: Registry & History
    with tab_history:
        st.markdown("#### Health Records History")
        h_df = database.get_health_records()
        if not h_df.empty:
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                f_cid = st.selectbox("Filter Cow", ["All"] + sorted(list(h_df['cow_id'].unique())), key="h_hist_cid")
            with f_col2:
                f_stat = st.selectbox("Filter Health Status", ["All", "Healthy", "Minor Concern", "Critical Alert", "Sick", "Under Observation"])

            filtered_h = h_df.copy()
            if f_cid != "All":
                filtered_h = filtered_h[filtered_h['cow_id'] == f_cid]
            if f_stat != "All":
                filtered_h = filtered_h[filtered_h['health_status'] == f_stat]

            cols = ['cow_id', 'observation_date', 'body_temperature', 'milk_production', 'appetite', 'activity_level', 'health_status', 'abnormality_flags', 'symptoms']
            st.dataframe(filtered_h[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No health records logged yet.")

    # TAB 3: Trends
    with tab_trends:
        st.markdown("#### Temperature & Health Analytics")
        h_df = database.get_health_records()
        if not h_df.empty:
            h_df_sorted = h_df.sort_values('observation_date')
            fig_temp = px.scatter(
                h_df_sorted, x='observation_date', y='body_temperature',
                color='health_status',
                hover_data=['cow_id', 'symptoms', 'appetite'],
                title="Body Temperature Observations (°C) Over Time",
                color_discrete_map={'Healthy': '#2d6a4f', 'Minor Concern': '#d4af37', 'Critical Alert': '#e53e3e', 'Sick': '#c53030', 'Under Observation': '#dd6b20'}
            )
            # Physiological threshold lines
            fig_temp.add_hline(y=38.0, line_dash="dash", line_color="#4a5568", annotation_text="Lower Normal Bound (38.0°C)")
            fig_temp.add_hline(y=39.2, line_dash="dash", line_color="#52b788", annotation_text="Upper Normal Bound (39.2°C)")
            fig_temp.add_hline(y=39.5, line_dash="dash", line_color="#e53e3e", annotation_text="Fever Threshold (39.5°C)")
            fig_temp.update_layout(xaxis_title="Date", yaxis_title="Body Temp (°C)", height=380)
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("No health data available for plotting.")


# ==========================================
# MODULE 5: Disease Risk Assessment
# ==========================================

def render_disease_assessment():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Preliminary Disease Risk Screening</div>
            <div class="brand-tagline">Rule-based preliminary screening for mastitis, systemic pyrexia, digestive, and reproductive health concerns.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="alert-card-warning">
        <b>CLINICAL DISCLAIMER:</b> This module provides preliminary decision support and herd screening based on user-entered clinical signs.
        It does NOT replace diagnostic veterinary pathology or physical veterinary examination.
    </div>
    """, unsafe_allow_html=True)

    tab_eval, tab_hist = st.tabs(["⚠️ Screen Cow for Disease Risks", "📜 Disease Screening Registry"])

    cows_df = database.get_all_cows()

    with tab_eval:
        if cows_df.empty:
            st.warning("Please register cows first in Cow Management.")
            return

        c1, c2 = st.columns([1, 1.2])

        with c1:
            st.markdown("#### Clinical Signs & Observations")
            cow_choices = [f"{r['cow_id']} – {r['name']}" for _, r in cows_df.iterrows()]
            sel_cow = st.selectbox("Select Cow for Screening", cow_choices, key="dis_cow_sel")
            cid = sel_cow.split(" – ")[0]
            cow_data = database.get_cow(cid)

            assess_date = st.date_input("Screening Date", value=date.today(), key="dis_date")
            body_temp = st.number_input("Body Temperature (°C)", min_value=35.0, max_value=44.0, value=38.6, step=0.1, key="dis_temp")
            milk_drop = st.number_input("Estimated Milk Yield Drop (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="dis_drop")

            st.markdown("##### 1. Udder & Mastitis Markers")
            u_swell = st.checkbox("Udder swelling / inflammation")
            u_pain = st.checkbox("Udder tenderness / flinching")
            u_app = st.checkbox("Abnormal udder appearance (redness/heat)")
            u_milk = st.checkbox("Abnormal milk (clots, flakes, watery)")

            st.markdown("##### 2. Systemic & Digestive Markers")
            appetite = st.selectbox("Appetite Level", ["Normal", "Reduced", "Anorexic", "Severely Reduced"], key="dis_app")
            dig_symp = st.text_input("Digestive Symptoms", placeholder="e.g. Diarrhea, bloat, reduced cud chewing")

            st.markdown("##### 3. Reproductive Markers")
            rep_symp = st.text_input("Reproductive Symptoms", placeholder="e.g. Purulent discharge, retained placenta")
            notes = st.text_area("Clinical Notes", placeholder="Diagnostic notes")

        with c2:
            st.markdown("#### Decision-Support Screening Output")

            mast_risk, sys_risk, dig_risk, rep_risk, overall, rationale, vet_rec = evaluate_disease_risk(
                body_temp, milk_drop, u_swell, u_pain, u_app, u_milk, dig_symp, rep_symp, appetite
            )

            # Card styling
            card_border = "#e53e3e" if overall == "High concern" else ("#d4af37" if overall == "Moderate concern" else "#2d6a4f")
            st.markdown(f"""
            <div class="section-box" style="border-top: 5px solid {card_border};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.1rem; font-weight:700; color:#1b4332;">Overall Concern Level</span>
                    <span class="demo-badge" style="background:{card_border}; color:white; font-size:1rem; padding:6px 16px;">
                        {overall}
                    </span>
                </div>
                <hr style="margin:12px 0;">
                <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap: 12px; font-size:0.95rem;">
                    <div><b>Possible Mastitis:</b> <span style="font-weight:600;">{mast_risk}</span></div>
                    <div><b>Systemic / Fever Risk:</b> <span style="font-weight:600;">{sys_risk}</span></div>
                    <div><b>Digestive Concern:</b> <span style="font-weight:600;">{dig_risk}</span></div>
                    <div><b>Reproductive Concern:</b> <span style="font-weight:600;">{rep_risk}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if vet_rec == 1 or overall == "High concern":
                st.markdown("""
                <div class="alert-card-danger">
                    <b>🚨 VETERINARY EXAMINATION STRONGLY RECOMMENDED:</b> One or more clinical parameters exceed critical screening thresholds. Schedule immediate examination by a qualified veterinarian.
                </div>
                """, unsafe_allow_html=True)

            st.markdown("##### Screening Rationale")
            st.info(rationale)

            if st.button("💾 Save Disease Risk Screening Record", type="primary", use_container_width=True):
                assessment_payload = {
                    "cow_id": cid,
                    "assessment_date": assess_date.strftime("%Y-%m-%d"),
                    "mastitis_risk": mast_risk,
                    "systemic_risk": sys_risk,
                    "digestive_risk": dig_risk,
                    "reproductive_risk": rep_risk,
                    "overall_concern": overall,
                    "udder_swelling": 1 if u_swell else 0,
                    "udder_pain": 1 if u_pain else 0,
                    "abnormal_udder_appearance": 1 if u_app else 0,
                    "abnormal_milk": 1 if u_milk else 0,
                    "elevated_temp": 1 if body_temp >= 39.5 else 0,
                    "reduced_yield": 1 if milk_drop >= 20.0 else 0,
                    "digestive_symptoms": dig_symp,
                    "reproductive_symptoms": rep_symp,
                    "rationale": rationale,
                    "screening_notes": notes,
                    "vet_consultation_recommended": vet_rec
                }
                database.add_disease_assessment(assessment_payload)
                st.success(f"Disease risk assessment logged for {cid}!")
                st.rerun()

    with tab_hist:
        st.markdown("#### Historical Disease Screening Records")
        d_df = database.get_disease_assessments()
        if not d_df.empty:
            cols = ['cow_id', 'assessment_date', 'overall_concern', 'mastitis_risk', 'systemic_risk', 'digestive_risk', 'reproductive_risk', 'vet_consultation_recommended', 'rationale']
            st.dataframe(d_df[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No disease risk assessments logged yet.")


# ==========================================
# MODULE 6: THI and Heat Stress Analytics
# ==========================================

def render_thi_analytics():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Temperature-Humidity Index (THI) & Heat Stress Analytics</div>
            <div class="brand-tagline">Dedicated environmental biometeorological monitoring for dairy cattle comfort and productivity.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    thi_df = database.get_thi_records()

    # Active Real-time Alert Banner based on latest recorded environmental reading
    if not thi_df.empty:
        latest_rec = thi_df.iloc[0]
        l_thi = float(latest_rec['thi_value'])
        l_cat = str(latest_rec['heat_stress_category'])
        l_date = str(latest_rec['observation_date'])
        l_time = str(latest_rec['observation_time'])

        if l_thi >= 80.0:
            st.markdown(f"""
            <div class="alert-card-danger" style="margin-bottom: 18px;">
                <b>🚨 CRITICAL HEAT STRESS EMERGENCY ACTIVE:</b> Latest reading ({l_date} {l_time}) is <b>THI {l_thi} ({l_cat})</b>.
                <br>• <b>Immediate Actions:</b> Activate continuous fans, high-pressure misting / evaporative cooling in holding yards. Ensure unlimited access to chilled drinking water.
                <br>• <b>Reproductive Warning:</b> Overt standing estrus expression is severely suppressed ("silent heat"). Do not rely on daytime visual checks alone.
            </div>
            """, unsafe_allow_html=True)
        elif l_thi >= 72.0:
            st.markdown(f"""
            <div class="alert-card-warning" style="margin-bottom: 18px;">
                <b>⚠️ SIGNIFICANT HEAT STRESS ADVISORY:</b> Latest reading ({l_date} {l_time}) is <b>THI {l_thi} ({l_cat})</b>.
                <br>• <b>Advisory:</b> Respiration rates elevated. Dry matter intake and milk yields declining. Run cooling cycles before milking.
            </div>
            """, unsafe_allow_html=True)
        elif l_thi >= 68.0:
            st.markdown(f"""
            <div class="alert-card-warning" style="background-color: #f7fee7; border-left-color: #84cc16; color: #365314; margin-bottom: 18px;">
                <b>🌡️ MILD HEAT STRESS WATCH:</b> Latest reading ({l_date} {l_time}) is <b>THI {l_thi} ({l_cat})</b>.
                <br>• High-producing cows may begin to seek shade and increase respiration. Ensure adequate shade and ventilation.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-card-success" style="margin-bottom: 18px;">
                <b>✅ THERMAL COMFORT ZONE:</b> Latest reading ({l_date} {l_time}) is <b>THI {l_thi} ({l_cat})</b>. Environmental conditions are optimal for herd productivity.
            </div>
            """, unsafe_allow_html=True)

    # Scientific Reference & Breed Variability Explanation Box
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="color: #1b4332; font-weight: 700; font-size: 0.95rem; margin-bottom: 4px;">
            🔬 Scientific Biometeorology & Biological Governance Rules
        </div>
        <div style="font-size: 0.85rem; color: #475569; line-height: 1.5;">
            <b>Standard NRC Dairy Equation:</b> <code>THI = (1.8 × T + 32) - ((0.55 - 0.0055 × RH) × (1.8 × T - 26))</code>
            <br>• <b>Environmental Exclusivity:</b> THI is strictly an environmental index. Cow body temperature is <b>never</b> substituted or used in the THI formula.
            <br>• <b>Independent Risk Metric:</b> THI is evaluated as an independent herd risk factor and is <b>never</b> automatically subtracted from estrus evidence scores.
            <br>• <b>Indicative Screening Categories:</b> Thermal sensitivity varies across individuals:
            <i>High-producing Holstein Friesians</i> experience stress at <b>THI ≥ 68</b>; <i>Jerseys & Crossbreds</i> at <b>THI ~70–72</b>; and <i>Indigenous Zebu cattle (Gir, Sahiwal)</i> possess greater heat tolerance up to <b>THI 76–78</b>.
            <i>Exposure duration and nighttime cooling (THI &lt; 65 at night) significantly mitigate daytime heat impacts.</i>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_calc, tab_trends, tab_impact = st.tabs([
        "🌡️ Interactive THI Calculator & Logger", "📈 Historical THI Trajectory", "🐄 Heat Stress & Herd Impact"
    ])

    with tab_calc:
        st.markdown("#### Instant Interactive Environmental THI Calculator")
        st.write("Adjust environmental temperature and relative humidity using the sliders below to calculate the Temperature-Humidity Index (THI) and evaluate heat-stress risk in real time.")

        # ONLY TWO WORKING SLIDERS - No +/- controls, no duplicate number inputs
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            calc_temp = st.slider(
                "Ambient Temperature (°C)",
                min_value=0.0,
                max_value=50.0,
                value=30.0,
                step=0.1,
                format="%.1f",
                key="thi_interactive_temp_slider"
            )
        with s_col2:
            calc_rh = st.slider(
                "Relative Humidity (%)",
                min_value=0,
                max_value=100,
                value=60,
                step=1,
                format="%d",
                key="thi_interactive_rh_slider"
            )

        # Recalculate THI immediately using the NRC formula
        # THI = (1.8 * T + 32) - ((0.55 - 0.0055 * RH) * (1.8 * T - 26))
        cur_thi = database.calculate_thi(calc_temp, calc_rh)

        # Categorization & Advisory
        if cur_thi < 68.0:
            cur_cat = "Lower Concern"
            cat_color = "#2d6a4f"
            cat_bg = "#e8f5e9"
            badge_icon = "🟢"
            cat_desc = "Optimal cow comfort zone. Respiratory rates and dry matter intake normal. Bovine thermoregulatory balance fully maintained."
            advisory = "Normal management routines. Maintain standard shade and ensure clean drinking water access."
        elif cur_thi < 72.0:
            cur_cat = "Possible Mild Heat Stress"
            cat_color = "#84cc16"
            cat_bg = "#f7fee7"
            badge_icon = "🟡"
            cat_desc = "Respiration rate elevated (60+ breaths/min). Cows seek shade; mild yield variation. Dry matter intake begins to fluctuate."
            advisory = "Verify shade availability, ensure optimal drinking water flow rates, and maximize barn ventilation."
        elif cur_thi < 80.0:
            cur_cat = "Significant Heat-Stress Concern"
            cat_color = "#f59f00"
            cat_bg = "#fffbeb"
            badge_icon = "🟠"
            cat_desc = "Noticeable drop in feed intake (-10% to -20%) and milk production. Open-mouth panting; standing heat duration suppressed ('silent heat')."
            advisory = "Activate fans and evaporative cooling/sprinklers in holding pens and feeding alleys. Shift feeding times to cooler morning and evening periods."
        else:
            cur_cat = "Severe Heat-Stress Concern"
            cat_color = "#e53e3e"
            cat_bg = "#fef2f2"
            badge_icon = "🔴"
            cat_desc = "Severe heat exhaustion alert. Heavy salivation, acute drop in milk yield, high embryonic mortality, and silent heat."
            advisory = "CRITICAL EMERGENCY: Continuous fan operation and high-pressure evaporative soaking. Provide chilled drinking water. Cease non-essential cow movement during peak heat."

        # LIVE RESULT DISPLAY IMMEDIATELY BELOW THE SLIDERS
        st.markdown("<hr style='margin: 16px 0 12px 0;'>", unsafe_allow_html=True)
        st.markdown("##### Real-Time Biometeorological Assessment")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("1. Ambient Temperature", f"{calc_temp:.1f} °C")
        with m2:
            st.metric("2. Relative Humidity", f"{calc_rh}%")
        with m3:
            st.metric("3. Calculated THI Value", f"{cur_thi:.2f}")
        with m4:
            st.markdown(f"""
            <div style="padding: 10px; background: {cat_bg}; border: 1.5px solid {cat_color}; border-radius: 8px; text-align: center;">
                <div style="font-size: 0.72rem; color: #475569; font-weight: 700; text-transform: uppercase;">4. Heat-Stress Category</div>
                <div style="font-size: 1.0rem; font-weight: 800; color: {cat_color}; margin-top: 4px;">{badge_icon} {cur_cat}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: {cat_bg}; border-left: 6px solid {cat_color}; border-radius: 8px; padding: 16px 20px; margin-top: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 1.15rem; font-weight: 800; color: {cat_color};">
                    {badge_icon} 4. Heat-Stress Category: {cur_cat} (THI: {cur_thi:.2f})
                </span>
                <span style="background: {cat_color}; color: white; font-size: 0.8rem; font-weight: 700; padding: 3px 12px; border-radius: 12px;">
                    Biometeorological Alert
                </span>
            </div>
            <div style="font-size: 0.92rem; color: #1e293b; line-height: 1.5; margin-bottom: 10px;">
                <b>Biological Impact:</b> {cat_desc}
            </div>
            <div style="font-size: 0.92rem; color: #1e293b; line-height: 1.5; background: rgba(255,255,255,0.7); padding: 10px 14px; border-radius: 6px; border: 1px solid {cat_color}33;">
                <b>5. Appropriate Advisory Message:</b> {advisory}
            </div>
            <div style="margin-top: 10px; font-size: 0.8rem; color: #64748b;">
                <b>Indicative Category Scale:</b> THI &lt; 68: Lower Concern &nbsp;|&nbsp; THI 68–71: Possible Mild Heat Stress &nbsp;|&nbsp; THI 72–79: Significant Heat-Stress Concern &nbsp;|&nbsp; THI ≥ 80: Severe Heat-Stress Concern
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Optional expander or form below the calculator allowing users to log reading to SQLite
        with st.expander("💾 Log This Environmental Reading to Database (bovisense.db)", expanded=False):
            with st.form("thi_log_form", clear_on_submit=False):
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1:
                    obs_date = st.date_input("Observation Date", value=date.today())
                    obs_time = st.time_input("Observation Time", value=datetime.now().time())
                with f_col2:
                    log_temp = st.number_input("Ambient Temperature (°C)", min_value=0.0, max_value=50.0, value=float(calc_temp), step=0.1, format="%.1f")
                    log_rh = st.number_input("Relative Humidity (%)", min_value=0.0, max_value=100.0, value=float(calc_rh), step=1.0, format="%.0f")
                with f_col3:
                    notes = st.text_area("Weather / Microclimate Remarks", placeholder="e.g. Afternoon reading, ventilation fans operational", value=f"Simulated reading from interactive calculator (THI {cur_thi:.2f})")

                save_thi = st.form_submit_button("💾 Save Reading to bovisense.db", use_container_width=True)
                if save_thi:
                    thi_val = database.calculate_thi(log_temp, log_rh)
                    cat_logged = database.classify_thi(thi_val)
                    rec = {
                        "observation_date": obs_date.strftime("%Y-%m-%d"),
                        "observation_time": obs_time.strftime("%H:%M"),
                        "ambient_temp": log_temp,
                        "relative_humidity": log_rh,
                        "notes": notes
                    }
                    database.add_thi_record(rec)
                    st.success(f"Environmental observation logged: THI {thi_val} ({cat_logged})")
                    st.rerun()

    with tab_trends:
        st.markdown("#### Historical Environmental THI Trends & Timeline")

        if not thi_df.empty:
            tf1, tf2 = st.columns([1, 2])
            with tf1:
                period_filter = st.selectbox(
                    "Select Timeline Filter",
                    ["Last 14 Days", "Last 7 Days", "Last 30 Days", "All Records"],
                    index=0
                )

            thi_df_sorted = thi_df.copy()
            thi_df_sorted['datetime'] = pd.to_datetime(thi_df_sorted['observation_date'] + ' ' + thi_df_sorted['observation_time'])
            thi_df_sorted = thi_df_sorted.sort_values('datetime')

            today_dt = pd.to_datetime(date.today())
            if period_filter == "Last 7 Days":
                thi_df_sorted = thi_df_sorted[thi_df_sorted['datetime'] >= (today_dt - timedelta(days=7))]
            elif period_filter == "Last 14 Days":
                thi_df_sorted = thi_df_sorted[thi_df_sorted['datetime'] >= (today_dt - timedelta(days=14))]
            elif period_filter == "Last 30 Days":
                thi_df_sorted = thi_df_sorted[thi_df_sorted['datetime'] >= (today_dt - timedelta(days=30))]

            if not thi_df_sorted.empty:
                k1, k2, k3, k4 = st.columns(4)
                latest_val = thi_df_sorted.iloc[-1]['thi_value']
                max_val = thi_df_sorted['thi_value'].max()
                mean_val = round(thi_df_sorted['thi_value'].mean(), 1)
                stressed_count = len(thi_df_sorted[thi_df_sorted['thi_value'] >= 72.0])

                with k1:
                    st.metric("Latest Period Reading", f"{latest_val}")
                with k2:
                    st.metric("Peak THI Recorded", f"{max_val}")
                with k3:
                    st.metric("Mean THI", f"{mean_val}")
                with k4:
                    st.metric("Stressed Readings (≥72)", f"{stressed_count}")

                fig_thi = go.Figure()

                # Shaded threshold zones
                fig_thi.add_hrect(y0=0, y1=68, fillcolor="#2d6a4f", opacity=0.08, line_width=0, annotation_text="Thermal Comfort (<68)", annotation_position="top left")
                fig_thi.add_hrect(y0=68, y1=72, fillcolor="#52b788", opacity=0.12, line_width=0, annotation_text="Mild Stress (68–71)", annotation_position="top left")
                fig_thi.add_hrect(y0=72, y1=80, fillcolor="#f59f00", opacity=0.12, line_width=0, annotation_text="Significant Stress (72–79)", annotation_position="top left")
                fig_thi.add_hrect(y0=80, y1=110, fillcolor="#e53e3e", opacity=0.15, line_width=0, annotation_text="Severe Stress (≥80)", annotation_position="top left")

                # Continuous Trajectory line
                fig_thi.add_trace(go.Scatter(
                    x=thi_df_sorted['datetime'],
                    y=thi_df_sorted['thi_value'],
                    mode='lines',
                    name='Continuous THI Trajectory',
                    line=dict(color='#2d6a4f', width=2.5, shape='spline'),
                    hoverinfo='skip'
                ))

                color_map = {
                    "Lower concern": "#2d6a4f",
                    "Possible mild heat stress": "#52b788",
                    "Significant heat-stress concern": "#f59f00",
                    "Severe heat-stress concern": "#e53e3e"
                }

                for cat, group in thi_df_sorted.groupby('heat_stress_category'):
                    fig_thi.add_trace(go.Scatter(
                        x=group['datetime'],
                        y=group['thi_value'],
                        mode='markers',
                        name=cat,
                        marker=dict(size=9, color=color_map.get(cat, '#2d6a4f'), line=dict(width=1, color='#ffffff')),
                        customdata=group[['ambient_temp', 'relative_humidity', 'notes']],
                        hovertemplate="<b>Date/Time:</b> %{x|%Y-%m-%d %H:%M}<br><b>THI:</b> %{y}<br><b>Temp:</b> %{customdata[0]}°C<br><b>RH:</b> %{customdata[1]}%<br><b>Notes:</b> %{customdata[2]}<extra></extra>"
                    ))

                fig_thi.add_hline(y=68, line_dash="dash", line_color="#52b788", line_width=1.5)
                fig_thi.add_hline(y=72, line_dash="dash", line_color="#f59f00", line_width=1.5)
                fig_thi.add_hline(y=80, line_dash="dash", line_color="#e53e3e", line_width=1.5)

                fig_thi.update_layout(
                    title=f"Environmental THI Trajectory ({period_filter})",
                    xaxis_title="Timeline",
                    yaxis_title="Calculated THI",
                    height=400,
                    margin=dict(t=40, b=10, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_thi, use_container_width=True)

                st.markdown("##### Environmental Observations Registry")
                display_cols = ['observation_date', 'observation_time', 'ambient_temp', 'relative_humidity', 'thi_value', 'heat_stress_category', 'notes']
                st.dataframe(thi_df_sorted[display_cols].sort_values(['observation_date', 'observation_time'], ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("No THI observations in the selected timeframe filter.")
        else:
            st.info("No THI records recorded yet. Enter manual readings in the calculator or load demonstration data.")

    with tab_impact:
        st.markdown("#### Cross-Analysis: THI Impact on Milk Yield & Estrus Expression")
        st.markdown("""
        High environmental Temperature-Humidity Index (THI) impairs bovine thermoregulation,
        depresses dry matter intake (DMI), and severely blunts behavioral estrus manifestations (*silent heat*).
        This cross-analysis module models the empirical impact of recorded thermal stress on herd lactation volume
        and estrus detection sensitivity.
        """)

        # Scientific rule advisory alert
        st.markdown("""
        <div class="alert-card-warning" style="font-size:0.85rem; margin-bottom:16px;">
            <b>BIOLOGICAL GOVERNANCE RULES:</b>
            <br>1. <b>Environmental Independence:</b> THI is computed exclusively from ambient temperature and relative humidity. Cow body temperature is <i>never</i> used in the THI formula.
            <br>2. <b>Score Integrity:</b> THI is an external environmental risk factor and is <i>never</i> automatically subtracted from estrus evidence scores.
            <br>3. <b>Screening Insight:</b> Elevated THI warns the herd manager that standing heat duration is curtailed (down to 4–6 hours), increasing the incidence of unobserved heats.
        </div>
        """, unsafe_allow_html=True)

        milk_df = database.get_milk_records()
        thi_df = database.get_thi_records()
        estrus_df = database.get_estrus_observations()

        if thi_df.empty:
            st.info("No THI environmental records found. Log THI records or load demonstration data to view cross-analytics.")
        else:
            # -----------------------------------------------------------------
            # SECTION A: THI Distribution Across Recorded Period
            # -----------------------------------------------------------------
            st.markdown("##### 1. Environmental THI Stress Classification Distribution")
            thi_cat_counts = thi_df['heat_stress_category'].value_counts().reset_index()
            thi_cat_counts.columns = ['Category', 'Readings']

            c_dist1, c_dist2 = st.columns([1, 1.2])
            with c_dist1:
                fig_thi_dist = px.pie(
                    thi_cat_counts, names='Category', values='Readings',
                    title="Environmental THI Category Distribution",
                    color='Category',
                    color_discrete_map={
                        "Lower concern": "#2d6a4f",
                        "Possible mild heat stress": "#52b788",
                        "Significant heat-stress concern": "#f59f00",
                        "Severe heat-stress concern": "#e53e3e"
                    },
                    hole=0.45
                )
                fig_thi_dist.update_layout(margin=dict(t=40, b=10, l=10, r=10), height=280)
                st.plotly_chart(fig_thi_dist, use_container_width=True)

            with c_dist2:
                total_readings = len(thi_df)
                stress_readings = len(thi_df[thi_df['thi_value'] >= 72.0])
                stress_pct = round((stress_readings / total_readings) * 100, 1) if total_readings > 0 else 0.0

                st.markdown("<div style='padding-top:10px;'>", unsafe_allow_html=True)
                st.metric("Total Biometeorological Readings", f"{total_readings}")
                st.metric("Heat-Stressed Readings (THI ≥ 72)", f"{stress_readings} ({stress_pct}%)")
                st.markdown(f"""
                <div style="font-size:0.85rem; color:#495057; background:#f8f9fa; padding:10px; border-radius:6px; border-left:4px solid {'#e53e3e' if stress_pct > 25 else '#52b788'};">
                    <b>Herd Exposure Status:</b> {f'High thermal challenge: {stress_pct}% of readings exceed the significant heat-stress threshold.' if stress_pct > 25 else 'Thermal environment is within acceptable herd comfort bounds.'}
                </div>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")

            # -----------------------------------------------------------------
            # SECTION B: THI Impact on Milk Production
            # -----------------------------------------------------------------
            st.markdown("##### 2. Empirical Correlation: Environmental THI vs. Daily Milk Yield")

            if not milk_df.empty:
                daily_m = milk_df.groupby('production_date').agg(
                    avg_yield=('total_yield', 'mean'),
                    total_volume=('total_yield', 'sum'),
                    cow_count=('cow_id', 'nunique')
                ).reset_index()

                daily_t = thi_df.groupby('observation_date').agg(
                    mean_thi=('thi_value', 'mean'),
                    max_thi=('thi_value', 'max'),
                    ambient_temp=('ambient_temp', 'mean'),
                    relative_humidity=('relative_humidity', 'mean'),
                    heat_stress_category=('heat_stress_category', 'first')
                ).reset_index()

                merged_m = pd.merge(daily_m, daily_t, left_on='production_date', right_on='observation_date')

                if len(merged_m) >= 2:
                    # Calculate linear regression with pure NumPy (no statsmodels dependency)
                    x_vals = merged_m['mean_thi'].values
                    y_vals = merged_m['avg_yield'].values
                    slope, intercept = np.polyfit(x_vals, y_vals, 1)

                    corr_matrix = np.corrcoef(x_vals, y_vals)
                    corr_coeff = corr_matrix[0, 1] if not np.isnan(corr_matrix[0, 1]) else 0.0
                    r2 = corr_coeff ** 2

                    # Comfort vs Stressed Yield
                    comfort_mask = merged_m['mean_thi'] < 68.0
                    stressed_mask = merged_m['mean_thi'] >= 72.0
                    comfort_yield = merged_m.loc[comfort_mask, 'avg_yield'].mean() if comfort_mask.any() else np.nan
                    stressed_yield = merged_m.loc[stressed_mask, 'avg_yield'].mean() if stressed_mask.any() else np.nan

                    drop_pct = 0.0
                    if pd.notna(comfort_yield) and pd.notna(stressed_yield) and comfort_yield > 0:
                        drop_pct = round(((comfort_yield - stressed_yield) / comfort_yield) * 100, 1)

                    # Metric Cards Row
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    with mc1:
                        st.metric("Comfort Yield (THI < 68)", f"{comfort_yield:.1f} L/cow" if pd.notna(comfort_yield) else "N/A")
                    with mc2:
                        st.metric("Stressed Yield (THI ≥ 72)", f"{stressed_yield:.1f} L/cow" if pd.notna(stressed_yield) else "N/A")
                    with mc3:
                        st.metric("Heat-Induced Yield Drop", f"-{drop_pct}%" if drop_pct > 0 else "0.0%")
                    with mc4:
                        st.metric("Yield Sensitivity (Slope)", f"{slope:.2f} L / THI pt")

                    # Regression Scatter Plot
                    fig_m_corr = px.scatter(
                        merged_m, x='mean_thi', y='avg_yield',
                        color='heat_stress_category',
                        hover_data=['production_date', 'cow_count', 'ambient_temp', 'relative_humidity'],
                        title=f"Daily Mean Milk Yield vs. THI Index (Correlation r = {corr_coeff:.2f}, R² = {r2:.2f})",
                        labels={'mean_thi': 'Mean Daily Environmental THI', 'avg_yield': 'Average Milk Yield / Cow (L)'},
                        color_discrete_map={
                            "Lower concern": "#2d6a4f",
                            "Possible mild heat stress": "#52b788",
                            "Significant heat-stress concern": "#f59f00",
                            "Severe heat-stress concern": "#e53e3e"
                        }
                    )

                    # Add regression line cleanly using go.Scatter
                    x_trend = np.linspace(x_vals.min(), x_vals.max(), 50)
                    y_trend = slope * x_trend + intercept
                    fig_m_corr.add_trace(go.Scatter(
                        x=x_trend, y=y_trend,
                        mode='lines',
                        name=f'Trendline ({slope:+.2f} L/THI)',
                        line=dict(color='#b8860b', width=2.5, dash='dash')
                    ))

                    # Vertical threshold lines
                    fig_m_corr.add_vline(x=68, line_dash="dot", line_color="#52b788", annotation_text="Mild (68)")
                    fig_m_corr.add_vline(x=72, line_dash="dot", line_color="#f59f00", annotation_text="Significant (72)")
                    fig_m_corr.add_vline(x=80, line_dash="dot", line_color="#e53e3e", annotation_text="Severe (80)")
                    fig_m_corr.update_layout(height=360, margin=dict(t=40, b=10, l=10, r=10))
                    st.plotly_chart(fig_m_corr, use_container_width=True)

                    # Category-wise Yield Bar Chart
                    cat_summary = merged_m.groupby('heat_stress_category')['avg_yield'].mean().reset_index()
                    cat_order = ["Lower concern", "Possible mild heat stress", "Significant heat-stress concern", "Severe heat-stress concern"]
                    cat_summary['sort_order'] = cat_summary['heat_stress_category'].apply(lambda x: cat_order.index(x) if x in cat_order else 99)
                    cat_summary = cat_summary.sort_values('sort_order')

                    fig_cat_bar = px.bar(
                        cat_summary, x='heat_stress_category', y='avg_yield',
                        title="Average Daily Milk Yield by Heat Stress Tier",
                        labels={'heat_stress_category': 'Heat Stress Category', 'avg_yield': 'Average Milk Yield (L/cow)'},
                        color='heat_stress_category',
                        color_discrete_map={
                            "Lower concern": "#2d6a4f",
                            "Possible mild heat stress": "#52b788",
                            "Significant heat-stress concern": "#f59f00",
                            "Severe heat-stress concern": "#e53e3e"
                        }
                    )
                    fig_cat_bar.update_layout(showlegend=False, height=280, margin=dict(t=40, b=10, l=10, r=10))
                    st.plotly_chart(fig_cat_bar, use_container_width=True)

                else:
                    st.info("At least 2 matching calendar days of milk records and THI records are required for regression analysis.")
            else:
                st.info("No milk records found. Enter daily milking yields or load demo data to analyze production correlation.")

            st.markdown("---")

            # -----------------------------------------------------------------
            # SECTION C: THI Impact on Estrus Expression & Silent Heat
            # -----------------------------------------------------------------
            st.markdown("##### 3. Estrus Expression Sensitivity & Silent Heat Analysis")

            if not estrus_df.empty:
                daily_e = estrus_df.groupby('observation_date').agg(
                    avg_estrus_score=('estrus_score', 'mean'),
                    high_evidence_count=('evidence_category', lambda s: (s == 'High').sum()),
                    moderate_evidence_count=('evidence_category', lambda s: (s == 'Moderate').sum()),
                    low_evidence_count=('evidence_category', lambda s: (s == 'Low').sum()),
                    total_observations=('id', 'count')
                ).reset_index()

                merged_e = pd.merge(daily_e, daily_t, left_on='observation_date', right_on='observation_date')

                if not merged_e.empty:
                    ec1, ec2, ec3 = st.columns(3)

                    # Comfort vs Stressed Estrus Score
                    c_mask_e = merged_e['mean_thi'] < 68.0
                    s_mask_e = merged_e['mean_thi'] >= 72.0
                    comfort_score = merged_e.loc[c_mask_e, 'avg_estrus_score'].mean() if c_mask_e.any() else np.nan
                    stressed_score = merged_e.loc[s_mask_e, 'avg_estrus_score'].mean() if s_mask_e.any() else np.nan

                    total_high_obs = merged_e['high_evidence_count'].sum()
                    total_all_obs = merged_e['total_observations'].sum()
                    standing_visibility = round((total_high_obs / total_all_obs) * 100, 1) if total_all_obs > 0 else 0.0

                    with ec1:
                        st.metric("Avg Estrus Score (THI < 68)", f"{comfort_score:.1f} / 100" if pd.notna(comfort_score) else "N/A")
                    with ec2:
                        st.metric("Avg Estrus Score (THI ≥ 72)", f"{stressed_score:.1f} / 100" if pd.notna(stressed_score) else "N/A")
                    with ec3:
                        st.metric("Standing Heat Visibility Ratio", f"{standing_visibility}%")

                    e_col1, e_col2 = st.columns(2)
                    with e_col1:
                        fig_e_scatter = px.scatter(
                            merged_e, x='mean_thi', y='avg_estrus_score',
                            color='heat_stress_category',
                            title="Average Estrus Evidence Score vs. Daily THI",
                            labels={'mean_thi': 'Environmental THI', 'avg_estrus_score': 'Avg Estrus Evidence Score (0–100)'},
                            color_discrete_map={
                                "Lower concern": "#2d6a4f",
                                "Possible mild heat stress": "#52b788",
                                "Significant heat-stress concern": "#f59f00",
                                "Severe heat-stress concern": "#e53e3e"
                            }
                        )
                        fig_e_scatter.add_vline(x=72, line_dash="dash", line_color="#e53e3e", annotation_text="Silent Heat Threshold (72)")
                        fig_e_scatter.update_layout(height=320, margin=dict(t=40, b=10, l=10, r=10))
                        st.plotly_chart(fig_e_scatter, use_container_width=True)

                    with e_col2:
                        e_cat_df = merged_e.groupby('heat_stress_category')[['high_evidence_count', 'moderate_evidence_count', 'low_evidence_count']].sum().reset_index()
                        fig_stacked = px.bar(
                            e_cat_df, x='heat_stress_category',
                            y=['high_evidence_count', 'moderate_evidence_count', 'low_evidence_count'],
                            title="Estrus Evidence Expression by Heat Stress Tier",
                            labels={'value': 'Number of Observations', 'heat_stress_category': 'Heat Stress Category', 'variable': 'Evidence Level'},
                            color_discrete_map={
                                'high_evidence_count': '#2d6a4f',
                                'moderate_evidence_count': '#d4af37',
                                'low_evidence_count': '#a3b18a'
                            }
                        )
                        fig_stacked.update_layout(height=320, margin=dict(t=40, b=10, l=10, r=10), legend_title_text="Evidence Tier")
                        st.plotly_chart(fig_stacked, use_container_width=True)

                else:
                    st.info("Dates between estrus observations and THI records do not overlap. Ensure observation dates coincide with environmental logs.")
            else:
                st.info("No estrus observations found. Log estrus signs or load demo data to analyze reproductive sensitivity.")

            # -----------------------------------------------------------------
            # SECTION D: Dairy Science Decision Support & Heat Mitigation Protocols
            # -----------------------------------------------------------------
            st.markdown("##### 4. Clinical & Management Decision-Support Protocols")
            st.markdown("""
            <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin-top: 10px;">
                <h5 style="color: #1b4332; margin-top: 0;">🐄 Biological Understanding of "Silent Heat" under Heat Stress:</h5>
                <ul style="font-size: 0.9rem; color: #343a40; line-height: 1.6;">
                    <li><b>Physiological Suppression:</b> When THI reaches or exceeds 72, cows experience hyperthermia, elevating cortisol and inhibiting the pre-ovulatory surge of Luteinizing Hormone (LH) from the pituitary gland.</li>
                    <li><b>Shortened Standing Heat Duration:</b> Standing estrus duration is dramatically truncated from a normal <b>14–18 hours</b> down to as brief as <b>3–6 hours</b>, often occurring during the coolest hours of the night.</li>
                    <li><b>Subtle Signs Predominate:</b> Overt standing to be mounted is frequently absent; cows exhibit only secondary indicators such as restlessness, vulvar mucus, or increased walking.</li>
                </ul>
                <h5 style="color: #2d6a4f; margin-top: 12px;">📋 Actionable Recommendations for Herdsmen:</h5>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.88rem;">
                    <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #52b788;">
                        <b>🌙 Night-Time Estrus Observation:</b>
                        <br>Schedule visual checks or camera reviews between <b>10:00 PM and 4:00 AM</b> when ambient heat drops, as &gt;70% of mounting activity shifts to nighttime under heat stress.
                    </div>
                    <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #2d6a4f;">
                        <b>💧 Active Evaporative Cooling:</b>
                        <br>Operate high-velocity low-speed (HVLS) fans combined with cyclic sprinkler soaking (1–2 min soak every 10–15 min) in the holding yard and feed bunk.
                    </div>
                    <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #d4af37;">
                        <b>🌾 Nutritional Buffer Management:</b>
                        <br>Increase dietary energy density using rumen-inert bypass fats; shift 60% of total mixed ration (TMR) feeding to cooler evening hours to counteract daytime feed refusal.
                    </div>
                    <div style="background: #ffffff; padding: 12px; border-radius: 6px; border-left: 4px solid #e53e3e;">
                        <b>💉 Insemination Timing Adjustments:</b>
                        <br>Inseminate early in the morning before peak solar exposure. Provide chilled drinking water freely to protect ovum viability and early embryonic survival.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# MODULE 7: Milk Production Management
# ==========================================

def render_milk_production():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Milk Production Tracking & Yield Analytics</div>
            <div class="brand-tagline">Daily milk recording, morning/evening yields, individual cow histories, and drop alerts.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_record, tab_trends, tab_alerts = st.tabs([
        "➕ Log Daily Milking", "📈 Production Analytics & Comparisons", "🚨 Yield Drop Alerts"
    ])

    cows_df = database.get_all_cows()

    with tab_record:
        if cows_df.empty:
            st.warning("Please register cows first in Cow Management.")
            return

        with st.form("milk_log_form", clear_on_submit=True):
            m1, m2, m3 = st.columns(3)
            with m1:
                cow_choices = [f"{r['cow_id']} – {r['name']}" for _, r in cows_df.iterrows()]
                sel_cow = st.selectbox("Select Cow *", cow_choices, key="milk_cow_sel")
                cid = sel_cow.split(" – ")[0]
                prod_date = st.date_input("Milking Date *", value=date.today())
            with m2:
                morning_yield = st.number_input("Morning Yield (L)", min_value=0.0, max_value=50.0, value=12.0, step=0.5)
                evening_yield = st.number_input("Evening Yield (L)", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
            with m3:
                auto_total = round(morning_yield + evening_yield, 2)
                st.metric("Total Daily Yield (Auto-Calculated)", f"{auto_total} L")
                notes = st.text_input("Milking Notes", placeholder="e.g. Standard morning and evening shift")

            save_milk = st.form_submit_button("💾 Save Milk Record", use_container_width=True)
            if save_milk:
                rec = {
                    "cow_id": cid,
                    "production_date": prod_date.strftime("%Y-%m-%d"),
                    "morning_yield": morning_yield,
                    "evening_yield": evening_yield,
                    "total_yield": auto_total,
                    "notes": notes
                }
                database.add_milk_record(rec)
                st.success(f"Milk record logged for {cid}: {auto_total} Litres!")
                st.rerun()

    with tab_trends:
        st.markdown("#### Herd & Cow-Wise Milk Production Trends")
        milk_df = database.get_milk_records()
        if not milk_df.empty:
            f1, f2 = st.columns(2)
            with f1:
                f_cid = st.selectbox("Select Cow", ["All"] + sorted(list(milk_df['cow_id'].unique())), key="milk_f_cid")
            with f2:
                f_date = st.date_input("From Date", value=date.today() - timedelta(days=30))

            f_milk = milk_df.copy()
            f_milk = f_milk[f_milk['production_date'] >= f_date.strftime("%Y-%m-%d")]
            if f_cid != "All":
                f_milk = f_milk[f_milk['cow_id'] == f_cid]
                fig_m = px.bar(
                    f_milk.sort_values('production_date'), x='production_date', y=['morning_yield', 'evening_yield'],
                    title=f"Daily Milk Production Breakdown – {f_cid}",
                    barmode='stack',
                    color_discrete_sequence=['#52b788', '#2d6a4f']
                )
            else:
                herd_daily = f_milk.groupby('production_date')['total_yield'].sum().reset_index()
                fig_m = px.line(
                    herd_daily.sort_values('production_date'), x='production_date', y='total_yield',
                    title="Herd Aggregate Daily Milk Yield (Litres)",
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=['#2d6a4f']
                )
            fig_m.update_layout(xaxis_title="Date", yaxis_title="Yield (L)", height=380)
            st.plotly_chart(fig_m, use_container_width=True)

            st.dataframe(f_milk[['cow_id', 'production_date', 'morning_yield', 'evening_yield', 'total_yield', 'is_drop_alert', 'notes']], use_container_width=True, hide_index=True)
        else:
            st.info("No milk records logged yet.")

    with tab_alerts:
        st.markdown("#### 🚨 Unusual Milk Production Drop Indicators")
        milk_df = database.get_milk_records()
        if not milk_df.empty:
            drop_df = milk_df[milk_df['is_drop_alert'] == 1]
            if not drop_df.empty:
                st.markdown("""
                <div class="alert-card-danger">
                    <b>Attention:</b> The following cows had sudden yield drops (>25% below recent rolling average).
                    Sudden milk drop is a primary indicator of mastitis, systemic illness, or acute stress.
                </div>
                """, unsafe_allow_html=True)
                st.dataframe(drop_df[['cow_id', 'production_date', 'total_yield', 'notes']], use_container_width=True, hide_index=True)
            else:
                st.success("No critical yield drops flagged in the records.")
        else:
            st.info("No milk records available.")


# ==========================================
# MODULE 8: Reports and Analytics
# ==========================================

def render_reports_analytics():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Reports, Statistical Analytics & PDF Generation</div>
            <div class="brand-tagline">Export filtered herd records, statistical summaries, CSV exports, and printable ReportLab PDF reports.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    report_type = st.selectbox("Select Report Category", [
        "Overall Herd Summary Report",
        "Individual Cow Performance Report",
        "Estrus & Reproductive Cycle Report",
        "2-Hourly Sensor Telemetry & Estrus Detection Report",
        "Health Monitoring & Screening Report",
        "Environmental THI & Heat Stress Report",
        "Milk Production Tracking Report"
    ])

    cows_df = database.get_all_cows()
    estrus_df = database.get_estrus_observations()
    health_df = database.get_health_records()
    thi_df = database.get_thi_records()
    milk_df = database.get_milk_records()

    st.markdown("---")

    if report_type == "Overall Herd Summary Report":
        st.markdown("### 📋 Overall Herd Summary Report")
        kpis = database.get_dashboard_kpis()

        summary_dict = {
            "Total Cows Registered": kpis["total_cows"],
            "Active Milking Herd": kpis["active_cows"],
            "High Estrus Evidence Cows": kpis["high_estrus_count"],
            "Health Alerts Active": kpis["health_attention_count"],
            "Total Daily Milk (L)": kpis["total_daily_milk"],
            "Average Milk/Cow (L)": kpis["avg_daily_milk"],
            "Current THI Index": kpis["latest_thi"] or "N/A",
            "Upcoming Estrus (7d)": kpis["upcoming_estrus_count"]
        }

        # Show Table
        st.dataframe(cows_df, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Herd Registry CSV",
                data=cows_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_herd_summary_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            pdf_data = create_pdf_report(
                "Overall Herd Management Report",
                summary_dict,
                cows_df,
                "Comprehensive census of registered dairy cattle, reproductive statuses, and yield outputs."
            )
            st.download_button(
                "📄 Download Official PDF Report",
                data=pdf_data,
                file_name=f"bovisense_herd_report_{date.today().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    elif report_type == "Individual Cow Performance Report":
        st.markdown("### 🔍 Individual Cow Performance Report")
        if not cows_df.empty:
            c_list = [f"{r['cow_id']} – {r['name']}" for _, r in cows_df.iterrows()]
            sel_c = st.selectbox("Select Cow for Report", c_list)
            cid = sel_c.split(" – ")[0]
            c_info = database.get_cow(cid)
            c_milk = database.get_milk_records(cid)

            summary_dict = {
                "Cow ID": c_info['cow_id'],
                "Name": c_info['name'],
                "Breed": c_info['breed'],
                "Lactation Number": c_info['lactation_number'],
                "Daily Milk Yield (L)": c_info['daily_milk_production'],
                "Pregnancy Status": c_info['pregnancy_status'],
                "Health Status": c_info['health_status'],
                "Reproductive Status": c_info['reproductive_status']
            }

            st.write(f"Showing milk records for **{c_info['name']} ({c_info['cow_id']})**:")
            st.dataframe(c_milk, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Cow Milk CSV",
                    data=c_milk.to_csv(index=False).encode('utf-8'),
                    file_name=f"cow_{cid}_milk_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                pdf_data = create_pdf_report(
                    f"Individual Cow Profile & Performance – {c_info['name']} ({cid})",
                    summary_dict,
                    c_milk,
                    f"Individual biological and yield report for {c_info['name']}. Current status: {c_info['reproductive_status']}."
                )
                st.download_button(
                    "📄 Download Cow PDF Dossier",
                    data=pdf_data,
                    file_name=f"cow_{cid}_dossier_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("No cows available.")

    elif report_type == "Estrus & Reproductive Cycle Report":
        st.markdown("### 🎯 Estrus & Reproductive Cycle Report")
        if not estrus_df.empty:
            summary_dict = {
                "Total Observations": len(estrus_df),
                "High Evidence Events": len(estrus_df[estrus_df['evidence_category'] == 'High']),
                "Moderate Evidence Events": len(estrus_df[estrus_df['evidence_category'] == 'Moderate']),
                "Low Evidence Events": len(estrus_df[estrus_df['evidence_category'] == 'Low'])
            }
            st.dataframe(estrus_df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Estrus Observations CSV",
                    data=estrus_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"estrus_report_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                pdf_data = create_pdf_report(
                    "Estrus Detection & Reproductive Cycle Report",
                    summary_dict,
                    estrus_df,
                    "Rule-based estrus scoring audit and projected next-cycle windows."
                )
                st.download_button(
                    "📄 Download Estrus PDF Report",
                    data=pdf_data,
                    file_name=f"estrus_report_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("No estrus records available.")

    elif report_type == "2-Hourly Sensor Telemetry & Estrus Detection Report":
        st.markdown("### 📡 2-Hourly Sensor Telemetry & Estrus Detection Report")
        sensor_df = database.get_sensor_records()
        if not sensor_df.empty:
            analyzed = database.analyze_sensor_estrus(sensor_df)
            summary_dict = {
                "Total Sensor Intervals": len(analyzed),
                "Cows Monitored": analyzed['cow_id'].nunique(),
                "High Estrus Evidence Intervals": len(analyzed[analyzed['evidence_category'] == 'High']),
                "Moderate Evidence Intervals": len(analyzed[analyzed['evidence_category'] == 'Moderate']),
                "Average Herd Activity": round(analyzed['activity_index'].mean(), 1),
                "Average Rumination (min/2h)": round(analyzed['rumination_minutes'].mean(), 1)
            }
            disp_cols = ['cow_id', 'timestamp', 'activity_index', 'baseline_activity', 'activity_change_pct', 'rumination_minutes', 'baseline_rumination', 'rumination_change_pct', 'combined_evidence_score', 'evidence_category', 'explanation']
            st.dataframe(analyzed[disp_cols].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Sensor Predictions CSV",
                    data=analyzed[disp_cols].to_csv(index=False).encode('utf-8'),
                    file_name=f"sensor_report_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                pdf_table = analyzed[['cow_id', 'timestamp', 'activity_index', 'rumination_minutes', 'combined_evidence_score', 'evidence_category']].head(40)
                pdf_data = create_pdf_report(
                    "2-Hourly Sensor Biometrics & Estrus Detection Audit",
                    summary_dict,
                    pdf_table,
                    "Rule-based estrus detection using 2-hourly activity index and rumination telemetry with individual diurnal baselines."
                )
                st.download_button(
                    "📄 Download Sensor PDF Report",
                    data=pdf_data,
                    file_name=f"sensor_report_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("No sensor telemetry records available.")

    elif report_type == "Health Monitoring & Screening Report":
        st.markdown("### 🩺 Health Monitoring & Screening Report")
        if not health_df.empty:
            summary_dict = {
                "Total Health Logs": len(health_df),
                "Critical Alerts": len(health_df[health_df['health_status'] == 'Critical Alert']),
                "Minor Concerns": len(health_df[health_df['health_status'] == 'Minor Concern']),
                "Healthy Records": len(health_df[health_df['health_status'] == 'Healthy'])
            }
            st.dataframe(health_df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Health History CSV",
                    data=health_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"health_report_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                pdf_data = create_pdf_report(
                    "Herd Health Monitoring & Screening Report",
                    summary_dict,
                    health_df,
                    "Screening audit log of clinical temperatures, appetite logs, and abnormality flags."
                )
                st.download_button(
                    "📄 Download Health PDF Report",
                    data=pdf_data,
                    file_name=f"health_report_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("No health records available.")

    elif report_type == "Environmental THI & Heat Stress Report":
        st.markdown("### 🌡️ Environmental THI & Heat Stress Report")
        if not thi_df.empty:
            summary_dict = {
                "Total Readings": len(thi_df),
                "Average THI": round(thi_df['thi_value'].mean(), 1),
                "Peak THI": round(thi_df['thi_value'].max(), 1),
                "Severe Stress Incidents": len(thi_df[thi_df['heat_stress_category'] == 'Severe heat-stress concern'])
            }
            st.dataframe(thi_df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download THI Records CSV",
                    data=thi_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"thi_report_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                pdf_data = create_pdf_report(
                    "Environmental THI & Heat Stress Audit",
                    summary_dict,
                    thi_df,
                    "Historical ambient temperature and relative humidity recordings with calculated dairy THI classifications."
                )
                st.download_button(
                    "📄 Download THI PDF Report",
                    data=pdf_data,
                    file_name=f"thi_report_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("No THI records available.")

    elif report_type == "Milk Production Tracking Report":
        st.markdown("### 🥛 Milk Production Tracking Report")
        if not milk_df.empty:
            summary_dict = {
                "Total Milking Records": len(milk_df),
                "Total Volume (L)": round(milk_df['total_yield'].sum(), 1),
                "Average Yield/Milking": round(milk_df['total_yield'].mean(), 1),
                "Flagged Yield Drops": len(milk_df[milk_df['is_drop_alert'] == 1])
            }
            st.dataframe(milk_df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Milk Records CSV",
                    data=milk_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"milk_report_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                pdf_data = create_pdf_report(
                    "Herd Milk Production & Yield Report",
                    summary_dict,
                    milk_df,
                    "Recorded milk yields, morning/evening yields, and drop detection alerts."
                )
                st.download_button(
                    "📄 Download Milk PDF Report",
                    data=pdf_data,
                    file_name=f"milk_report_{date.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info("No milk records available.")


# ==========================================
# MODULE 9: Centralized CSV Import Center
# ==========================================

def render_csv_import_center():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">Centralized CSV Import Center</div>
            <div class="brand-tagline">Bulk data import, schema validation, foreign key checks, and row-by-row error logs across all 7 categories.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    category_labels = {
        "cows": "A. Cow Registration Registry",
        "estrus_observations": "B. Estrus Observations (Visual Markers)",
        "sensor_records": "C. 2-Hourly Sensor Telemetry (Activity & Rumination)",
        "health_records": "D. Health Monitoring Records",
        "disease_assessments": "E. Disease Screening Observations",
        "thi_records": "F. Environmental THI Records",
        "milk_records": "G. Milk Production Records",
        "reproductive_history": "H. Reproductive History Events"
    }

    sel_cat_key = st.selectbox(
        "Select CSV Import Category",
        list(category_labels.keys()),
        format_func=lambda k: category_labels[k]
    )

    schema_info = CSV_SCHEMAS[sel_cat_key]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"##### 1. Download Official Template for {category_labels[sel_cat_key]}")
        sample_df = schema_info["sample"]
        st.download_button(
            f"📥 Download {sel_cat_key}_template.csv",
            data=sample_df.to_csv(index=False).encode('utf-8'),
            file_name=f"{sel_cat_key}_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c2:
        st.markdown("##### Required Columns Specification")
        st.info(f"**Required:** {', '.join(schema_info['required'])} \n\n**Optional:** {', '.join(schema_info['optional'])}")

    st.markdown("---")
    st.markdown("##### 2. Upload CSV File for Ingestion")
    uploaded_file = st.file_uploader(f"Upload CSV for {category_labels[sel_cat_key]}", type=["csv"], key=f"uploader_{sel_cat_key}")

    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            st.write(f"File uploaded successfully: **{uploaded_file.name}** ({len(raw_df)} total rows).")
            st.markdown("###### Preview of Uploaded Data (First 5 Rows):")
            st.dataframe(raw_df.head(), use_container_width=True)

            # Retrieve existing cow IDs for FK validation
            all_cows = database.get_all_cows()
            existing_cids = set(all_cows['cow_id'].astype(str).str.strip()) if not all_cows.empty else set()

            valid_rows, rejected_rows = validate_csv_dataframe(raw_df, sel_cat_key, existing_cids)

            st.markdown("##### 3. Validation Summary & Quality Audit")
            v_col1, v_col2, v_col3 = st.columns(3)
            with v_col1:
                st.metric("Total Rows in CSV", len(raw_df))
            with v_col2:
                st.metric("Valid Rows Ready for Import", len(valid_rows))
            with v_col3:
                st.metric("Rejected / Invalid Rows", len(rejected_rows))

            if rejected_rows:
                st.markdown("""
                <div class="alert-card-warning">
                    <b>Validation Warnings Detected:</b> Some rows do not meet schema constraints or reference unknown Cow IDs.
                    You can inspect the row-specific errors below or download the rejected rows with error annotations.
                </div>
                """, unsafe_allow_html=True)
                rej_df = pd.DataFrame(rejected_rows)
                st.dataframe(rej_df, use_container_width=True)

                st.download_button(
                    "📥 Download Rejected Rows (with Error Explanations)",
                    data=rej_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"rejected_rows_{sel_cat_key}.csv",
                    mime="text/csv"
                )

            # Import confirmation
            if valid_rows:
                st.markdown("---")
                st.markdown("##### 4. Commit Valid Rows to Database")
                st.write(f"Click below to safely import **{len(valid_rows)}** valid records into SQLite table `{sel_cat_key}`.")

                if st.button("🚀 Confirm & Import Valid Rows", type="primary", use_container_width=True):
                    success_count = 0
                    dup_count = 0

                    for r in valid_rows:
                        try:
                            if sel_cat_key == "cows":
                                # Check duplicate cow_id
                                if database.get_cow(r["cow_id"]):
                                    dup_count += 1
                                else:
                                    database.add_cow(r)
                                    success_count += 1
                            elif sel_cat_key == "estrus_observations":
                                database.add_estrus_observation(r)
                                success_count += 1
                            elif sel_cat_key == "health_records":
                                database.add_health_record(r)
                                success_count += 1
                            elif sel_cat_key == "disease_assessments":
                                database.add_disease_assessment(r)
                                success_count += 1
                            elif sel_cat_key == "thi_records":
                                database.add_thi_record(r)
                                success_count += 1
                            elif sel_cat_key == "milk_records":
                                database.add_milk_record(r)
                                success_count += 1
                            elif sel_cat_key == "reproductive_history":
                                database.add_reproductive_event(r)
                                success_count += 1
                            elif sel_cat_key == "sensor_records":
                                ok, _ = database.add_sensor_record(r)
                                if ok:
                                    success_count += 1
                                else:
                                    dup_count += 1
                        except Exception as ex:
                            pass

                    # Log import history
                    database.log_csv_import(
                        uploaded_file.name,
                        sel_cat_key,
                        len(raw_df),
                        success_count,
                        len(rejected_rows),
                        dup_count,
                        "Completed",
                        f"Imported {success_count} rows, {dup_count} duplicates skipped."
                    )

                    st.success(f"🎉 Import complete! Successfully committed {success_count} records to `{sel_cat_key}` ({dup_count} duplicates prevented).")
                    st.rerun()
            else:
                st.error("No valid rows available to import. Please correct the CSV and re-upload.")

        except Exception as e:
            st.error(f"Failed to read CSV: {str(e)}")

    st.markdown("---")
    st.markdown("##### 📜 CSV Import Audit Log")
    history_df = database.get_csv_import_history()
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No prior CSV import sessions logged.")


# ==========================================
# MODULE 10: CSV Export & Backup Center
# ==========================================

def render_csv_export_backup():
    st.markdown("""
    <div class="brand-header">
        <div>
            <div class="brand-title">CSV Export & SQLite Database Backup Center</div>
            <div class="brand-tagline">Download persistent farm records, perform database snapshots, and restore backups.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_export, tab_backup = st.tabs(["📤 Bulk CSV Data Export", "💾 Database Snapshot & Restore"])

    with tab_export:
        st.markdown("#### One-Click CSV Data Downloads")
        st.write("Download current database tables as standard UTF-8 CSV spreadsheets.")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            cows_df = database.get_all_cows()
            st.download_button(
                "📥 Export Cow Registry CSV",
                data=cows_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_cows_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            estrus_df = database.get_estrus_observations()
            st.download_button(
                "📥 Export Estrus Observations CSV",
                data=estrus_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_estrus_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with c2:
            health_df = database.get_health_records()
            st.download_button(
                "📥 Export Health Records CSV",
                data=health_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_health_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            disease_df = database.get_disease_assessments()
            st.download_button(
                "📥 Export Disease Screenings CSV",
                data=disease_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_disease_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with c3:
            thi_df = database.get_thi_records()
            st.download_button(
                "📥 Export THI Weather CSV",
                data=thi_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_thi_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            milk_df = database.get_milk_records()
            st.download_button(
                "📥 Export Milk Records CSV",
                data=milk_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_milk_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with c4:
            sensor_df = database.get_sensor_records()
            st.download_button(
                "📥 Export Sensor Telemetry CSV",
                data=sensor_df.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_sensor_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

            analyzed_sensor = database.analyze_sensor_estrus(sensor_df)
            st.download_button(
                "📥 Export Sensor Predictions CSV",
                data=analyzed_sensor.to_csv(index=False).encode('utf-8'),
                file_name=f"bovisense_sensor_predictions_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with tab_backup:
        st.markdown("#### Database Snapshot & Restore")
        st.write("Create a binary SQLite snapshot of `bovisense.db` or restore from a previous backup file.")

        b1, b2 = st.columns(2)
        with b1:
            st.markdown("##### 1. Download Database Snapshot")
            if os.path.exists("bovisense.db"):
                with open("bovisense.db", "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    "💾 Download bovisense.db Backup",
                    data=db_bytes,
                    file_name=f"bovisense_backup_{date.today().strftime('%Y%m%d')}.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
            else:
                st.info("Database file not yet created.")

        with b2:
            st.markdown("##### 2. Restore Database from Backup File")
            uploaded_db = st.file_uploader("Upload .db Backup File", type=["db", "sqlite", "sqlite3"], key="db_restore_uploader")
            if uploaded_db is not None:
                st.warning("⚠️ Restoring a database file will replace all current tables and records.")
                confirm_restore = st.checkbox("I confirm replacing the current database")
                if st.button("🔄 Execute Database Restore", type="primary", use_container_width=True):
                    if confirm_restore:
                        with open("bovisense_temp_restore.db", "wb") as f:
                            f.write(uploaded_db.getbuffer())
                        ok = database.restore_database("bovisense_temp_restore.db", "bovisense.db")
                        if os.path.exists("bovisense_temp_restore.db"):
                            os.remove("bovisense_temp_restore.db")
                        if ok:
                            st.success("Database restored successfully!")
                            st.rerun()
                    else:
                        st.error("Please confirm the restore action above.")


# ==========================================
# Main Application Router
# ==========================================

def main():
    selected_page = render_sidebar()

    if selected_page == "Executive Dashboard":
        render_dashboard()
    elif selected_page == "Cow Management":
        render_cow_management()
    elif selected_page == "Estrus Prediction":
        render_estrus_prediction()
    elif selected_page == "Health Monitoring":
        render_health_monitoring()
    elif selected_page == "Disease Risk Assessment":
        render_disease_assessment()
    elif selected_page == "THI & Heat Stress":
        render_thi_analytics()
    elif selected_page == "Milk Production":
        render_milk_production()
    elif selected_page == "Reports & Analytics":
        render_reports_analytics()
    elif selected_page == "CSV Import Center":
        render_csv_import_center()
    elif selected_page == "CSV Export & Backup":
        render_csv_export_backup()


if __name__ == "__main__":
    main()
