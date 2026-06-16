import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SQLITE_DB_PATH = os.getenv("MARKSENSE_SQLITE_PATH", os.path.join(DATA_DIR, "marksense.sqlite3"))
DEFAULT_FREE_CREDITS = 10

_DB_READY = False


def _dict_factory(cursor: sqlite3.Cursor, row: Tuple[Any, ...]) -> Dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class SQLiteCompatCursor:
    """Tiny PyMySQL-style cursor wrapper for the few direct cursor calls in main.py."""

    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    @staticmethod
    def _sql(sql: str) -> str:
        return sql.replace("%s", "?")

    def execute(self, sql: str, params: Iterable[Any] = ()):
        if params is None:
            params = ()
        return self._cursor.execute(self._sql(sql), tuple(params))

    def executemany(self, sql: str, seq_of_params: Iterable[Iterable[Any]]):
        return self._cursor.executemany(self._sql(sql), seq_of_params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class SQLiteCompatConnection:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def cursor(self):
        return SQLiteCompatCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _raw_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db_connection():
    try:
        ensure_database()
        return SQLiteCompatConnection(_raw_connection())
    except Exception as e:
        print(f"[DB] Cannot open SQLite database: {e}")
        return None


def ensure_database() -> None:
    global _DB_READY
    if _DB_READY:
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = _raw_connection()
    try:
        _create_schema(conn)
        _seed_default_settings(conn)
        _seed_marks_from_json_if_empty(conn)
        conn.commit()
        _DB_READY = True
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL DEFAULT '',
            display_name TEXT,
            provider TEXT,
            scan_credits INTEGER DEFAULT 10,
            role TEXT DEFAULT 'user',
            locked INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY,
            chu_han TEXT,
            chu_han_4 TEXT,
            chu_han_6 TEXT,
            bien_the TEXT,
            phien_am TEXT,
            ten_viet TEXT,
            hoang_de TEXT,
            trieu_dai TEXT,
            nam_bat_dau INTEGER,
            nam_ket_thuc INTEGER,
            ghi_chu TEXT,
            hien_thi_chinh TEXT,
            nien_hieu TEXT,
            nien_dai TEXT,
            hieu_de_en TEXT,
            mo_ta TEXT,
            hieu_de_vi TEXT,
            thu_phap TEXT,
            nghe_thuat TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            image_path TEXT,
            ocr_text TEXT,
            match_result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount_vnd INTEGER NOT NULL,
            credits INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            sepay_tx_id INTEGER UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    _ensure_column(conn, "users", "display_name", "TEXT")
    _ensure_column(conn, "users", "provider", "TEXT")
    _ensure_column(conn, "users", "scan_credits", f"INTEGER DEFAULT {DEFAULT_FREE_CREDITS}")
    _ensure_column(conn, "users", "role", "TEXT DEFAULT 'user'")
    _ensure_column(conn, "users", "locked", "INTEGER DEFAULT 0")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _seed_default_settings(conn: sqlite3.Connection) -> None:
    defaults = {
        "credit_rate": "10000",
        "free_credits": str(DEFAULT_FREE_CREDITS),
        "pkg_pro_credits": "200",
        "pkg_pro_price": "499999",
        "pkg_enterprise_credits": "99999",
        "pkg_enterprise_price": "2490000",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
            (key, value),
        )


def _seed_marks_from_json_if_empty(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT COUNT(*) AS cnt FROM marks").fetchone()
    if row and row["cnt"]:
        return

    path = os.path.join(DATA_DIR, "hieu_de_database.json")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        marks = json.load(f)
    for mark in marks:
        _insert_mark(conn, mark, replace=True)
    print(f"[DB] Seeded {len(marks)} marks into SQLite.")


def _insert_mark(conn: sqlite3.Connection, mark_data: Dict[str, Any], replace: bool = False) -> int:
    bien_the = mark_data.get("bien_the", [])
    if isinstance(bien_the, list):
        bien_the = json.dumps(bien_the, ensure_ascii=False)

    columns = [
        "id", "chu_han", "chu_han_4", "chu_han_6", "bien_the", "phien_am",
        "ten_viet", "hoang_de", "trieu_dai", "nam_bat_dau", "nam_ket_thuc",
        "ghi_chu", "hien_thi_chinh", "nien_hieu", "nien_dai", "hieu_de_en",
        "mo_ta", "hieu_de_vi", "thu_phap", "nghe_thuat",
    ]
    values = [
        mark_data.get("id"),
        mark_data.get("chu_han", ""),
        mark_data.get("chu_han_4", ""),
        mark_data.get("chu_han_6", ""),
        bien_the,
        mark_data.get("phien_am", ""),
        mark_data.get("ten_viet", ""),
        mark_data.get("hoang_de", ""),
        mark_data.get("trieu_dai", ""),
        mark_data.get("nam_bat_dau"),
        mark_data.get("nam_ket_thuc"),
        mark_data.get("ghi_chu", ""),
        mark_data.get("hien_thi_chinh", ""),
        mark_data.get("nien_hieu", ""),
        mark_data.get("nien_dai", ""),
        mark_data.get("hieu_de_en", ""),
        mark_data.get("mo_ta", ""),
        mark_data.get("hieu_de_vi", ""),
        mark_data.get("thu_phap", ""),
        mark_data.get("nghe_thuat", ""),
    ]
    verb = "INSERT OR REPLACE" if replace else "INSERT"
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"{verb} INTO marks ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )
    return int(values[0])


def _format_datetime(value: Any) -> Any:
    if not value:
        return value
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _json_load_field(row: Dict[str, Any], key: str) -> None:
    if row.get(key) and isinstance(row[key], str):
        try:
            row[key] = json.loads(row[key])
        except Exception:
            pass


def _get_setting_int(conn: sqlite3.Connection, key: str, default: int) -> int:
    try:
        row = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,)).fetchone()
        if not row or row.get("setting_value") in (None, ""):
            return default
        return int(row["setting_value"])
    except Exception:
        return default


def _free_credits_for_new_user(conn: sqlite3.Connection) -> int:
    return _get_setting_int(conn, "free_credits", DEFAULT_FREE_CREDITS)


def fetch_all_marks():
    ensure_database()
    conn = _raw_connection()
    try:
        marks = conn.execute("SELECT * FROM marks ORDER BY id").fetchall()
        for mark in marks:
            _json_load_field(mark, "bien_the")
        return marks
    except Exception as e:
        print(f"[DB] Error fetching marks: {e}")
        return None
    finally:
        conn.close()


def create_user(username, password_hash):
    ensure_database()
    conn = _raw_connection()
    try:
        free_credits = _free_credits_for_new_user(conn)
        conn.execute(
            "INSERT INTO users (username, password_hash, scan_credits, role, locked) VALUES (?, ?, ?, 'user', 0)",
            (username, password_hash, free_credits),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error creating user: {e}")
        return False
    finally:
        conn.close()


def get_user_by_username(username):
    ensure_database()
    conn = _raw_connection()
    try:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    ensure_database()
    conn = _raw_connection()
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def add_scan_history(user_id, image_path, ocr_text, match_result):
    ensure_database()
    conn = _raw_connection()
    try:
        user_row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        username = user_row["username"] if user_row else "unknown"
        conn.execute(
            "INSERT INTO scan_history (user_id, username, image_path, ocr_text, match_result) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, image_path, ocr_text, json.dumps(match_result, ensure_ascii=False)),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error adding scan history: {e}")
        return False
    finally:
        conn.close()


def get_scan_history(user_id):
    ensure_database()
    conn = _raw_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM scan_history WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        for row in rows:
            _json_load_field(row, "match_result")
            row["created_at"] = _format_datetime(row.get("created_at"))
        return rows
    except Exception as e:
        print(f"[DB] Error getting scan history: {e}")
        return []
    finally:
        conn.close()


def get_or_create_social_user(email, name, provider):
    ensure_database()
    conn = _raw_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (email,)).fetchone()
        if user:
            return user
        conn.execute(
            """
            INSERT INTO users (username, password_hash, display_name, provider, scan_credits, role, locked)
            VALUES (?, '', ?, ?, ?, 'user', 0)
            """,
            (email, name, provider, _free_credits_for_new_user(conn)),
        )
        conn.commit()
        return conn.execute("SELECT * FROM users WHERE username = ?", (email,)).fetchone()
    except Exception as e:
        print(f"[DB] Social login error: {e}")
        return None
    finally:
        conn.close()


def ensure_credits_column():
    ensure_database()


def get_user_credits(user_id):
    ensure_database()
    conn = _raw_connection()
    try:
        row = conn.execute("SELECT scan_credits FROM users WHERE id = ?", (user_id,)).fetchone()
        if row and row.get("scan_credits") is not None:
            return row["scan_credits"]
        return _free_credits_for_new_user(conn)
    except Exception as e:
        print(f"[DB] Error getting credits: {e}")
        return 0
    finally:
        conn.close()


def deduct_credit(user_id):
    ensure_database()
    conn = _raw_connection()
    try:
        row = conn.execute("SELECT scan_credits FROM users WHERE id = ?", (user_id,)).fetchone()
        current = row["scan_credits"] if row and row.get("scan_credits") is not None else 0
        if current <= 0:
            return -1
        new_credits = current - 1
        conn.execute("UPDATE users SET scan_credits = ? WHERE id = ?", (new_credits, user_id))
        conn.commit()
        return new_credits
    except Exception as e:
        print(f"[DB] Error deducting credit: {e}")
        return -1
    finally:
        conn.close()


def add_credits(user_id, amount):
    ensure_database()
    conn = _raw_connection()
    try:
        conn.execute(
            "UPDATE users SET scan_credits = COALESCE(scan_credits, 0) + ? WHERE id = ?",
            (amount, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error adding credits: {e}")
        return False
    finally:
        conn.close()


def create_payment(user_id: int, amount_vnd: int, credits: int):
    ensure_database()
    conn = _raw_connection()
    try:
        cur = conn.execute(
            "INSERT INTO payments (user_id, amount_vnd, credits) VALUES (?, ?, ?)",
            (user_id, amount_vnd, credits),
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"[DB] Error creating payment: {e}")
        return None
    finally:
        conn.close()


def get_payment(payment_id: int):
    ensure_database()
    conn = _raw_connection()
    try:
        return conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    finally:
        conn.close()


def get_user_payments(user_id: int):
    ensure_database()
    conn = _raw_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        for row in rows:
            row["created_at"] = _format_datetime(row.get("created_at"))
        return rows
    finally:
        conn.close()


def complete_payment(payment_id: int, sepay_tx_id: int):
    ensure_database()
    conn = _raw_connection()
    try:
        cur = conn.execute(
            "UPDATE payments SET status = 'completed', sepay_tx_id = ? WHERE id = ?",
            (sepay_tx_id, payment_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"[DB] Error completing payment: {e}")
        return False
    finally:
        conn.close()


def ensure_admin_columns():
    ensure_database()


def create_admin_account(username, password_hash):
    ensure_database()
    conn = _raw_connection()
    try:
        existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET role = 'admin', password_hash = ?, locked = 0 WHERE username = ?",
                (password_hash, username),
            )
            conn.commit()
            print(f"[DB] Updated existing user '{username}' to admin role.")
            return True
        conn.execute(
            """
            INSERT INTO users (username, password_hash, role, scan_credits, locked)
            VALUES (?, ?, 'admin', 9999, 0)
            """,
            (username, password_hash),
        )
        conn.commit()
        print(f"[DB] Created admin account '{username}'.")
        return True
    except Exception as e:
        print(f"[DB] Error creating admin account: {e}")
        return False
    finally:
        conn.close()


def admin_login(username, password_hash_verify_fn, password):
    ensure_database()
    conn = _raw_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return None
        if not password_hash_verify_fn(password, user["password_hash"]):
            return None
        if user.get("role") != "admin":
            return None
        return user
    finally:
        conn.close()


def get_all_users_admin():
    ensure_database()
    conn = _raw_connection()
    try:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.scan_credits, u.role, u.locked, u.created_at,
                   (SELECT COUNT(*) FROM scan_history sh WHERE sh.user_id = u.id) AS total_scans,
                   (SELECT COALESCE(SUM(p.amount_vnd), 0) FROM payments p WHERE p.user_id = u.id AND p.status = 'completed') AS total_spent
            FROM users u ORDER BY u.created_at DESC
            """
        ).fetchall()
        for row in rows:
            row["created_at"] = _format_datetime(row.get("created_at"))
            row["locked"] = row.get("locked") or 0
            row["role"] = row.get("role") or "user"
        return rows
    except Exception as e:
        print(f"[DB] Error getting all users: {e}")
        return []
    finally:
        conn.close()


def toggle_user_lock(user_id, locked):
    ensure_database()
    conn = _raw_connection()
    try:
        conn.execute("UPDATE users SET locked = ? WHERE id = ?", (1 if locked else 0, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error toggling lock: {e}")
        return False
    finally:
        conn.close()


def admin_update_credits(user_id, amount, action="add"):
    ensure_database()
    conn = _raw_connection()
    try:
        if action == "set":
            conn.execute("UPDATE users SET scan_credits = ? WHERE id = ?", (amount, user_id))
        elif action == "subtract":
            conn.execute(
                "UPDATE users SET scan_credits = MAX(0, COALESCE(scan_credits, 0) - ?) WHERE id = ?",
                (amount, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET scan_credits = COALESCE(scan_credits, 0) + ? WHERE id = ?",
                (amount, user_id),
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating credits: {e}")
        return False
    finally:
        conn.close()


def admin_reset_password(user_id, new_password_hash):
    ensure_database()
    conn = _raw_connection()
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error resetting password: {e}")
        return False
    finally:
        conn.close()


def admin_delete_user(user_id):
    ensure_database()
    conn = _raw_connection()
    try:
        user = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "Khong tim thay nguoi dung"
        if user.get("role") == "admin":
            return False, "Khong the xoa tai khoan admin"
        conn.execute("DELETE FROM scan_history WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "Da xoa nguoi dung"
    except Exception as e:
        print(f"[DB] Error deleting user: {e}")
        return False, "Loi xoa nguoi dung"
    finally:
        conn.close()


def get_all_payments_admin(status_filter=None):
    ensure_database()
    conn = _raw_connection()
    try:
        params: Tuple[Any, ...] = ()
        query = """
            SELECT p.*, u.username
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
        """
        if status_filter and status_filter != "all":
            query += " WHERE p.status = ?"
            params = (status_filter,)
        query += " ORDER BY p.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        for row in rows:
            row["created_at"] = _format_datetime(row.get("created_at"))
        return rows
    except Exception as e:
        print(f"[DB] Error getting all payments: {e}")
        return []
    finally:
        conn.close()


def admin_approve_payment(payment_id):
    ensure_database()
    conn = _raw_connection()
    try:
        payment = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if not payment:
            return False, "Khong tim thay giao dich"
        if payment["status"] == "completed":
            return False, "Giao dich da duoc duyet truoc do"

        import random

        manual_tx_id = random.randint(90000000, 99999999)
        conn.execute(
            "UPDATE payments SET status = 'completed', sepay_tx_id = ? WHERE id = ?",
            (manual_tx_id, payment_id),
        )
        conn.execute(
            "UPDATE users SET scan_credits = COALESCE(scan_credits, 0) + ? WHERE id = ?",
            (payment["credits"], payment["user_id"]),
        )
        conn.commit()
        return True, f"Da duyet thanh cong, cong {payment['credits']} credits cho user #{payment['user_id']}"
    except Exception as e:
        print(f"[DB] Error approving payment: {e}")
        return False, str(e)
    finally:
        conn.close()


def get_all_scan_history_admin(limit=200):
    ensure_database()
    conn = _raw_connection()
    try:
        rows = conn.execute(
            """
            SELECT sh.*, u.username
            FROM scan_history sh
            LEFT JOIN users u ON sh.user_id = u.id
            ORDER BY sh.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for row in rows:
            _json_load_field(row, "match_result")
            row["created_at"] = _format_datetime(row.get("created_at"))
        return rows
    except Exception as e:
        print(f"[DB] Error getting all scan history: {e}")
        return []
    finally:
        conn.close()


def get_dashboard_stats():
    ensure_database()
    conn = _raw_connection()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        seven_days_ago = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
        stats: Dict[str, Any] = {}

        stats["total_users"] = conn.execute(
            "SELECT COUNT(*) AS cnt FROM users WHERE role != 'admin' OR role IS NULL"
        ).fetchone()["cnt"]
        stats["new_users_today"] = conn.execute(
            "SELECT COUNT(*) AS cnt FROM users WHERE DATE(created_at) >= ?",
            (today,),
        ).fetchone()["cnt"]
        stats["total_revenue"] = conn.execute(
            "SELECT COALESCE(SUM(amount_vnd), 0) AS total FROM payments WHERE status = 'completed'"
        ).fetchone()["total"]
        stats["revenue_this_month"] = conn.execute(
            "SELECT COALESCE(SUM(amount_vnd), 0) AS total FROM payments WHERE status = 'completed' AND strftime('%Y-%m', created_at) = ?",
            (month,),
        ).fetchone()["total"]
        stats["total_scans"] = conn.execute("SELECT COUNT(*) AS cnt FROM scan_history").fetchone()["cnt"]
        stats["scans_today"] = conn.execute(
            "SELECT COUNT(*) AS cnt FROM scan_history WHERE DATE(created_at) >= ?",
            (today,),
        ).fetchone()["cnt"]
        stats["pending_payments"] = conn.execute(
            "SELECT COUNT(*) AS cnt FROM payments WHERE status = 'pending'"
        ).fetchone()["cnt"]
        stats["total_marks"] = conn.execute("SELECT COUNT(*) AS cnt FROM marks").fetchone()["cnt"]

        revenue_rows = conn.execute(
            """
            SELECT DATE(created_at) AS day, COALESCE(SUM(amount_vnd), 0) AS revenue
            FROM payments
            WHERE status = 'completed' AND DATE(created_at) >= ?
            GROUP BY DATE(created_at) ORDER BY day
            """,
            (seven_days_ago,),
        ).fetchall()
        stats["revenue_chart"] = [
            {"day": datetime.strptime(r["day"], "%Y-%m-%d").strftime("%d/%m"), "revenue": r["revenue"]}
            for r in revenue_rows
        ]

        scan_rows = conn.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS scans
            FROM scan_history
            WHERE DATE(created_at) >= ?
            GROUP BY DATE(created_at) ORDER BY day
            """,
            (seven_days_ago,),
        ).fetchall()
        stats["scans_chart"] = [
            {"day": datetime.strptime(r["day"], "%Y-%m-%d").strftime("%d/%m"), "scans": r["scans"]}
            for r in scan_rows
        ]
        return stats
    except Exception as e:
        print(f"[DB] Error getting dashboard stats: {e}")
        return {}
    finally:
        conn.close()


def admin_add_mark(mark_data):
    ensure_database()
    conn = _raw_connection()
    try:
        row = conn.execute("SELECT MAX(id) AS max_id FROM marks").fetchone()
        new_id = (row["max_id"] or 0) + 1
        mark_data = dict(mark_data)
        mark_data["id"] = new_id
        _insert_mark(conn, mark_data)
        conn.commit()
        return new_id
    except Exception as e:
        print(f"[DB] Error adding mark: {e}")
        return False
    finally:
        conn.close()


def admin_update_mark(mark_id, mark_data):
    ensure_database()
    conn = _raw_connection()
    try:
        existing = conn.execute("SELECT id FROM marks WHERE id = ?", (mark_id,)).fetchone()
        if not existing:
            return False
        mark_data = dict(mark_data)
        mark_data["id"] = mark_id
        _insert_mark(conn, mark_data, replace=True)
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating mark: {e}")
        return False
    finally:
        conn.close()


def admin_delete_mark(mark_id):
    ensure_database()
    conn = _raw_connection()
    try:
        conn.execute("DELETE FROM marks WHERE id = ?", (mark_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error deleting mark: {e}")
        return False
    finally:
        conn.close()


def get_system_settings():
    ensure_database()
    conn = _raw_connection()
    try:
        rows = conn.execute("SELECT * FROM system_settings").fetchall()
        return {row["setting_key"]: row["setting_value"] for row in rows}
    except Exception as e:
        print(f"[DB] Error getting settings: {e}")
        return {}
    finally:
        conn.close()


def update_system_setting(key, value):
    ensure_database()
    conn = _raw_connection()
    try:
        conn.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating setting: {e}")
        return False
    finally:
        conn.close()


def apply_free_credits_to_unpaid_users(amount: int):
    ensure_database()
    conn = _raw_connection()
    try:
        amount = max(0, int(amount))
        cursor = conn.execute(
            """
            UPDATE users
            SET scan_credits = ?
            WHERE COALESCE(role, 'user') != 'admin'
              AND id NOT IN (
                SELECT DISTINCT user_id
                FROM payments
                WHERE status = 'completed'
                  AND user_id IS NOT NULL
              )
            """,
            (amount,),
        )
        conn.commit()
        return True, cursor.rowcount
    except Exception as e:
        print(f"[DB] Error applying free credits to unpaid users: {e}")
        return False, 0
    finally:
        conn.close()
