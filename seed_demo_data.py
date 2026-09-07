import os
import sqlite3

DB_FILE = "railway.db"
SCHEMA_FILE = "schema.sql"

def init_db(conn):
    """Ensure tables are created from schema.sql if present."""
    if os.path.exists(SCHEMA_FILE):
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

def seed_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Ensure schema exists
    init_db(conn)

    # Clear existing rows in the 3 target tables
    cursor.execute("DELETE FROM defects")
    cursor.execute("DELETE FROM timetable")
    cursor.execute("DELETE FROM corridors")

    # Reset SQLite autoincrement counters if table exists
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('defects', 'timetable', 'schedule_results')")

    # 1. Insert 5 corridors (mix of high-density and normal)
    corridors = [
        ("CORR-NDLS-CNB", "New Delhi - Kanpur Central", 1),
        ("CORR-HWH-MGS", "Howrah - Pt. Deen Dayal Upadhyaya", 1),
        ("CORR-BCT-BRC", "Mumbai Central - Vadodara", 1),
        ("CORR-MAS-GDR", "Chennai Central - Gudur", 0),
        ("CORR-SBC-MYS", "KSR Bengaluru - Mysuru", 0),
    ]

    cursor.executemany("""
        INSERT INTO corridors (corridor_id, section_name, is_high_density)
        VALUES (?, ?, ?)
    """, corridors)

    # 2. Insert 18 defects spread across Engineering, S&T, and Track Machine (TD) departments
    defects = [
        ("TMS", "RAIL-101", "CORR-NDLS-CNB", "Rail Fracture Risk", 5, "2026-09-02", "2026-09-07", 3.5, "Engineering", "NDLS-CNB @ 42.3km"),
        ("SMMS", "SIG-204", "CORR-NDLS-CNB", "Point Machine Failure", 4, "2026-09-03", "2026-09-08", 2.0, "S&T", "NDLS-CNB @ 108.7km"),
        ("TDMS", "TRK-305", "CORR-HWH-MGS", "Track De-stressing", 3, "2026-09-04", "2026-09-10", 4.0, "Track Machine", "HWH-MGS @ 215.1km"),
        ("TMS", "RAIL-108", "CORR-BCT-BRC", "Worn Out Switch Rail", 4, "2026-09-05", "2026-09-09", 3.0, "Engineering", "BCT-BRC @ 312.4km"),
        ("COA", "OHE-401", "CORR-MAS-GDR", "Cantilever Alignment Defect", 2, "2026-09-06", "2026-09-11", 1.5, "Engineering", "MAS-GDR @ 56.8km"),
        ("SMMS", "SIG-210", "CORR-HWH-MGS", "Axle Counter Maintenance", 3, "2026-09-05", "2026-09-09", 2.5, "S&T", "HWH-MGS @ 482.0km"),
        ("TDMS", "TRK-312", "CORR-NDLS-CNB", "CSM Tamping Operation", 4, "2026-09-04", "2026-09-08", 4.5, "Track Machine", "NDLS-CNB @ 175.6km"),
        ("TMS", "RAIL-115", "CORR-SBC-MYS", "Fishplate Joint Defect", 2, "2026-09-06", "2026-09-12", 2.0, "Engineering", "SBC-MYS @ 84.2km"),
        ("SMMS", "SIG-218", "CORR-BCT-BRC", "Track Circuit Glitch", 5, "2026-09-06", "2026-09-07", 1.5, "S&T", "BCT-BRC @ 129.5km"),
        ("COA", "BLK-502", "CORR-MAS-GDR", "Level Crossing Gate Interlocking", 3, "2026-09-05", "2026-09-10", 3.0, "S&T", "MAS-GDR @ 110.3km"),
        ("TDMS", "TRK-320", "CORR-BCT-BRC", "BCM Ballast Cleaning", 5, "2026-09-03", "2026-09-08", 5.0, "Track Machine", "BCT-BRC @ 245.8km"),
        ("TMS", "RAIL-122", "CORR-HWH-MGS", "Deep Screening Required", 4, "2026-09-04", "2026-09-11", 4.0, "Engineering", "HWH-MGS @ 360.2km"),
        ("COA", "OHE-415", "CORR-NDLS-CNB", "Catenary Wire Tension Check", 1, "2026-09-07", "2026-09-13", 1.5, "Engineering", "NDLS-CNB @ 290.4km"),
        ("SMMS", "SIG-225", "CORR-SBC-MYS", "Signal LED Lamp Replacement", 1, "2026-09-07", "2026-09-13", 1.0, "S&T", "SBC-MYS @ 32.1km"),
        ("TDMS", "TRK-333", "CORR-MAS-GDR", "Unimat Switch Tamping", 2, "2026-09-06", "2026-09-12", 3.0, "Track Machine", "MAS-GDR @ 92.7km"),
        ("TMS", "RAIL-130", "CORR-NDLS-CNB", "Track Alignment Deviation", 3, "2026-09-05", "2026-09-10", 2.5, "Engineering", "NDLS-CNB @ 340.0km"),
        ("SMMS", "SIG-231", "CORR-HWH-MGS", "Block Instrument Defect", 4, "2026-09-06", "2026-09-08", 2.0, "S&T", "HWH-MGS @ 610.5km"),
        ("TDMS", "TRK-345", "CORR-SBC-MYS", "DGS Track Stabilization", 3, "2026-09-05", "2026-09-11", 3.5, "Track Machine", "SBC-MYS @ 120.9km"),
    ]

    cursor.executemany("""
        INSERT INTO defects 
        (source_system, asset_id, corridor_id, defect_type, severity, date_reported, due_date, estimated_block_duration, department, location_marker)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, defects)

    # 3. Insert 25 timetable rows across corridors/dates/time_slots
    timetable = [
        ("CORR-NDLS-CNB", "2026-09-07", "00:00-04:00", 4, 2),
        ("CORR-NDLS-CNB", "2026-09-07", "04:00-08:00", 14, 6),
        ("CORR-NDLS-CNB", "2026-09-07", "08:00-12:00", 18, 5),
        ("CORR-NDLS-CNB", "2026-09-08", "01:00-05:00", 3, 1),
        ("CORR-NDLS-CNB", "2026-09-08", "12:00-16:00", 15, 7),
        ("CORR-NDLS-CNB", "2026-09-09", "02:00-06:00", 5, 2),
        ("CORR-NDLS-CNB", "2026-09-10", "00:00-04:00", 4, 1),
        ("CORR-HWH-MGS", "2026-09-07", "01:00-05:00", 3, 2),
        ("CORR-HWH-MGS", "2026-09-07", "08:00-12:00", 16, 8),
        ("CORR-HWH-MGS", "2026-09-08", "02:00-06:00", 4, 2),
        ("CORR-HWH-MGS", "2026-09-08", "14:00-18:00", 14, 6),
        ("CORR-HWH-MGS", "2026-09-09", "01:00-05:00", 3, 1),
        ("CORR-HWH-MGS", "2026-09-11", "03:00-07:00", 5, 2),
        ("CORR-BCT-BRC", "2026-09-07", "02:00-06:00", 4, 1),
        ("CORR-BCT-BRC", "2026-09-07", "09:00-13:00", 15, 5),
        ("CORR-BCT-BRC", "2026-09-08", "01:00-05:00", 3, 2),
        ("CORR-BCT-BRC", "2026-09-09", "16:00-20:00", 13, 6),
        ("CORR-BCT-BRC", "2026-09-12", "00:00-04:00", 4, 2),
        ("CORR-MAS-GDR", "2026-09-07", "02:00-06:00", 2, 0),
        ("CORR-MAS-GDR", "2026-09-08", "08:00-12:00", 7, 3),
        ("CORR-MAS-GDR", "2026-09-10", "01:00-05:00", 2, 1),
        ("CORR-MAS-GDR", "2026-09-11", "13:00-17:00", 6, 2),
        ("CORR-SBC-MYS", "2026-09-07", "01:00-05:00", 1, 0),
        ("CORR-SBC-MYS", "2026-09-09", "07:00-11:00", 6, 1),
        ("CORR-SBC-MYS", "2026-09-13", "02:00-06:00", 2, 0),
    ]

    cursor.executemany("""
        INSERT INTO timetable (corridor_id, date, time_slot, train_count, goods_forecast_count)
        VALUES (?, ?, ?, ?, ?)
    """, timetable)

    conn.commit()
    conn.close()

    print(f"Successfully seeded railway.db:")
    print(f"  - Corridors inserted: {len(corridors)}")
    print(f"  - Defects inserted:   {len(defects)}")
    print(f"  - Timetable rows:     {len(timetable)}")

if __name__ == "__main__":
    seed_data()
