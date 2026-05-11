import pymysql
import json
from contextlib import contextmanager

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'hieude_ai_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 2
}

def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"[DB] Cannot connect to MySQL: {e}")
        return None

def fetch_all_marks():
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM marks")
            marks = cursor.fetchall()
            # Restore JSON fields
            for mark in marks:
                if mark.get('bien_the'):
                    if isinstance(mark['bien_the'], str):
                        try:
                            mark['bien_the'] = json.loads(mark['bien_the'])
                        except:
                            mark['bien_the'] = []
            return marks
    except Exception as e:
        print(f"[DB] Error fetching marks: {e}")
        return None
    finally:
        conn.close()

def create_user(username, password_hash):
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
    finally:
        conn.close()

def add_scan_history(user_id, image_path, ocr_text, match_result):
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            user_row = cursor.fetchone()
            username = user_row['username'] if user_row else 'unknown'
            
            cursor.execute(
                "INSERT INTO scan_history (user_id, username, image_path, ocr_text, match_result) VALUES (%s, %s, %s, %s, %s)",
                (user_id, username, image_path, ocr_text, json.dumps(match_result, ensure_ascii=False))
            )
        conn.commit()
        return True
    finally:
        conn.close()

def get_scan_history(user_id):
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM scan_history WHERE user_id = %s ORDER BY created_at DESC", 
                (user_id,)
            )
            rows = cursor.fetchall()
            for r in rows:
                if r.get('match_result'):
                    try:
                        r['match_result'] = json.loads(r['match_result'])
                    except:
                        pass
                # Format datetime for JSON safely
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            return rows
    except Exception as e:
        print(e)
        return []
    finally:
        conn.close()

def get_or_create_social_user(email, name, provider):
    """Tìm hoặc tạo user từ đăng nhập mạng xã hội (Google/Facebook)."""
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            # Kiểm tra user đã tồn tại chưa
            cursor.execute("SELECT * FROM users WHERE username = %s", (email,))
            user = cursor.fetchone()
            if user:
                return user
            # Tạo user mới (không cần password cho social login)
            cursor.execute(
                "INSERT INTO users (username, password_hash, display_name, provider, scan_credits) VALUES (%s, %s, %s, %s, %s)",
                (email, '', name, provider, 10)
            )
        conn.commit()
        # Lấy lại user vừa tạo
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (email,))
            return cursor.fetchone()
    except Exception as e:
        print(f"[DB] Social login error: {e}")
        # Nếu bảng chưa có cột display_name/provider, fallback tạo đơn giản
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (email, '')
                )
            conn.commit()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (email,))
                return cursor.fetchone()
        except Exception as e2:
            print(f"[DB] Fallback social login error: {e2}")
            return None
    finally:
        conn.close()

# ========== SCAN CREDITS SYSTEM ==========

DEFAULT_FREE_CREDITS = 10

def ensure_credits_column():
    """Đảm bảo cột scan_credits tồn tại trong bảng users."""
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = 'users' AND column_name = 'scan_credits'
            """, (DB_CONFIG['database'],))
            result = cursor.fetchone()
            if result['cnt'] == 0:
                cursor.execute(f"ALTER TABLE users ADD COLUMN scan_credits INT DEFAULT {DEFAULT_FREE_CREDITS}")
                cursor.execute(f"UPDATE users SET scan_credits = {DEFAULT_FREE_CREDITS} WHERE scan_credits IS NULL")
                conn.commit()
                print("[DB] Added scan_credits column to users table.")
            else:
                print("[DB] scan_credits column already exists.")
    except Exception as e:
        print(f"[DB] Error ensuring credits column: {e}")
    finally:
        conn.close()

def get_user_credits(user_id):
    """Lấy số lượt phân tích còn lại của user."""
    conn = get_db_connection()
    if not conn: return 0
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT scan_credits FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if row and row.get('scan_credits') is not None:
                return row['scan_credits']
            return DEFAULT_FREE_CREDITS
    except Exception as e:
        print(f"[DB] Error getting credits: {e}")
        return 0
    finally:
        conn.close()

def deduct_credit(user_id):
    """Trừ 1 lượt phân tích. Trả về số lượt còn lại hoặc -1 nếu hết lượt."""
    conn = get_db_connection()
    if not conn: return -1
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT scan_credits FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            current = row['scan_credits'] if row and row.get('scan_credits') is not None else 0
            if current <= 0:
                return -1
            new_credits = current - 1
            cursor.execute("UPDATE users SET scan_credits = %s WHERE id = %s", (new_credits, user_id))
        conn.commit()
        return new_credits
    except Exception as e:
        print(f"[DB] Error deducting credit: {e}")
        return -1
    finally:
        conn.close()

def add_credits(user_id, amount):
    """Thêm lượt phân tích cho user (sau khi mua gói)."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET scan_credits = scan_credits + %s WHERE id = %s", (amount, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error adding credits: {e}")
        return False
    finally:
        conn.close()

def create_payment(user_id: int, amount_vnd: int, credits: int):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO payments (user_id, amount_vnd, credits) VALUES (%s, %s, %s)",
                (user_id, amount_vnd, credits)
            )
            conn.commit()
            return cursor.lastrowid
    finally:
        if conn: conn.close()

def get_payment(payment_id: int):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
            return cursor.fetchone()
    finally:
        if conn: conn.close()

def get_user_payments(user_id: int):
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM payments WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            return rows
    finally:
        if conn: conn.close()

def complete_payment(payment_id: int, sepay_tx_id: int):
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE payments SET status = 'completed', sepay_tx_id = %s WHERE id = %s",
                (sepay_tx_id, payment_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    finally:
        if conn: conn.close()


# ========== ADMIN SYSTEM ==========

def ensure_admin_columns():
    """Đảm bảo cột role và locked tồn tại trong bảng users."""
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cursor:
            # Thêm cột role
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = 'users' AND column_name = 'role'
            """, (DB_CONFIG['database'],))
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
                conn.commit()
                print("[DB] Added role column to users table.")
            
            # Thêm cột locked
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM information_schema.columns 
                WHERE table_schema = %s AND table_name = 'users' AND column_name = 'locked'
            """, (DB_CONFIG['database'],))
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute("ALTER TABLE users ADD COLUMN locked TINYINT DEFAULT 0")
                conn.commit()
                print("[DB] Added locked column to users table.")

            # Tạo bảng system_settings nếu chưa có
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    setting_key VARCHAR(100) PRIMARY KEY,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Thêm cài đặt mặc định
            cursor.execute("SELECT COUNT(*) as cnt FROM system_settings WHERE setting_key = 'credit_rate'")
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute("INSERT INTO system_settings (setting_key, setting_value) VALUES ('credit_rate', '10000')")
                conn.commit()
            
            cursor.execute("SELECT COUNT(*) as cnt FROM system_settings WHERE setting_key = 'free_credits'")
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute("INSERT INTO system_settings (setting_key, setting_value) VALUES ('free_credits', '10')")
                conn.commit()
                
    except Exception as e:
        print(f"[DB] Error ensuring admin columns: {e}")
    finally:
        conn.close()


def create_admin_account(username, password_hash):
    """Tạo tài khoản admin nếu chưa tồn tại."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing = cursor.fetchone()
            if existing:
                # Cập nhật role thành admin
                cursor.execute("UPDATE users SET role = 'admin', password_hash = %s WHERE username = %s", (password_hash, username))
                conn.commit()
                print(f"[DB] Updated existing user '{username}' to admin role.")
                return True
            else:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, scan_credits) VALUES (%s, %s, 'admin', 9999)",
                    (username, password_hash)
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
    """Đăng nhập admin, trả về user nếu role='admin'."""
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if not user:
                return None
            if not password_hash_verify_fn(password, user['password_hash']):
                return None
            if user.get('role') != 'admin':
                return None
            return user
    finally:
        conn.close()


def get_all_users_admin():
    """Lấy danh sách tất cả users cho admin."""
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.scan_credits, u.role, u.locked, u.created_at,
                       (SELECT COUNT(*) FROM scan_history sh WHERE sh.user_id = u.id) as total_scans,
                       (SELECT COALESCE(SUM(p.amount_vnd), 0) FROM payments p WHERE p.user_id = u.id AND p.status = 'completed') as total_spent
                FROM users u ORDER BY u.created_at DESC
            """)
            rows = cursor.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                if r.get('locked') is None:
                    r['locked'] = 0
                if r.get('role') is None:
                    r['role'] = 'user'
            return rows
    except Exception as e:
        print(f"[DB] Error getting all users: {e}")
        return []
    finally:
        conn.close()


def toggle_user_lock(user_id, locked):
    """Khóa/Mở khóa tài khoản user."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET locked = %s WHERE id = %s", (1 if locked else 0, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error toggling lock: {e}")
        return False
    finally:
        conn.close()


def admin_update_credits(user_id, amount, action='add'):
    """Admin cộng/trừ credit cho user."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            if action == 'set':
                cursor.execute("UPDATE users SET scan_credits = %s WHERE id = %s", (amount, user_id))
            elif action == 'add':
                cursor.execute("UPDATE users SET scan_credits = scan_credits + %s WHERE id = %s", (amount, user_id))
            elif action == 'subtract':
                cursor.execute("UPDATE users SET scan_credits = GREATEST(0, scan_credits - %s) WHERE id = %s", (amount, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating credits: {e}")
        return False
    finally:
        conn.close()


def admin_reset_password(user_id, new_password_hash):
    """Admin reset mật khẩu cho user."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error resetting password: {e}")
        return False
    finally:
        conn.close()


def get_all_payments_admin(status_filter=None):
    """Lấy danh sách tất cả giao dịch cho admin."""
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT p.*, u.username 
                FROM payments p
                LEFT JOIN users u ON p.user_id = u.id
            """
            if status_filter and status_filter != 'all':
                query += f" WHERE p.status = %s"
                query += " ORDER BY p.created_at DESC"
                cursor.execute(query, (status_filter,))
            else:
                query += " ORDER BY p.created_at DESC"
                cursor.execute(query)
            rows = cursor.fetchall()
            for r in rows:
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            return rows
    except Exception as e:
        print(f"[DB] Error getting all payments: {e}")
        return []
    finally:
        conn.close()


def admin_approve_payment(payment_id):
    """Admin duyệt thủ công một giao dịch pending."""
    conn = get_db_connection()
    if not conn: return False, "DB connection failed"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
            payment = cursor.fetchone()
            if not payment:
                return False, "Không tìm thấy giao dịch"
            if payment['status'] == 'completed':
                return False, "Giao dịch đã được duyệt trước đó"
            
            import random
            manual_tx_id = random.randint(90000000, 99999999)
            cursor.execute(
                "UPDATE payments SET status = 'completed', sepay_tx_id = %s WHERE id = %s",
                (manual_tx_id, payment_id)
            )
            cursor.execute(
                "UPDATE users SET scan_credits = scan_credits + %s WHERE id = %s",
                (payment['credits'], payment['user_id'])
            )
        conn.commit()
        return True, f"Đã duyệt thành công, cộng {payment['credits']} credits cho user #{payment['user_id']}"
    except Exception as e:
        print(f"[DB] Error approving payment: {e}")
        return False, str(e)
    finally:
        conn.close()


def get_all_scan_history_admin(limit=200):
    """Lấy toàn bộ lịch sử scan cho admin."""
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT sh.*, u.username
                FROM scan_history sh
                LEFT JOIN users u ON sh.user_id = u.id
                ORDER BY sh.created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            for r in rows:
                if r.get('match_result'):
                    if isinstance(r['match_result'], str):
                        try:
                            r['match_result'] = json.loads(r['match_result'])
                        except:
                            pass
                if r.get('created_at'):
                    r['created_at'] = r['created_at'].strftime("%Y-%m-%d %H:%M:%S")
            return rows
    except Exception as e:
        print(f"[DB] Error getting all scan history: {e}")
        return []
    finally:
        conn.close()


def get_dashboard_stats():
    """Lấy thống kê tổng quan cho Dashboard."""
    conn = get_db_connection()
    if not conn: return {}
    try:
        stats = {}
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role != 'admin' OR role IS NULL")
            stats['total_users'] = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE created_at >= CURDATE()")
            stats['new_users_today'] = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COALESCE(SUM(amount_vnd), 0) as total FROM payments WHERE status = 'completed'")
            stats['total_revenue'] = cursor.fetchone()['total']
            
            cursor.execute("SELECT COALESCE(SUM(amount_vnd), 0) as total FROM payments WHERE status = 'completed' AND MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())")
            stats['revenue_this_month'] = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM scan_history")
            stats['total_scans'] = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM scan_history WHERE created_at >= CURDATE()")
            stats['scans_today'] = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM payments WHERE status = 'pending'")
            stats['pending_payments'] = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM marks")
            stats['total_marks'] = cursor.fetchone()['cnt']
            
            # Doanh thu 7 ngày gần nhất
            cursor.execute("""
                SELECT DATE(created_at) as day, COALESCE(SUM(amount_vnd), 0) as revenue
                FROM payments WHERE status = 'completed' AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at) ORDER BY day
            """)
            stats['revenue_chart'] = [{'day': r['day'].strftime("%d/%m"), 'revenue': r['revenue']} for r in cursor.fetchall()]
            
            # Lượt scan 7 ngày gần nhất
            cursor.execute("""
                SELECT DATE(created_at) as day, COUNT(*) as scans
                FROM scan_history WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at) ORDER BY day
            """)
            stats['scans_chart'] = [{'day': r['day'].strftime("%d/%m"), 'scans': r['scans']} for r in cursor.fetchall()]
            
        return stats
    except Exception as e:
        print(f"[DB] Error getting dashboard stats: {e}")
        return {}
    finally:
        conn.close()


def admin_add_mark(mark_data):
    """Thêm hiệu đề mới vào database."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            # Lấy ID lớn nhất
            cursor.execute("SELECT MAX(id) as max_id FROM marks")
            result = cursor.fetchone()
            new_id = (result['max_id'] or 0) + 1
            
            bien_the = mark_data.get('bien_the', [])
            if isinstance(bien_the, list):
                bien_the = json.dumps(bien_the, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO marks (id, chu_han, chu_han_4, chu_han_6, bien_the, phien_am, ten_viet, 
                hoang_de, trieu_dai, nam_bat_dau, nam_ket_thuc, ghi_chu, hien_thi_chinh, 
                nien_hieu, nien_dai, hieu_de_en, mo_ta, hieu_de_vi, thu_phap, nghe_thuat)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                new_id, mark_data.get('chu_han', ''), mark_data.get('chu_han_4', ''),
                mark_data.get('chu_han_6', ''), bien_the, mark_data.get('phien_am', ''),
                mark_data.get('ten_viet', ''), mark_data.get('hoang_de', ''),
                mark_data.get('trieu_dai', ''), mark_data.get('nam_bat_dau'),
                mark_data.get('nam_ket_thuc'), mark_data.get('ghi_chu', ''),
                mark_data.get('hien_thi_chinh', ''), mark_data.get('nien_hieu', ''),
                mark_data.get('nien_dai', ''), mark_data.get('hieu_de_en', ''),
                mark_data.get('mo_ta', ''), mark_data.get('hieu_de_vi', ''),
                mark_data.get('thu_phap', ''), mark_data.get('nghe_thuat', '')
            ))
        conn.commit()
        return new_id
    except Exception as e:
        print(f"[DB] Error adding mark: {e}")
        return False
    finally:
        conn.close()


def admin_update_mark(mark_id, mark_data):
    """Cập nhật hiệu đề trong database."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            bien_the = mark_data.get('bien_the', [])
            if isinstance(bien_the, list):
                bien_the = json.dumps(bien_the, ensure_ascii=False)
            
            cursor.execute("""
                UPDATE marks SET chu_han=%s, chu_han_4=%s, chu_han_6=%s, bien_the=%s, phien_am=%s,
                ten_viet=%s, hoang_de=%s, trieu_dai=%s, nam_bat_dau=%s, nam_ket_thuc=%s,
                ghi_chu=%s, hien_thi_chinh=%s, nien_hieu=%s, nien_dai=%s, hieu_de_en=%s,
                mo_ta=%s, hieu_de_vi=%s, thu_phap=%s, nghe_thuat=%s
                WHERE id=%s
            """, (
                mark_data.get('chu_han', ''), mark_data.get('chu_han_4', ''),
                mark_data.get('chu_han_6', ''), bien_the, mark_data.get('phien_am', ''),
                mark_data.get('ten_viet', ''), mark_data.get('hoang_de', ''),
                mark_data.get('trieu_dai', ''), mark_data.get('nam_bat_dau'),
                mark_data.get('nam_ket_thuc'), mark_data.get('ghi_chu', ''),
                mark_data.get('hien_thi_chinh', ''), mark_data.get('nien_hieu', ''),
                mark_data.get('nien_dai', ''), mark_data.get('hieu_de_en', ''),
                mark_data.get('mo_ta', ''), mark_data.get('hieu_de_vi', ''),
                mark_data.get('thu_phap', ''), mark_data.get('nghe_thuat', ''),
                mark_id
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating mark: {e}")
        return False
    finally:
        conn.close()


def admin_delete_mark(mark_id):
    """Xóa hiệu đề khỏi database."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM marks WHERE id = %s", (mark_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error deleting mark: {e}")
        return False
    finally:
        conn.close()


def get_system_settings():
    """Lấy tất cả system settings."""
    conn = get_db_connection()
    if not conn: return {}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM system_settings")
            rows = cursor.fetchall()
            return {r['setting_key']: r['setting_value'] for r in rows}
    except Exception as e:
        print(f"[DB] Error getting settings: {e}")
        return {}
    finally:
        conn.close()


def update_system_setting(key, value):
    """Cập nhật một system setting."""
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value = %s
            """, (key, value, value))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] Error updating setting: {e}")
        return False
    finally:
        conn.close()
