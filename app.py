import os
import sqlite3
import pandas as pd
from flask import Flask, jsonify, request
from scoring import priority_score, health_score
from scheduler import generate_schedule

DB_FILE = "railway.db"
SCHEMA_FILE = "schema.sql"

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database schema if not present."""
    if not os.path.exists(SCHEMA_FILE):
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()

# Auto-initialize database schema on startup
init_db()

@app.route("/", methods=["GET"])
def home():
    """Index status route."""
    return jsonify({
        "system": "AI-Powered Automatic Block Planning API",
        "status": "online",
        "version": "1.0.0-MVP"
    })

@app.route("/api/defects", methods=["GET"])
def get_defects():
    """GET /api/defects - Returns list of defects with calculated priority and health scores."""
    conn = get_db_connection()
    defects_rows = conn.execute("SELECT * FROM defects").fetchall()
    corridors_rows = conn.execute("SELECT * FROM corridors").fetchall()
    conn.close()

    corridor_map = {c["corridor_id"]: dict(c) for c in corridors_rows}

    defects_list = []
    for d in defects_rows:
        d_dict = dict(d)
        c_row = corridor_map.get(d_dict.get("corridor_id"))
        
        # Calculate dynamic stub scores
        d_dict["priority_score"] = priority_score(d_dict, c_row)
        d_dict["health_score"] = health_score(d_dict)
        defects_list.append(d_dict)

    return jsonify(defects_list)

@app.route("/api/corridors", methods=["GET"])
def get_corridors():
    """GET /api/corridors - Returns list of railway corridors."""
    conn = get_db_connection()
    corridors_rows = conn.execute("SELECT * FROM corridors").fetchall()
    conn.close()
    
    corridors_list = [dict(c) for c in corridors_rows]
    return jsonify(corridors_list)

@app.route("/api/schedule", methods=["GET"])
def get_schedule():
    """GET /api/schedule - Returns generated schedule results from DB."""
    conn = get_db_connection()
    results_rows = conn.execute("SELECT * FROM schedule_results").fetchall()
    conn.close()
    
    schedule_list = [dict(r) for r in results_rows]
    return jsonify(schedule_list)

@app.route("/api/schedule/generate", methods=["POST"])
def generate_schedule_route():
    """POST /api/schedule/generate - Runs scheduler and persists output into DB."""
    conn = get_db_connection()
    
    # Read DB tables into DataFrames for scheduler module
    defects_df = pd.read_sql_query("SELECT * FROM defects", conn)
    corridors_df = pd.read_sql_query("SELECT * FROM corridors", conn)
    timetable_df = pd.read_sql_query("SELECT * FROM timetable", conn)
    
    # Execute scheduler stub / algorithm
    schedule_df = generate_schedule(defects_df, corridors_df, timetable_df)
    
    # Persist results to DB (replace schedule_results table)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule_results")
    
    for _, row in schedule_df.iterrows():
        cursor.execute("""
            INSERT INTO schedule_results 
            (task_id, corridor_id, date, slot_start, slot_end, priority_score, merged_with, explanation_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(row["task_id"]),
            str(row["corridor_id"]),
            str(row["date"]),
            str(row["slot_start"]),
            str(row["slot_end"]),
            float(row["priority_score"]),
            row["merged_with"] if pd.notna(row.get("merged_with")) else None,
            str(row["explanation_text"])
        ))
        
    conn.commit()
    
    # Return committed schedule results
    results_rows = cursor.execute("SELECT * FROM schedule_results").fetchall()
    conn.close()
    
    schedule_list = [dict(r) for r in results_rows]
    return jsonify({
        "status": "success",
        "count": len(schedule_list),
        "schedule": schedule_list
    })

@app.route("/api/whatif", methods=["POST"])
def whatif_route():
    """
    POST /api/whatif - Re-runs scheduler in-memory with modified inputs.
    Accepts JSON body with overrides (e.g., modified task duration or severity).
    Does NOT modify committed DB state.
    """
    payload = request.get_json(silent=True) or {}
    
    conn = get_db_connection()
    defects_df = pd.read_sql_query("SELECT * FROM defects", conn)
    corridors_df = pd.read_sql_query("SELECT * FROM corridors", conn)
    timetable_df = pd.read_sql_query("SELECT * FROM timetable", conn)
    conn.close()
    
    # Apply inline what-if modifications if provided
    if "override_defect" in payload:
        override = payload["override_defect"]
        task_id = override.get("task_id")
        if task_id and not defects_df.empty:
            for field, val in override.items():
                if field in defects_df.columns:
                    defects_df.loc[defects_df["task_id"] == task_id, field] = val

    if "defects" in payload and isinstance(payload["defects"], list):
        defects_df = pd.DataFrame(payload["defects"])
        
    if "corridors" in payload and isinstance(payload["corridors"], list):
        corridors_df = pd.DataFrame(payload["corridors"])

    if "timetable" in payload and isinstance(payload["timetable"], list):
        timetable_df = pd.DataFrame(payload["timetable"])

    # Recalculate schedule in-memory without saving to DB
    schedule_df = generate_schedule(defects_df, corridors_df, timetable_df)
    results_list = schedule_df.to_dict(orient="records")
    
    return jsonify({
        "status": "success",
        "is_whatif": True,
        "schedule": results_list
    })

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
