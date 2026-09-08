import os
import sqlite3
import unittest
import json
from app import app, init_db, DB_FILE

class BackendTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test database and insert dummy rows for route validation."""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Remove existing db if present to ensure clean slate
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)

        # Initialize schema
        init_db()

        # Insert small set of dummy test rows directly
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Corridors dummy data
        cursor.executemany("""
            INSERT INTO corridors (corridor_id, section_name, is_high_density)
            VALUES (?, ?, ?)
        """, [
            ("CORR-NDLS-CNB", "New Delhi - Kanpur Central", 1),
            ("CORR-HWH-MGS", "Howrah - Pt. Deen Dayal Upadhyaya", 1),
            ("CORR-BCT-BRC", "Mumbai Central - Vadodara", 0)
        ])

        # Defects dummy data
        cursor.executemany("""
            INSERT INTO defects 
            (source_system, asset_id, corridor_id, defect_type, severity, date_reported, due_date, estimated_block_duration, department, location_marker)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("TMS", "RAIL-101", "CORR-NDLS-CNB", "Rail Fracture Risk", 5, "2026-09-01", "2026-09-03", 3.5, "Engineering", "NDLS-CNB @ 42.3km"),
            ("SMMS", "SIG-204", "CORR-NDLS-CNB", "Point Machine Failure", 4, "2026-09-02", "2026-09-09", 2.0, "S&T", "NDLS-CNB @ 108.7km"),
            ("TDMS", "TRK-305", "CORR-HWH-MGS", "Track De-stressing", 3, "2026-09-04", "2026-09-19", 4.0, "TD", "HWH-MGS @ 215.1km")
        ])

        # Timetable dummy data
        cursor.executemany("""
            INSERT INTO timetable (corridor_id, date, time_slot, train_count, goods_forecast_count)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("CORR-NDLS-CNB", "2026-09-07", "02:00-04:00", 3, 1),
            ("CORR-NDLS-CNB", "2026-09-07", "04:00-06:00", 12, 5),
            ("CORR-HWH-MGS", "2026-09-07", "01:00-03:00", 2, 0)
        ])

        conn.commit()
        conn.close()

    def test_01_get_corridors(self):
        """Test GET /api/corridors route."""
        response = self.client.get("/api/corridors")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["corridor_id"], "CORR-NDLS-CNB")
        self.assertIn("is_high_density", data[0])

    def test_02_get_defects(self):
        """Test GET /api/defects route and verify priority/health scores."""
        response = self.client.get("/api/defects")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)
        
        # Verify schema fields and stub scores attached
        first_defect = data[0]
        self.assertIn("task_id", first_defect)
        self.assertIn("source_system", first_defect)
        self.assertIn("location_marker", first_defect)
        self.assertIn("priority_score", first_defect)
        self.assertIn("health_score", first_defect)
        self.assertIsInstance(first_defect["priority_score"], float)
        self.assertIsInstance(first_defect["health_score"], float)

    def test_03_get_schedule(self):
        """Test GET /api/schedule route."""
        response = self.client.get("/api/schedule")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)

    def test_04_generate_schedule(self):
        """Test POST /api/schedule/generate route and DB persistence."""
        response = self.client.post("/api/schedule/generate")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("schedule", data)
        self.assertGreater(data.get("count"), 0)

        # Verify that GET /api/schedule now returns saved results
        sched_res = self.client.get("/api/schedule")
        saved_schedule = sched_res.get_json()
        self.assertEqual(len(saved_schedule), data.get("count"))
        self.assertIn("task_id", saved_schedule[0])
        self.assertIn("explanation_text", saved_schedule[0])

    def test_05_whatif(self):
        """Test POST /api/whatif route with overrides without modifying DB state."""
        # Initial schedule count
        initial_sched = self.client.get("/api/schedule").get_json()
        
        payload = {
            "override_defect": {
                "task_id": 1,
                "estimated_block_duration": 1.5,
                "severity": 5
            }
        }
        response = self.client.post("/api/whatif", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("is_whatif"))
        self.assertIn("schedule", data)
        self.assertIsInstance(data["schedule"], list)

        # Verify DB schedule results remain unchanged
        post_whatif_sched = self.client.get("/api/schedule").get_json()
        self.assertEqual(len(initial_sched), len(post_whatif_sched))

    def test_06_page_routes(self):
        """Test multipage HTML serving routes (/ , /overview, /defects, /schedule, /whatif, /submit)."""
        for route in ["/", "/overview", "/defects", "/schedule", "/whatif", "/submit"]:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Failed for route {route}")
            self.assertIn("text/html", res.content_type)
            self.assertIn(b"<!DOCTYPE html>", res.data)

    def test_07_static_routes(self):
        """Test static CSS and JS routes (/style.css, /app.js)."""
        css_res = self.client.get("/style.css")
        self.assertEqual(css_res.status_code, 200)
        self.assertIn("text/css", css_res.content_type)

        js_res = self.client.get("/app.js")
        self.assertEqual(js_res.status_code, 200)
        self.assertIn("text/javascript", js_res.content_type)

    def test_08_post_defect_success(self):
        """Test POST /api/defects creates a new defect row with priority and health scores attached."""
        payload = {
            "source_system": "TMS",
            "asset_id": "RAIL-999",
            "corridor_id": "CORR-NDLS-CNB",
            "defect_type": "Emergency Weld Crack",
            "severity": 5,
            "date_reported": "2026-09-07",
            "due_date": "2026-09-08",
            "estimated_block_duration": 4.0,
            "department": "Engineering",
            "location_marker": "NDLS-CNB @ 15.0km"
        }
        res = self.client.post("/api/defects", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("task_id", data)
        self.assertEqual(data["asset_id"], "RAIL-999")
        self.assertIn("priority_score", data)
        self.assertIn("health_score", data)
        self.assertIsInstance(data["priority_score"], float)

    def test_09_post_defect_missing_fields(self):
        """Test POST /api/defects with missing required fields returns 400."""
        incomplete_payload = {
            "source_system": "TMS",
            "asset_id": "RAIL-888"
            # Missing corridor_id, defect_type, severity, etc.
        }
        res = self.client.post("/api/defects", data=json.dumps(incomplete_payload), content_type="application/json")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)

    def test_10_patch_schedule_overrun(self):
        """Test PATCH /api/schedule/<id>/complete with duration overrun appends OVERRUN note."""
        # 1. Generate schedule first
        gen_res = self.client.post("/api/schedule/generate")
        self.assertEqual(gen_res.status_code, 200)
        sched_items = gen_res.get_json().get("schedule", [])
        self.assertGreater(len(sched_items), 0)

        target_item = sched_items[0]
        sched_id = target_item["id"]

        # 2. Patch with actual_duration exceeding scheduled slot
        patch_payload = {"actual_duration": 8.0}
        patch_res = self.client.patch(f"/api/schedule/{sched_id}/complete", data=json.dumps(patch_payload), content_type="application/json")
        self.assertEqual(patch_res.status_code, 200)
        updated_item = patch_res.get_json()
        self.assertEqual(updated_item["actual_duration"], 8.0)
        self.assertIn("OVERRUN:", updated_item["explanation_text"])

    def test_11_whatif_valid_json_nan_regression(self):
        """Test POST /api/whatif response has valid JSON without NaN literals when merged_with is all None."""
        payload = {
            "defects": [
                {
                    "task_id": 1,
                    "source_system": "TMS",
                    "asset_id": "RAIL-101",
                    "corridor_id": "CORR-NDLS-CNB",
                    "defect_type": "Rail Fracture Risk",
                    "severity": 5,
                    "date_reported": "2026-09-02",
                    "due_date": "2026-09-07",
                    "estimated_block_duration": 3.5,
                    "department": "Engineering"
                }
            ],
            "corridors": [
                {
                    "corridor_id": "CORR-NDLS-CNB",
                    "section_name": "New Delhi - Kanpur Central",
                    "is_high_density": 1
                }
            ]
        }
        res = self.client.post("/api/whatif", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        raw_text = res.get_data(as_text=True)
        
        # Confirm literal NaN is NOT in JSON output
        self.assertNotIn("NaN", raw_text)
        self.assertNotIn(": NaN", raw_text)
        
        # Confirm strict JSON parsing succeeds without NaN errors
        parsed_json = json.loads(raw_text)
        self.assertIn("schedule", parsed_json)
        self.assertEqual(len(parsed_json["schedule"]), 1)
        # Confirm merged_with is strictly Python None (JSON null)
        self.assertIsNone(parsed_json["schedule"][0]["merged_with"])

if __name__ == "__main__":
    unittest.main()
