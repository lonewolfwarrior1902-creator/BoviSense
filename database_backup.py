"""
BoviSense – Database Architecture and Data Access Layer
Persistent SQLite storage, transaction management, data validation,
synthetic demonstration data generation, and backup/restore utilities.
"""

import sqlite3
import os
import shutil
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

DB_FILE = "bovisense.db"


def get_connection(db_path=DB_FILE):
    """Establish a thread-safe connection to SQLite with foreign keys enabled."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=DB_FILE):
    """Initialize all SQLite tables and required indexes."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    # 1. Cows Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cows (
        cow_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        breed TEXT NOT NULL,
        dob TEXT,
        age REAL,
        weight REAL,
        lactation_number INTEGER DEFAULT 1,
        daily_milk_production REAL DEFAULT 0.0,
        last_calving_date TEXT,
        last_observed_estrus_date TEXT,
        last_insemination_date TEXT,
        pregnancy_status TEXT DEFAULT 'Open',
        health_status TEXT DEFAULT 'Healthy',
        reproductive_status TEXT DEFAULT 'Open',
        remarks TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    );
    """)

    # 2. Estrus Observations Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS estrus_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cow_id TEXT NOT NULL,
        observation_date TEXT NOT NULL,
        selected_markers TEXT,
        increased_activity INTEGER DEFAULT 0,
        restlessness INTEGER DEFAULT 0,
        mounting_behaviour INTEGER DEFAULT 0,
        standing_to_be_mounted INTEGER DEFAULT 0,
        frequent_vocalization INTEGER DEFAULT 0,
        reduced_feed_intake INTEGER DEFAULT 0,
        clear_mucus_discharge INTEGER DEFAULT 0,
        swollen_vulva INTEGER DEFAULT 0,
        reduced_milk_yield INTEGER DEFAULT 0,
        estrus_score REAL DEFAULT 0.0,
        evidence_category TEXT DEFAULT 'Low',
        cycle_stage TEXT DEFAULT 'Unknown',
        estimated_next_estrus TEXT,
        score_reasons TEXT,
        notes TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (cow_id) REFERENCES cows(cow_id) ON DELETE CASCADE
    );
    """)

    # Backward-compatible column migration
    try:
        cur.execute("ALTER TABLE estrus_observations ADD COLUMN selected_markers TEXT;")
    except Exception:
        pass

    # 3. Health Records Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS health_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cow_id TEXT NOT NULL,
        observation_date TEXT NOT NULL,
        body_temperature REAL NOT NULL,
        milk_production REAL,
        appetite TEXT DEFAULT 'Normal',
        feed_intake REAL,
        water_intake REAL,
        activity_level TEXT DEFAULT 'Normal',
        behaviour TEXT DEFAULT 'Normal',
        symptoms TEXT,
        health_status TEXT DEFAULT 'Healthy',
        abnormality_flags TEXT,
        health_notes TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (cow_id) REFERENCES cows(cow_id) ON DELETE CASCADE
    );
    """)

    # 4. Disease Risk Assessments Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS disease_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cow_id TEXT NOT NULL,
        assessment_date TEXT NOT NULL,
        mastitis_risk TEXT DEFAULT 'Low concern',
        systemic_risk TEXT DEFAULT 'Low concern',
        digestive_risk TEXT DEFAULT 'Low concern',
        reproductive_risk TEXT DEFAULT 'Low concern',
        overall_concern TEXT DEFAULT 'Low concern',
        udder_swelling INTEGER DEFAULT 0,
        udder_pain INTEGER DEFAULT 0,
        abnormal_udder_appearance INTEGER DEFAULT 0,
        abnormal_milk INTEGER DEFAULT 0,
        elevated_temp INTEGER DEFAULT 0,
        reduced_yield INTEGER DEFAULT 0,
        digestive_symptoms TEXT,
        reproductive_symptoms TEXT,
        rationale TEXT,
        screening_notes TEXT,
        vet_consultation_recommended INTEGER DEFAULT 0,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (cow_id) REFERENCES cows(cow_id) ON DELETE CASCADE
    );
    """)

    # 5. THI Records Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS thi_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        observation_date TEXT NOT NULL,
        observation_time TEXT NOT NULL,
        ambient_temp REAL NOT NULL,
        relative_humidity REAL NOT NULL,
        thi_value REAL NOT NULL,
        heat_stress_category TEXT NOT NULL,
        notes TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)

    # 6. Milk Records Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS milk_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cow_id TEXT NOT NULL,
        production_date TEXT NOT NULL,
        morning_yield REAL DEFAULT 0.0,
        evening_yield REAL DEFAULT 0.0,
        total_yield REAL NOT NULL,
        is_drop_alert INTEGER DEFAULT 0,
        notes TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (cow_id) REFERENCES cows(cow_id) ON DELETE CASCADE
    );
    """)

    # 7. Reproductive History Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reproductive_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cow_id TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_type TEXT NOT NULL,
        details TEXT,
        technician_or_sire TEXT,
        outcome TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (cow_id) REFERENCES cows(cow_id) ON DELETE CASCADE
    );
    """)

    # 8. CSV Import History Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS csv_import_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        category TEXT NOT NULL,
        import_date TEXT NOT NULL,
        total_rows INTEGER DEFAULT 0,
        success_rows INTEGER DEFAULT 0,
        rejected_rows INTEGER DEFAULT 0,
        duplicate_rows INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Completed',
        error_summary TEXT
    );
    """)

    # 9. Sensor Telemetry Records Table (2-hour observation intervals: Activity Index + Rumination Minutes)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sensor_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cow_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        activity_index REAL NOT NULL,
        rumination_minutes REAL NOT NULL,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(cow_id, timestamp),
        FOREIGN KEY (cow_id) REFERENCES cows(cow_id) ON DELETE CASCADE
    );
    """)

    # Useful Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cows_breed ON cows(breed);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cows_rep_status ON cows(reproductive_status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_estrus_cow_date ON estrus_observations(cow_id, observation_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_health_cow_date ON health_records(cow_id, observation_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_disease_cow_date ON disease_assessments(cow_id, assessment_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_thi_date ON thi_records(observation_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_milk_cow_date ON milk_records(cow_id, production_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rep_cow_date ON reproductive_history(cow_id, event_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_cow_time ON sensor_records(cow_id, timestamp);")

    conn.commit()
    conn.close()


# ==========================================
# CRUD Operations: Cows
# ==========================================

def get_all_cows(db_path=DB_FILE):
    """Retrieve all cow records as a pandas DataFrame."""
    conn = get_connection(db_path)
    df = pd.read_sql_query("SELECT * FROM cows ORDER BY cow_id ASC", conn)
    conn.close()
    return df




def get_cow(cow_id, db_path=DB_FILE):
    """Retrieve a single cow dictionary by cow_id."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM cows WHERE cow_id = ?", (cow_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def add_cow(cow_dict, db_path=DB_FILE):
    """Insert a new cow record."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate age if DOB provided and age not set
    dob = cow_dict.get("dob")
    age = cow_dict.get("age")
    if dob and (age is None or age == 0):
        try:
            d = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
            age = round((date.today() - d).days / 365.25, 1)
        except Exception:
            pass

    cur.execute("""
        INSERT INTO cows (
            cow_id, name, breed, dob, age, weight, lactation_number,
            daily_milk_production, last_calving_date, last_observed_estrus_date,
            last_insemination_date, pregnancy_status, health_status,
            reproductive_status, remarks, is_demo, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(cow_dict.get("cow_id")).strip(),
        str(cow_dict.get("name", "")).strip(),
        str(cow_dict.get("breed", "Holstein Friesian")),
        str(dob) if dob else None,
        float(age) if age is not None else None,
        float(cow_dict.get("weight", 0.0)) if cow_dict.get("weight") else None,
        int(cow_dict.get("lactation_number", 1)),
        float(cow_dict.get("daily_milk_production", 0.0)),
        str(cow_dict.get("last_calving_date")) if cow_dict.get("last_calving_date") else None,
        str(cow_dict.get("last_observed_estrus_date")) if cow_dict.get("last_observed_estrus_date") else None,
        str(cow_dict.get("last_insemination_date")) if cow_dict.get("last_insemination_date") else None,
        str(cow_dict.get("pregnancy_status", "Open")),
        str(cow_dict.get("health_status", "Healthy")),
        str(cow_dict.get("reproductive_status", "Open")),
        str(cow_dict.get("remarks", "")),
        int(cow_dict.get("is_demo", 0)),
        now,
        now
    ))
    conn.commit()
    conn.close()
    return True


def update_cow(cow_id, cow_dict, db_path=DB_FILE):
    """Update an existing cow record."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dob = cow_dict.get("dob")
    age = cow_dict.get("age")
    if dob and (age is None or age == 0):
        try:
            d = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
            age = round((date.today() - d).days / 365.25, 1)
        except Exception:
            pass

    cur.execute("""
        UPDATE cows SET
            name = ?, breed = ?, dob = ?, age = ?, weight = ?,
            lactation_number = ?, daily_milk_production = ?,
            last_calving_date = ?, last_observed_estrus_date = ?,
            last_insemination_date = ?, pregnancy_status = ?,
            health_status = ?, reproductive_status = ?,
            remarks = ?, updated_at = ?
        WHERE cow_id = ?
    """, (
        str(cow_dict.get("name", "")).strip(),
        str(cow_dict.get("breed", "Holstein Friesian")),
        str(dob) if dob else None,
        float(age) if age is not None else None,
        float(cow_dict.get("weight", 0.0)) if cow_dict.get("weight") else None,
        int(cow_dict.get("lactation_number", 1)),
        float(cow_dict.get("daily_milk_production", 0.0)),
        str(cow_dict.get("last_calving_date")) if cow_dict.get("last_calving_date") else None,
        str(cow_dict.get("last_observed_estrus_date")) if cow_dict.get("last_observed_estrus_date") else None,
        str(cow_dict.get("last_insemination_date")) if cow_dict.get("last_insemination_date") else None,
        str(cow_dict.get("pregnancy_status", "Open")),
        str(cow_dict.get("health_status", "Healthy")),
        str(cow_dict.get("reproductive_status", "Open")),
        str(cow_dict.get("remarks", "")),
        now,
        str(cow_id).strip()
    ))
    conn.commit()
    conn.close()
    return True


def delete_cow(cow_id, db_path=DB_FILE):
    """Delete a cow and cascade remove all related records."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM cows WHERE cow_id = ?", (str(cow_id).strip(),))
    conn.commit()
    conn.close()
    return True


# ==========================================
# CRUD Operations: Estrus Observations
# ==========================================

def add_estrus_observation(obs_dict, db_path=DB_FILE):
    """Insert an estrus observation and update cow's last observed estrus if high evidence."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Process selected_markers for persistent storage
    raw_markers = obs_dict.get("selected_markers")
    if isinstance(raw_markers, (list, tuple, set)):
        markers_str = ", ".join(raw_markers)
    elif raw_markers and str(raw_markers).strip() and str(raw_markers).strip().lower() != "none":
        markers_str = str(raw_markers).strip()
    else:
        # Backward-compatible auto-reconstruction from discrete flags
        reconstructed = []
        if obs_dict.get("standing_to_be_mounted"):
            reconstructed.append("Standing to Be Mounted")
        if obs_dict.get("mounting_behaviour"):
            reconstructed.append("Mounting Other Cows")
        if obs_dict.get("clear_mucus_discharge"):
            reconstructed.append("Clear Vaginal Mucus Discharge")
        if obs_dict.get("increased_activity") or obs_dict.get("restlessness"):
            reconstructed.append("Increased Activity / Restlessness")
        if obs_dict.get("swollen_vulva"):
            reconstructed.append("Vulval Swelling and Redness")
        markers_str = ", ".join(reconstructed) if reconstructed else "None observed"

    cur.execute("""
        INSERT INTO estrus_observations (
            cow_id, observation_date, selected_markers, increased_activity, restlessness,
            mounting_behaviour, standing_to_be_mounted, frequent_vocalization,
            reduced_feed_intake, clear_mucus_discharge, swollen_vulva,
            reduced_milk_yield, estrus_score, evidence_category,
            cycle_stage, estimated_next_estrus, score_reasons, notes,
            is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(obs_dict.get("cow_id")).strip(),
        str(obs_dict.get("observation_date")),
        markers_str,
        int(obs_dict.get("increased_activity", 0)),
        int(obs_dict.get("restlessness", 0)),
        int(obs_dict.get("mounting_behaviour", 0)),
        int(obs_dict.get("standing_to_be_mounted", 0)),
        int(obs_dict.get("frequent_vocalization", 0)),
        int(obs_dict.get("reduced_feed_intake", 0)),
        int(obs_dict.get("clear_mucus_discharge", 0)),
        int(obs_dict.get("swollen_vulva", 0)),
        int(obs_dict.get("reduced_milk_yield", 0)),
        float(obs_dict.get("estrus_score", 0.0)),
        str(obs_dict.get("evidence_category", "Low")),
        str(obs_dict.get("cycle_stage", "Unknown")),
        str(obs_dict.get("estimated_next_estrus", "")) if obs_dict.get("estimated_next_estrus") else None,
        str(obs_dict.get("score_reasons", "")),
        str(obs_dict.get("notes", "")),
        int(obs_dict.get("is_demo", 0)),
        now
    ))

    # Update cow's last_observed_estrus_date if evidence is high (>= 65)
    score = float(obs_dict.get("estrus_score", 0.0))
    if score >= 65:
        cur.execute("""
            UPDATE cows
            SET last_observed_estrus_date = ?,
                reproductive_status = CASE WHEN pregnancy_status != 'Pregnant' THEN 'In Heat' ELSE reproductive_status END
            WHERE cow_id = ?
        """, (str(obs_dict.get("observation_date")), str(obs_dict.get("cow_id")).strip()))

    conn.commit()
    conn.close()
    return True


def get_estrus_observations(cow_id=None, db_path=DB_FILE):
    """Retrieve estrus observations, optionally filtered by cow_id with backward-compatible marker formatting."""
    conn = get_connection(db_path)
    if cow_id:
        df = pd.read_sql_query(
            "SELECT * FROM estrus_observations WHERE cow_id = ? ORDER BY observation_date DESC, id DESC",
            conn, params=(str(cow_id).strip(),)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM estrus_observations ORDER BY observation_date DESC, id DESC",
            conn
        )
    conn.close()

    if not df.empty:
        if 'selected_markers' not in df.columns:
            df['selected_markers'] = None

        def _reconstruct_markers(row):
            val = row.get('selected_markers')
            if pd.notna(val) and str(val).strip() and str(val).strip().lower() != 'none':
                return str(val).strip()
            parts = []
            if row.get('standing_to_be_mounted') == 1:
                parts.append("Standing to Be Mounted")
            if row.get('mounting_behaviour') == 1:
                parts.append("Mounting Other Cows")
            if row.get('clear_mucus_discharge') == 1:
                parts.append("Clear Vaginal Mucus Discharge")
            if (row.get('increased_activity') == 1) or (row.get('restlessness') == 1):
                parts.append("Increased Activity / Restlessness")
            if row.get('swollen_vulva') == 1:
                parts.append("Vulval Swelling and Redness")
            return ", ".join(parts) if parts else "None observed"

        df['selected_markers'] = df.apply(_reconstruct_markers, axis=1)

    return df


# ==========================================
# CRUD Operations: Health Records
# ==========================================

def add_health_record(rec_dict, db_path=DB_FILE):
    """Insert a health record and update cow health status accordingly."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO health_records (
            cow_id, observation_date, body_temperature, milk_production,
            appetite, feed_intake, water_intake, activity_level,
            behaviour, symptoms, health_status, abnormality_flags,
            health_notes, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(rec_dict.get("cow_id")).strip(),
        str(rec_dict.get("observation_date")),
        float(rec_dict.get("body_temperature")),
        float(rec_dict.get("milk_production")) if rec_dict.get("milk_production") is not None else None,
        str(rec_dict.get("appetite", "Normal")),
        float(rec_dict.get("feed_intake")) if rec_dict.get("feed_intake") is not None else None,
        float(rec_dict.get("water_intake")) if rec_dict.get("water_intake") is not None else None,
        str(rec_dict.get("activity_level", "Normal")),
        str(rec_dict.get("behaviour", "Normal")),
        str(rec_dict.get("symptoms", "")),
        str(rec_dict.get("health_status", "Healthy")),
        str(rec_dict.get("abnormality_flags", "")),
        str(rec_dict.get("health_notes", "")),
        int(rec_dict.get("is_demo", 0)),
        now
    ))

    # Update cow's overall health status
    status = str(rec_dict.get("health_status", "Healthy"))
    cur.execute("""
        UPDATE cows SET health_status = ?, updated_at = ? WHERE cow_id = ?
    """, (status, now, str(rec_dict.get("cow_id")).strip()))

    conn.commit()
    conn.close()
    return True


def get_health_records(cow_id=None, db_path=DB_FILE):
    """Retrieve health records, optionally filtered by cow_id."""
    conn = get_connection(db_path)
    if cow_id:
        df = pd.read_sql_query(
            "SELECT * FROM health_records WHERE cow_id = ? ORDER BY observation_date DESC, id DESC",
            conn, params=(str(cow_id).strip(),)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM health_records ORDER BY observation_date DESC, id DESC",
            conn
        )
    conn.close()
    return df




# ==========================================
# CRUD Operations: Disease Risk Assessments
# ==========================================

def add_disease_assessment(rec_dict, db_path=DB_FILE):
    """Insert a disease risk assessment."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO disease_assessments (
            cow_id, assessment_date, mastitis_risk, systemic_risk,
            digestive_risk, reproductive_risk, overall_concern,
            udder_swelling, udder_pain, abnormal_udder_appearance,
            abnormal_milk, elevated_temp, reduced_yield,
            digestive_symptoms, reproductive_symptoms, rationale,
            screening_notes, vet_consultation_recommended, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(rec_dict.get("cow_id")).strip(),
        str(rec_dict.get("assessment_date")),
        str(rec_dict.get("mastitis_risk", "Low concern")),
        str(rec_dict.get("systemic_risk", "Low concern")),
        str(rec_dict.get("digestive_risk", "Low concern")),
        str(rec_dict.get("reproductive_risk", "Low concern")),
        str(rec_dict.get("overall_concern", "Low concern")),
        int(rec_dict.get("udder_swelling", 0)),
        int(rec_dict.get("udder_pain", 0)),
        int(rec_dict.get("abnormal_udder_appearance", 0)),
        int(rec_dict.get("abnormal_milk", 0)),
        int(rec_dict.get("elevated_temp", 0)),
        int(rec_dict.get("reduced_yield", 0)),
        str(rec_dict.get("digestive_symptoms", "")),
        str(rec_dict.get("reproductive_symptoms", "")),
        str(rec_dict.get("rationale", "")),
        str(rec_dict.get("screening_notes", "")),
        int(rec_dict.get("vet_consultation_recommended", 0)),
        int(rec_dict.get("is_demo", 0)),
        now
    ))
    conn.commit()
    conn.close()
    return True


def get_disease_assessments(cow_id=None, db_path=DB_FILE):
    """Retrieve disease risk assessments."""
    conn = get_connection(db_path)
    if cow_id:
        df = pd.read_sql_query(
            "SELECT * FROM disease_assessments WHERE cow_id = ? ORDER BY assessment_date DESC, id DESC",
            conn, params=(str(cow_id).strip(),)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM disease_assessments ORDER BY assessment_date DESC, id DESC",
            conn
        )
    conn.close()
    return df




# ==========================================
# CRUD Operations: THI Records
# ==========================================

def calculate_thi(temp_c, rh):
    """
    Standard Dairy THI equation:
    THI = (1.8 * T + 32) - ((0.55 - 0.0055 * RH) * (1.8 * T - 26))
    where T is environmental temperature in Celsius and RH is relative humidity in percentage.
    """
    try:
        t = float(temp_c)
        rh_val = float(rh)
        thi = (1.8 * t + 32.0) - ((0.55 - 0.0055 * rh_val) * (1.8 * t - 26.0))
        return round(thi, 2)
    except Exception:
        return 0.0


def classify_thi(thi):
    """
    Classify THI according to standard agricultural heat-stress guidelines:
    - THI < 68: Lower concern
    - THI 68–71: Possible mild heat stress
    - THI 72–79: Significant heat-stress concern
    - THI >= 80: Severe heat-stress concern
    """
    try:
        val = float(thi)
        if val < 68.0:
            return "Lower concern"
        elif val < 72.0:
            return "Possible mild heat stress"
        elif val < 80.0:
            return "Significant heat-stress concern"
        else:
            return "Severe heat-stress concern"
    except Exception:
        return "Lower concern"


def add_thi_record(rec_dict, db_path=DB_FILE):
    """Insert a new environmental THI record."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    t = float(rec_dict.get("ambient_temp"))
    rh = float(rec_dict.get("relative_humidity"))
    thi = calculate_thi(t, rh)
    cat = classify_thi(thi)

    cur.execute("""
        INSERT INTO thi_records (
            observation_date, observation_time, ambient_temp,
            relative_humidity, thi_value, heat_stress_category,
            notes, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(rec_dict.get("observation_date")),
        str(rec_dict.get("observation_time", "12:00")),
        t,
        rh,
        thi,
        cat,
        str(rec_dict.get("notes", "")),
        int(rec_dict.get("is_demo", 0)),
        now
    ))
    conn.commit()
    conn.close()
    return True


def get_thi_records(db_path=DB_FILE):
    """Retrieve all THI records ordered by date and time descending."""
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM thi_records ORDER BY observation_date DESC, observation_time DESC, id DESC",
        conn
    )
    conn.close()
    return df




# ==========================================
# CRUD Operations: Milk Records
# ==========================================

def add_milk_record(rec_dict, db_path=DB_FILE):
    """Insert a milk record and update cow's daily milk production."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cow_id = str(rec_dict.get("cow_id")).strip()
    m_yield = float(rec_dict.get("morning_yield", 0.0))
    e_yield = float(rec_dict.get("evening_yield", 0.0))
    t_yield = rec_dict.get("total_yield")
    if t_yield is None or float(t_yield) == 0.0:
        t_yield = round(m_yield + e_yield, 2)
    else:
        t_yield = round(float(t_yield), 2)

    # Check for drop alert: compare with recent 5-day average for this cow
    cur.execute("""
        SELECT AVG(total_yield) FROM milk_records
        WHERE cow_id = ? ORDER BY production_date DESC LIMIT 5
    """, (cow_id,))
    row = cur.fetchone()
    avg_prev = row[0] if (row and row[0]) else None
    drop_alert = 0
    if avg_prev and avg_prev > 5.0 and t_yield < (0.75 * avg_prev):
        drop_alert = 1

    cur.execute("""
        INSERT INTO milk_records (
            cow_id, production_date, morning_yield, evening_yield,
            total_yield, is_drop_alert, notes, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cow_id,
        str(rec_dict.get("production_date")),
        m_yield,
        e_yield,
        t_yield,
        drop_alert,
        str(rec_dict.get("notes", "")),
        int(rec_dict.get("is_demo", 0)),
        now
    ))

    # Update cow's daily_milk_production
    cur.execute("""
        UPDATE cows SET daily_milk_production = ?, updated_at = ? WHERE cow_id = ?
    """, (t_yield, now, cow_id))

    conn.commit()
    conn.close()
    return True


def get_milk_records(cow_id=None, db_path=DB_FILE):
    """Retrieve milk records, optionally filtered by cow_id."""
    conn = get_connection(db_path)
    if cow_id:
        df = pd.read_sql_query(
            "SELECT * FROM milk_records WHERE cow_id = ? ORDER BY production_date DESC, id DESC",
            conn, params=(str(cow_id).strip(),)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM milk_records ORDER BY production_date DESC, id DESC",
            conn
        )
    conn.close()
    return df




# ==========================================
# CRUD Operations: Reproductive History
# ==========================================

def add_reproductive_event(rec_dict, db_path=DB_FILE):
    """Insert a reproductive event and synchronize cow reproductive dates and statuses."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cow_id = str(rec_dict.get("cow_id")).strip()
    e_date = str(rec_dict.get("event_date"))
    e_type = str(rec_dict.get("event_type", "Estrus Observed"))

    cur.execute("""
        INSERT INTO reproductive_history (
            cow_id, event_date, event_type, details,
            technician_or_sire, outcome, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cow_id,
        e_date,
        e_type,
        str(rec_dict.get("details", "")),
        str(rec_dict.get("technician_or_sire", "")),
        str(rec_dict.get("outcome", "")),
        int(rec_dict.get("is_demo", 0)),
        now
    ))

    # Synchronize dates and statuses on cow
    if "Calving" in e_type:
        cur.execute("""
            UPDATE cows SET
                last_calving_date = ?,
                pregnancy_status = 'Open',
                reproductive_status = 'Calved',
                lactation_number = lactation_number + 1,
                updated_at = ?
            WHERE cow_id = ?
        """, (e_date, now, cow_id))
    elif "Insemination" in e_type or "Service" in e_type:
        cur.execute("""
            UPDATE cows SET
                last_insemination_date = ?,
                pregnancy_status = 'Inseminated',
                reproductive_status = 'Inseminated',
                updated_at = ?
            WHERE cow_id = ?
        """, (e_date, now, cow_id))
    elif "Positive" in e_type or "Pregnant" in e_type:
        cur.execute("""
            UPDATE cows SET
                pregnancy_status = 'Pregnant',
                reproductive_status = 'Confirmed Pregnant',
                updated_at = ?
            WHERE cow_id = ?
        """, (now, cow_id))
    elif "Estrus" in e_type:
        cur.execute("""
            UPDATE cows SET
                last_observed_estrus_date = ?,
                updated_at = ?
            WHERE cow_id = ?
        """, (e_date, now, cow_id))

    conn.commit()
    conn.close()
    return True


def get_reproductive_history(cow_id=None, db_path=DB_FILE):
    """Retrieve reproductive history records."""
    conn = get_connection(db_path)
    if cow_id:
        df = pd.read_sql_query(
            "SELECT * FROM reproductive_history WHERE cow_id = ? ORDER BY event_date DESC, id DESC",
            conn, params=(str(cow_id).strip(),)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM reproductive_history ORDER BY event_date DESC, id DESC",
            conn
        )
    conn.close()
    return df




# ==========================================
# CSV Import History
# ==========================================

def log_csv_import(filename, category, total, success, rejected, duplicates, status, error_summary, db_path=DB_FILE):
    """Log an import session."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO csv_import_history (
            filename, category, import_date, total_rows,
            success_rows, rejected_rows, duplicate_rows,
            status, error_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename, category, now, total, success, rejected, duplicates, status, error_summary
    ))
    conn.commit()
    conn.close()


def get_csv_import_history(db_path=DB_FILE):
    """Get all CSV import logs."""
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM csv_import_history ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


# ==========================================
# CRUD & Analytics: Sensor Telemetry Records
# ==========================================

def add_sensor_record(rec_dict, db_path=DB_FILE):
    """
    Insert a 2-hour sensor observation interval (activity_index, rumination_minutes).
    Returns (success: bool, message: str).
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cid = str(rec_dict.get("cow_id", "")).strip()
    ts = str(rec_dict.get("timestamp", "")).strip()
    try:
        act = float(rec_dict.get("activity_index", 0.0))
        rum = float(rec_dict.get("rumination_minutes", 0.0))
    except (ValueError, TypeError):
        conn.close()
        return False, "Invalid numerical data for activity_index or rumination_minutes"

    if rum < 0.0 or rum > 120.0:
        conn.close()
        return False, "Rumination minutes must be between 0 and 120 minutes for a 2-hour interval."

    is_demo = int(rec_dict.get("is_demo", 0))

    try:
        cur.execute("""
            INSERT INTO sensor_records (
                cow_id, timestamp, activity_index, rumination_minutes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (cid, ts, act, rum, is_demo, now))
        conn.commit()
        success = True
        msg = "Record inserted successfully."
    except sqlite3.IntegrityError:
        conn.rollback()
        success = False
        msg = f"Duplicate record detected for Cow {cid} at timestamp {ts}."
    except Exception as ex:
        conn.rollback()
        success = False
        msg = str(ex)
    finally:
        conn.close()

    return success, msg


def check_sensor_duplicate(cow_id, timestamp, db_path=DB_FILE):
    """Check if a sensor reading for (cow_id, timestamp) already exists."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sensor_records WHERE cow_id = ? AND timestamp = ?",
        (str(cow_id).strip(), str(timestamp).strip())
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_sensor_records(cow_id=None, start_date=None, end_date=None, db_path=DB_FILE):
    """
    Retrieve sensor records with optional filtering by cow_id and date range.
    Returns DataFrame sorted chronologically (timestamp ASC).
    """
    conn = get_connection(db_path)
    query = "SELECT * FROM sensor_records WHERE 1=1"
    params = []

    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        query += " AND cow_id = ?"
        params.append(str(cow_id).strip())

    if start_date:
        s_str = str(start_date).strip()
        query += " AND timestamp >= ?"
        params.append(s_str)

    if end_date:
        e_str = str(end_date).strip()
        if len(e_str) == 10:
            e_str += " 23:59:59"
        query += " AND timestamp <= ?"
        params.append(e_str)

    query += " ORDER BY timestamp ASC, id ASC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def delete_sensor_record(record_id, db_path=DB_FILE):
    """Delete a single sensor record by ID."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM sensor_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return True


def analyze_sensor_estrus(
    df,
    min_baseline_intervals=24,
    activity_threshold_pct=35.0,
    rumination_drop_pct=25.0
):
    """
    Transparent Rule-Based Estrus Prediction Algorithm using 2-hourly Activity & Rumination telemetry.
    
    Scientific Rules:
    1. Historical Baseline: Evaluates individual cow's diurnal (time-of-day) or rolling median baseline.
       Requires minimum historical readings (default 24 intervals = 2 days of 2h intervals, recommended 14 days).
       If insufficient valid data exists, flags record as 'Insufficient Data' and does not generate false score.
    2. Missing Readings: Never treated as zero (null/missing intervals excluded from baseline).
    3. Activity Index: Unusually elevated activity relative to cow's historical baseline contributes up to 45 pts.
    4. Rumination Time: Unusually suppressed rumination relative to cow's historical baseline contributes up to 35 pts.
    5. Combined Synergy Bonus: When activity increases significantly AND rumination decreases significantly together (+12 pts).
    6. Persistence Bonus: When deviations persist across consecutive 2-hour observation intervals (+8 pts).
    7. Classification:
       - Score >= 70: High Evidence (Probable Estrus Spike)
       - 40 <= Score < 70: Moderate Evidence (Watchlist / Elevated Behaviour)
       - Score < 40: Low Evidence (Normal Herd Baseline)
    
    Returns DataFrame with:
    - cow_id, timestamp, activity_index, rumination_minutes
    - baseline_activity, baseline_rumination
    - activity_change_pct, rumination_change_pct
    - combined_evidence_score (0-100)
    - evidence_category (Low, Moderate, High, or Insufficient Data)
    - explanation
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out_rows = []
    work_df = df.copy()
    work_df['timestamp_dt'] = pd.to_datetime(work_df['timestamp'], errors='coerce')
    work_df = work_df.dropna(subset=['timestamp_dt', 'cow_id'])
    work_df['activity_index'] = pd.to_numeric(work_df['activity_index'], errors='coerce')
    work_df['rumination_minutes'] = pd.to_numeric(work_df['rumination_minutes'], errors='coerce')
    work_df = work_df.sort_values(by=['cow_id', 'timestamp_dt'])

    for cid, cow_group in work_df.groupby('cow_id'):
        valid_cow = cow_group.dropna(subset=['activity_index', 'rumination_minutes'])
        n_obs = len(valid_cow)

        if n_obs < min_baseline_intervals:
            for _, r in cow_group.iterrows():
                out_rows.append({
                    "cow_id": cid,
                    "timestamp": str(r['timestamp']),
                    "timestamp_dt": r['timestamp_dt'],
                    "activity_index": r['activity_index'],
                    "rumination_minutes": r['rumination_minutes'],
                    "baseline_activity": np.nan,
                    "baseline_rumination": np.nan,
                    "activity_change_pct": np.nan,
                    "rumination_change_pct": np.nan,
                    "combined_evidence_score": 0.0,
                    "evidence_category": "Insufficient Data",
                    "explanation": f"Insufficient historical baseline: {n_obs} valid 2-hour intervals recorded (minimum required: {min_baseline_intervals} intervals / ~{max(2, min_baseline_intervals//12)} days). Reliable individual baseline cannot be established."
                })
            continue

        # Sufficient data: compute cow diurnal slot medians
        valid_cow = valid_cow.copy()
        valid_cow['time_slot'] = valid_cow['timestamp_dt'].dt.strftime('%H:00')
        slot_medians_act = valid_cow.groupby('time_slot')['activity_index'].median().to_dict()
        slot_medians_rum = valid_cow.groupby('time_slot')['rumination_minutes'].median().to_dict()

        overall_med_act = float(valid_cow['activity_index'].median())
        overall_med_rum = float(valid_cow['rumination_minutes'].median())

        prev_score = 0.0
        prev_time = None

        for _, r in cow_group.iterrows():
            t_dt = r['timestamp_dt']
            raw_act = r['activity_index']
            raw_rum = r['rumination_minutes']

            if pd.isna(raw_act) or pd.isna(raw_rum):
                out_rows.append({
                    "cow_id": cid,
                    "timestamp": str(r['timestamp']),
                    "timestamp_dt": t_dt,
                    "activity_index": raw_act,
                    "rumination_minutes": raw_rum,
                    "baseline_activity": np.nan,
                    "baseline_rumination": np.nan,
                    "activity_change_pct": np.nan,
                    "rumination_change_pct": np.nan,
                    "combined_evidence_score": 0.0,
                    "evidence_category": "Missing Reading",
                    "explanation": "Sensor reading missing for this interval. Not treated as zero to prevent baseline skew."
                })
                continue

            slot = t_dt.strftime('%H:00')
            base_act = float(slot_medians_act.get(slot, overall_med_act))
            base_rum = float(slot_medians_rum.get(slot, overall_med_rum))

            base_act = max(1.0, base_act)
            base_rum = max(1.0, base_rum)

            act_diff_pct = ((raw_act - base_act) / base_act) * 100.0
            rum_diff_pct = ((raw_rum - base_rum) / base_rum) * 100.0

            # 1. Activity Points (0 to 45 pts)
            act_pts = 0.0
            if act_diff_pct > 0:
                if act_diff_pct < activity_threshold_pct:
                    act_pts = (act_diff_pct / activity_threshold_pct) * 15.0
                elif act_diff_pct < (2.0 * activity_threshold_pct):
                    act_pts = 15.0 + ((act_diff_pct - activity_threshold_pct) / activity_threshold_pct) * 20.0
                else:
                    act_pts = 35.0 + min(10.0, ((act_diff_pct - 2.0 * activity_threshold_pct) / activity_threshold_pct) * 10.0)

            # 2. Rumination Drop Points (0 to 35 pts)
            rum_drop_pct = -rum_diff_pct
            rum_pts = 0.0
            if rum_drop_pct > 0:
                if rum_drop_pct < rumination_drop_pct:
                    rum_pts = (rum_drop_pct / rumination_drop_pct) * 12.0
                elif rum_drop_pct < (2.0 * rumination_drop_pct):
                    rum_pts = 12.0 + ((rum_drop_pct - rumination_drop_pct) / rumination_drop_pct) * 15.0
                else:
                    rum_pts = 27.0 + min(8.0, ((rum_drop_pct - 2.0 * rumination_drop_pct) / rumination_drop_pct) * 8.0)

            # 3. Synergy Bonus (12 pts when both primary signals diverge)
            synergy = 0.0
            if act_diff_pct >= activity_threshold_pct and rum_drop_pct >= rumination_drop_pct:
                synergy = 12.0

            # 4. Consecutive Persistence Bonus (8 pts)
            persistence = 0.0
            if prev_time is not None:
                delta_hrs = (t_dt - prev_time).total_seconds() / 3600.0
                if 1.5 <= delta_hrs <= 2.5 and prev_score >= 40.0:
                    persistence = 8.0

            total_score = min(100.0, round(act_pts + rum_pts + synergy + persistence, 1))

            if total_score >= 70.0:
                cat = "High"
            elif total_score >= 40.0:
                cat = "Moderate"
            else:
                cat = "Low"

            # Explanation
            exp_parts = []
            if act_diff_pct >= activity_threshold_pct:
                exp_parts.append(f"Activity elevated +{act_diff_pct:.1f}% above baseline ({base_act:.1f})")
            elif act_diff_pct > 0:
                exp_parts.append(f"Activity slightly elevated +{act_diff_pct:.1f}%")
            else:
                exp_parts.append(f"Activity normal ({act_diff_pct:.1f}%)")

            if rum_drop_pct >= rumination_drop_pct:
                exp_parts.append(f"rumination suppressed -{rum_drop_pct:.1f}% below baseline ({base_rum:.1f} min)")
            elif rum_drop_pct > 0:
                exp_parts.append(f"rumination slight decrease -{rum_drop_pct:.1f}%")
            else:
                exp_parts.append(f"rumination normal ({rum_diff_pct:+.1f}%)")

            if persistence > 0:
                exp_parts.append("deviation sustained across consecutive 2-hr intervals (+8 pts)")

            if synergy > 0:
                exp_parts.append("concurrent reciprocal divergence (+12 pts)")

            expl = "; ".join(exp_parts) + ". Sensor-derived behavioral evidence; not a confirmed ovulation diagnosis."

            prev_score = total_score
            prev_time = t_dt

            out_rows.append({
                "cow_id": cid,
                "timestamp": str(r['timestamp']),
                "timestamp_dt": t_dt,
                "activity_index": raw_act,
                "rumination_minutes": raw_rum,
                "baseline_activity": round(base_act, 1),
                "baseline_rumination": round(base_rum, 1),
                "activity_change_pct": round(act_diff_pct, 1),
                "rumination_change_pct": round(rum_diff_pct, 1),
                "combined_evidence_score": total_score,
                "evidence_category": cat,
                "explanation": expl
            })

    res_df = pd.DataFrame(out_rows)
    return res_df


# ==========================================
# Database Backup and Restore
# ==========================================

def backup_database(destination_path, db_path=DB_FILE):
    """Create a safe snapshot of the SQLite database."""
    init_db(db_path)
    # Using SQLite backup API for transactionally safe copy
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(destination_path)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    return True


def restore_database(source_path, db_path=DB_FILE):
    """Restore the database from a backup copy."""
    src_conn = sqlite3.connect(source_path)
    dst_conn = sqlite3.connect(db_path)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    return True


# ==========================================
# Synthetic Demonstration Data Generator
# ==========================================

def generate_demo_data(db_path=DB_FILE):
    """
    Populate realistic synthetic dairy farm records labeled as DEMONSTRATION DATA (is_demo=1).
    Avoids duplicate entries if demo data is already present.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Check if demo cows already exist
    cur.execute("SELECT COUNT(*) FROM cows WHERE is_demo = 1")
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return False, "Demonstration data is already loaded."

    today = date.today()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Generate 20 Cows
    cow_templates = [
        ("COW-101", "Bella", "Holstein Friesian", 4.2, 580.0, 3, 28.5, 90, "Confirmed Pregnant", "Healthy", "Pregnant", "High yielding foundation cow"),
        ("COW-102", "Daisy", "Jersey", 3.5, 430.0, 2, 21.0, 140, "Open", "Healthy", "Open", "Good butterfat producer"),
        ("COW-103", "Luna", "Holstein Friesian", 2.8, 540.0, 1, 24.0, 45, "Inseminated", "Healthy", "Inseminated", "First lactation, calm temperament"),
        ("COW-104", "Rosie", "Ayrshire", 5.1, 510.0, 4, 22.5, 210, "Confirmed Pregnant", "Healthy", "Pregnant", "Consistent reproductive history"),
        ("COW-105", "Molly", "Gir", 4.0, 460.0, 3, 16.5, 60, "Open", "Under Observation", "Open", "Indigenous heat-tolerant breed"),
        ("COW-106", "Ruby", "Sahiwal", 3.8, 450.0, 2, 15.0, 110, "Confirmed Pregnant", "Healthy", "Pregnant", "High disease resistance"),
        ("COW-107", "Stella", "Holstein Friesian", 4.5, 600.0, 3, 31.0, 30, "Open", "Under Observation", "In Heat", "Showing strong estrus signs"),
        ("COW-108", "Penny", "Brown Swiss", 5.5, 620.0, 4, 26.0, 180, "Open", "Healthy", "Open", "Robust constitution, high protein yield"),
        ("COW-109", "Willow", "Jersey", 2.5, 410.0, 1, 19.5, 75, "Inseminated", "Healthy", "Inseminated", "Recently bred"),
        ("COW-110", "Chloe", "Holstein Friesian", 3.9, 565.0, 2, 27.0, 120, "Confirmed Pregnant", "Healthy", "Pregnant", "Strong feeder"),
        ("COW-111", "Hazel", "Guernsey", 4.8, 480.0, 3, 20.0, 200, "Open", "Sick", "Open", "Mastitis screening triggered, under care"),
        ("COW-112", "Ginger", "Red Sindhi", 3.2, 420.0, 2, 14.5, 95, "Open", "Healthy", "Open", "Tropical adapted dairy cow"),
        ("COW-113", "Lily", "Holstein Friesian", 6.0, 610.0, 5, 29.0, 240, "Confirmed Pregnant", "Healthy", "Pregnant", "Senior herd matron"),
        ("COW-114", "Zoe", "Jersey", 2.2, 395.0, 1, 18.0, 25, "Open", "Healthy", "In Heat", "Heifer fresh, showing active estrus"),
        ("COW-115", "Nova", "Crossbred", 3.7, 505.0, 2, 23.5, 130, "Open", "Healthy", "Open", "F1 Holstein-Gir cross"),
        ("COW-116", "Maya", "Holstein Friesian", 4.1, 570.0, 3, 26.5, 85, "Confirmed Pregnant", "Healthy", "Pregnant", "Regular cycle before AI"),
        ("COW-117", "Coco", "Jersey", 3.0, 425.0, 2, 20.5, 160, "Open", "Under Observation", "Open", "Slight appetite decrease observed"),
        ("COW-118", "Piper", "Ayrshire", 4.6, 520.0, 3, 23.0, 175, "Inseminated", "Healthy", "Inseminated", "Second insemination service"),
        ("COW-119", "Amber", "Gir", 5.2, 475.0, 4, 17.0, 310, "Open", "Healthy", "Dry", "Late lactation dry-off candidate"),
        ("COW-120", "Olive", "Holstein Friesian", 3.4, 550.0, 2, 25.0, 40, "Open", "Healthy", "Open", "Scheduled for reproductive check")
    ]

    for cid, name, breed, age, wt, lact, d_milk, days_calved, preg, health, rep, rem in cow_templates:
        dob_dt = today - timedelta(days=int(age * 365.25))
        calv_dt = today - timedelta(days=days_calved)
        # estrus date
        estrus_dt = today - timedelta(days=np.random.randint(5, 45))
        insem_dt = estrus_dt if preg in ["Inseminated", "Confirmed Pregnant"] else None

        cur.execute("""
            INSERT INTO cows (
                cow_id, name, breed, dob, age, weight, lactation_number,
                daily_milk_production, last_calving_date, last_observed_estrus_date,
                last_insemination_date, pregnancy_status, health_status,
                reproductive_status, remarks, is_demo, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            cid, name, breed, dob_dt.strftime("%Y-%m-%d"), age, wt, lact,
            d_milk, calv_dt.strftime("%Y-%m-%d"), estrus_dt.strftime("%Y-%m-%d"),
            insem_dt.strftime("%Y-%m-%d") if insem_dt else None,
            preg, health, rep, rem, now_str, now_str
        ))

    # 2. Generate Estrus Observations
    estrus_samples = [
        ("COW-107", 1, 1, 1, 1, 1, 1, 1, 1, 1, 88.0, "High", "Estrus", "Standing to be mounted (+35), Mounting behaviour (+15), Clear mucus (+15), Swollen vulva (+10)"),
        ("COW-114", 1, 1, 1, 1, 1, 0, 1, 1, 0, 78.0, "High", "Estrus", "Standing to be mounted (+35), Restlessness (+10), Mucus (+15), Activity (+10)"),
        ("COW-102", 1, 1, 0, 0, 1, 0, 1, 0, 0, 45.0, "Moderate", "Proestrus", "Increased activity (+10), Restlessness (+10), Mucus (+15), Vocalization (+10)"),
        ("COW-105", 1, 0, 1, 0, 0, 0, 0, 1, 0, 38.0, "Moderate", "Proestrus", "Activity (+10), Mounting (+15), Swollen vulva (+10)"),
        ("COW-120", 0, 1, 0, 0, 1, 0, 0, 0, 0, 20.0, "Low", "Diestrus", "Restlessness (+10), Vocalization (+10)"),
        ("COW-101", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, "Low", "Diestrus", "No behavioral signs detected; confirmed pregnant"),
        ("COW-103", 0, 1, 0, 0, 0, 0, 0, 0, 0, 10.0, "Low", "Diestrus", "Mild restlessness (+10)"),
        ("COW-117", 1, 1, 0, 0, 0, 1, 0, 0, 0, 28.0, "Low", "Metestrus", "Activity (+10), Restlessness (+10), Feed decrease (+8)"),
    ]

    for item in estrus_samples:
        cid, act, rest, mount, stand, voc, feed, mucus, vulva, m_drop, sc, cat, stg, reas = item
        obs_date = today - timedelta(days=np.random.randint(0, 10))
        next_dt = obs_date + timedelta(days=21)
        cur.execute("""
            INSERT INTO estrus_observations (
                cow_id, observation_date, increased_activity, restlessness,
                mounting_behaviour, standing_to_be_mounted, frequent_vocalization,
                reduced_feed_intake, clear_mucus_discharge, swollen_vulva,
                reduced_milk_yield, estrus_score, evidence_category,
                cycle_stage, estimated_next_estrus, score_reasons, notes,
                is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            cid, obs_date.strftime("%Y-%m-%d"), act, rest, mount, stand, voc,
            feed, mucus, vulva, m_drop, sc, cat, stg, next_dt.strftime("%Y-%m-%d"),
            reas, "Demonstration estrus observation record", now_str
        ))

    # Add historical estrus observations across previous cycles (e.g. 21 and 42 days ago)
    for cid in ["COW-102", "COW-104", "COW-107", "COW-110", "COW-116"]:
        for past_days in [21, 42]:
            past_date = today - timedelta(days=past_days + np.random.randint(-1, 2))
            next_estrus = past_date + timedelta(days=21)
            cur.execute("""
                INSERT INTO estrus_observations (
                    cow_id, observation_date, increased_activity, restlessness,
                    mounting_behaviour, standing_to_be_mounted, frequent_vocalization,
                    reduced_feed_intake, clear_mucus_discharge, swollen_vulva,
                    reduced_milk_yield, estrus_score, evidence_category,
                    cycle_stage, estimated_next_estrus, score_reasons, notes,
                    is_demo, created_at
                ) VALUES (?, ?, 1, 1, 1, 1, 0, 0, 1, 1, 0, 80.0, 'High', 'Estrus', ?,
                    'Historical estrus confirmation: Standing heat (+35), Mounting (+15), Mucus (+15)',
                    'Historical cycle baseline record', 1, ?)
            """, (cid, past_date.strftime("%Y-%m-%d"), next_estrus.strftime("%Y-%m-%d"), now_str))

    # 3. Generate Health Monitoring Records
    for cid in [c[0] for c in cow_templates]:
        for days_ago in [0, 2, 5, 10, 15]:
            rec_date = today - timedelta(days=days_ago)
            if cid == "COW-111" and days_ago <= 5:
                # Sick cow (elevated temp, drop in milk)
                temp = round(39.8 + np.random.uniform(0.1, 0.5), 1)
                milk = 11.5
                appetite = "Reduced"
                feed_kg = 8.0
                water_l = 45.0
                act = "Lethargic"
                beh = "Dull"
                symp = "Swollen right-rear quarter, clotty milk, warm udder"
                status = "Critical Alert"
                flags = "High Temp (>39.5°C), Appetite Drop, Severe Milk Drop"
            elif cid in ["COW-107", "COW-114"] and days_ago == 0:
                # In heat cow (slightly elevated temp, restless)
                temp = 39.1
                milk = 24.0
                appetite = "Reduced"
                feed_kg = 14.0
                water_l = 75.0
                act = "Restless"
                beh = "Agitated"
                symp = "Frequent vocalization, clear vaginal mucus"
                status = "Minor Concern"
                flags = "Restless Behaviour, Mild Milk Variance"
            else:
                # Normal cow
                temp = round(38.5 + np.random.uniform(-0.3, 0.4), 1)
                milk = round(22.0 + np.random.uniform(-4.0, 6.0), 1)
                appetite = "Normal"
                feed_kg = 18.0
                water_l = 80.0
                act = "Normal"
                beh = "Normal"
                symp = "None"
                status = "Healthy"
                flags = "Normal parameters"

            cur.execute("""
                INSERT INTO health_records (
                    cow_id, observation_date, body_temperature, milk_production,
                    appetite, feed_intake, water_intake, activity_level,
                    behaviour, symptoms, health_status, abnormality_flags,
                    health_notes, is_demo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                cid, rec_date.strftime("%Y-%m-%d"), temp, milk,
                appetite, feed_kg, water_l, act, beh, symp,
                status, flags, "Routine herd health screening entry", now_str
            ))

    # 4. Generate Disease Risk Assessments
    disease_cases = [
        ("COW-111", "High concern", "Moderate concern", "Low concern", "Low concern", "High concern",
         1, 1, 1, 1, 1, 1, "None", "None",
         "Classical mastitis symptoms present: swollen painful quarter, abnormal clotty milk, body temp > 39.5°C, milk yield drop > 35%. Immediate veterinary intervention and CMT confirmation recommended.",
         "Quarantine pen 2, antibiotic therapy pending vet confirmation.", 1),

        ("COW-105", "Low concern", "Low concern", "Moderate concern", "Low concern", "Moderate concern",
         0, 0, 0, 0, 0, 0, "Reduced cud chewing, slightly loose stool", "None",
         "Mild rumen fill reduction and loose consistency noted. Monitor fiber intake and mineral mix.",
         "Add supplemental dry hay, re-evaluate rumen motility tomorrow.", 0),

        ("COW-117", "Low concern", "Moderate concern", "Moderate concern", "Low concern", "Moderate concern",
         0, 0, 0, 0, 1, 0, "Mild anorexia", "None",
         "Elevated temperature (39.3°C) and partial feed refusal. Possible early systemic challenge or heat influence.",
         "Hydration check and shade enclosure provided.", 0),

        ("COW-101", "Low concern", "Low concern", "Low concern", "Low concern", "Low concern",
         0, 0, 0, 0, 0, 0, "None", "None",
         "All health and clinical indicators within physiological baseline ranges.",
         "Routine herd inspection clear.", 0),

        ("COW-107", "Low concern", "Low concern", "Low concern", "Low concern", "Low concern",
         0, 0, 0, 0, 0, 0, "None", "Clear physiological estrus discharge",
         "Signs consistent with normal estrous cycle expression without pathological markers.",
         "Eligible for insemination timing.", 0)
    ]

    for item in disease_cases:
        cid, mast, sys, dig, rep, ov, us, up, ua, am, et, ry, ds, rs, rat, notes, vet = item
        cur.execute("""
            INSERT INTO disease_assessments (
                cow_id, assessment_date, mastitis_risk, systemic_risk,
                digestive_risk, reproductive_risk, overall_concern,
                udder_swelling, udder_pain, abnormal_udder_appearance,
                abnormal_milk, elevated_temp, reduced_yield,
                digestive_symptoms, reproductive_symptoms, rationale,
                screening_notes, vet_consultation_recommended, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            cid, today.strftime("%Y-%m-%d"), mast, sys, dig, rep, ov,
            us, up, ua, am, et, ry, ds, rs, rat, notes, vet, now_str
        ))

    # 5. Generate Comprehensive 30-Day THI Records (Covering cool, mild, significant, and severe heat stress)
    for d_off in range(30, -1, -1):
        rec_dt = today - timedelta(days=d_off)
        if d_off in [1, 2, 8, 9, 10]:
            # Severe heatwave period (THI > 80)
            m_t, m_rh = 26.5, 75.0
            n_t, n_rh = 34.5, 78.0
            e_t, e_rh = 29.0, 72.0
            cond = "Severe heatwave condition"
        elif d_off in [0, 3, 7, 11, 12, 18, 19]:
            # Significant heat stress (THI 72-79)
            m_t, m_rh = 24.0, 70.0
            n_t, n_rh = 30.5, 72.0
            e_t, e_rh = 27.0, 68.0
            cond = "Significant heat stress exposure"
        elif d_off in [4, 5, 13, 14, 20, 21, 25]:
            # Mild heat stress (THI 68-71)
            m_t, m_rh = 21.5, 62.0
            n_t, n_rh = 26.5, 65.0
            e_t, e_rh = 23.0, 60.0
            cond = "Mild thermal stress"
        else:
            # Optimal cow comfort zone (THI < 68)
            m_t, m_rh = 18.0, 52.0
            n_t, n_rh = 22.5, 55.0
            e_t, e_rh = 19.5, 50.0
            cond = "Optimal thermal comfort"

        for t_str, temp, rh, note in [
            ("08:00", m_t, m_rh, f"{cond} – morning baseline"),
            ("14:00", n_t, n_rh, f"{cond} – afternoon solar peak"),
            ("19:00", e_t, e_rh, f"{cond} – evening cooling")
        ]:
            thi_val = calculate_thi(temp, rh)
            cat = classify_thi(thi_val)
            cur.execute("""
                INSERT INTO thi_records (
                    observation_date, observation_time, ambient_temp,
                    relative_humidity, thi_value, heat_stress_category,
                    notes, is_demo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                rec_dt.strftime("%Y-%m-%d"), t_str, temp, rh, thi_val, cat, note, now_str
            ))

    # 6. Generate Milk Records (Last 14 days for all 20 cows with realistic thermal depression)
    for cid, _, _, _, _, _, base_yield, _, _, _, _, _ in cow_templates:
        for d_off in range(14, -1, -1):
            m_dt = today - timedelta(days=d_off)
            
            # Base biological daily fluctuation
            variation = np.random.uniform(-1.0, 1.0)
            
            # Heat stress depression factor based on day's heat level
            if d_off in [1, 2, 8, 9, 10]:
                heat_loss = np.random.uniform(2.8, 4.2)  # Severe heat depression
            elif d_off in [0, 3, 7, 11, 12]:
                heat_loss = np.random.uniform(1.2, 2.2)  # Moderate heat depression
            elif d_off in [4, 5, 13, 14]:
                heat_loss = np.random.uniform(0.3, 0.8)  # Mild heat impact
            else:
                heat_loss = 0.0

            total = max(3.0, round(base_yield + variation - heat_loss, 2))
            
            # Specific drop for COW-111 during recent sick days
            if cid == "COW-111" and d_off <= 4:
                total = round(base_yield * 0.55, 2)
            
            m_part = round(total * 0.58, 2)
            e_part = round(total - m_part, 2)
            is_drop = 1 if (cid == "COW-111" and d_off <= 4) or (heat_loss >= 3.5) else 0

            cur.execute("""
                INSERT INTO milk_records (
                    cow_id, production_date, morning_yield, evening_yield,
                    total_yield, is_drop_alert, notes, is_demo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                cid, m_dt.strftime("%Y-%m-%d"), m_part, e_part, total, is_drop,
                "Demonstration automated yield record", now_str
            ))

    # 7. Generate Reproductive History
    rep_events = [
        ("COW-101", 90, "Calving", "Normal unassisted delivery of female calf. Good mothering instincts.", "Farm Staff", "Successful Calf"),
        ("COW-101", 60, "Estrus Observed", "Standing heat confirmed, strong mucus. AI scheduled.", "Dr. Sharma", "Bred"),
        ("COW-101", 59, "Artificial Insemination", "Straw #HF-9042 high-index sire used. Good uterine tone.", "Dr. Sharma", "Completed"),
        ("COW-101", 20, "Pregnancy Check - Positive", "Transrectal ultrasonography confirmed viable embryo at 39 days.", "Dr. Patel", "Confirmed Pregnant"),
        ("COW-102", 140, "Calving", "Assisted twin birth; calf 1 healthy, calf 2 healthy.", "Dr. Sharma", "Successful Calves"),
        ("COW-102", 18, "Estrus Observed", "Moderate estrus signs observed during paddock turn-out.", "Herdsman John", "Observation Logged"),
        ("COW-103", 45, "Calving", "Heifer first calving, unassisted.", "Farm Staff", "Single Male Calf"),
        ("COW-103", 24, "Estrus Observed", "Active mounting behavior recorded.", "Herdsman John", "Scheduled AI"),
        ("COW-103", 23, "Artificial Insemination", "Sexed female semen straw #HF-1022 used.", "Dr. Sharma", "Pending Check"),
        ("COW-104", 210, "Calving", "Normal calving, bull calf born.", "Farm Staff", "Calf Vigorous"),
        ("COW-104", 150, "Artificial Insemination", "Ayrshire champion bull semen used.", "Dr. Patel", "Confirmed Pregnant"),
        ("COW-107", 30, "Calving", "Fourth lactation commencement.", "Farm Staff", "Normal Calf"),
        ("COW-107", 2, "Estrus Observed", "Intense standing heat, clear discharge, restless.", "Herdsman John", "AI Candidate Today"),
        ("COW-111", 200, "Calving", "Normal delivery.", "Farm Staff", "Normal Calf"),
        ("COW-114", 25, "Calving", "Heifer first fresh calving.", "Farm Staff", "Female Calf"),
        ("COW-114", 1, "Estrus Observed", "First postpartum estrus observed on paddock camera.", "Herdsman John", "Observation Logged"),
        ("COW-119", 310, "Calving", "Previous calving milestone.", "Farm Staff", "Healthy Calf"),
        ("COW-119", 10, "Dry Off", "Routine dry cow therapy administered, quarters sealed.", "Dr. Sharma", "Dry Period Started")
    ]

    for cid, d_ago, etype, det, tech, outc in rep_events:
        e_date = today - timedelta(days=d_ago)
        cur.execute("""
            INSERT INTO reproductive_history (
                cow_id, event_date, event_type, details,
                technician_or_sire, outcome, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            cid, e_date.strftime("%Y-%m-%d"), etype, det, tech, outc, now_str
        ))

    # 8. Generate 2-Hourly Sensor Telemetry (Activity Index & Rumination Minutes) for Past 14 Days
    sensor_rows = []
    times_of_day = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    diurnal_profile = {
        "00:00": (30.0, 58.0),
        "02:00": (26.0, 62.0),
        "04:00": (32.0, 56.0),
        "06:00": (58.0, 32.0),
        "08:00": (68.0, 26.0),
        "10:00": (52.0, 42.0),
        "12:00": (46.0, 46.0),
        "14:00": (48.0, 44.0),
        "16:00": (64.0, 30.0),
        "18:00": (60.0, 34.0),
        "20:00": (42.0, 48.0),
        "22:00": (34.0, 54.0),
    }

    for cid, _, _, _, _, _, _, _, _, _, _, _ in cow_templates:
        if cid == "COW-120":
            # Newly registered cow with only 6 recent intervals to showcase 'Insufficient Data' handling
            days_to_gen = [0]
            tod_list = times_of_day[-6:]
        else:
            days_to_gen = list(range(14, -1, -1))
            tod_list = times_of_day

        for d_ago in days_to_gen:
            curr_date = (today - timedelta(days=d_ago)).strftime("%Y-%m-%d")
            for t_str in tod_list:
                ts = f"{curr_date} {t_str}"
                base_act, base_rum = diurnal_profile[t_str]
                cow_hash = hash(cid) % 7
                act = base_act + cow_hash + np.random.normal(0, 3.5)
                rum = base_rum - (cow_hash * 0.5) + np.random.normal(0, 3.0)

                # COW-107 and COW-114 (In Heat): high activity surge & rumination crash
                if cid in ["COW-107", "COW-114"]:
                    if (d_ago == 1 and t_str in ["16:00", "18:00", "20:00", "22:00"]) or (d_ago == 0 and t_str in ["00:00", "02:00", "04:00"]):
                        act = base_act * 2.2 + np.random.uniform(15, 30)
                        rum = max(6.0, base_rum * 0.28 - np.random.uniform(2, 6))

                # COW-105: moderate behavioral deviation on day 2 ago
                if cid == "COW-105" and d_ago == 2 and t_str in ["08:00", "10:00"]:
                    act = base_act * 1.5 + 5.0
                    rum = max(15.0, base_rum * 0.65)

                act = round(max(5.0, act), 1)
                rum = round(min(120.0, max(0.0, rum)), 1)
                sensor_rows.append((cid, ts, act, rum, 1, now_str))

    cur.executemany("""
        INSERT OR IGNORE INTO sensor_records (
            cow_id, timestamp, activity_index, rumination_minutes, is_demo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, sensor_rows)

    conn.commit()
    conn.close()
    return True, "Demonstration data successfully populated across all tables."


def clear_demo_data(db_path=DB_FILE):
    """
    Remove all demonstration records (is_demo = 1) across all tables with transaction safety.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM estrus_observations WHERE is_demo = 1")
        cur.execute("DELETE FROM sensor_records WHERE is_demo = 1")
        cur.execute("DELETE FROM health_records WHERE is_demo = 1")
        cur.execute("DELETE FROM disease_assessments WHERE is_demo = 1")
        cur.execute("DELETE FROM thi_records WHERE is_demo = 1")
        cur.execute("DELETE FROM milk_records WHERE is_demo = 1")
        cur.execute("DELETE FROM reproductive_history WHERE is_demo = 1")
        cur.execute("DELETE FROM cows WHERE is_demo = 1")
        conn.commit()
        conn.close()
        return True, "All demonstration data cleared successfully."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Failed to clear demo data: {str(e)}"


# ==========================================
# Dashboard & KPI Statistics Helper
# ==========================================

def get_dashboard_kpis(db_path=DB_FILE):
    """Calculate key performance indicators directly from SQLite records."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    # 1. Total & Active cows
    cur.execute("SELECT COUNT(*) FROM cows")
    total_cows = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cows WHERE reproductive_status != 'Dry'")
    active_cows = cur.fetchone()[0]

    # 2. Cows showing high estrus evidence in last 7 days
    seven_days_ago = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    cur.execute("""
        SELECT COUNT(DISTINCT cow_id) FROM estrus_observations
        WHERE estrus_score >= 65.0 AND observation_date >= ?
    """, (seven_days_ago,))
    high_estrus_count = cur.fetchone()[0]

    # 3. Cows requiring health attention
    cur.execute("""
        SELECT COUNT(DISTINCT cow_id) FROM health_records
        WHERE health_status IN ('Under Observation', 'Sick', 'Critical Alert', 'Minor Concern')
        AND observation_date >= ?
    """, (seven_days_ago,))
    health_attention_count = cur.fetchone()[0]

    # Also count cows whose cow record health_status is not Healthy
    cur.execute("SELECT COUNT(*) FROM cows WHERE health_status != 'Healthy'")
    cows_sick_record = cur.fetchone()[0]
    total_health_concern = max(health_attention_count, cows_sick_record)

    # 4. Cows under heat stress concern (latest THI reading)
    cur.execute("SELECT thi_value, heat_stress_category FROM thi_records ORDER BY observation_date DESC, observation_time DESC, id DESC LIMIT 1")
    latest_thi_row = cur.fetchone()
    latest_thi = latest_thi_row[0] if latest_thi_row else None
    latest_thi_cat = latest_thi_row[1] if latest_thi_row else "Normal"
    thi_stress_active = (latest_thi >= 72.0) if latest_thi else False

    # 5. Total daily milk & average milk
    today_str = date.today().strftime("%Y-%m-%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    cur.execute("SELECT SUM(total_yield), AVG(total_yield) FROM milk_records WHERE production_date = ?", (today_str,))
    milk_row = cur.fetchone()
    total_milk = milk_row[0]
    avg_milk = milk_row[1]

    if total_milk is None or total_milk == 0:
        cur.execute("SELECT SUM(total_yield), AVG(total_yield) FROM milk_records WHERE production_date = ?", (yesterday_str,))
        milk_row = cur.fetchone()
        total_milk = milk_row[0] or 0.0
        avg_milk = milk_row[1] or 0.0

    if total_milk == 0 and total_cows > 0:
        cur.execute("SELECT SUM(daily_milk_production), AVG(daily_milk_production) FROM cows")
        crow = cur.fetchone()
        total_milk = crow[0] or 0.0
        avg_milk = crow[1] or 0.0

    # 6. Upcoming estimated estrus windows in next 7 days
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    next_week_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    cur.execute("""
        SELECT COUNT(DISTINCT cow_id) FROM estrus_observations
        WHERE estimated_next_estrus BETWEEN ? AND ?
    """, (today_str, next_week_str))
    upcoming_estrus_count = cur.fetchone()[0]

    # 7. Sensor Telemetry KPIs
    total_sensor_records = 0
    sensor_high_estrus_count = 0
    try:
        cur.execute("SELECT COUNT(*) FROM sensor_records")
        total_sensor_records = cur.fetchone()[0]
        if total_sensor_records > 0:
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
            cur.execute("""
                SELECT DISTINCT cow_id FROM sensor_records WHERE timestamp >= ?
            """, (two_days_ago,))
            recent_cids = [r[0] for r in cur.fetchall()]
            if recent_cids:
                q = f"SELECT * FROM sensor_records WHERE cow_id IN ({','.join(['?']*len(recent_cids))})"
                s_df = pd.read_sql_query(q, conn, params=recent_cids)
                if not s_df.empty:
                    analyzed = analyze_sensor_estrus(s_df, min_baseline_intervals=12)
                    if not analyzed.empty and 'evidence_category' in analyzed.columns:
                        recent_high = analyzed[
                            (analyzed['timestamp'] >= two_days_ago) & 
                            (analyzed['evidence_category'] == 'High')
                        ]
                        sensor_high_estrus_count = int(recent_high['cow_id'].nunique())
    except Exception:
        pass

    # 8. Check if any demo data exists
    cur.execute("SELECT COUNT(*) FROM cows WHERE is_demo = 1")
    demo_count = cur.fetchone()[0]
    has_demo = demo_count > 0

    conn.close()

    return {
        "total_cows": total_cows,
        "active_cows": active_cows,
        "high_estrus_count": high_estrus_count,
        "health_attention_count": total_health_concern,
        "latest_thi": latest_thi,
        "latest_thi_category": latest_thi_cat,
        "thi_stress_active": thi_stress_active,
        "total_daily_milk": round(total_milk, 1),
        "avg_daily_milk": round(avg_milk, 1),
        "upcoming_estrus_count": upcoming_estrus_count,
        "total_sensor_records": total_sensor_records,
        "sensor_high_estrus_count": sensor_high_estrus_count,
        "has_demo": has_demo
    }
