from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from database import connect_db, create_tables
from face_utils import get_encoding
app = Flask(__name__)
CORS(app)

create_tables()

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
FACE_MATCH_THRESHOLD = 0.68
COLLEGE_FALLBACK = [
"Indian Institute of Science",
"Indian Institute of Technology Bombay",
"Indian Institute of Technology Delhi",
"National Institute of Technology Trichy",
"BMS College of Engineering",
"Christ University",
"PES University",
"RV College of Engineering",
"St. Joseph's University",
"Visvesvaraya Technological University",
"Ballari Institute of technology and management",
"Siddaganga Institute of Technology",
    }
def json_error(message, status=400):
return jsonify({"success": False, "message": message}), status
def clean_text(value):
return str(value or "").strip()


def serialize_user(row):
return {
"usn": row["usn"],
"full_name": row["full_name"],
"dob": row["dob"],
"email": row["email"],
"college": row["college"],
"created_at": row["created_at"],
}
@app.route("/health")
def health():
return jsonify({"success": True, "message": "Attendance API is running"})

@app.route("/")
def root():
return send_from_directory(FRONTEND_DIR, "register.html")


@app.route("/frontend/<path:filename>")
def frontend_files(filename):
return send_from_directory(FRONTEND_DIR, filename)


@app.route("/colleges")
def colleges():
try:
res = requests.get(
"http://universities.hipolabs.com/search?country=India",
timeout=5,
)
res.raise_for_status()
data = res.json()
colleges_list = sorted({item["name"] for item in data if item.get("name")})
return jsonify(colleges_list[:100] or COLLEGE_FALLBACK)
except requests.RequestException:
return jsonify(COLLEGE_FALLBACK)

@app.route("/register", methods=["POST"])
def register():
data = request.get_json(silent=True) or {}
required_fields = ["usn", "full_name", "dob", "email", "college", "image"]
missing = [field for field in required_fields if not clean_text(data.get(field))]
if missing:
return json_error(f"Missing fields: {', '.join(missing)}")
encoding=get_encoding(data["image"])
if encoding is None:
return json_error("No face detected. Please capture a clearer image.")

payload = (
clean_text(data["usn"]).upper(),
clean_text(data["full_name"]),
clean_text(data["dob"]),
clean_text(data["email"]).lower(),
clean_text(data["college"]),
encoding.tobytes(),
datetime.utcnow().isoformat(timespec="seconds"),
)
conn = connect_db()
cur = conn.cursor()
cur.execute(
"""
INSERT INTO users (usn, full_name, dob, email, college, encoding, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(usn) DO UPDATE SET
full_name=excluded.full_name,
dob=excluded.dob,
email=excluded.email,
college=excluded.college,
encoding=excluded.encoding,
created_at=excluded.created_at
""",
payload,
)

conn.commit()

return jsonify(
{
"success": True,
"message": "Registration completed successfully.",
"user": {
"usn": payload[0],
"full_name": payload[1],
"email": payload[3],
"college": payload[4],
},
}
)
@app.route("/login", methods=["POST"])
def login():
data = request.get_json(silent=True) or {}

required_fields = ["usn", "dob", "email", "image"]
missing = [field for field in required_fields if not clean_text(data.get(field))]
if missing:
return json_error(f"Missing fields: {', '.join(missing)}")
encoding = get_encoding(data["image"])
if encoding is None:
return json_error("No face detected. Please look at the camera and try again.")
conn = connect_db()
cur = conn.cursor()

cur.execute(
"""
SELECT usn, full_name, dob, email, college, encoding, created_at
FROM users
WHERE usn=? AND dob=? AND email=?
""",
(
clean_text(data["usn"]).upper(),
clean_text(data["dob"]),
clean_text(data["email"]).lower(),
),
)
row = cur.fetchone()

if row is None:
return json_error("No registered user found with those details.", 404)

stored = np.frombuffer(row["encoding"], dtype=np.float64)
distance = float(np.linalg.norm(stored - encoding))

if distance >= FACE_MATCH_THRESHOLD:
return json_error(
f"Face match failed. Score: {distance:.3f}",
401,
)
return jsonify(
{
"success": True,
"message": "Login successful.",
"user": serialize_user(row),
"match_score": round(max(0.0, 1 - distance), 3),
}
)
@app.route("/dashboard")
def dashboard():
usn = clean_text(request.args.get("usn")).upper()

if not usn:
return json_error("USN is required.")

conn = connect_db()
cur = conn.cursor()

cur.execute(
"""
SELECT usn, full_name, dob, email, college, created_at
FROM users
WHERE usn=?
""",
(usn,),
)
user = cur.fetchone()

if user is None:
return json_error("User not found.", 404)

cur.execute(
"""
SELECT subject, COUNT(*) AS total
FROM attendance
WHERE usn=?
GROUP BY subject
""",
(usn,),
)

subjects = [{"subject": r["subject"], "count": r["total"]} for r in cur.fetchall()]

cur.execute(
"""
SELECT id, usn, subject, attendance_date, status, marked_at
FROM attendance
WHERE usn=?
ORDER BY attendance_date DESC
LIMIT 8
""",
(usn,),
)

recent = [dict(r) for r in cur.fetchall()]

cur.execute("SELECT COUNT(*) AS total FROM attendance WHERE usn=?", (usn,))
total = cur.fetchone()["total"]

return jsonify(
{
"success": True,
"user": serialize_user(user),
"stats": {"total_classes": total},
"attendance_by_subject": subjects,
"recent_attendance": recent,
}
)


    
    @app.route("/mark", methods=["POST"])
    def mark():
    data = request.get_json(silent=True) or {}
    
    usn = clean_text(data.get("usn")).upper()
    subject = clean_text(data.get("subject"))
    attendance_date = clean_text(data.get("attendance_date")) or str(date.today())
    
    if not usn or not subject:
    return json_error("USN and subject are required.")
conn = connect_db()
cur = conn.cursor()
cur.execute("SELECT 1 FROM users WHERE usn=?", (usn,))
if cur.fetchone() is None:
return json_error("Register first.", 404)

try:
cur.execute(
"""
INSERT INTO attendance (usn, subject, attendance_date, status, marked_at)
VALUES (?, ?, ?, ?, ?)
""",
(
usn,
subject,
attendance_date,
"Present",
datetime.utcnow().isoformat(timespec="seconds"),
),
)

conn.commit()

except Exception as exc:
if "UNIQUE constraint failed" in str(exc):
return json_error("Already marked today.", 409)
raise

return jsonify(
{
"success": True,
"message": f"Attendance marked for {subject}",
}
)
@app.route("/attendance")
def attendance():
usn = clean_text(request.args.get("usn")).upper()

if not usn:
return json_error("USN required")

conn = connect_db()
cur = conn.cursor()

cur.execute(
"""
SELECT * FROM attendance WHERE usn=? ORDER BY attendance_date DESC
""",
(usn,),
)

return jsonify({"success": True, "records": [dict(r) for r in cur.fetchall()]})
@app.route("/export")
def export():
usn = clean_text(request.args.get("usn")).upper()
conn = connect_db()

if usn:
df = pd.read_sql_query(
"SELECT * FROM attendance WHERE usn=?", conn, params=(usn,)
)
filename = f"{usn}.xlsx"
else:
df = pd.read_sql_query("SELECT * FROM attendance", conn)
filename = "all.xlsx"

buffer = BytesIO()
df.to_excel(buffer, index=False)
buffer.seek(0)

return send_file(buffer, download_name=filename, as_attachment=True)

if __name__ == "__main__":
app.run(debug=True)
