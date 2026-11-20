"""
BoviSense – Intelligent Dairy Cow Management and Monitoring Platform
database.py: Unified SQLite Database Operations, Scientific Analytics & Processing
"""

import sqlite3
import os
import shutil
from datetime import datetime, date, timedelta
from contextlib import contextmanager
import pandas as pd
import numpy as np

DB_FILE = "bovisense.db"


# ==========================================
# Database Connection & Transaction Helpers
# ==========================================

def get_connection(db_path=DB_FILE):
    """Create and return a SQLite connection with dictionary row access."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session(db_path=DB_FILE):
    """
    Context manager providing safe transaction management.
    Commits on success, rolls back on error, and guarantees connection closure.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_df(query, params=(), db_path=DB_FILE):
    """Execute a SQL SELECT query and return results as a Pandas DataFrame."""
    conn = get_connection(db_path)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def execute_write(query, params=(), db_path=DB_FILE):
    """Execute a single INSERT/UPDATE/DELETE query within an auto-committing session."""
    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.lastrowid


def delete_record(table, record_id, id_col="id", db_path=DB_FILE):
    """Generic helper to delete a record by ID."""
    with db_session(db_path) as conn:
        conn.cursor().execute(f"DELETE FROM {table} WHERE {id_col} = ?", (record_id,))
    return True


# ==========================================
# Schema Initialization
# ==========================================

def init_db(db_path=DB_FILE):
    """Initialize all SQLite tables and required indexes."""
    with db_session(db_path) as conn:
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

        # 2. Estrus Observations Table (Manual Visual Signs)
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

        # 5. THI Records Table (Environmental Weather)
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

        # Indexes for fast lookup & filtering
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cows_breed ON cows(breed);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cows_rep_status ON cows(reproductive_status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_estrus_cow_date ON estrus_observations(cow_id, observation_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_health_cow_date ON health_records(cow_id, observation_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_disease_cow_date ON disease_assessments(cow_id, assessment_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_thi_date ON thi_records(observation_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_milk_cow_date ON milk_records(cow_id, production_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rep_cow_date ON reproductive_history(cow_id, event_date);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_cow_time ON sensor_records(cow_id, timestamp);")


# ==========================================
# CRUD Operations: Cows
# ==========================================

def get_all_cows(db_path=DB_FILE):
    """Retrieve all cow records as a pandas DataFrame."""
    return query_df("SELECT * FROM cows ORDER BY cow_id ASC", db_path=db_path)


def get_cow(cow_id, db_path=DB_FILE):
    """Retrieve a single cow dictionary by cow_id."""
    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cows WHERE cow_id = ?", (str(cow_id).strip(),))
        row = cur.fetchone()
        return dict(row) if row else None


def add_cow(cow_dict, db_path=DB_FILE):
    """Insert a new cow record."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dob = cow_dict.get("dob")
    age = cow_dict.get("age")
    if dob and (age is None or age == 0):
        try:
            d = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
            age = round((date.today() - d).days / 365.25, 1)
        except Exception:
            age = None

    q = """
    INSERT INTO cows (
        cow_id, name, breed, dob, age, weight, lactation_number,
        daily_milk_production, last_calving_date, last_observed_estrus_date,
        last_insemination_date, pregnancy_status, health_status,
        reproductive_status, remarks, is_demo, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
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
        now, now
    )
    execute_write(q, params, db_path=db_path)
    return True


def update_cow(cow_id, cow_dict, db_path=DB_FILE):
    """Update an existing cow record."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dob = cow_dict.get("dob")
    age = cow_dict.get("age")
    if dob and (age is None or age == 0):
        try:
            d = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
            age = round((date.today() - d).days / 365.25, 1)
        except Exception:
            age = None

    q = """
    UPDATE cows SET
        name = ?, breed = ?, dob = ?, age = ?, weight = ?,
        lactation_number = ?, daily_milk_production = ?,
        last_calving_date = ?, last_observed_estrus_date = ?,
        last_insemination_date = ?, pregnancy_status = ?,
        health_status = ?, reproductive_status = ?,
        remarks = ?, updated_at = ?
    WHERE cow_id = ?
    """
    params = (
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
    )
    execute_write(q, params, db_path=db_path)
    return True


def delete_cow(cow_id, db_path=DB_FILE):
    """Delete a cow record by cow_id."""
    return delete_record("cows", str(cow_id).strip(), id_col="cow_id", db_path=db_path)


# ==========================================
# CRUD Operations: Estrus Observations (Manual Signs)
# ==========================================

def add_estrus_observation(obs_dict, db_path=DB_FILE):
    """Insert an estrus observation and update cow's last observed estrus if high evidence."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Process selected_markers for persistent storage
    raw_markers = obs_dict.get("selected_markers")
    if isinstance(raw_markers, (list, tuple, set)):
        markers_str = ", ".join(raw_markers)
    elif raw_markers and str(raw_markers).strip() and str(raw_markers).strip().lower() != "none":
        markers_str = str(raw_markers).strip()
    else:
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

    cow_id = str(obs_dict.get("cow_id")).strip()
    obs_date = str(obs_dict.get("observation_date"))
    score = float(obs_dict.get("estrus_score", 0.0))
    category = str(obs_dict.get("evidence_category", "Low"))

    with db_session(db_path) as conn:
        cur = conn.cursor()
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
            cow_id, obs_date, markers_str,
            int(obs_dict.get("increased_activity", 0)),
            int(obs_dict.get("restlessness", 0)),
            int(obs_dict.get("mounting_behaviour", 0)),
            int(obs_dict.get("standing_to_be_mounted", 0)),
            int(obs_dict.get("frequent_vocalization", 0)),
            int(obs_dict.get("reduced_feed_intake", 0)),
            int(obs_dict.get("clear_mucus_discharge", 0)),
            int(obs_dict.get("swollen_vulva", 0)),
            int(obs_dict.get("reduced_milk_yield", 0)),
            score, category,
            str(obs_dict.get("cycle_stage", "Unknown")),
            str(obs_dict.get("estimated_next_estrus")) if obs_dict.get("estimated_next_estrus") else None,
            str(obs_dict.get("score_reasons", "")),
            str(obs_dict.get("notes", "")),
            int(obs_dict.get("is_demo", 0)),
            now
        ))

        if category == "High":
            cur.execute("""
                UPDATE cows SET
                    last_observed_estrus_date = ?,
                    reproductive_status = 'In Heat',
                    updated_at = ?
                WHERE cow_id = ?
            """, (obs_date, now, cow_id))
    return True


def get_estrus_observations(cow_id=None, db_path=DB_FILE):
    """Retrieve estrus observations, optionally filtered by cow_id with backward-compatible marker formatting."""
    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        df = query_df(
            "SELECT * FROM estrus_observations WHERE cow_id = ? ORDER BY observation_date DESC, id DESC",
            params=(str(cow_id).strip(),), db_path=db_path
        )
    else:
        df = query_df(
            "SELECT * FROM estrus_observations ORDER BY observation_date DESC, id DESC",
            db_path=db_path
        )

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


def delete_estrus_observation(obs_id, db_path=DB_FILE):
    return delete_record("estrus_observations", obs_id, db_path=db_path)


# ==========================================
# CRUD Operations: Health Records
# ==========================================

def add_health_record(rec_dict, db_path=DB_FILE):
    """Insert a health monitoring record and update cow health status."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp = float(rec_dict.get("body_temperature", 38.6))
    symptoms = str(rec_dict.get("symptoms", "None"))
    appetite = str(rec_dict.get("appetite", "Normal"))

    flags = []
    if temp > 39.5:
        flags.append("High Fever")
    elif temp < 38.0:
        flags.append("Hypothermia")
    if appetite in ["Poor", "Anorexic", "Reduced"]:
        flags.append("Appetite Drop")
    if "mastitis" in symptoms.lower():
        flags.append("Suspected Mastitis")

    status = "Healthy"
    if any(f in ["High Fever", "Hypothermia", "Suspected Mastitis"] for f in flags):
        status = "Critical Alert" if temp > 40.5 else "Under Observation"
    elif flags:
        status = "Minor Concern"

    cow_id = str(rec_dict.get("cow_id")).strip()
    obs_date = str(rec_dict.get("observation_date"))

    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO health_records (
                cow_id, observation_date, body_temperature, milk_production,
                appetite, feed_intake, water_intake, activity_level,
                behaviour, symptoms, health_status, abnormality_flags,
                health_notes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cow_id, obs_date, temp,
            float(rec_dict.get("milk_production", 0.0)) if rec_dict.get("milk_production") else None,
            appetite,
            float(rec_dict.get("feed_intake", 0.0)) if rec_dict.get("feed_intake") else None,
            float(rec_dict.get("water_intake", 0.0)) if rec_dict.get("water_intake") else None,
            str(rec_dict.get("activity_level", "Normal")),
            str(rec_dict.get("behaviour", "Normal")),
            symptoms, status, "; ".join(flags),
            str(rec_dict.get("health_notes", "")),
            int(rec_dict.get("is_demo", 0)),
            now
        ))

        cur.execute("UPDATE cows SET health_status = ?, updated_at = ? WHERE cow_id = ?", (status, now, cow_id))
    return True


def get_health_records(cow_id=None, db_path=DB_FILE):
    """Retrieve health records, optionally filtered by cow_id."""
    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        return query_df(
            "SELECT * FROM health_records WHERE cow_id = ? ORDER BY observation_date DESC, id DESC",
            params=(str(cow_id).strip(),), db_path=db_path
        )
    return query_df("SELECT * FROM health_records ORDER BY observation_date DESC, id DESC", db_path=db_path)


def delete_health_record(rec_id, db_path=DB_FILE):
    return delete_record("health_records", rec_id, db_path=db_path)


# ==========================================
# CRUD Operations: Disease Risk Assessments
# ==========================================

def add_disease_assessment(rec_dict, db_path=DB_FILE):
    """Insert a disease risk assessment."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    q = """
    INSERT INTO disease_assessments (
        cow_id, assessment_date, mastitis_risk, systemic_risk,
        digestive_risk, reproductive_risk, overall_concern,
        udder_swelling, udder_pain, abnormal_udder_appearance,
        abnormal_milk, elevated_temp, reduced_yield,
        digestive_symptoms, reproductive_symptoms, rationale,
        screening_notes, vet_consultation_recommended, is_demo, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
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
        str(rec_dict.get("digestive_symptoms", "None")),
        str(rec_dict.get("reproductive_symptoms", "None")),
        str(rec_dict.get("rationale", "")),
        str(rec_dict.get("screening_notes", "")),
        int(rec_dict.get("vet_consultation_recommended", 0)),
        int(rec_dict.get("is_demo", 0)),
        now
    )
    execute_write(q, params, db_path=db_path)
    return True


def get_disease_assessments(cow_id=None, db_path=DB_FILE):
    """Retrieve disease assessments, optionally filtered by cow_id."""
    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        return query_df(
            "SELECT * FROM disease_assessments WHERE cow_id = ? ORDER BY assessment_date DESC, id DESC",
            params=(str(cow_id).strip(),), db_path=db_path
        )
    return query_df("SELECT * FROM disease_assessments ORDER BY assessment_date DESC, id DESC", db_path=db_path)


def delete_disease_assessment(rec_id, db_path=DB_FILE):
    return delete_record("disease_assessments", rec_id, db_path=db_path)


# ==========================================
# THI Calculations & Records (Weather Biometeorology)
# ==========================================

def calculate_thi(temp_c, rh):
    """
    Standard Dairy NRC THI equation:
    THI = (1.8 * T + 32) - ((0.55 - 0.0055 * RH) * (1.8 * T - 26))
    where T is environmental temperature in Celsius and RH is relative humidity in percentage.
    Operates strictly on ambient variables; cow body temperature is NEVER used.
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
        return "Unknown"


def add_thi_record(rec_dict, db_path=DB_FILE):
    """Insert an environmental THI weather observation."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    t = float(rec_dict.get("ambient_temp", 25.0))
    rh = float(rec_dict.get("relative_humidity", 60.0))
    thi = float(rec_dict.get("thi_value", calculate_thi(t, rh)))
    cat = str(rec_dict.get("heat_stress_category", classify_thi(thi)))

    q = """
    INSERT INTO thi_records (
        observation_date, observation_time, ambient_temp, relative_humidity,
        thi_value, heat_stress_category, notes, is_demo, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        str(rec_dict.get("observation_date")),
        str(rec_dict.get("observation_time", "12:00")),
        t, rh, thi, cat,
        str(rec_dict.get("notes", "")),
        int(rec_dict.get("is_demo", 0)),
        now
    )
    execute_write(q, params, db_path=db_path)
    return True


def get_thi_records(db_path=DB_FILE):
    """Retrieve all THI records ordered by date and time descending."""
    return query_df(
        "SELECT * FROM thi_records ORDER BY observation_date DESC, observation_time DESC, id DESC",
        db_path=db_path
    )


def delete_thi_record(rec_id, db_path=DB_FILE):
    return delete_record("thi_records", rec_id, db_path=db_path)


# ==========================================
# CRUD Operations: Milk Records
# ==========================================

def add_milk_record(rec_dict, db_path=DB_FILE):
    """Insert a milk record and update cow's daily milk production and drop alert."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cow_id = str(rec_dict.get("cow_id")).strip()
    m_yield = float(rec_dict.get("morning_yield", 0.0))
    e_yield = float(rec_dict.get("evening_yield", 0.0))
    t_yield = rec_dict.get("total_yield")
    if t_yield is None or float(t_yield) == 0.0:
        t_yield = round(m_yield + e_yield, 2)
    else:
        t_yield = round(float(t_yield), 2)

    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT AVG(total_yield) FROM milk_records
            WHERE cow_id = ? ORDER BY production_date DESC LIMIT 5
        """, (cow_id,))
        row = cur.fetchone()
        avg_prev = row[0] if (row and row[0]) else None
        drop_alert = 1 if (avg_prev and avg_prev > 5.0 and t_yield < (0.75 * avg_prev)) else 0

        cur.execute("""
            INSERT INTO milk_records (
                cow_id, production_date, morning_yield, evening_yield,
                total_yield, is_drop_alert, notes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cow_id, str(rec_dict.get("production_date")),
            m_yield, e_yield, t_yield, drop_alert,
            str(rec_dict.get("notes", "")),
            int(rec_dict.get("is_demo", 0)),
            now
        ))

        cur.execute("UPDATE cows SET daily_milk_production = ?, updated_at = ? WHERE cow_id = ?", (t_yield, now, cow_id))
    return True


def get_milk_records(cow_id=None, db_path=DB_FILE):
    """Retrieve milk records, optionally filtered by cow_id."""
    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        return query_df(
            "SELECT * FROM milk_records WHERE cow_id = ? ORDER BY production_date DESC, id DESC",
            params=(str(cow_id).strip(),), db_path=db_path
        )
    return query_df("SELECT * FROM milk_records ORDER BY production_date DESC, id DESC", db_path=db_path)


def delete_milk_record(rec_id, db_path=DB_FILE):
    return delete_record("milk_records", rec_id, db_path=db_path)


# ==========================================
# CRUD Operations: Reproductive History
# ==========================================

def add_reproductive_event(rec_dict, db_path=DB_FILE):
    """Insert a reproductive event and synchronize cow reproductive dates and statuses."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cow_id = str(rec_dict.get("cow_id")).strip()
    e_date = str(rec_dict.get("event_date"))
    e_type = str(rec_dict.get("event_type", "Estrus Observed"))

    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reproductive_history (
                cow_id, event_date, event_type, details,
                technician_or_sire, outcome, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cow_id, e_date, e_type,
            str(rec_dict.get("details", "")),
            str(rec_dict.get("technician_or_sire", "")),
            str(rec_dict.get("outcome", "")),
            int(rec_dict.get("is_demo", 0)),
            now
        ))

        # Status sync rules
        if "inseminat" in e_type.lower():
            cur.execute("""
                UPDATE cows SET
                    last_insemination_date = ?,
                    pregnancy_status = 'Inseminated',
                    reproductive_status = 'Inseminated',
                    updated_at = ?
                WHERE cow_id = ?
            """, (e_date, now, cow_id))
        elif "calv" in e_type.lower():
            cur.execute("""
                UPDATE cows SET
                    last_calving_date = ?,
                    pregnancy_status = 'Open',
                    reproductive_status = 'Open',
                    updated_at = ?
                WHERE cow_id = ?
            """, (e_date, now, cow_id))
        elif "pregnant" in e_type.lower() or "confirmed" in str(rec_dict.get("outcome", "")).lower():
            cur.execute("""
                UPDATE cows SET
                    pregnancy_status = 'Pregnant',
                    reproductive_status = 'Confirmed Pregnant',
                    updated_at = ?
                WHERE cow_id = ?
            """, (now, cow_id))
        elif "dry" in e_type.lower():
            cur.execute("""
                UPDATE cows SET reproductive_status = 'Dry', updated_at = ? WHERE cow_id = ?
            """, (now, cow_id))
    return True


def get_reproductive_history(cow_id=None, db_path=DB_FILE):
    """Retrieve reproductive history records, optionally filtered by cow_id."""
    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        return query_df(
            "SELECT * FROM reproductive_history WHERE cow_id = ? ORDER BY event_date DESC, id DESC",
            params=(str(cow_id).strip(),), db_path=db_path
        )
    return query_df("SELECT * FROM reproductive_history ORDER BY event_date DESC, id DESC", db_path=db_path)


def delete_reproductive_event(rec_id, db_path=DB_FILE):
    return delete_record("reproductive_history", rec_id, db_path=db_path)


# ==========================================
# CRUD & Analytics: Sensor Telemetry Records
# ==========================================

def add_sensor_record(rec_dict, db_path=DB_FILE):
    """
    Insert a 2-hour sensor observation interval (activity_index, rumination_minutes).
    Validates rumination between 0 and 120 minutes. Prevents duplicate (cow_id, timestamp).
    Returns (success: bool, message: str).
    """
    cid = str(rec_dict.get("cow_id", "")).strip()
    ts = str(rec_dict.get("timestamp", "")).strip()
    try:
        act = float(rec_dict.get("activity_index", 0.0))
        rum = float(rec_dict.get("rumination_minutes", 0.0))
    except (ValueError, TypeError):
        return False, "Invalid numerical data for activity_index or rumination_minutes"

    if rum < 0.0 or rum > 120.0:
        return False, f"Rumination minutes ({rum}) out of bounds (must be 0–120 min for a 2-hour interval)."

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_demo = int(rec_dict.get("is_demo", 0))

    try:
        execute_write("""
            INSERT INTO sensor_records (
                cow_id, timestamp, activity_index, rumination_minutes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (cid, ts, act, rum, is_demo, now), db_path=db_path)
        return True, "Record inserted successfully."
    except sqlite3.IntegrityError:
        return False, f"Duplicate record detected for Cow {cid} at timestamp {ts}."
    except Exception as ex:
        return False, str(ex)


def check_sensor_duplicate(cow_id, timestamp, db_path=DB_FILE):
    """Check if a sensor reading for (cow_id, timestamp) already exists."""
    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM sensor_records WHERE cow_id = ? AND timestamp = ?",
            (str(cow_id).strip(), str(timestamp).strip())
        )
        return cur.fetchone() is not None


def get_sensor_records(cow_id=None, start_date=None, end_date=None, db_path=DB_FILE):
    """
    Retrieve sensor records with optional filtering by cow_id and date range.
    Returns DataFrame sorted chronologically (timestamp ASC).
    """
    query = "SELECT * FROM sensor_records WHERE 1=1"
    params = []
    if cow_id and str(cow_id).strip() and str(cow_id).strip() != "All":
        query += " AND cow_id = ?"
        params.append(str(cow_id).strip())
    if start_date:
        query += " AND timestamp >= ?"
        params.append(str(start_date).strip())
    if end_date:
        e_str = str(end_date).strip()
        if len(e_str) == 10:
            e_str += " 23:59:59"
        query += " AND timestamp <= ?"
        params.append(e_str)

    query += " ORDER BY timestamp ASC, id ASC"
    return query_df(query, params=params, db_path=db_path)


def delete_sensor_record(record_id, db_path=DB_FILE):
    return delete_record("sensor_records", record_id, db_path=db_path)


def analyze_sensor_estrus(
    df,
    min_baseline_intervals=24,
    activity_threshold_pct=35.0,
    rumination_drop_pct=25.0
):
    """
    Transparent Rule-Based Estrus Prediction Algorithm using 2-hourly Activity & Rumination telemetry.
    
    Scientific Rules:
    1. Historical Baseline: Evaluates individual cow's diurnal (time-of-day median) baseline over available history.
       Requires minimum historical readings (default 24 intervals = 2 days, recommended ~14 days).
       If insufficient valid data exists, flags record as 'Insufficient Data' with clear explanation.
    2. Missing Readings: Never treated as zero (null/missing intervals excluded from baseline calculation).
    3. Activity Elevation: Unusually elevated activity relative to cow's historical baseline contributes up to 45 pts.
    4. Rumination Suppression: Unusually suppressed rumination relative to cow's baseline contributes up to 35 pts.
    5. Combined Synergy Bonus: +12 pts when activity surges and rumination drops concurrently.
    6. Multi-Interval Persistence Bonus: +8 pts when behavioral shifts persist across consecutive 2-hour blocks.
    7. Classification: High (>= 70), Moderate (40–69), Low (< 40), Insufficient Data.
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

        # Compute diurnal slot medians for this specific cow
        valid_cow = valid_cow.copy()
        valid_cow['time_slot'] = valid_cow['timestamp_dt'].dt.strftime('%H:00')
        slot_act = valid_cow.groupby('time_slot')['activity_index'].median().to_dict()
        slot_rum = valid_cow.groupby('time_slot')['rumination_minutes'].median().to_dict()
        overall_act = float(valid_cow['activity_index'].median())
        overall_rum = float(valid_cow['rumination_minutes'].median())

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
            base_act = max(1.0, float(slot_act.get(slot, overall_act)))
            base_rum = max(1.0, float(slot_rum.get(slot, overall_rum)))

            act_diff_pct = ((raw_act - base_act) / base_act) * 100.0
            rum_diff_pct = ((raw_rum - base_rum) / base_rum) * 100.0
            rum_drop_pct = -rum_diff_pct

            # Activity points (0 to 45 pts)
            act_pts = 0.0
            if act_diff_pct > 0:
                if act_diff_pct < activity_threshold_pct:
                    act_pts = (act_diff_pct / activity_threshold_pct) * 15.0
                elif act_diff_pct < (2.0 * activity_threshold_pct):
                    act_pts = 15.0 + ((act_diff_pct - activity_threshold_pct) / activity_threshold_pct) * 20.0
                else:
                    act_pts = 35.0 + min(10.0, ((act_diff_pct - 2.0 * activity_threshold_pct) / activity_threshold_pct) * 10.0)

            # Rumination drop points (0 to 35 pts)
            rum_pts = 0.0
            if rum_drop_pct > 0:
                if rum_drop_pct < rumination_drop_pct:
                    rum_pts = (rum_drop_pct / rumination_drop_pct) * 12.0
                elif rum_drop_pct < (2.0 * rumination_drop_pct):
                    rum_pts = 12.0 + ((rum_drop_pct - rumination_drop_pct) / rumination_drop_pct) * 15.0
                else:
                    rum_pts = 27.0 + min(8.0, ((rum_drop_pct - 2.0 * rumination_drop_pct) / rumination_drop_pct) * 8.0)

            # Synergy bonus (12 pts)
            synergy = 12.0 if (act_diff_pct >= activity_threshold_pct and rum_drop_pct >= rumination_drop_pct) else 0.0

            # Consecutive persistence bonus (8 pts)
            persistence = 0.0
            if prev_time is not None:
                delta_hrs = (t_dt - prev_time).total_seconds() / 3600.0
                if 1.5 <= delta_hrs <= 2.5 and prev_score >= 40.0:
                    persistence = 8.0

            total_score = min(100.0, round(act_pts + rum_pts + synergy + persistence, 1))
            cat = "High" if total_score >= 70.0 else ("Moderate" if total_score >= 40.0 else "Low")

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

    return pd.DataFrame(out_rows)


# ==========================================
# CSV Import Audit History
# ==========================================

def log_csv_import(filename, category, total, success, rejected, duplicates, status, error_summary, db_path=DB_FILE):
    """Log an import session."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    q = """
    INSERT INTO csv_import_history (
        filename, category, import_date, total_rows,
        success_rows, rejected_rows, duplicate_rows,
        status, error_summary
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(q, (filename, category, now, total, success, rejected, duplicates, status, error_summary), db_path=db_path)
    return True


def get_csv_import_history(db_path=DB_FILE):
    """Get all CSV import logs."""
    return query_df("SELECT * FROM csv_import_history ORDER BY id DESC", db_path=db_path)


# ==========================================
# Database Backup and Restore
# ==========================================

def backup_database(destination_path, db_path=DB_FILE):
    """Create a safe snapshot of the SQLite database using SQLite backup API."""
    init_db(db_path)
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(destination_path)
    with dst_conn:
        src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    return True


def restore_database(source_path, db_path=DB_FILE):
    """Restore the database from a backup copy."""
    if not os.path.exists(source_path):
        return False, "Source backup file does not exist."
    try:
        shutil.copyfile(source_path, db_path)
        return True, "Database successfully restored."
    except Exception as e:
        return False, f"Restore failed: {str(e)}"


# ==========================================
# Synthetic Demonstration Data Generator
# ==========================================

def generate_demo_data(db_path=DB_FILE):
    """
    Populate realistic synthetic dairy farm records labeled as DEMONSTRATION DATA (is_demo=1).
    Avoids duplicate entries if demo data is already present.
    """
    init_db(db_path)
    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cows WHERE is_demo = 1")
        if cur.fetchone()[0] > 0:
            return False, "Demonstration data is already loaded."

        today = date.today()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. 20 Cows
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

        cow_rows = []
        for cid, name, breed, age, wt, lact, d_milk, days_calved, preg, health, rep, rem in cow_templates:
            dob_dt = today - timedelta(days=int(age * 365.25))
            calv_dt = today - timedelta(days=days_calved)
            estrus_dt = today - timedelta(days=np.random.randint(5, 45))
            insem_dt = estrus_dt + timedelta(days=1) if preg in ["Inseminated", "Confirmed Pregnant"] else None
            cow_rows.append((
                cid, name, breed, dob_dt.strftime("%Y-%m-%d"), age, wt, lact, d_milk,
                calv_dt.strftime("%Y-%m-%d"), estrus_dt.strftime("%Y-%m-%d"),
                insem_dt.strftime("%Y-%m-%d") if insem_dt else None,
                preg, health, rep, rem, 1, now_str, now_str
            ))

        cur.executemany("""
            INSERT INTO cows (
                cow_id, name, breed, dob, age, weight, lactation_number,
                daily_milk_production, last_calving_date, last_observed_estrus_date,
                last_insemination_date, pregnancy_status, health_status,
                reproductive_status, remarks, is_demo, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, cow_rows)

        # 2. Estrus Observations (18 records)
        estrus_rows = [
            ("COW-107", (today - timedelta(days=1)).strftime("%Y-%m-%d"), "Standing to Be Mounted, Mounting Other Cows, Clear Vaginal Mucus Discharge", 1, 1, 1, 1, 0, 0, 1, 1, 0, 85.0, "High", "Estrus (Standing Heat)", (today + timedelta(days=20)).strftime("%Y-%m-%d"), "Standing to Be Mounted (+30 pts) | Mounting Other Cows (+20 pts) | Clear Vaginal Mucus Discharge (+20 pts) | Vulval Swelling and Redness (+15 pts)", "Intense standing heat, recommended for A.M. service", 1, now_str),
            ("COW-114", today.strftime("%Y-%m-%d"), "Standing to Be Mounted, Clear Vaginal Mucus Discharge, Increased Activity / Restlessness", 1, 1, 0, 1, 0, 0, 1, 0, 0, 70.0, "High", "Estrus (Standing Heat)", (today + timedelta(days=21)).strftime("%Y-%m-%d"), "Standing to Be Mounted (+30 pts) | Clear Vaginal Mucus Discharge (+20 pts) | Increased Activity / Restlessness (+15 pts)", "Fresh heifer standing heat", 1, now_str),
            ("COW-105", (today - timedelta(days=2)).strftime("%Y-%m-%d"), "Mounting Other Cows, Increased Activity / Restlessness", 1, 1, 1, 0, 0, 0, 0, 1, 0, 50.0, "Moderate", "Proestrus (Coming into Heat)", (today + timedelta(days=19)).strftime("%Y-%m-%d"), "Mounting Other Cows (+20 pts) | Increased Activity / Restlessness (+15 pts) | Vulval Swelling and Redness (+15 pts)", "Active mounting, watch closely over 12h", 1, now_str),
            ("COW-102", (today - timedelta(days=6)).strftime("%Y-%m-%d"), "Increased Activity / Restlessness", 1, 0, 0, 0, 0, 0, 0, 0, 0, 15.0, "Low", "Proestrus / Mild Expression", (today + timedelta(days=15)).strftime("%Y-%m-%d"), "Increased Activity / Restlessness (+15 pts)", "Mild pacing noticed", 1, now_str),
            ("COW-108", (today - timedelta(days=12)).strftime("%Y-%m-%d"), "Standing to Be Mounted, Mounting Other Cows, Clear Vaginal Mucus Discharge, Increased Activity / Restlessness", 1, 1, 1, 1, 0, 0, 1, 0, 0, 85.0, "High", "Estrus (Standing Heat)", (today + timedelta(days=9)).strftime("%Y-%m-%d"), "Standing to Be Mounted (+30 pts) | Mounting Other Cows (+20 pts) | Clear Vaginal Mucus Discharge (+20 pts) | Increased Activity / Restlessness (+15 pts)", "Previous cycle logged", 1, now_str),
        ]
        # Add a few more low/baseline estrus observations
        for i, (cid, _, _, _, _, _, _, _, _, _, _, _) in enumerate(cow_templates[:13]):
            d_prev = (today - timedelta(days=int(15 + i))).strftime("%Y-%m-%d")
            estrus_rows.append((
                cid, d_prev, "None observed", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, "Low", "Diestrus / Baseline",
                (today + timedelta(days=int(21 - i % 10))).strftime("%Y-%m-%d"),
                "None observed", "Baseline routine check", 1, now_str
            ))

        cur.executemany("""
            INSERT INTO estrus_observations (
                cow_id, observation_date, selected_markers, increased_activity, restlessness,
                mounting_behaviour, standing_to_be_mounted, frequent_vocalization,
                reduced_feed_intake, clear_mucus_discharge, swollen_vulva,
                reduced_milk_yield, estrus_score, evidence_category,
                cycle_stage, estimated_next_estrus, score_reasons, notes,
                is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, estrus_rows)

        # 3. Health Records (100 records: 5 per cow for 20 cows)
        health_rows = []
        for cid, name, breed, age, wt, lact, d_milk, _, _, h_stat, _, _ in cow_templates:
            for d_ago in range(5):
                obs_d = (today - timedelta(days=d_ago)).strftime("%Y-%m-%d")
                temp = 38.6 + np.random.normal(0, 0.2)
                milk = d_milk + np.random.normal(0, 0.8)
                appetite = "Normal"
                status = "Healthy"
                flags = "Normal physiological range"
                symptoms = "None"

                if cid == "COW-111" and d_ago <= 2:
                    temp = 39.9 + (d_ago * 0.1)
                    milk = max(6.0, d_milk - 8.0)
                    appetite = "Poor"
                    status = "Under Observation"
                    flags = "High Fever; Appetite Drop; Suspected Mastitis"
                    symptoms = "Swollen right-rear quarter, clotty milk flakes"

                health_rows.append((
                    cid, obs_d, round(temp, 1), round(max(0, milk), 1), appetite,
                    round(18.0 + np.random.normal(0, 1.0), 1),
                    round(80.0 + np.random.normal(0, 5.0), 1),
                    "Normal" if status == "Healthy" else "Lethargic",
                    "Normal" if status == "Healthy" else "Dull",
                    symptoms, status, flags, "Routine health inspection", 1, now_str
                ))

        cur.executemany("""
            INSERT INTO health_records (
                cow_id, observation_date, body_temperature, milk_production,
                appetite, feed_intake, water_intake, activity_level,
                behaviour, symptoms, health_status, abnormality_flags,
                health_notes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, health_rows)

        # 4. Disease Risk Assessments (5 records)
        disease_rows = [
            ("COW-111", (today - timedelta(days=1)).strftime("%Y-%m-%d"), "High concern", "Moderate concern", "Low concern", "Low concern", "High concern", 1, 1, 1, 1, 1, 1, "None", "None", "Clinical mastitis quadrant positive: swollen quarter, milk clots, fever", "Immediate veterinary antibiotic infusion prescribed", 1, 1, now_str),
            ("COW-117", (today - timedelta(days=2)).strftime("%Y-%m-%d"), "Low concern", "Low concern", "Moderate concern", "Low concern", "Moderate concern", 0, 0, 0, 0, 0, 0, "Mild bloat, reduced rumen motility", "None", "Digestive ruminal stasis suspected", "Oral antacid drench administered", 0, 1, now_str),
            ("COW-105", (today - timedelta(days=3)).strftime("%Y-%m-%d"), "Low concern", "Low concern", "Low concern", "Low concern", "Low concern", 0, 0, 0, 0, 0, 0, "None", "None", "Routine herd surveillance", "All physiological signs normal", 0, 1, now_str),
            ("COW-101", (today - timedelta(days=4)).strftime("%Y-%m-%d"), "Low concern", "Low concern", "Low concern", "Low concern", "Low concern", 0, 0, 0, 0, 0, 0, "None", "None", "Healthy foundation cow check", "Normal", 0, 1, now_str),
            ("COW-107", (today - timedelta(days=5)).strftime("%Y-%m-%d"), "Low concern", "Low concern", "Low concern", "Low concern", "Low concern", 0, 0, 0, 0, 0, 0, "None", "None", "Reproductive inspection", "Normal", 0, 1, now_str),
        ]
        cur.executemany("""
            INSERT INTO disease_assessments (
                cow_id, assessment_date, mastitis_risk, systemic_risk,
                digestive_risk, reproductive_risk, overall_concern,
                udder_swelling, udder_pain, abnormal_udder_appearance,
                abnormal_milk, elevated_temp, reduced_yield,
                digestive_symptoms, reproductive_symptoms, rationale,
                screening_notes, vet_consultation_recommended, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, disease_rows)

        # 5. THI Weather Records (30 days x ~3 readings/day = ~90 records)
        thi_rows = []
        for d_ago in range(30, -1, -1):
            o_date = (today - timedelta(days=d_ago)).strftime("%Y-%m-%d")
            # 08:00 morning
            t_m = round(21.0 + np.random.normal(0, 1.5), 1)
            rh_m = round(72.0 + np.random.normal(0, 4.0), 1)
            thi_m = calculate_thi(t_m, rh_m)
            thi_rows.append((o_date, "08:00", t_m, rh_m, thi_m, classify_thi(thi_m), "Morning farm baseline", 1, now_str))

            # 14:00 afternoon peak
            t_a = round(31.5 + np.random.normal(0, 2.0), 1)
            rh_a = round(58.0 + np.random.normal(0, 5.0), 1)
            thi_a = calculate_thi(t_a, rh_a)
            thi_rows.append((o_date, "14:00", t_a, rh_a, thi_a, classify_thi(thi_a), "Afternoon peak reading", 1, now_str))

            # 20:00 evening
            t_e = round(25.0 + np.random.normal(0, 1.5), 1)
            rh_e = round(65.0 + np.random.normal(0, 4.0), 1)
            thi_e = calculate_thi(t_e, rh_e)
            thi_rows.append((o_date, "20:00", t_e, rh_e, thi_e, classify_thi(thi_e), "Evening reading", 1, now_str))

        cur.executemany("""
            INSERT INTO thi_records (
                observation_date, observation_time, ambient_temp, relative_humidity,
                thi_value, heat_stress_category, notes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, thi_rows)

        # 6. Milk Production Records (15 days x 20 cows = 300 records)
        milk_rows = []
        for cid, _, _, _, _, _, d_milk, _, _, _, _, _ in cow_templates:
            for d_ago in range(15):
                p_date = (today - timedelta(days=d_ago)).strftime("%Y-%m-%d")
                m_y = round(d_milk * 0.55 + np.random.normal(0, 0.5), 2)
                e_y = round(d_milk * 0.45 + np.random.normal(0, 0.4), 2)
                t_y = round(m_y + e_y, 2)
                is_drop = 1 if (cid == "COW-111" and d_ago <= 2) else 0
                if is_drop:
                    t_y = round(t_y * 0.55, 2)
                    m_y = round(m_y * 0.55, 2)
                    e_y = round(e_y * 0.55, 2)
                milk_rows.append((cid, p_date, m_y, e_y, t_y, is_drop, "Standard dairy parlor log", 1, now_str))

        cur.executemany("""
            INSERT INTO milk_records (
                cow_id, production_date, morning_yield, evening_yield,
                total_yield, is_drop_alert, notes, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, milk_rows)

        # 7. Reproductive History (18 records)
        rep_rows = []
        for i, (cid, name, breed, _, _, _, _, days_calved, preg, _, _, _) in enumerate(cow_templates[:18]):
            d_ago = int(days_calved + 10)
            e_date = (today - timedelta(days=min(300, d_ago))).strftime("%Y-%m-%d")
            etype = "Calving" if i % 2 == 0 else "Artificial Insemination"
            det = "Normal spontaneous delivery" if etype == "Calving" else "Commercial proven sire semen straw"
            tech = "Dr. Sharma" if etype == "Calving" else "Field AI Inseminator"
            outc = "Healthy heifer calf" if etype == "Calving" else ("Conceived" if preg == "Confirmed Pregnant" else "Pending pregnancy check")
            rep_rows.append((cid, e_date, etype, det, tech, outc, 1, now_str))

        cur.executemany("""
            INSERT INTO reproductive_history (
                cow_id, event_date, event_type, details,
                technician_or_sire, outcome, is_demo, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rep_rows)

        # 8. Sensor Telemetry Records (14 days x 12 intervals/day = 168 per cow)
        sensor_rows = []
        times_of_day = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
        diurnal_profile = {
            "00:00": (30.0, 58.0), "02:00": (26.0, 62.0), "04:00": (32.0, 56.0),
            "06:00": (58.0, 32.0), "08:00": (68.0, 26.0), "10:00": (52.0, 42.0),
            "12:00": (46.0, 46.0), "14:00": (48.0, 44.0), "16:00": (64.0, 30.0),
            "18:00": (60.0, 34.0), "20:00": (42.0, 48.0), "22:00": (34.0, 54.0)
        }

        for cid, _, _, _, _, _, _, _, _, _, _, _ in cow_templates:
            if cid == "COW-120":
                # Only 6 intervals to test 'Insufficient Baseline' handling
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

                    # Distinct estrus spikes for cows in heat
                    if cid in ["COW-107", "COW-114"]:
                        if (d_ago == 1 and t_str in ["16:00", "18:00", "20:00", "22:00"]) or (d_ago == 0 and t_str in ["00:00", "02:00", "04:00"]):
                            act = base_act * 2.2 + np.random.uniform(15, 30)
                            rum = max(6.0, base_rum * 0.28 - np.random.uniform(2, 6))

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

    return True, "Demonstration data successfully populated across all tables."


def clear_demo_data(db_path=DB_FILE):
    """
    Remove all demonstration records (is_demo = 1) across all tables with transaction safety.
    """
    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM estrus_observations WHERE is_demo = 1")
        cur.execute("DELETE FROM sensor_records WHERE is_demo = 1")
        cur.execute("DELETE FROM health_records WHERE is_demo = 1")
        cur.execute("DELETE FROM disease_assessments WHERE is_demo = 1")
        cur.execute("DELETE FROM thi_records WHERE is_demo = 1")
        cur.execute("DELETE FROM milk_records WHERE is_demo = 1")
        cur.execute("DELETE FROM reproductive_history WHERE is_demo = 1")
        cur.execute("DELETE FROM cows WHERE is_demo = 1")
    return True, "All demonstration data cleared successfully."


# ==========================================
# Dashboard & KPI Statistics Helper
# ==========================================

def get_dashboard_kpis(db_path=DB_FILE):
    """Calculate key performance indicators directly from SQLite records."""
    init_db(db_path)
    with db_session(db_path) as conn:
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

        cur.execute("SELECT COUNT(*) FROM cows WHERE health_status != 'Healthy'")
        cows_sick_record = cur.fetchone()[0]
        total_health_concern = max(health_attention_count, cows_sick_record)

        # 4. Latest THI reading
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
                cur.execute("SELECT DISTINCT cow_id FROM sensor_records WHERE timestamp >= ?", (two_days_ago,))
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
        has_demo = cur.fetchone()[0] > 0

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
