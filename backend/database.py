import sqlite3
def connect_db():
    conn = sqlite3.connect("attendance.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
def ensure_column(cur, table, column, definition):
    cur.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
def create_tables():
    conn=connect_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            usn TEXT PRIMARY KEY,
            dob TEXT,
            email TEXT,
            encoding BLOB
        )
        """
    )
    ensure_column(cur, "users", "full_name", "TEXT DEFAULT ''")
    ensure_column(cur, "users", "college", "TEXT DEFAULT ''")
    ensure_column(cur, "users", "created_at", "TEXT DEFAULT ''")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usn TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            status TEXT DEFAULT 'Present',
            marked_at TEXT DEFAULT '',
            UNIQUE(usn, attendance_date, subject)
        )
        """
    )
    cur.execute("PRAGMA table_info(attendance)")
    attendance_columns = {row[1] for row in cur.fetchall()}

    if "date" in attendance_columns and "attendance_date" not in attendance_columns:
        cur.execute("ALTER TABLE attendance RENAME COLUMN date TO attendance_date")
        attendance_columns.remove("date")
        attendance_columns.add("attendance_date")
    if "id" not in attendance_columns:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usn TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                subject TEXT NOT NULL,
                status TEXT DEFAULT 'Present',
                marked_at TEXT DEFAULT '',
                UNIQUE(usn, attendance_date, subject)
            )
            """
        )
        cur.execute(
            """
            INSERT OR IGNORE INTO attendance_new (usn, attendance_date, subject, status, marked_at)
            SELECT
                usn,
                COALESCE(attendance_date, date('now')),
                subject,
                'Present',
                ''
            FROM attendance
            """
        )
        cur.execute("DROP TABLE attendance")
        cur.execute("ALTER TABLE attendance_new RENAME TO attendance")
    else:
        ensure_column(cur, "attendance", "status", "TEXT DEFAULT 'Present'")
        ensure_column(cur, "attendance", "marked_at", "TEXT DEFAULT ''")
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_unique
            ON attendance (usn, attendance_date, subject)
            """
        )
    conn.commit()
