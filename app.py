"""
BoviSense – Intelligent Dairy Cow Management and Monitoring Platform
app.py: Streamlit Web Interface, Navigation, Analytics, Visualizations & Reports
"""

import os
import io
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

database.init_db()

# Core CSS Styles
st.markdown("""
<style>
    :root {
        --forest-green: #1b4332;
        --accent-green: #2d6a4f;
        --light-green: #52b788;
        --gold: #d4af37;
    }
    .brand-header {
        background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%);
        padding: 20px 24px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .brand-title {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff;
        margin: 0;
    }
    .brand-tagline {
        font-size: 0.92rem;
        color: #b7e4c7;
        margin-top: 3px;
    }
    .demo-badge {
        background-color: #d4af37;
        color: #1b4332;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .kpi-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 14px 16px;
        border-left: 5px solid #2d6a4f;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        margin-bottom: 10px;
        border-top: 1px solid #edf2f7;
        border-right: 1px solid #edf2f7;
        border-bottom: 1px solid #edf2f7;
    }
    .kpi-title {
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: #1b4332;
        line-height: 1.2;
    }
    .kpi-subtitle {
        font-size: 0.76rem;
        color: #52b788;
        font-weight: 600;
        margin-top: 3px;
    }
    .alert-card-warning {
        background-color: #fffbeb;
        border-left: 5px solid #d4af37;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
        color: #92400e;
        font-size: 0.9rem;
    }
    .alert-card-danger {
        background-color: #fef2f2;
        border-left: 5px solid #e53e3e;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
        color: #991b1b;
        font-size: 0.9rem;
    }
    .alert-card-success {
        background-color: #f0fdf4;
        border-left: 5px solid #2d6a4f;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 12px;
        color: #166534;
        font-size: 0.9rem;
    }
    .section-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# Reusable UI Components & Helpers
# ==========================================

def ui_header(title, subtitle):
    """Render consistent page header with BoviSense agricultural styling."""
    st.markdown(f"""
    <div class="brand-header">
        <div>
            <div class="brand-title">{title}</div>
            <div class="brand-tagline">{subtitle}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def ui_kpi(col, title, value, subtitle=None, border_color="#2d6a4f"):
    """Render standard KPI card in a column."""
    sub_html = f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ''
    with col:
        st.markdown(f"""
        <div class="kpi-card" style="border-left-color: {border_color};">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            {sub_html}
        </div>
        """, unsafe_allow_html=True)


def ui_alert(message, alert_type="info"):
    """Render alert banner."""
    css_class = {
        "warning": "alert-card-warning",
        "danger": "alert-card-danger",
        "success": "alert-card-success"
    }.get(alert_type, "alert-card-warning")
    st.markdown(f'<div class="{css_class}">{message}</div>', unsafe_allow_html=True)


def ui_download_csv(label, df, filename, key=None):
    """Standardized one-click CSV download button."""
    if df is not None and not df.empty:
        st.download_button(
            label=label,
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
            key=key
        )


def ui_plotly_chart(fig, height=340):
    """Apply standardized layout and render Plotly figure."""
    fig.update_layout(
        height=height,
        margin=dict(t=35, b=15, l=15, r=15),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)


def select_cow(cows_df, label="Select Cow", key=None, add_all=False):
    """Shared helper to render cow selector dropdown and return (cow_id, cow_dict)."""
    if cows_df.empty:
        return None, None
    choices = [f"{r['cow_id']} – {r['name']} ({r['breed']})" for _, r in cows_df.iterrows()]
    if add_all:
        choices = ["All Cows"] + choices
    sel = st.selectbox(label, choices, key=key)
    if add_all and sel == "All Cows":
        return "All", None
    cid = sel.split(" – ")[0]
    return cid, database.get_cow(cid)


# ==========================================
# Domain Logic: Scoring & PDF Reporting
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
    Markers: Standing (30), Mounting (20), Mucus (20), Activity/Restlessness (15), Swollen Vulva (15).
    Max score: 100. Categories: Low (<35), Moderate (35-64), High (65-100).
    """
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

    unique_selected = list(dict.fromkeys(selected_markers))
    score = 0.0
    contributions = []

    for marker in unique_selected:
        if marker in REPRODUCTIVE_MARKER_WEIGHTS:
            pts = REPRODUCTIVE_MARKER_WEIGHTS[marker]
            score += pts
            contributions.append(f"{marker} (+{int(pts)} pts)")

    score = min(100.0, score)
    category = "High" if score >= 65.0 else ("Moderate" if score >= 35.0 else "Low")

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

    if score >= 65.0:
        explanation = "High estrus evidence observed. Strong combination of definitive primary standing heat and secondary physiological markers. High likelihood of receptivity for artificial insemination (A.M.–P.M. protocol)."
    elif score >= 35.0:
        explanation = "Moderate estrus evidence observed. Active secondary signs present without definitive standing heat. Intensify visual observation over next 12 hours."
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
    abnormal_appearance,
    abnormal_milk,
    digestive_signs,
    reproductive_signs
):
    """Evaluate health observations to produce rule-based disease risk screenings."""
    reasons = []

    # 1. Mastitis Risk
    mast_score = 0
    if udder_swelling: mast_score += 2
    if udder_pain: mast_score += 2
    if abnormal_appearance: mast_score += 1
    if abnormal_milk: mast_score += 3
    if milk_drop_pct >= 20.0: mast_score += 1

    if mast_score >= 4 or abnormal_milk:
        mast_risk = "High concern"
        reasons.append("Clinical mastitis signs detected (abnormal milk / acute udder inflammation)")
    elif mast_score >= 2 or udder_swelling:
        mast_risk = "Moderate concern"
        reasons.append("Mild udder inflammation or localized tenderness observed")
    else:
        mast_risk = "Low concern"

    # 2. Systemic Risk
    if body_temp >= 40.0:
        sys_risk = "High concern"
        reasons.append(f"High pyrexia (fever): {body_temp}°C")
    elif body_temp >= 39.5:
        sys_risk = "Moderate concern"
        reasons.append(f"Mild elevated temperature: {body_temp}°C")
    elif body_temp < 38.0:
        sys_risk = "Moderate concern"
        reasons.append(f"Hypothermia: {body_temp}°C")
    else:
        sys_risk = "Low concern"

    # 3. Digestive Risk
    dig_str = str(digestive_signs).lower()
    if any(k in dig_str for k in ["severe bloat", "watery diarrhea", "impacted", "ketosis"]):
        dig_risk = "High concern"
        reasons.append(f"Severe digestive symptoms: {digestive_signs}")
    elif any(k in dig_str for k in ["mild bloat", "loose dung", "reduced rumination", "off feed"]):
        dig_risk = "Moderate concern"
        reasons.append(f"Digestive upset: {digestive_signs}")
    else:
        dig_risk = "Low concern"

    # 4. Reproductive Risk
    rep_str = str(reproductive_signs).lower()
    if any(k in rep_str for k in ["foul vaginal", "purulent discharge", "metritis", "retained placenta", "prolapse"]):
        rep_risk = "High concern"
        reasons.append(f"Acute reproductive pathology: {reproductive_signs}")
    elif any(k in rep_str for k in ["cloudy discharge", "delayed lochia", "straining"]):
        rep_risk = "Moderate concern"
        reasons.append(f"Mild reproductive abnormality: {reproductive_signs}")
    else:
        rep_risk = "Low concern"

    if "High concern" in [mast_risk, sys_risk, dig_risk, rep_risk]:
        overall = "High concern"
        vet_rec = 1
    elif "Moderate concern" in [mast_risk, sys_risk, dig_risk, rep_risk]:
        overall = "Moderate concern"
        vet_rec = 0
    else:
        overall = "Low concern"
        vet_rec = 0

    rationale_str = "; ".join(reasons) if reasons else "All screened health parameters within normal reference ranges."
    return mast_risk, sys_risk, dig_risk, rep_risk, overall, rationale_str, vet_rec


def create_pdf_report(report_title, summary_dict, table_df, notes_text=""):
    """Generate a clean styled PDF document using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1b4332'), spaceAfter=4, fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#52b788'), spaceAfter=12, fontName='Helvetica')
    sec_style = ParagraphStyle('SecHead', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#2d6a4f'), spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#212529'))

    elements = [
        Paragraph("🐄 BOVISENSE – INTELLIGENT DAIRY MANAGEMENT", sub_style),
        Paragraph(report_title, title_style),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Persistent Farm Records", sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1b4332'), spaceAfter=10)
    ]

    if summary_dict:
        elements.append(Paragraph("Executive Summary Metrics", sec_style))
        sum_data = [[Paragraph(f"<b>{k}:</b>", body_style), Paragraph(str(v), body_style)] for k, v in summary_dict.items()]
        t_sum = Table(sum_data, colWidths=[200, 320])
        t_sum.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sum)
        elements.append(Spacer(1, 10))

    if notes_text:
        elements.append(Paragraph(f"<b>Advisory Notes:</b> {notes_text}", body_style))
        elements.append(Spacer(1, 10))

    if table_df is not None and not table_df.empty:
        elements.append(Paragraph("Detailed Observation Records", sec_style))
        pdf_df = table_df.head(45).copy()
        for col in pdf_df.columns:
            pdf_df[col] = pdf_df[col].astype(str).str.slice(0, 40)
        col_headers = [Paragraph(f"<b>{c}</b>", body_style) for c in pdf_df.columns]
        rows = [col_headers]
        for _, r in pdf_df.iterrows():
            rows.append([Paragraph(str(r[c]), body_style) for c in pdf_df.columns])
        col_w = max(40, int(540 / len(pdf_df.columns)))
        t_det = Table(rows, colWidths=[col_w] * len(pdf_df.columns))
        t_det.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d6a4f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_det)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# ==========================================
# CSV Schemas & Centralized Validation
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
        "optional": ["selected_markers", "standing_to_be_mounted", "mounting_behaviour", "clear_mucus_discharge", "increased_activity", "restlessness", "swollen_vulva", "notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "observation_date": "2026-02-01", "selected_markers": "Standing to Be Mounted, Clear Vaginal Mucus Discharge", "standing_to_be_mounted": 1, "mounting_behaviour": 0, "clear_mucus_discharge": 1, "increased_activity": 1, "restlessness": 1, "swollen_vulva": 1, "notes": "Active morning heat"},
            {"cow_id": "COW-102", "observation_date": "2026-02-01", "selected_markers": "Increased Activity / Restlessness", "standing_to_be_mounted": 0, "mounting_behaviour": 0, "clear_mucus_discharge": 0, "increased_activity": 1, "restlessness": 1, "swollen_vulva": 0, "notes": "Early proestrus signs"}
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
            {"cow_id": "COW-102", "timestamp": "2026-02-01 00:00", "activity_index": 30.0, "rumination_minutes": 52.0},
            {"cow_id": "COW-102", "timestamp": "2026-02-01 02:00", "activity_index": 27.5, "rumination_minutes": 60.0}
        ])
    },
    "health_records": {
        "required": ["cow_id", "observation_date", "body_temperature"],
        "optional": ["milk_production", "appetite", "feed_intake", "water_intake", "activity_level", "behaviour", "symptoms", "health_notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "observation_date": "2026-02-01", "body_temperature": 38.6, "milk_production": 26.5, "appetite": "Normal", "feed_intake": 18.0, "water_intake": 80.0, "activity_level": "Normal", "behaviour": "Normal", "symptoms": "None", "health_notes": "Healthy morning screening"},
            {"cow_id": "COW-102", "observation_date": "2026-02-01", "body_temperature": 39.8, "milk_production": 14.0, "appetite": "Reduced", "feed_intake": 10.0, "water_intake": 50.0, "activity_level": "Lethargic", "behaviour": "Dull", "symptoms": "Fever", "health_notes": "Needs check"}
        ])
    },
    "disease_assessments": {
        "required": ["cow_id", "assessment_date"],
        "optional": ["udder_swelling", "udder_pain", "abnormal_udder_appearance", "abnormal_milk", "elevated_temp", "reduced_yield", "digestive_symptoms", "reproductive_symptoms", "screening_notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "assessment_date": "2026-02-01", "udder_swelling": 0, "udder_pain": 0, "abnormal_udder_appearance": 0, "abnormal_milk": 0, "elevated_temp": 0, "reduced_yield": 0, "digestive_symptoms": "None", "reproductive_symptoms": "None", "screening_notes": "Routine inspection normal"},
            {"cow_id": "COW-111", "assessment_date": "2026-02-01", "udder_swelling": 1, "udder_pain": 1, "abnormal_udder_appearance": 1, "abnormal_milk": 1, "elevated_temp": 1, "reduced_yield": 1, "digestive_symptoms": "None", "reproductive_symptoms": "None", "screening_notes": "Clinical mastitis signs"}
        ])
    },
    "thi_records": {
        "required": ["observation_date", "observation_time", "ambient_temp", "relative_humidity"],
        "optional": ["notes"],
        "sample": pd.DataFrame([
            {"observation_date": "2026-02-01", "observation_time": "08:00", "ambient_temp": 22.5, "relative_humidity": 65.0, "notes": "Morning reading"},
            {"observation_date": "2026-02-01", "observation_time": "14:00", "ambient_temp": 32.0, "relative_humidity": 75.0, "notes": "Afternoon peak"}
        ])
    },
    "milk_records": {
        "required": ["cow_id", "production_date"],
        "optional": ["morning_yield", "evening_yield", "total_yield", "notes"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "production_date": "2026-02-01", "morning_yield": 15.0, "evening_yield": 12.5, "total_yield": 27.5, "notes": "Standard milking"},
            {"cow_id": "COW-102", "production_date": "2026-02-01", "morning_yield": 11.0, "evening_yield": 9.5, "total_yield": 20.5, "notes": "Standard milking"}
        ])
    },
    "reproductive_history": {
        "required": ["cow_id", "event_date", "event_type"],
        "optional": ["details", "technician_or_sire", "outcome"],
        "sample": pd.DataFrame([
            {"cow_id": "COW-101", "event_date": "2026-01-05", "event_type": "Estrus Observed", "details": "Standing heat", "technician_or_sire": "Staff", "outcome": "Logged"},
            {"cow_id": "COW-101", "event_date": "2026-01-06", "event_type": "Artificial Insemination", "details": "Straw HF-9042", "technician_or_sire": "Dr. Sharma", "outcome": "Success"}
        ])
    }
}


def validate_csv_dataframe(df, category, existing_cow_ids):
    """
    Validates CSV records with comprehensive integrity checks:
    - Required columns
    - Data type & ranges
    - Date & timestamp formatting
    - Foreign key / Unknown Cow ID detection
    - Duplicate detection (both within CSV and against SQLite)
    Never silently ignores errors; returns (valid_rows, rejected_rows).
    """
    schema = CSV_SCHEMAS.get(category)
    if not schema:
        return [], [{"error_reason": f"Unknown category: {category}"}]

    missing_cols = [c for c in schema["required"] if c not in df.columns]
    if missing_cols:
        return [], [{"error_reason": f"Missing mandatory columns: {', '.join(missing_cols)}"}]

    valid_rows = []
    rejected_rows = []
    seen_csv_keys = set()

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        errors = []

        # 1. Cow ID existence check
        cid = str(row_dict.get("cow_id", "")).strip()
        if "cow_id" in schema["required"]:
            if not cid or cid.lower() in ["nan", "none"]:
                errors.append("Empty Cow ID")
            elif category != "cows" and cid not in existing_cow_ids:
                errors.append(f"Unknown Cow ID '{cid}' – please register cow first")

        # 2. Date column checks
        for date_col in ["observation_date", "production_date", "event_date", "assessment_date", "dob", "last_calving_date"]:
            if date_col in row_dict and pd.notna(row_dict[date_col]) and str(row_dict[date_col]).strip():
                val = str(row_dict[date_col]).strip()[:10]
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                    row_dict[date_col] = val
                except ValueError:
                    errors.append(f"Invalid date format in '{date_col}' (expected YYYY-MM-DD, got '{val}')")

        # 3. Category-specific validation
        if category == "health_records":
            try:
                temp = float(row_dict.get("body_temperature"))
                if not (35.0 <= temp <= 45.0):
                    errors.append(f"Body temperature {temp}°C out of range (35.0–45.0°C)")
                row_dict["body_temperature"] = temp
            except (ValueError, TypeError):
                errors.append("Invalid or missing numerical body_temperature")

        elif category == "thi_records":
            try:
                temp = float(row_dict.get("ambient_temp"))
                if not (-20.0 <= temp <= 60.0):
                    errors.append(f"Ambient temperature {temp}°C out of range")
                row_dict["ambient_temp"] = temp
            except (ValueError, TypeError):
                errors.append("Invalid numerical ambient_temp")

            try:
                rh = float(row_dict.get("relative_humidity"))
                if not (0.0 <= rh <= 100.0):
                    errors.append(f"Relative humidity {rh}% must be 0–100%")
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
                    if t_val < 0: errors.append("Total milk yield cannot be negative")
                    row_dict["total_yield"] = t_val
            except (ValueError, TypeError):
                errors.append("Invalid numerical milk yield values")

        elif category == "sensor_records":
            ts_raw = row_dict.get("timestamp")
            parsed_ts = None
            if pd.isna(ts_raw) or not str(ts_raw).strip():
                errors.append("Missing timestamp")
            else:
                try:
                    p_dt = pd.to_datetime(str(ts_raw).strip())
                    parsed_ts = p_dt.strftime("%Y-%m-%d %H:%M")
                    row_dict["timestamp"] = parsed_ts
                except Exception:
                    errors.append(f"Invalid timestamp '{ts_raw}'. Expected 'YYYY-MM-DD HH:MM'")

            try:
                act = float(row_dict.get("activity_index"))
                if act < 0.0: errors.append(f"Activity index ({act}) cannot be negative")
                row_dict["activity_index"] = act
            except (ValueError, TypeError):
                errors.append("Invalid or non-numeric activity_index")

            try:
                rum = float(row_dict.get("rumination_minutes"))
                if not (0.0 <= rum <= 120.0):
                    errors.append(f"Rumination minutes ({rum}) out of bounds (must be 0–120 min)")
                row_dict["rumination_minutes"] = rum
            except (ValueError, TypeError):
                errors.append("Invalid or non-numeric rumination_minutes")

            # Duplicate detection for sensor records
            if parsed_ts and cid:
                pair = (cid, parsed_ts)
                if pair in seen_csv_keys:
                    errors.append(f"Duplicate reading in CSV for Cow {cid} at {parsed_ts}")
                else:
                    seen_csv_keys.add(pair)
                    if database.check_sensor_duplicate(cid, parsed_ts):
                        errors.append(f"Duplicate reading: Cow {cid} at {parsed_ts} already exists in database")

        if errors:
            row_dict["error_reason"] = " | ".join(errors)
            rejected_rows.append(row_dict)
        else:
            valid_rows.append(row_dict)

    return valid_rows, rejected_rows


# ==========================================
# Sidebar Navigation & Herd Controls
# ==========================================

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0 16px 0;">
            <div style="background-color: #1b4332; color: #ffffff; padding: 12px; border-radius: 8px; font-weight: 800; font-size: 1.35rem;">
                🐄 BOVISENSE
            </div>
            <div style="font-size: 0.8rem; color: #52b788; font-weight: 700; margin-top: 4px;">
                Intelligent Dairy Management
            </div>
        </div>
        """, unsafe_allow_html=True)

        modules = [
            "1. Executive Dashboard",
            "2. Cow Management",
            "3. Estrus Prediction",
            "4. Health Monitoring",
            "5. Disease Risk Assessment",
            "6. THI and Heat Stress Analytics",
            "7. Milk Production Management",
            "8. Reports and Analytics",
            "9. CSV Import Center",
            "10. CSV Export and Backup"
        ]
        selected_mod = st.radio("Navigation Menu", modules, label_visibility="collapsed")

        st.markdown("---")
        kpis = database.get_dashboard_kpis()
        st.markdown(f"""
        <div style="font-size:0.82rem; color:#475569; padding: 4px 6px;">
            <b>Registered Cows:</b> {kpis['total_cows']}<br>
            <b>Active Milking:</b> {kpis['active_cows']}<br>
            <b>High Estrus Alert:</b> {kpis['high_estrus_count']} cows<br>
            <b>Health Concerns:</b> {kpis['health_attention_count']}<br>
            <b>Current THI:</b> {kpis['latest_thi'] or 'N/A'} ({kpis['latest_thi_category']})
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<div style='font-size:0.8rem; font-weight:700; color:#1b4332; margin-bottom:6px;'>Demonstration Dataset</div>", unsafe_allow_html=True)
        if kpis['has_demo']:
            if st.button("🗑️ Clear Demo Data", use_container_width=True):
                database.clear_demo_data()
                st.success("Demo data cleared.")
                st.rerun()
        else:
            if st.button("🚀 Load Synthetic Demo Herd", type="primary", use_container_width=True):
                database.generate_demo_data()
                st.success("20 cows, vitals, milk & sensors loaded.")
                st.rerun()

    return selected_mod


# ==========================================
# MODULE 1: Executive Dashboard
# ==========================================

def render_dashboard():
    ui_header("Executive Herd Management Dashboard", "Holistic dairy cattle health, rule-based estrus detection, and biometeorological analytics.")
    kpis = database.get_dashboard_kpis()

    # Row 1 KPIs
    c1, c2, c3, c4 = st.columns(4)
    ui_kpi(c1, "Total Registered", f"{kpis['total_cows']}", "Registered Herd", "#1b4332")
    ui_kpi(c2, "Active Milking", f"{kpis['active_cows']}", "Productive Cattle", "#52b788")
    ui_kpi(c3, "High Estrus Candidates", f"{kpis['high_estrus_count']}", "Insemination Ready", "#d4af37")
    h_col = "#e53e3e" if kpis['health_attention_count'] > 0 else "#52b788"
    ui_kpi(c4, "Health Attention", f"{kpis['health_attention_count']}", "Requires Clinical Check", h_col)

    # Row 2 KPIs
    c5, c6, c7, c8 = st.columns(4)
    thi_disp = f"{kpis['latest_thi']:.1f}" if kpis['latest_thi'] else "N/A"
    thi_col = "#e53e3e" if kpis['thi_stress_active'] else "#2d6a4f"
    ui_kpi(c5, "Current THI", thi_disp, kpis['latest_thi_category'], thi_col)
    ui_kpi(c6, "Total Daily Milk", f"{kpis['total_daily_milk']} L", "Bulk Tank Today", "#2d6a4f")
    ui_kpi(c7, "Avg Milk / Cow", f"{kpis['avg_daily_milk']} L", "Daily Mean Yield", "#52b788")
    ui_kpi(c8, "Upcoming Estrus (7d)", f"{kpis['upcoming_estrus_count']}", "Expected Breeding Window", "#d4af37")

    # Real-Time Telemetry Surveillance Bar
    tot_sensors = kpis.get('total_sensor_records', 0)
    high_sensor_cows = kpis.get('sensor_high_estrus_count', 0)
    if tot_sensors > 0:
        status_txt = f"🚨 {high_sensor_cows} COWS IN ACTIVE ESTRUS SPIKE" if high_sensor_cows > 0 else "🟢 BASELINE STABLE"
        s_bg = "#d4af37" if high_sensor_cows > 0 else "#52b788"
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #1b4332 0%, #2d6a4f 100%); color: white; border-radius: 8px; padding: 10px 16px; margin: 8px 0 16px 0; display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:0.88rem;">
                <b>📡 2-Hourly Sensor Telemetry Surveillance:</b>
                <span style="opacity:0.9; margin-left:8px;"><b>{tot_sensors:,}</b> intervals logged &nbsp;|&nbsp; <b>{high_sensor_cows}</b> cows with acute behavioral divergence in last 48h</span>
            </div>
            <div style="background:{s_bg}; color:#1b4332; padding:3px 10px; border-radius:12px; font-weight:800; font-size:0.75rem;">{status_txt}</div>
        </div>
        """, unsafe_allow_html=True)

    if kpis['health_attention_count'] > 0:
        ui_alert("⚠️ <b>Health Alert Active:</b> One or more cows have fever, anorexia, or mastitis flags. Review Health Monitoring module.", "danger")
    if kpis['thi_stress_active']:
        ui_alert(f"🌡️ <b>Thermal Stress Advisory:</b> Current environmental THI ({kpis['latest_thi']}) is in <b>{kpis['latest_thi_category']}</b>. Activate barn fans, shade, and fresh drinking water.", "warning")

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
                b_df = cows_df['breed'].value_counts().reset_index()
                b_df.columns = ['Breed', 'Count']
                fig_b = px.pie(b_df, names='Breed', values='Count', title="Herd Breed Composition", color_discrete_sequence=px.colors.sequential.Greens_r, hole=0.45)
                ui_plotly_chart(fig_b, 280)
            else:
                st.info("No cows registered.")
        with v2:
            if not cows_df.empty:
                r_df = cows_df['reproductive_status'].value_counts().reset_index()
                r_df.columns = ['Status', 'Count']
                fig_r = px.bar(r_df, x='Status', y='Count', title="Reproductive Status Breakdown", color='Status', color_discrete_sequence=px.colors.qualitative.Prism)
                ui_plotly_chart(fig_r, 280)
        with v3:
            if not cows_df.empty:
                h_df = cows_df['health_status'].value_counts().reset_index()
                h_df.columns = ['Health', 'Count']
                c_map = {'Healthy': '#2d6a4f', 'Under Observation': '#f59f00', 'Sick': '#e53e3e', 'Quarantined': '#6c757d'}
                fig_h = px.pie(h_df, names='Health', values='Count', title="Herd Health Status", color='Health', color_discrete_map=c_map, hole=0.45)
                ui_plotly_chart(fig_h, 280)

    with tab2:
        m1, m2 = st.columns(2)
        with m1:
            if not milk_df.empty:
                m_daily = milk_df.groupby('production_date')['total_yield'].sum().reset_index()
                fig_m = px.line(m_daily.sort_values('production_date'), x='production_date', y='total_yield', title="Herd Daily Milk Volume (L)", markers=True, color_discrete_sequence=['#2d6a4f'])
                ui_plotly_chart(fig_m, 280)
            else:
                st.info("No milk records logged.")
        with m2:
            if not thi_df.empty:
                thi_sub = thi_df.head(60).copy().sort_values(['observation_date', 'observation_time'])
                fig_t = px.line(thi_sub, x='observation_date', y='thi_value', title="Recent THI Environmental Trajectory", markers=True, color_discrete_sequence=['#d4af37'])
                fig_t.add_hline(y=72, line_dash="dash", line_color="#e53e3e", annotation_text="Stress (≥72)")
                ui_plotly_chart(fig_t, 280)
            else:
                st.info("No THI records logged.")

    with tab3:
        w1, w2 = st.columns(2)
        with w1:
            st.markdown("##### 🚨 Cows Requiring Health Attention")
            if not cows_df.empty:
                attn = cows_df[cows_df['health_status'] != 'Healthy'][['cow_id', 'name', 'breed', 'health_status', 'daily_milk_production']]
                if not attn.empty:
                    st.dataframe(attn, use_container_width=True, hide_index=True)
                else:
                    st.success("All registered cows are currently healthy.")
        with w2:
            st.markdown("##### 📅 Upcoming Estimated Estrus Windows (7 Days)")
            if not estrus_df.empty:
                today_s = date.today().strftime("%Y-%m-%d")
                next_7 = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
                upc = estrus_df[(estrus_df['estimated_next_estrus'] >= today_s) & (estrus_df['estimated_next_estrus'] <= next_7)][['cow_id', 'estimated_next_estrus', 'evidence_category', 'cycle_stage']]
                if not upc.empty:
                    st.dataframe(upc.drop_duplicates(subset=['cow_id']), use_container_width=True, hide_index=True)
                else:
                    st.info("No estrus windows expected in immediate 7 days.")
            else:
                st.info("No estrus history.")

    with tab4:
        sensor_df = database.get_sensor_records()
        if not sensor_df.empty:
            analyzed_all = database.analyze_sensor_estrus(sensor_df)
            col_s1, col_s2 = st.columns([1.3, 1])
            with col_s1:
                st.markdown("##### 🚨 Active Sensor Estrus Alerts (Last 48h)")
                two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
                recent_spikes = analyzed_all[(analyzed_all['timestamp'] >= two_days_ago) & (analyzed_all['evidence_category'] == 'High')].sort_values('timestamp', ascending=False)
                if not recent_spikes.empty:
                    st.dataframe(recent_spikes[['cow_id', 'timestamp', 'activity_index', 'activity_change_pct', 'rumination_minutes', 'rumination_change_pct', 'combined_evidence_score', 'explanation']], use_container_width=True, hide_index=True)
                else:
                    st.info("No high-evidence sensor estrus spikes in the last 48 hours.")
            with col_s2:
                st.markdown("""
                <div style="background:#f8fafc; border-left:4px solid #2d6a4f; padding:12px; border-radius:6px; font-size:0.85rem; color:#334155;">
                    <b>Contextual Analytics Principles:</b><br>
                    • <b>THI Impact:</b> High THI (≥72) blunts visual activity. Sensor nighttime spikes catch silent heats.<br>
                    • <b>Milk Fluctuation:</b> Acute estrus restlessness often induces a temporary 10–25% daily milk drop.<br>
                    • <b>Disease Separation:</b> Sensor deviations provide behavioral insight, not clinical diagnoses.
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No sensor records available. Ingest sensor CSV in Import Center or load demo data.")


# ==========================================
# MODULE 2: Cow Management
# ==========================================

def render_cow_management():
    ui_header("Cow Management & Registry", "Livestock census, profile dossiers, lactation trajectories, and reproductive histories.")
    cows_df = database.get_all_cows()

    tab_list, tab_add, tab_profile, tab_edit = st.tabs([
        "📋 Herd Registry & Filter", "➕ Add New Cow", "🔍 Individual Cow Profile", "✏️ Edit / Delete Cow"
    ])

    with tab_list:
        if not cows_df.empty:
            f1, f2, f3 = st.columns(3)
            with f1: q_search = st.text_input("Search Cow ID or Name", "")
            with f2: sel_breed = st.selectbox("Filter Breed", ["All"] + sorted(cows_df['breed'].unique().tolist()))
            with f3: sel_rep = st.selectbox("Filter Reproductive Status", ["All"] + sorted(cows_df['reproductive_status'].unique().tolist()))

            f_df = cows_df.copy()
            if q_search:
                f_df = f_df[f_df['cow_id'].str.contains(q_search, case=False) | f_df['name'].str.contains(q_search, case=False)]
            if sel_breed != "All": f_df = f_df[f_df['breed'] == sel_breed]
            if sel_rep != "All": f_df = f_df[f_df['reproductive_status'] == sel_rep]

            st.dataframe(f_df[['cow_id', 'name', 'breed', 'age', 'weight', 'lactation_number', 'daily_milk_production', 'pregnancy_status', 'health_status', 'reproductive_status']], use_container_width=True, hide_index=True)
            ui_download_csv("📥 Download Filtered Registry CSV", f_df, f"bovisense_cows_{date.today().strftime('%Y%m%d')}.csv")
        else:
            st.info("No cows registered yet.")

    with tab_add:
        with st.form("add_cow_form", clear_on_submit=True):
            st.markdown("##### Register New Dairy Cow")
            c1, c2, c3 = st.columns(3)
            with c1:
                cid = st.text_input("Cow ID *", placeholder="e.g. COW-121")
                name = st.text_input("Cow Name *", placeholder="e.g. Daisy")
                breed = st.selectbox("Breed", ["Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss", "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred", "Other"])
            with c2:
                dob = st.date_input("Date of Birth", value=date.today() - timedelta(days=365*3))
                weight = st.number_input("Weight (kg)", min_value=100.0, max_value=1200.0, value=520.0, step=10.0)
                lactation = st.number_input("Lactation Number", min_value=1, max_value=15, value=2, step=1)
            with c3:
                daily_milk = st.number_input("Daily Milk Production (L)", min_value=0.0, max_value=80.0, value=22.0, step=0.5)
                preg_status = st.selectbox("Pregnancy Status", ["Open", "Inseminated", "Pregnant", "Unknown"])
                health_status = st.selectbox("Health Status", ["Healthy", "Under Observation", "Sick", "Quarantined"])
            remarks = st.text_input("Remarks", placeholder="Pedigree or management notes")

            if st.form_submit_button("💾 Save Cow to Database", type="primary", use_container_width=True):
                if not cid.strip() or not name.strip():
                    st.error("Cow ID and Name are mandatory.")
                elif database.get_cow(cid.strip()):
                    st.error(f"Cow ID '{cid.strip()}' already exists.")
                else:
                    payload = {
                        "cow_id": cid.strip(), "name": name.strip(), "breed": breed,
                        "dob": dob.strftime("%Y-%m-%d"), "weight": weight, "lactation_number": lactation,
                        "daily_milk_production": daily_milk, "pregnancy_status": preg_status,
                        "health_status": health_status, "reproductive_status": preg_status, "remarks": remarks
                    }
                    database.add_cow(payload)
                    st.success(f"Cow {cid.strip()} registered successfully!")
                    st.rerun()

    with tab_profile:
        if not cows_df.empty:
            sel_cid, cow_info = select_cow(cows_df, label="Select Cow for Dossier Inspection", key="profile_cow_sel")
            if cow_info:
                st.markdown(f"""
                <div class="section-box">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0; color:#1b4332;">{cow_info['name']} ({cow_info['cow_id']})</h3>
                            <div style="color:#52b788; font-weight:600;">{cow_info['breed']} | Lactation #{cow_info['lactation_number']}</div>
                        </div>
                        <div>
                            <span class="demo-badge" style="background:{'#2d6a4f' if cow_info['health_status']=='Healthy' else '#e53e3e'}; color:white;">{cow_info['health_status']}</span>
                            <span class="demo-badge" style="margin-left:6px;">{cow_info['reproductive_status']}</span>
                        </div>
                    </div>
                    <hr style="margin:10px 0;">
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-size:0.86rem;">
                        <div><b>Age:</b> {cow_info['age']} yrs</div>
                        <div><b>Weight:</b> {cow_info['weight']} kg</div>
                        <div><b>Yield:</b> {cow_info['daily_milk_production']} L/day</div>
                        <div><b>Pregnancy:</b> {cow_info['pregnancy_status']}</div>
                        <div><b>Last Calved:</b> {cow_info['last_calving_date'] or 'N/A'}</div>
                        <div><b>Last Estrus:</b> {cow_info['last_observed_estrus_date'] or 'N/A'}</div>
                        <div><b>Last AI:</b> {cow_info['last_insemination_date'] or 'N/A'}</div>
                        <div><b>Registered:</b> {cow_info['created_at'][:10] if cow_info['created_at'] else 'N/A'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                h_tab1, h_tab2, h_tab3, h_tab4, h_tab5 = st.tabs([
                    "🥛 Milk History", "🎯 Estrus Observations", "📡 Sensor Telemetry", "🩺 Health History", "📜 Reproductive Events"
                ])
                with h_tab1:
                    c_milk = database.get_milk_records(sel_cid)
                    if not c_milk.empty:
                        fig_cm = px.line(c_milk.sort_values('production_date'), x='production_date', y=['morning_yield', 'evening_yield', 'total_yield'], title=f"Milk Yield Trajectory – {cow_info['name']}", markers=True, color_discrete_sequence=['#52b788', '#d4af37', '#1b4332'])
                        ui_plotly_chart(fig_cm, 270)
                        st.dataframe(c_milk[['production_date', 'morning_yield', 'evening_yield', 'total_yield', 'is_drop_alert', 'notes']], use_container_width=True, hide_index=True)
                    else: st.info("No milk records logged.")

                with h_tab2:
                    c_estrus = database.get_estrus_observations(sel_cid)
                    if not c_estrus.empty:
                        cols = [c for c in ['observation_date', 'selected_markers', 'estrus_score', 'evidence_category', 'cycle_stage', 'estimated_next_estrus', 'score_reasons'] if c in c_estrus.columns]
                        st.dataframe(c_estrus[cols], use_container_width=True, hide_index=True)
                    else: st.info("No manual estrus observations recorded.")

                with h_tab3:
                    c_sensors = database.get_sensor_records(sel_cid)
                    if not c_sensors.empty:
                        c_analysis = database.analyze_sensor_estrus(c_sensors)
                        k1, k2, k3, k4 = st.columns(4)
                        ui_kpi(k1, "2-Hr Observations", f"{len(c_analysis)}", "Telemetry Ingested")
                        ui_kpi(k2, "Avg Activity", f"{c_analysis['activity_index'].mean():.1f}", "Sensor Units")
                        ui_kpi(k3, "Avg Rumination", f"{c_analysis['rumination_minutes'].mean():.1f}m", "Per 2h Interval")
                        latest_sc = c_analysis.iloc[-1]['combined_evidence_score']
                        latest_cat = c_analysis.iloc[-1]['evidence_category']
                        ui_kpi(k4, "Latest Sensor Estrus", f"{latest_sc}/100", latest_cat, "#d4af37" if latest_cat == "High" else "#2d6a4f")

                        # Trajectory line
                        fig_tel = px.line(c_analysis.sort_values('timestamp_dt'), x='timestamp_dt', y=['activity_index', 'rumination_minutes'], title=f"2-Hourly Activity & Rumination Telemetry – {cow_info['name']}", color_discrete_sequence=['#2d6a4f', '#2b6cb0'])
                        ui_plotly_chart(fig_tel, 270)

                        # Corroboration Callout
                        has_manual_h = not c_estrus.empty and len(c_estrus[c_estrus['evidence_category'] == 'High']) > 0
                        has_sensor_h = len(c_analysis[c_analysis['evidence_category'] == 'High']) > 0
                        if has_manual_h and has_sensor_h:
                            ui_alert("🎯 <b>Dual-Source Corroboration Confirmed:</b> Both manual visual signs and 2-hourly sensor telemetry exhibit concurrent high evidence. Optimal breeding candidate.", "success")
                        elif has_sensor_h and not has_manual_h:
                            ui_alert("📡 <b>Sensor-Detected Silent Heat / Subestrus:</b> Significant activity surge and rumination crash recorded without visual standing heat logged.", "warning")

                        st.dataframe(c_analysis[['timestamp', 'activity_index', 'baseline_activity', 'activity_change_pct', 'rumination_minutes', 'baseline_rumination', 'rumination_change_pct', 'combined_evidence_score', 'evidence_category', 'explanation']].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
                    else: st.info("No sensor telemetry records uploaded for this cow.")

                with h_tab4:
                    c_health = database.get_health_records(sel_cid)
                    if not c_health.empty:
                        st.dataframe(c_health[['observation_date', 'body_temperature', 'milk_production', 'appetite', 'activity_level', 'health_status', 'symptoms']], use_container_width=True, hide_index=True)
                    else: st.info("No health records recorded.")

                with h_tab5:
                    c_rep = database.get_reproductive_history(sel_cid)
                    if not c_rep.empty:
                        st.dataframe(c_rep[['event_date', 'event_type', 'details', 'technician_or_sire', 'outcome']], use_container_width=True, hide_index=True)
                    else: st.info("No reproductive events logged.")
        else:
            st.info("No cows available.")

    with tab_edit:
        if not cows_df.empty:
            edit_cid, c_data = select_cow(cows_df, label="Select Cow to Modify or Remove", key="cow_edit_sel")
            if c_data:
                with st.form("edit_cow_form"):
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        n_name = st.text_input("Name", value=c_data['name'])
                        n_breed = st.selectbox("Breed", ["Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss", "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred", "Other"], index=0 if c_data['breed'] not in ["Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss", "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred"] else ["Holstein Friesian", "Jersey", "Ayrshire", "Brown Swiss", "Guernsey", "Gir", "Sahiwal", "Red Sindhi", "Crossbred", "Other"].index(c_data['breed']))
                    with e2:
                        n_lact = st.number_input("Lactation #", value=int(c_data['lactation_number'] or 1), step=1)
                        n_milk = st.number_input("Daily Yield (L)", value=float(c_data['daily_milk_production'] or 20.0), step=0.5)
                    with e3:
                        n_preg = st.selectbox("Pregnancy Status", ["Open", "Inseminated", "Pregnant", "Unknown"], index=["Open", "Inseminated", "Pregnant", "Unknown"].index(c_data['pregnancy_status']) if c_data['pregnancy_status'] in ["Open", "Inseminated", "Pregnant", "Unknown"] else 0)
                        n_rep = st.selectbox("Reproductive Status", ["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"], index=["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"].index(c_data['reproductive_status']) if c_data['reproductive_status'] in ["Open", "In Heat", "Inseminated", "Confirmed Pregnant", "Calved", "Dry"] else 0)
                    n_rem = st.text_input("Remarks", value=c_data['remarks'] or "")

                    if st.form_submit_button("💾 Update Cow Record", use_container_width=True):
                        up_payload = {"name": n_name.strip(), "breed": n_breed, "dob": c_data['dob'], "age": c_data['age'], "weight": c_data['weight'], "lactation_number": n_lact, "daily_milk_production": n_milk, "last_calving_date": c_data['last_calving_date'], "last_observed_estrus_date": c_data['last_observed_estrus_date'], "last_insemination_date": c_data['last_insemination_date'], "pregnancy_status": n_preg, "health_status": c_data['health_status'], "reproductive_status": n_rep, "remarks": n_rem}
                        database.update_cow(edit_cid, up_payload)
                        st.success(f"Cow {edit_cid} updated.")
                        st.rerun()

                st.markdown("---")
                if st.button("🗑️ Delete This Cow Record", type="secondary"):
                    database.delete_cow(edit_cid)
                    st.warning(f"Cow {edit_cid} removed from database.")
                    st.rerun()


# ==========================================
# MODULE 3: Estrus Prediction
# ==========================================

def render_estrus_prediction():
    ui_header("Rule-Based Estrus Prediction & Reproductive Tracking", "Multi-sign visual scoring, 2-hourly activity/rumination biometrics, and breeding window forecast.")
    cows_df = database.get_all_cows()

    tab_eval, tab_hist, tab_bulk, tab_sensor = st.tabs([
        "🎯 Record & Evaluate Observation", "📜 Estrus Observation History", "📥 Bulk CSV Estrus Screening", "📡 2-Hourly Sensor Prediction"
    ])

    with tab_eval:
        if cows_df.empty:
            st.warning("Please register cows in Cow Management first.")
            return

        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.markdown("##### 1. Select Observed Reproductive Markers")
            sel_cid, cow_data = select_cow(cows_df, label="Target Cow *", key="estrus_eval_cow")
            obs_date = st.date_input("Observation Date", value=date.today())

            selected_markers = st.multiselect(
                "Select Reproductive Markers / Estrus Signs *",
                options=REPRODUCTIVE_MARKERS,
                default=[],
                help="Select all signs observed during turnout or visual inspection."
            )
            notes = st.text_area("Optional Remarks / Clinical Notes", placeholder="e.g. Observed during morning turnout; clear mucous discharge")

        with c2:
            st.markdown("##### 2. Rule-Based Estrus Evidence & Cycle Stage")
            days_estrus = None
            if cow_data and cow_data.get('last_observed_estrus_date'):
                try:
                    d_prev = datetime.strptime(str(cow_data['last_observed_estrus_date'])[:10], "%Y-%m-%d").date()
                    days_estrus = (obs_date - d_prev).days
                except Exception:
                    days_estrus = None

            score, category, stage, contributions, explanation = calculate_estrus_score(
                selected_markers=selected_markers,
                days_since_last_estrus=days_estrus
            )

            badge_col = "#2d6a4f" if category == "High" else ("#d4af37" if category == "Moderate" else "#6c757d")
            st.markdown(f"""
            <div class="section-box" style="border-top: 5px solid {badge_col};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.1rem; font-weight:700; color:#1b4332;">Estrus Evidence Score</span>
                    <span class="demo-badge" style="background:{badge_col}; color:white; font-size:0.95rem;">
                        {category} Evidence ({score}/100)
                    </span>
                </div>
                <div style="margin:12px 0; background:#e2e8f0; border-radius:10px; height:14px; overflow:hidden;">
                    <div style="background:{badge_col}; height:100%; width:{min(score, 100)}%;"></div>
                </div>
                <div style="font-size:0.88rem; line-height:1.5;">
                    <b>Cycle Stage:</b> <span style="color:#1b4332; font-weight:700;">{stage}</span><br>
                    <b>Days Since Last Estrus:</b> {days_estrus if days_estrus is not None else 'Unknown'}<br>
                    <b>Estimated Next Window:</b> {(obs_date + timedelta(days=21)).strftime('%Y-%m-%d')} (±2 days)
                </div>
            </div>
            """, unsafe_allow_html=True)

            if contributions:
                st.markdown("**Marker Contributions:** " + " &nbsp;|&nbsp; ".join([f"✅ <b>{c}</b>" for c in contributions]), unsafe_allow_html=True)
            else:
                st.caption("ℹ️ No reproductive markers selected. Baseline observation (0/100).")

            st.markdown(f"""
            <div style="background:#f8f9fa; border-left:4px solid {badge_col}; padding:8px 12px; border-radius:6px; font-size:0.85rem; margin:8px 0;">
                <b>Result Explanation:</b> {explanation}
            </div>
            """, unsafe_allow_html=True)

            if st.button("💾 Save Estrus Observation Record", type="primary", use_container_width=True):
                next_e = (obs_date + timedelta(days=21)).strftime("%Y-%m-%d")
                rec = {
                    "cow_id": sel_cid, "observation_date": obs_date.strftime("%Y-%m-%d"),
                    "selected_markers": selected_markers,
                    "standing_to_be_mounted": 1 if "Standing to Be Mounted" in selected_markers else 0,
                    "mounting_behaviour": 1 if "Mounting Other Cows" in selected_markers else 0,
                    "clear_mucus_discharge": 1 if "Clear Vaginal Mucus Discharge" in selected_markers else 0,
                    "increased_activity": 1 if "Increased Activity / Restlessness" in selected_markers else 0,
                    "restlessness": 1 if "Increased Activity / Restlessness" in selected_markers else 0,
                    "swollen_vulva": 1 if "Vulval Swelling and Redness" in selected_markers else 0,
                    "estrus_score": score, "evidence_category": category, "cycle_stage": stage,
                    "estimated_next_estrus": next_e, "score_reasons": " | ".join(contributions), "notes": notes
                }
                database.add_estrus_observation(rec)
                st.success(f"Estrus observation saved for {sel_cid}! Evidence: {category} ({score}/100).")
                st.rerun()

    with tab_hist:
        estrus_df = database.get_estrus_observations()
        if not estrus_df.empty:
            f1, f2 = st.columns(2)
            with f1: filter_cid = st.selectbox("Filter Cow", ["All"] + sorted(estrus_df['cow_id'].unique().tolist()), key="estrus_hist_cid")
            with f2: filter_cat = st.selectbox("Filter Category", ["All", "High", "Moderate", "Low"], key="estrus_hist_cat")

            f_df = estrus_df.copy()
            if filter_cid != "All": f_df = f_df[f_df['cow_id'] == filter_cid]
            if filter_cat != "All": f_df = f_df[f_df['evidence_category'] == filter_cat]

            cols = ['cow_id', 'observation_date', 'selected_markers', 'estrus_score', 'evidence_category', 'cycle_stage', 'estimated_next_estrus', 'score_reasons']
            st.dataframe(f_df[cols], use_container_width=True, hide_index=True)
            ui_download_csv("📥 Download Estrus History CSV", f_df[cols], f"estrus_history_{date.today().strftime('%Y%m%d')}.csv")
        else:
            st.info("No estrus observations logged yet.")

    with tab_bulk:
        st.markdown("##### Bulk CSV Estrus Scoring & Batch Prediction")
        sample_csv = CSV_SCHEMAS["estrus_observations"]["sample"]
        st.download_button("📥 Download Estrus Observations CSV Template", data=sample_csv.to_csv(index=False).encode('utf-8'), file_name="estrus_template.csv", mime="text/csv")

        up_file = st.file_uploader("Upload Estrus Observation CSV", type=["csv"], key="bulk_estrus_up")
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
                        raw_m = r.get("selected_markers")
                        m_list = str(raw_m).strip() if pd.notna(raw_m) and str(raw_m).strip().lower() != "nan" else None
                        stnd = int(r.get("standing_to_be_mounted", 0)) if pd.notna(r.get("standing_to_be_mounted")) else 0
                        mnt = int(r.get("mounting_behaviour", 0)) if pd.notna(r.get("mounting_behaviour")) else 0
                        muc = int(r.get("clear_mucus_discharge", 0)) if pd.notna(r.get("clear_mucus_discharge")) else 0
                        rest = int(r.get("restlessness", 0)) if pd.notna(r.get("restlessness")) else 0
                        act = int(r.get("increased_activity", 0)) if pd.notna(r.get("increased_activity")) else 0
                        vul = int(r.get("swollen_vulva", 0)) if pd.notna(r.get("swollen_vulva")) else 0

                        sc, cat, stg, contribs, expl = calculate_estrus_score(
                            selected_markers=m_list, standing_to_be_mounted=bool(stnd),
                            mounting_behaviour=bool(mnt), clear_mucus_discharge=bool(muc),
                            restlessness=bool(rest), increased_activity=bool(act), swollen_vulva=bool(vul)
                        )
                        next_dt = (datetime.strptime(o_date[:10], "%Y-%m-%d") + timedelta(days=21)).strftime("%Y-%m-%d")
                        processed.append({
                            "cow_id": cid, "observation_date": o_date,
                            "selected_markers": ", ".join([c.split(" (+")[0] for c in contribs]) if contribs else "None",
                            "estrus_score": sc, "evidence_category": cat, "cycle_stage": stg,
                            "estimated_next_estrus": next_dt, "score_reasons": " | ".join(contribs), "explanation": expl
                        })
                    res_df = pd.DataFrame(processed)
                    st.success("Batch predictions computed successfully!")
                    st.dataframe(res_df, use_container_width=True)
                    ui_download_csv("📥 Download Calculated Predictions CSV", res_df, "estrus_predictions_output.csv")
            except Exception as e:
                st.error(f"Error processing CSV: {str(e)}")

    with tab_sensor:
        st.markdown("##### 📡 2-Hourly Sensor Telemetry Estrus Prediction")
        st.write("Analyzes continuous 2-hour observation intervals of Activity Index and Rumination Time against each cow's historical diurnal baseline.")

        with st.expander("⚙️ Algorithm Parameters & Thresholds", expanded=False):
            tc1, tc2, tc3 = st.columns(3)
            with tc1: cfg_act = st.slider("Activity Increase Threshold (%)", 15.0, 80.0, 35.0, 5.0)
            with tc2: cfg_rum = st.slider("Rumination Drop Threshold (%)", 10.0, 60.0, 25.0, 5.0)
            with tc3: cfg_min = st.number_input("Minimum Baseline Intervals", 6, 168, 24, 6)

        all_sensors = database.get_sensor_records()
        if not all_sensors.empty:
            cows_with_s = sorted(all_sensors['cow_id'].unique().tolist())
            f1, f2, f3 = st.columns([1.5, 1.5, 1])
            with f1: s_cow = st.selectbox("Select Cow for Telemetry", ["All Cows"] + cows_with_s, key="s_tab_cow")
            with f2: s_period = st.selectbox("Timeline Filter", ["Last 14 Days", "Last 7 Days", "Last 30 Days", "All History"], index=0, key="s_tab_period")
            with f3: s_cat = st.selectbox("Evidence Level", ["All Levels", "High Only", "Moderate & High", "Insufficient Data"], key="s_tab_cat")

            active_s = all_sensors if s_cow == "All Cows" else all_sensors[all_sensors['cow_id'] == s_cow]
            analyzed_df = database.analyze_sensor_estrus(active_s, min_baseline_intervals=int(cfg_min), activity_threshold_pct=float(cfg_act), rumination_drop_pct=float(cfg_rum))

            if not analyzed_df.empty:
                max_dt = analyzed_df['timestamp_dt'].max()
                if s_period == "Last 7 Days": analyzed_df = analyzed_df[analyzed_df['timestamp_dt'] >= (max_dt - timedelta(days=7))]
                elif s_period == "Last 14 Days": analyzed_df = analyzed_df[analyzed_df['timestamp_dt'] >= (max_dt - timedelta(days=14))]
                elif s_period == "Last 30 Days": analyzed_df = analyzed_df[analyzed_df['timestamp_dt'] >= (max_dt - timedelta(days=30))]

                if s_cat == "High Only": analyzed_df = analyzed_df[analyzed_df['evidence_category'] == 'High']
                elif s_cat == "Moderate & High": analyzed_df = analyzed_df[analyzed_df['evidence_category'].isin(['High', 'Moderate'])]
                elif s_cat == "Insufficient Data": analyzed_df = analyzed_df[analyzed_df['evidence_category'] == 'Insufficient Data']

            if not analyzed_df.empty:
                k1, k2, k3, k4 = st.columns(4)
                ui_kpi(k1, "Observations", f"{len(analyzed_df):,}", "2-Hour Blocks")
                ui_kpi(k2, "Cows Evaluated", f"{analyzed_df['cow_id'].nunique()}")
                n_high = len(analyzed_df[analyzed_df['evidence_category'] == 'High'])
                ui_kpi(k3, "High Evidence (≥70)", f"{n_high}", "Probable Estrus Spikes", "#e53e3e" if n_high > 0 else "#2d6a4f")
                n_mod = len(analyzed_df[analyzed_df['evidence_category'] == 'Moderate'])
                ui_kpi(k4, "Moderate (40–69)", f"{n_mod}", "Watchlist Signals", "#d4af37")

                if s_cow != "All Cows":
                    c_disp = analyzed_df.sort_values('timestamp_dt')
                    fig_act = px.line(c_disp, x='timestamp_dt', y=['activity_index', 'baseline_activity'], title=f"Activity Telemetry vs Diurnal Baseline ({s_cow})", color_discrete_sequence=['#2d6a4f', '#52b788'])
                    ui_plotly_chart(fig_act, 260)

                    fig_rum = px.line(c_disp, x='timestamp_dt', y=['rumination_minutes', 'baseline_rumination'], title=f"Rumination Minutes vs Diurnal Baseline ({s_cow})", color_discrete_sequence=['#2b6cb0', '#63b3ed'])
                    ui_plotly_chart(fig_rum, 260)
                else:
                    valid_s = analyzed_df[analyzed_df['evidence_category'] != 'Insufficient Data']
                    if not valid_s.empty:
                        fig_quad = px.scatter(valid_s, x='activity_change_pct', y='rumination_change_pct', color='evidence_category', hover_data=['cow_id', 'timestamp', 'combined_evidence_score'], color_discrete_map={'High': '#e53e3e', 'Moderate': '#f59f00', 'Low': '#52b788', 'Missing Reading': '#94a3b8'}, title="Herd Activity Deviation (%) vs Rumination Deviation (%) across 2-Hour Intervals")
                        fig_quad.add_vline(x=cfg_act, line_dash="dash", line_color="#e53e3e")
                        fig_quad.add_hline(y=-cfg_rum, line_dash="dash", line_color="#2b6cb0")
                        ui_plotly_chart(fig_quad, 320)

                disp_cols = ['cow_id', 'timestamp', 'activity_index', 'baseline_activity', 'activity_change_pct', 'rumination_minutes', 'baseline_rumination', 'rumination_change_pct', 'combined_evidence_score', 'evidence_category', 'explanation']
                st.dataframe(analyzed_df[disp_cols].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
                ui_download_csv("📥 Download Sensor Predictions CSV", analyzed_df[disp_cols], "sensor_estrus_predictions.csv")
            else:
                st.info("No sensor records match selected filters.")
        else:
            st.info("No sensor records available.")


# ==========================================
# MODULE 4: Health Monitoring
# ==========================================

def render_health_monitoring():
    ui_header("Health Monitoring & Clinical Vitals", "Body temperature tracking, appetite, milk drop flags, and clinical health observation logs.")
    cows_df = database.get_all_cows()

    tab_log, tab_hist, tab_trends = st.tabs([
        "🩺 Log Vital Parameters", "📜 Health Observation History", "📈 Temperature & Vital Trends"
    ])

    with tab_log:
        if not cows_df.empty:
            with st.form("log_health_form", clear_on_submit=True):
                st.markdown("##### Record Daily Health Check")
                c1, c2, c3 = st.columns(3)
                with c1:
                    sel_cid, _ = select_cow(cows_df, label="Cow *", key="h_log_cid")
                    obs_date = st.date_input("Date", value=date.today(), key="h_log_date")
                    temp = st.number_input("Body Temperature (°C) *", min_value=35.0, max_value=45.0, value=38.6, step=0.1)
                with c2:
                    milk_prod = st.number_input("Milk Yield (L)", min_value=0.0, max_value=60.0, value=20.0, step=0.5)
                    appetite = st.selectbox("Appetite", ["Normal", "Reduced", "Poor", "Anorexic"])
                    feed_in = st.number_input("Feed Intake (kg)", min_value=0.0, max_value=50.0, value=18.0, step=0.5)
                with c3:
                    water_in = st.number_input("Water Intake (L)", min_value=0.0, max_value=200.0, value=80.0, step=5.0)
                    act_level = st.selectbox("Activity Level", ["Normal", "Hyperactive", "Lethargic", "Restless"])
                    behaviour = st.selectbox("Behaviour", ["Normal", "Dull", "Depressed", "Excited", "Aggressive"])
                symptoms = st.text_input("Symptoms Observed", placeholder="e.g. Mild coughing, swollen quarter, nasal discharge")
                h_notes = st.text_input("Clinical Notes", placeholder="e.g. Under observation following routine morning check")

                if st.form_submit_button("💾 Save Health Record", type="primary", use_container_width=True):
                    h_rec = {
                        "cow_id": sel_cid, "observation_date": obs_date.strftime("%Y-%m-%d"),
                        "body_temperature": temp, "milk_production": milk_prod, "appetite": appetite,
                        "feed_intake": feed_in, "water_intake": water_in, "activity_level": act_level,
                        "behaviour": behaviour, "symptoms": symptoms or "None", "health_notes": h_notes
                    }
                    database.add_health_record(h_rec)
                    st.success(f"Health record saved for {sel_cid} (Temp: {temp}°C).")
                    st.rerun()
        else:
            st.info("No cows available.")

    with tab_hist:
        h_df = database.get_health_records()
        if not h_df.empty:
            f1, f2 = st.columns(2)
            with f1: filter_cid = st.selectbox("Filter Cow", ["All"] + sorted(h_df['cow_id'].unique().tolist()), key="h_hist_cid")
            with f2: filter_stat = st.selectbox("Filter Status", ["All"] + sorted(h_df['health_status'].unique().tolist()), key="h_hist_stat")

            f_df = h_df.copy()
            if filter_cid != "All": f_df = f_df[f_df['cow_id'] == filter_cid]
            if filter_stat != "All": f_df = f_df[f_df['health_status'] == filter_stat]

            cols = ['cow_id', 'observation_date', 'body_temperature', 'milk_production', 'appetite', 'activity_level', 'health_status', 'abnormality_flags', 'symptoms']
            st.dataframe(f_df[cols], use_container_width=True, hide_index=True)
            ui_download_csv("📥 Download Health Records CSV", f_df[cols], "health_records.csv")
        else:
            st.info("No health records recorded yet.")

    with tab_trends:
        h_df = database.get_health_records()
        if not h_df.empty:
            sel_cid, _ = select_cow(cows_df, label="Select Cow for Temperature Curve", key="h_trend_cid")
            c_h = h_df[h_df['cow_id'] == sel_cid].sort_values('observation_date')
            if not c_h.empty:
                fig_temp = px.line(c_h, x='observation_date', y='body_temperature', title=f"Body Temperature Curve – Cow {sel_cid}", markers=True, color_discrete_sequence=['#e53e3e'])
                fig_temp.add_hline(y=39.5, line_dash="dash", line_color="#e53e3e", annotation_text="Fever Threshold (39.5°C)")
                fig_temp.add_hline(y=38.0, line_dash="dash", line_color="#2b6cb0", annotation_text="Hypothermia (38.0°C)")
                ui_plotly_chart(fig_temp, 300)
            else:
                st.info(f"No records for cow {sel_cid}.")
        else:
            st.info("No records to plot.")


# ==========================================
# MODULE 5: Disease Risk Assessment
# ==========================================

def render_disease_risk_assessment():
    ui_header("Preliminary Disease Risk Assessment", "Heuristic clinical screening for mastitis, systemic pyrexia, digestive disorders, and reproductive abnormalities.")
    cows_df = database.get_all_cows()

    tab_eval, tab_hist, tab_vet = st.tabs([
        "🔍 Clinical Symptom Screening", "📜 Disease Screening History", "⚠️ Veterinary Attention Worklist"
    ])

    with tab_eval:
        if not cows_df.empty:
            c1, c2 = st.columns([1, 1.2])
            with c1:
                st.markdown("##### 1. Clinical Symptom Checklist")
                sel_cid, cow_info = select_cow(cows_df, label="Cow *", key="dis_eval_cid")
                ass_date = st.date_input("Assessment Date", value=date.today(), key="dis_eval_date")

                st.markdown("<b>Udder & Milking Signs:</b>", unsafe_allow_html=True)
                u_swell = st.checkbox("Udder Swelling / Hardness")
                u_pain = st.checkbox("Udder Heat or Tenderness")
                u_abn = st.checkbox("Abnormal Udder Appearance (Redness / Asymmetry)")
                m_abn = st.checkbox("Abnormal Milk (Clots, Flakes, Watery, Blood)")

                st.markdown("<b>Systemic & Physiological Signs:</b>", unsafe_allow_html=True)
                b_temp = st.number_input("Recorded Body Temperature (°C)", 35.0, 45.0, 38.6, 0.1)
                m_drop = st.number_input("Estimated Milk Yield Drop (%)", 0.0, 100.0, 0.0, 5.0)

                st.markdown("<b>Other Symptoms:</b>", unsafe_allow_html=True)
                dig_signs = st.selectbox("Digestive Signs", ["None", "Mild bloat, reduced rumination", "Severe bloat", "Watery diarrhea", "Ketosis sweet breath, off feed"])
                rep_signs = st.selectbox("Reproductive Signs", ["None", "Cloudy vaginal discharge", "Purulent foul vaginal discharge", "Retained fetal membranes (Placenta)", "Metritis signs"])
                notes = st.text_input("Screening Notes", placeholder="e.g. Routine post-milking visual exam")

            with c2:
                st.markdown("##### 2. Screening Risk Analysis")
                mast_r, sys_r, dig_r, rep_r, overall, rationale, vet_rec = evaluate_disease_risk(
                    b_temp, m_drop, u_swell, u_pain, u_abn, m_abn, dig_signs, rep_signs
                )

                b_col = "#e53e3e" if overall == "High concern" else ("#f59f00" if overall == "Moderate concern" else "#2d6a4f")
                st.markdown(f"""
                <div class="section-box" style="border-top: 5px solid {b_col};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:1.1rem; font-weight:700; color:#1b4332;">Overall Screening Risk</span>
                        <span class="demo-badge" style="background:{b_col}; color:white; font-size:0.95rem;">{overall}</span>
                    </div>
                    <hr style="margin:10px 0;">
                    <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size:0.86rem;">
                        <div><b>Mastitis Risk:</b> {mast_r}</div>
                        <div><b>Systemic Risk:</b> {sys_r}</div>
                        <div><b>Digestive Risk:</b> {dig_r}</div>
                        <div><b>Reproductive Risk:</b> {rep_r}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if vet_rec:
                    ui_alert("🚨 <b>Veterinary Attention Recommended:</b> High clinical concern detected. Segregate cow and request prompt professional veterinary examination.", "danger")
                else:
                    ui_alert("✅ Health parameters within acceptable ranges. Continue routine herd management.", "success")

                st.markdown(f"""
                <div style="background:#f8f9fa; border-left:4px solid {b_col}; padding:8px 12px; border-radius:6px; font-size:0.85rem; margin-bottom:12px;">
                    <b>Screening Rationale:</b> {rationale}
                </div>
                """, unsafe_allow_html=True)

                if st.button("💾 Save Disease Screening Record", type="primary", use_container_width=True):
                    rec = {
                        "cow_id": sel_cid, "assessment_date": ass_date.strftime("%Y-%m-%d"),
                        "mastitis_risk": mast_r, "systemic_risk": sys_r, "digestive_risk": dig_r,
                        "reproductive_risk": rep_r, "overall_concern": overall,
                        "udder_swelling": int(u_swell), "udder_pain": int(u_pain),
                        "abnormal_udder_appearance": int(u_abn), "abnormal_milk": int(m_abn),
                        "elevated_temp": 1 if b_temp >= 39.5 else 0, "reduced_yield": 1 if m_drop >= 15.0 else 0,
                        "digestive_symptoms": dig_signs, "reproductive_symptoms": rep_signs,
                        "rationale": rationale, "screening_notes": notes, "vet_consultation_recommended": vet_rec
                    }
                    database.add_disease_assessment(rec)
                    st.success(f"Disease assessment saved for {sel_cid} ({overall}).")
                    st.rerun()
        else:
            st.info("No cows available.")

    with tab_hist:
        dis_df = database.get_disease_assessments()
        if not dis_df.empty:
            cols = ['cow_id', 'assessment_date', 'overall_concern', 'mastitis_risk', 'systemic_risk', 'digestive_risk', 'reproductive_risk', 'vet_consultation_recommended', 'rationale']
            st.dataframe(dis_df[cols], use_container_width=True, hide_index=True)
            ui_download_csv("📥 Download Disease Screenings CSV", dis_df[cols], "disease_screenings.csv")
        else:
            st.info("No disease assessments recorded yet.")

    with tab_vet:
        st.markdown("##### Cows Flagged for Veterinary Attention")
        dis_df = database.get_disease_assessments()
        if not dis_df.empty:
            v_list = dis_df[dis_df['vet_consultation_recommended'] == 1].sort_values('assessment_date', ascending=False)
            if not v_list.empty:
                st.dataframe(v_list[['cow_id', 'assessment_date', 'overall_concern', 'rationale', 'screening_notes']], use_container_width=True, hide_index=True)
            else:
                st.success("No active veterinary alerts across screened herd records.")
        else:
            st.info("No assessments logged.")


# ==========================================
# MODULE 6: THI and Heat Stress Analytics
# ==========================================

def render_thi_analytics():
    ui_header("Temperature-Humidity Index (THI) & Heat Stress Analytics", "Environmental weather biometeorology, real-time NRC heat stress calculation, and production cross-impact.")
    thi_df = database.get_thi_records()

    if not thi_df.empty:
        l_rec = thi_df.iloc[0]
        l_thi, l_cat = float(l_rec['thi_value']), str(l_rec['heat_stress_category'])
        if l_thi >= 80.0:
            ui_alert(f"🚨 <b>CRITICAL HEAT STRESS EMERGENCY:</b> Latest environmental reading is <b>THI {l_thi} ({l_cat})</b>. Activate continuous fans, high-pressure soakers, and chilled water.", "danger")
        elif l_thi >= 72.0:
            ui_alert(f"⚠️ <b>SIGNIFICANT HEAT STRESS ADVISORY:</b> Latest environmental reading is <b>THI {l_thi} ({l_cat})</b>. Run cooling fans and adjust feeding to cooler morning/evening hours.", "warning")

    tab_calc, tab_trends, tab_impact = st.tabs([
        "🌡️ Interactive THI Calculator & Logger", "📈 Historical THI Trajectory", "🐄 Heat Stress & Herd Impact"
    ])

    with tab_calc:
        st.markdown("##### Instant Interactive Environmental THI Calculator")
        st.write("Adjust environmental temperature and relative humidity sliders below to calculate the Temperature-Humidity Index (THI) and evaluate heat-stress severity in real time.")

        # ONLY TWO WORKING SLIDERS - Purely environmental
        s1, s2 = st.columns(2)
        with s1:
            calc_temp = st.slider("Ambient Temperature (°C)", min_value=0.0, max_value=50.0, value=30.0, step=0.1, format="%.1f", key="thi_ambient_temp_slider")
        with s2:
            calc_rh = st.slider("Relative Humidity (%)", min_value=0, max_value=100, value=60, step=1, format="%d", key="thi_relative_humidity_slider")

        # THI Formula & Classification
        cur_thi = database.calculate_thi(calc_temp, calc_rh)

        if cur_thi < 68.0:
            cur_cat, cat_color, cat_bg, badge_icon = "Lower Concern", "#2d6a4f", "#e8f5e9", "🟢"
            cat_desc = "Optimal cow comfort zone. Respiratory rates and dry matter intake normal. Bovine thermoregulatory balance fully maintained."
            advisory = "Normal management routines. Maintain standard shade and ensure clean drinking water access."
        elif cur_thi < 72.0:
            cur_cat, cat_color, cat_bg, badge_icon = "Possible Mild Heat Stress", "#84cc16", "#f7fee7", "🟡"
            cat_desc = "Respiration rate elevated (60+ breaths/min). Cows seek shade; mild dry matter intake and milk yield fluctuations."
            advisory = "Verify shade availability, ensure optimal drinking water flow rates, and maximize natural/mechanical barn ventilation."
        elif cur_thi < 80.0:
            cur_cat, cat_color, cat_bg, badge_icon = "Significant Heat-Stress Concern", "#f59f00", "#fffbeb", "🟠"
            cat_desc = "Noticeable drop in feed intake (-10% to -20%) and milk production. Open-mouth panting; standing heat duration suppressed ('silent heat')."
            advisory = "Activate fans and evaporative cooling/sprinklers in holding pens and feeding alleys. Conduct estrus visual checks during cool night hours."
        else:
            cur_cat, cat_color, cat_bg, badge_icon = "Severe Heat-Stress Concern", "#e53e3e", "#fef2f2", "🔴"
            cat_desc = "Severe heat exhaustion alert. Heavy salivation, acute drop in daily milk yield, high embryonic mortality, and silent heat."
            advisory = "CRITICAL EMERGENCY: Continuous fan operation and evaporative soaking. Provide chilled drinking water. Cease handling or moving cows during peak heat."

        st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
        st.markdown("##### Real-Time Biometeorological Assessment")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("1. Ambient Temperature", f"{calc_temp:.1f} °C")
        m2.metric("2. Relative Humidity", f"{calc_rh}%")
        m3.metric("3. Calculated THI Value", f"{cur_thi:.2f}")
        with m4:
            st.markdown(f"""
            <div style="padding:10px; background:{cat_bg}; border:1.5px solid {cat_color}; border-radius:8px; text-align:center;">
                <div style="font-size:0.72rem; color:#475569; font-weight:700; text-transform:uppercase;">4. Heat-Stress Category</div>
                <div style="font-size:1.0rem; font-weight:800; color:{cat_color}; margin-top:4px;">{badge_icon} {cur_cat}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:{cat_bg}; border-left:6px solid {cat_color}; border-radius:8px; padding:14px 18px; margin-top:12px;">
            <div style="font-size:1.1rem; font-weight:800; color:{cat_color}; margin-bottom:4px;">
                {badge_icon} 4. Heat-Stress Category: {cur_cat} (THI: {cur_thi:.2f})
            </div>
            <div style="font-size:0.9rem; color:#1e293b; line-height:1.4; margin-bottom:8px;">
                <b>Biological Impact:</b> {cat_desc}
            </div>
            <div style="font-size:0.9rem; color:#1e293b; line-height:1.4; background:rgba(255,255,255,0.7); padding:8px 12px; border-radius:6px;">
                <b>5. Appropriate Advisory Message:</b> {advisory}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("💾 Log This Reading to Database (bovisense.db)", expanded=False):
            with st.form("log_thi_form"):
                f1, f2, f3 = st.columns(3)
                with f1:
                    o_date = st.date_input("Date", value=date.today())
                    o_time = st.time_input("Time", value=datetime.now().time())
                with f2:
                    l_t = st.number_input("Ambient Temperature (°C)", 0.0, 50.0, float(calc_temp), 0.1)
                    l_rh = st.number_input("Relative Humidity (%)", 0.0, 100.0, float(calc_rh), 1.0)
                with f3:
                    notes = st.text_input("Weather Notes", value=f"Interactive calculation (THI {cur_thi:.2f})")

                if st.form_submit_button("💾 Save Reading to SQLite", use_container_width=True):
                    val = database.calculate_thi(l_t, l_rh)
                    c_tag = database.classify_thi(val)
                    database.add_thi_record({
                        "observation_date": o_date.strftime("%Y-%m-%d"),
                        "observation_time": o_time.strftime("%H:%M"),
                        "ambient_temp": l_t, "relative_humidity": l_rh, "notes": notes
                    })
                    st.success(f"Environmental reading logged: THI {val} ({c_tag})")
                    st.rerun()

    with tab_trends:
        if not thi_df.empty:
            p_sel = st.selectbox("Timeline Filter", ["Last 14 Days", "Last 7 Days", "Last 30 Days", "All History"], index=0)
            t_df = thi_df.copy()
            t_df['datetime'] = pd.to_datetime(t_df['observation_date'] + ' ' + t_df['observation_time'])
            t_df = t_df.sort_values('datetime')
            max_d = t_df['datetime'].max()

            if p_sel == "Last 7 Days": t_df = t_df[t_df['datetime'] >= (max_d - timedelta(days=7))]
            elif p_sel == "Last 14 Days": t_df = t_df[t_df['datetime'] >= (max_d - timedelta(days=14))]
            elif p_sel == "Last 30 Days": t_df = t_df[t_df['datetime'] >= (max_d - timedelta(days=30))]

            fig_t = go.Figure()
            fig_t.add_hrect(y0=0, y1=68, fillcolor="#2d6a4f", opacity=0.08, line_width=0, annotation_text="Comfort (<68)")
            fig_t.add_hrect(y0=68, y1=72, fillcolor="#84cc16", opacity=0.10, line_width=0, annotation_text="Mild (68–71)")
            fig_t.add_hrect(y0=72, y1=80, fillcolor="#f59f00", opacity=0.12, line_width=0, annotation_text="Significant (72–79)")
            fig_t.add_hrect(y0=80, y1=110, fillcolor="#e53e3e", opacity=0.15, line_width=0, annotation_text="Severe (≥80)")
            fig_t.add_trace(go.Scatter(x=t_df['datetime'], y=t_df['thi_value'], mode='lines+markers', name='THI Trajectory', line=dict(color='#1b4332', width=2.5)))
            fig_t.update_layout(title="Continuous Environmental THI Trajectory", xaxis_title="Timeline", yaxis_title="Calculated THI")
            ui_plotly_chart(fig_t, 340)

            st.dataframe(t_df[['observation_date', 'observation_time', 'ambient_temp', 'relative_humidity', 'thi_value', 'heat_stress_category', 'notes']].sort_values(['observation_date', 'observation_time'], ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No THI records recorded.")

    with tab_impact:
        st.markdown("##### Cross-Analysis: Thermal Stress Impact on Milk Yield & Estrus Expression")
        st.write("Elevated environmental THI disrupts bovine thermal homeostasis, reduces dry matter intake, and severely attenuates overt visual standing heat expression (silent heat).")
        m_df = database.get_milk_records()
        if not thi_df.empty and not m_df.empty:
            m_sum = m_df.groupby('production_date')['total_yield'].sum().reset_index()
            t_sum = thi_df.groupby('observation_date')['thi_value'].mean().reset_index()
            merged = pd.merge(m_sum, t_sum, left_on='production_date', right_on='observation_date', how='inner').sort_values('production_date')

            if not merged.empty:
                fig_imp = go.Figure()
                fig_imp.add_trace(go.Scatter(x=merged['production_date'], y=merged['total_yield'], mode='lines+markers', name='Herd Milk Yield (L)', line=dict(color='#2d6a4f', width=2.5)))
                fig_imp.add_trace(go.Scatter(x=merged['production_date'], y=merged['thi_value'], mode='lines+markers', name='Daily Mean THI', line=dict(color='#e53e3e', width=2, dash='dot'), yaxis='y2'))
                fig_imp.update_layout(
                    title="Herd Milk Volume vs Mean Environmental THI",
                    xaxis_title="Date",
                    yaxis=dict(title=dict(text="Total Milk (L)", font=dict(color="#2d6a4f"))),
                    yaxis2=dict(title=dict(text="THI Value", font=dict(color="#e53e3e")), overlaying="y", side="right")
                )
                ui_plotly_chart(fig_imp, 320)
        else:
            st.info("Need both milk records and THI observations to plot cross-analysis.")


# ==========================================
# MODULE 7: Milk Production Management
# ==========================================

def render_milk_production():
    ui_header("Milk Production Tracking & Yield Analytics", "Parlor yield logging, morning/evening segregation, automatic drop detection alerts, and lactation trajectory curves.")
    cows_df = database.get_all_cows()

    tab_log, tab_hist, tab_trends = st.tabs([
        "🥛 Record Daily Milking", "📜 Production Records & History", "📈 Lactation Trajectory & Herd Yield Analytics"
    ])

    with tab_log:
        if not cows_df.empty:
            with st.form("log_milk_form", clear_on_submit=True):
                st.markdown("##### Log Milking Session")
                c1, c2, c3 = st.columns(3)
                with c1:
                    sel_cid, _ = select_cow(cows_df, label="Cow *", key="m_log_cid")
                    p_date = st.date_input("Date", value=date.today(), key="m_log_date")
                with c2:
                    m_yield = st.number_input("Morning Yield (L) *", min_value=0.0, max_value=50.0, value=12.5, step=0.5)
                    e_yield = st.number_input("Evening Yield (L) *", min_value=0.0, max_value=50.0, value=10.0, step=0.5)
                with c3:
                    t_yield = round(m_yield + e_yield, 2)
                    st.metric("Total Daily Yield", f"{t_yield} L")
                    notes = st.text_input("Milking Notes", placeholder="e.g. Standard parlor milking")

                if st.form_submit_button("💾 Save Milk Record", type="primary", use_container_width=True):
                    database.add_milk_record({
                        "cow_id": sel_cid, "production_date": p_date.strftime("%Y-%m-%d"),
                        "morning_yield": m_yield, "evening_yield": e_yield, "total_yield": t_yield, "notes": notes
                    })
                    st.success(f"Milk record logged for {sel_cid}: {t_yield} L total.")
                    st.rerun()
        else:
            st.info("No cows available.")

    with tab_hist:
        m_df = database.get_milk_records()
        if not m_df.empty:
            f1, f2 = st.columns(2)
            with f1: filter_cid = st.selectbox("Filter Cow", ["All"] + sorted(m_df['cow_id'].unique().tolist()), key="m_hist_cid")
            with f2: filter_alert = st.selectbox("Drop Alert", ["All", "Drop Alerts Only"], key="m_hist_alert")

            f_df = m_df.copy()
            if filter_cid != "All": f_df = f_df[f_df['cow_id'] == filter_cid]
            if filter_alert == "Drop Alerts Only": f_df = f_df[f_df['is_drop_alert'] == 1]

            cols = ['cow_id', 'production_date', 'morning_yield', 'evening_yield', 'total_yield', 'is_drop_alert', 'notes']
            st.dataframe(f_df[cols], use_container_width=True, hide_index=True)
            ui_download_csv("📥 Download Milk Records CSV", f_df[cols], "milk_records.csv")
        else:
            st.info("No milk records logged yet.")

    with tab_trends:
        m_df = database.get_milk_records()
        if not m_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                # Herd total volume line
                h_daily = m_df.groupby('production_date')['total_yield'].sum().reset_index().sort_values('production_date')
                fig_h = px.line(h_daily, x='production_date', y='total_yield', title="Herd Aggregate Daily Milk Yield (L)", markers=True, color_discrete_sequence=['#2d6a4f'])
                ui_plotly_chart(fig_h, 300)
            with c2:
                sel_cid, _ = select_cow(cows_df, label="Cow Lactation Trajectory", key="m_trend_cid")
                c_m = m_df[m_df['cow_id'] == sel_cid].sort_values('production_date')
                if not c_m.empty:
                    fig_c = px.line(c_m, x='production_date', y=['morning_yield', 'evening_yield', 'total_yield'], title=f"Individual Trajectory – {sel_cid}", markers=True, color_discrete_sequence=['#52b788', '#d4af37', '#1b4332'])
                    ui_plotly_chart(fig_c, 300)
                else:
                    st.info(f"No records for cow {sel_cid}.")
        else:
            st.info("No milk records to plot.")


# ==========================================
# MODULE 8: Reports and Analytics
# ==========================================

def render_reports_analytics():
    ui_header("Reports, Statistical Analytics & PDF Generation", "Export filtered herd census, statistical audits, CSV spreadsheets, and printable ReportLab PDF reports.")

    report_type = st.selectbox("Select Report Category", [
        "Overall Herd Summary Report",
        "Individual Cow Performance Report",
        "Estrus & Reproductive Cycle Report",
        "2-Hourly Sensor Telemetry & Estrus Detection Report",
        "Health Monitoring & Screening Report",
        "Disease Risk Assessment Audit",
        "Environmental THI & Heat Stress Report",
        "Milk Production Tracking Report"
    ])

    cows_df = database.get_all_cows()
    estrus_df = database.get_estrus_observations()
    health_df = database.get_health_records()
    dis_df = database.get_disease_assessments()
    thi_df = database.get_thi_records()
    milk_df = database.get_milk_records()
    sensor_df = database.get_sensor_records()

    st.markdown("---")

    if report_type == "Overall Herd Summary Report":
        st.markdown("### 📋 Overall Herd Summary Report")
        kpis = database.get_dashboard_kpis()
        summary_dict = {
            "Total Cows Registered": kpis["total_cows"], "Active Milking Herd": kpis["active_cows"],
            "High Estrus Evidence Cows": kpis["high_estrus_count"], "Health Concerns": kpis["health_attention_count"],
            "Total Daily Milk (L)": kpis["total_daily_milk"], "Average Milk/Cow (L)": kpis["avg_daily_milk"],
            "Current THI Index": kpis["latest_thi"] or "N/A"
        }
        st.dataframe(cows_df, use_container_width=True, hide_index=True)
        col1, col2 = st.columns(2)
        with col1: ui_download_csv("📥 Download Herd Registry CSV", cows_df, "herd_summary.csv")
        with col2:
            pdf_b = create_pdf_report("Overall Herd Management Census", summary_dict, cows_df, "Census of registered cattle, reproductive statuses, and yield outputs.")
            st.download_button("📄 Download Herd PDF Report", data=pdf_b, file_name="herd_summary.pdf", mime="application/pdf", use_container_width=True)

    elif report_type == "Individual Cow Performance Report":
        st.markdown("### 🔍 Individual Cow Performance Report")
        if not cows_df.empty:
            sel_cid, c_info = select_cow(cows_df, label="Select Cow", key="rep_cid")
            c_milk = database.get_milk_records(sel_cid)
            summary_dict = {
                "Cow ID": c_info['cow_id'], "Name": c_info['name'], "Breed": c_info['breed'],
                "Lactation Number": c_info['lactation_number'], "Status": c_info['reproductive_status'],
                "Health": c_info['health_status'], "Current Daily Milk": f"{c_info['daily_milk_production']} L"
            }
            st.dataframe(c_milk, use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1: ui_download_csv("📥 Download Cow Milk CSV", c_milk, f"cow_{sel_cid}_milk.csv")
            with col2:
                pdf_b = create_pdf_report(f"Individual Cow Profile – {c_info['name']} ({sel_cid})", summary_dict, c_milk, f"Individual biological and yield dossier for {c_info['name']}.")
                st.download_button("📄 Download Cow PDF Dossier", data=pdf_b, file_name=f"cow_{sel_cid}_dossier.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No cows available.")

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
            with col1: ui_download_csv("📥 Download Estrus Observations CSV", estrus_df, "estrus_report.csv")
            with col2:
                pdf_b = create_pdf_report("Estrus Detection & Reproductive Cycle Report", summary_dict, estrus_df, "Rule-based estrus scoring audit and projected next-cycle windows.")
                st.download_button("📄 Download Estrus PDF Report", data=pdf_b, file_name="estrus_report.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No estrus records available.")

    elif report_type == "2-Hourly Sensor Telemetry & Estrus Detection Report":
        st.markdown("### 📡 2-Hourly Sensor Telemetry & Estrus Detection Report")
        if not sensor_df.empty:
            analyzed = database.analyze_sensor_estrus(sensor_df)
            summary_dict = {
                "Total Sensor Intervals": len(analyzed), "Cows Monitored": analyzed['cow_id'].nunique(),
                "High Estrus Evidence Spikes": len(analyzed[analyzed['evidence_category'] == 'High']),
                "Moderate Evidence Signals": len(analyzed[analyzed['evidence_category'] == 'Moderate']),
                "Average Herd Activity": f"{analyzed['activity_index'].mean():.1f}",
                "Average Rumination": f"{analyzed['rumination_minutes'].mean():.1f} min/2h"
            }
            disp_cols = ['cow_id', 'timestamp', 'activity_index', 'baseline_activity', 'activity_change_pct', 'rumination_minutes', 'baseline_rumination', 'rumination_change_pct', 'combined_evidence_score', 'evidence_category', 'explanation']
            st.dataframe(analyzed[disp_cols].sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1: ui_download_csv("📥 Download Sensor Predictions CSV", analyzed[disp_cols], "sensor_report.csv")
            with col2:
                pdf_t = analyzed[['cow_id', 'timestamp', 'activity_index', 'rumination_minutes', 'combined_evidence_score', 'evidence_category']].head(40)
                pdf_b = create_pdf_report("2-Hourly Sensor Biometrics & Estrus Detection Audit", summary_dict, pdf_t, "Sensor telemetry activity and rumination estrus prediction using diurnal individual baselines.")
                st.download_button("📄 Download Sensor PDF Report", data=pdf_b, file_name="sensor_report.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No sensor records available.")

    elif report_type == "Health Monitoring & Screening Report":
        st.markdown("### 🩺 Health Monitoring & Screening Report")
        if not health_df.empty:
            summary_dict = {
                "Total Health Logs": len(health_df),
                "Critical Alerts": len(health_df[health_df['health_status'] == 'Critical Alert']),
                "Under Observation": len(health_df[health_df['health_status'] == 'Under Observation'])
            }
            st.dataframe(health_df, use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1: ui_download_csv("📥 Download Health Records CSV", health_df, "health_report.csv")
            with col2:
                pdf_b = create_pdf_report("Herd Health Monitoring Audit", summary_dict, health_df, "Vitals, temperatures, and clinical observations.")
                st.download_button("📄 Download Health PDF Report", data=pdf_b, file_name="health_report.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No health records available.")

    elif report_type == "Disease Risk Assessment Audit":
        st.markdown("### 🔍 Disease Risk Assessment Audit")
        if not dis_df.empty:
            summary_dict = {
                "Total Screenings": len(dis_df),
                "High Concern Flags": len(dis_df[dis_df['overall_concern'] == 'High concern']),
                "Vet Consultation Recommended": len(dis_df[dis_df['vet_consultation_recommended'] == 1])
            }
            st.dataframe(dis_df, use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1: ui_download_csv("📥 Download Disease Screenings CSV", dis_df, "disease_report.csv")
            with col2:
                pdf_b = create_pdf_report("Clinical Disease Screening Audit", summary_dict, dis_df, "Screening results across mastitis, systemic, digestive, and reproductive health.")
                st.download_button("📄 Download Disease PDF Report", data=pdf_b, file_name="disease_report.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No assessments available.")

    elif report_type == "Environmental THI & Heat Stress Report":
        st.markdown("### 🌡️ Environmental THI & Heat Stress Report")
        if not thi_df.empty:
            summary_dict = {
                "Total Readings": len(thi_df), "Mean THI": round(thi_df['thi_value'].mean(), 1),
                "Peak THI": round(thi_df['thi_value'].max(), 1),
                "Severe Stress Readings (≥80)": len(thi_df[thi_df['thi_value'] >= 80.0])
            }
            st.dataframe(thi_df, use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1: ui_download_csv("📥 Download THI Records CSV", thi_df, "thi_report.csv")
            with col2:
                pdf_b = create_pdf_report("Environmental THI Heat Stress Audit", summary_dict, thi_df, "Ambient weather recordings and NRC dairy thermal stress index.")
                st.download_button("📄 Download THI PDF Report", data=pdf_b, file_name="thi_report.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No THI records available.")

    elif report_type == "Milk Production Tracking Report":
        st.markdown("### 🥛 Milk Production Tracking Report")
        if not milk_df.empty:
            summary_dict = {
                "Total Milking Logs": len(milk_df), "Total Herd Yield (L)": round(milk_df['total_yield'].sum(), 1),
                "Average Yield/Milking": round(milk_df['total_yield'].mean(), 1),
                "Flagged Yield Drops": len(milk_df[milk_df['is_drop_alert'] == 1])
            }
            st.dataframe(milk_df, use_container_width=True, hide_index=True)
            col1, col2 = st.columns(2)
            with col1: ui_download_csv("📥 Download Milk Records CSV", milk_df, "milk_report.csv")
            with col2:
                pdf_b = create_pdf_report("Herd Milk Production Audit", summary_dict, milk_df, "Recorded parlor milk yields, morning/evening volumes, and yield drop alerts.")
                st.download_button("📄 Download Milk PDF Report", data=pdf_b, file_name="milk_report.pdf", mime="application/pdf", use_container_width=True)
        else: st.info("No milk records available.")


# ==========================================
# MODULE 9: Centralized CSV Import Center
# ==========================================

def render_csv_import_center():
    ui_header("Centralized CSV Import Center", "Bulk data ingestion, schema validation, foreign key checks, and row-by-row error auditing across all 8 datasets.")

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

    sel_cat = st.selectbox("Select CSV Import Category", list(category_labels.keys()), format_func=lambda k: category_labels[k])
    schema_info = CSV_SCHEMAS[sel_cat]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"##### 1. Download Official Template for {category_labels[sel_cat]}")
        st.download_button(
            f"📥 Download {sel_cat}_template.csv",
            data=schema_info["sample"].to_csv(index=False).encode('utf-8'),
            file_name=f"{sel_cat}_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    with c2:
        st.markdown("##### Required Columns Specification")
        st.info(f"**Required:** {', '.join(schema_info['required'])} \n\n**Optional:** {', '.join(schema_info['optional'])}")

    st.markdown("---")
    st.markdown("##### 2. Upload CSV File for Ingestion")
    up_file = st.file_uploader(f"Upload CSV for {category_labels[sel_cat]}", type=["csv"], key=f"uploader_{sel_cat}")

    if up_file is not None:
        try:
            raw_df = pd.read_csv(up_file)
            st.write(f"File uploaded: **{up_file.name}** ({len(raw_df)} total rows). Preview:")
            st.dataframe(raw_df.head(), use_container_width=True)

            all_cows = database.get_all_cows()
            existing_cids = set(all_cows['cow_id'].astype(str).str.strip()) if not all_cows.empty else set()
            valid_rows, rejected_rows = validate_csv_dataframe(raw_df, sel_cat, existing_cids)

            st.markdown("##### 3. Validation Summary & Audit")
            v1, v2, v3 = st.columns(3)
            ui_kpi(v1, "Total Rows in CSV", f"{len(raw_df)}")
            ui_kpi(v2, "Valid Rows Ready", f"{len(valid_rows)}", border_color="#2d6a4f")
            ui_kpi(v3, "Rejected Rows", f"{len(rejected_rows)}", border_color="#e53e3e" if rejected_rows else "#2d6a4f")

            if rejected_rows:
                ui_alert("Validation issues detected. Inspect row-specific rejection reasons below or download the rejected rows spreadsheet.", "warning")
                rej_df = pd.DataFrame(rejected_rows)
                st.dataframe(rej_df, use_container_width=True)
                st.download_button("📥 Download Rejected Rows (with Error Explanations)", data=rej_df.to_csv(index=False).encode('utf-8'), file_name=f"rejected_{sel_cat}.csv", mime="text/csv")

            if valid_rows:
                st.markdown("---")
                st.markdown(f"##### 4. Commit {len(valid_rows)} Valid Rows to SQLite `{sel_cat}`")
                if st.button("🚀 Confirm & Import Valid Rows", type="primary", use_container_width=True):
                    success_cnt = 0
                    dup_cnt = 0

                    for r in valid_rows:
                        try:
                            if sel_cat == "cows":
                                if database.get_cow(r["cow_id"]): dup_cnt += 1
                                else: database.add_cow(r); success_cnt += 1
                            elif sel_cat == "estrus_observations": database.add_estrus_observation(r); success_cnt += 1
                            elif sel_cat == "sensor_records":
                                ok, _ = database.add_sensor_record(r)
                                if ok: success_cnt += 1
                                else: dup_cnt += 1
                            elif sel_cat == "health_records": database.add_health_record(r); success_cnt += 1
                            elif sel_cat == "disease_assessments": database.add_disease_assessment(r); success_cnt += 1
                            elif sel_cat == "thi_records": database.add_thi_record(r); success_cnt += 1
                            elif sel_cat == "milk_records": database.add_milk_record(r); success_cnt += 1
                            elif sel_cat == "reproductive_history": database.add_reproductive_event(r); success_cnt += 1
                        except Exception as ex:
                            pass

                    database.log_csv_import(up_file.name, sel_cat, len(raw_df), success_cnt, len(rejected_rows), dup_cnt, "Completed", f"Committed {success_cnt} rows, {dup_cnt} duplicates skipped.")
                    st.success(f"🎉 Import complete! Successfully committed {success_cnt} records to `{sel_cat}` ({dup_cnt} duplicates prevented).")
                    st.rerun()
        except Exception as e:
            st.error(f"Failed to read CSV: {str(e)}")

    st.markdown("---")
    st.markdown("##### 📜 CSV Import Audit History")
    hist_df = database.get_csv_import_history()
    if not hist_df.empty:
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("No prior CSV import sessions logged.")


# ==========================================
# MODULE 10: CSV Export & Backup Center
# ==========================================

def render_csv_export_backup():
    ui_header("CSV Export & SQLite Database Backup Center", "Export persistent farm records to CSV spreadsheets, perform binary database snapshots, and restore backups.")

    tab_export, tab_backup = st.tabs(["📤 Bulk CSV Data Export", "💾 Database Snapshot & Restore"])

    with tab_export:
        st.markdown("#### One-Click CSV Data Downloads")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ui_download_csv("📥 Export Cows CSV", database.get_all_cows(), f"bovisense_cows_{date.today().strftime('%Y%m%d')}.csv")
            ui_download_csv("📥 Export Estrus CSV", database.get_estrus_observations(), f"bovisense_estrus_{date.today().strftime('%Y%m%d')}.csv")
        with c2:
            ui_download_csv("📥 Export Health CSV", database.get_health_records(), f"bovisense_health_{date.today().strftime('%Y%m%d')}.csv")
            ui_download_csv("📥 Export Disease CSV", database.get_disease_assessments(), f"bovisense_disease_{date.today().strftime('%Y%m%d')}.csv")
        with c3:
            ui_download_csv("📥 Export THI Weather CSV", database.get_thi_records(), f"bovisense_thi_{date.today().strftime('%Y%m%d')}.csv")
            ui_download_csv("📥 Export Milk CSV", database.get_milk_records(), f"bovisense_milk_{date.today().strftime('%Y%m%d')}.csv")
        with c4:
            s_records = database.get_sensor_records()
            ui_download_csv("📥 Export Sensor Telemetry CSV", s_records, f"bovisense_sensor_{date.today().strftime('%Y%m%d')}.csv")
            if not s_records.empty:
                s_pred = database.analyze_sensor_estrus(s_records)
                ui_download_csv("📥 Export Sensor Predictions CSV", s_pred, f"bovisense_sensor_predictions_{date.today().strftime('%Y%m%d')}.csv")

    with tab_backup:
        st.markdown("#### Database Snapshot & Restore")
        st.write("Create a binary snapshot of `bovisense.db` or restore from a previous backup file.")

        b1, b2 = st.columns(2)
        with b1:
            st.markdown("##### 1. Download Database Snapshot")
            if os.path.exists("bovisense.db"):
                with open("bovisense.db", "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    "💾 Download bovisense.db Snapshot",
                    data=db_bytes,
                    file_name=f"bovisense_snapshot_{date.today().strftime('%Y%m%d_%H%M')}.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
        with b2:
            st.markdown("##### 2. Restore Database from Snapshot")
            up_backup = st.file_uploader("Upload .db Backup File", type=["db", "sqlite", "sqlite3"], key="backup_restore_up")
            if up_backup and st.button("⚠️ Restore Database from Uploaded File", type="primary", use_container_width=True):
                with open("bovisense_temp_restore.db", "wb") as f:
                    f.write(up_backup.read())
                ok, msg = database.restore_database("bovisense_temp_restore.db")
                if os.path.exists("bovisense_temp_restore.db"):
                    os.remove("bovisense_temp_restore.db")
                if ok:
                    st.success("Database restored successfully!")
                    st.rerun()
                else:
                    st.error(f"Restore failed: {msg}")


# ==========================================
# Main Application Router
# ==========================================

def main():
    selected_module = render_sidebar()

    if selected_module == "1. Executive Dashboard":
        render_dashboard()
    elif selected_module == "2. Cow Management":
        render_cow_management()
    elif selected_module == "3. Estrus Prediction":
        render_estrus_prediction()
    elif selected_module == "4. Health Monitoring":
        render_health_monitoring()
    elif selected_module == "5. Disease Risk Assessment":
        render_disease_risk_assessment()
    elif selected_module == "6. THI and Heat Stress Analytics":
        render_thi_analytics()
    elif selected_module == "7. Milk Production Management":
        render_milk_production()
    elif selected_module == "8. Reports and Analytics":
        render_reports_analytics()
    elif selected_module == "9. CSV Import Center":
        render_csv_import_center()
    elif selected_module == "10. CSV Export and Backup":
        render_csv_export_backup()


if __name__ == "__main__":
    main()
