import db
import pymysql

conn = db.get_db_connection()

updates = {
    "Minh Triều": "Nhà Minh",
    "Thanh Triều": "Nhà Thanh",
    "Nhà Nguyễn (Việt Nam)": "Nhà Nguyễn",
    "Nhà Nguyễn (Việt Nam) - Thời Chúa Nguyễn": "Thời Chúa Nguyễn",
    "Đặc biệt - Cung đình": "Cung Đình",
    "Đặc biệt - Chúc tụng": "Chúc Tụng",
    "Đặc biệt - Địa danh": "Địa Danh",
    "Đặc biệt - Cung đình Thanh": "Cung Đình Nhà Thanh",
    "Đặc biệt - Hall mark": "Thất Danh (Hallmark)",
    "Đặc biệt - Nghệ nhân": "Nghệ Nhân",
    "Đặc biệt - Giả/Kết hợp": "Giả / Kết Hợp",
    "Can Chi - Đặc biệt": "Năm Can Chi"
}

with conn.cursor() as cursor:
    for old_val, new_val in updates.items():
        cursor.execute("UPDATE marks SET trieu_dai = %s WHERE trieu_dai = %s", (new_val, old_val))
    
    # Optional: Fix any other inconsistencies in origin/trieu_dai
    
conn.commit()
conn.close()
print("Updated trieu_dai database fields.")
