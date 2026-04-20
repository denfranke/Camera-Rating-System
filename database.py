import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
import sqlite3

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


import numpy as np

def convert_numpy_types(obj):
    if obj is None:
        return None
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj

class DatabaseInterface(ABC):    
    @abstractmethod
    def save_analysis(self, data: Dict[str, Any]) -> int:
        pass
    
    @abstractmethod
    def get_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_all_analyses(self, limit: int, offset: int, sort_by: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_rating(self, analysis_id: int, rating: int, notes: str = None, tags: str = None):
        pass
    
    @abstractmethod
    def delete_analysis(self, analysis_id: int):
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def search_photos(self, query: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def close(self):
        pass


class SQLiteDatabase(DatabaseInterface):    
    def __init__(self, db_path: str = "photo_analysis.db"):
        self.db_path = db_path
        self._init_database()
    
    def _connect(self):
        return sqlite3.connect(self.db_path)
    
    def _init_database(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    image_width INTEGER,
                    image_height INTEGER,
                    sharpness_score REAL,
                    noise_level REAL,
                    brightness REAL,
                    contrast REAL,
                    saturation REAL,
                    dynamic_range REAL,
                    avg_red REAL,
                    avg_green REAL,
                    avg_blue REAL,
                    exposure_score REAL,
                    composition_score REAL,
                    overall_score REAL,
                    user_rating INTEGER,
                    user_tags TEXT,
                    user_notes TEXT,
                    camera_make TEXT,
                    camera_model TEXT,
                    iso INTEGER,
                    exposure_time TEXT,
                    aperture REAL,
                    focal_length REAL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photo_categories (
                    photo_id INTEGER,
                    category_id INTEGER,
                    PRIMARY KEY (photo_id, category_id)
                )
            """)

            # --- DXOMARK TABLE ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dxomark (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model TEXT NOT NULL,
                    score INTEGER NOT NULL
                )
            """)
            
            # --- ЗАПОЛНЕНИЕ DXOMARK ---
            cursor.execute("SELECT COUNT(*) FROM dxomark")
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.executemany("""
                    INSERT INTO dxomark (model, score) VALUES (?, ?)
                """, [
                    ('Huawei Pura 80 Ultra', 175),
                    ('Vivo X300 Pro', 171),
                    ('Oppo Find X8 Ultra', 168),
                    ('Apple iPhone 17 Pro', 168),
                    ('Vivo X200 Ultra', 167),
                    ('Oppo Find X9 Pro', 166),
                    ('Xiaomi 17 Ultra', 166),
                    ('Honor Magic8 Pro', 164),
                    ('Motorola Razr Fold', 164),
                    ('Motorola Signature', 164),
                    ('Google Pixel 10 Pro XL', 163),
                    ('Huawei Pura 70 Ultra', 163),
                    ('Apple iPhone 16 Pro Max', 161),
                    ('Google Pixel 9 Pro XL', 160),
                    ('Xiaomi 17 Pro Max', 159),
                    ('Xiaomi 15 Ultra', 159),
                    ('Honor Magic6 Pro', 158),
                    ('Apple iPhone 16 Pro', 157),
                    ('Huawei Mate 60 Pro+', 157),
                    ('Oppo Find X8 Pro', 157),
                    ('Oppo Find X7 Ultra', 157),
                    ('Samsung Galaxy S26 Ultra', 157),
                    ('Huawei P60 Pro', 156),
                    ('Apple iPhone 15 Pro Max', 154),
                    ('Apple iPhone 15 Pro', 154),
                    ('Google Pixel 8 Pro', 153),
                    ('Oppo Find X6 Pro', 153),
                    ('Honor Magic5 Pro', 152),
                    ('Samsung Galaxy S25 Ultra', 151),
                    ('Honor Magic V5', 150),
                    ('Oppo Find X6', 150),
                    ('Vivo X100 Pro', 150),
                    ('Huawei Mate 50 Pro', 149),
                    ('Xiaomi 15T Pro', 149),
                    ('Xiaomi 14 Ultra', 149),
                    ('Google Pixel 8', 148),
                    ('Honor Magic7 Pro', 148),
                    ('Apple iPhone 16', 147),
                    ('Google Pixel 7 Pro', 147),
                    ('Xiaomi 15', 147),
                    ('Apple iPhone 14 Pro Max', 146),
                    ('Apple iPhone 14 Pro', 146),
                    ('Motorola Edge 50 Ultra', 146),
                    ('Tecno Camon 50 Ultra 5G', 146),
                    ('Apple iPhone 15', 145),
                    ('Apple iPhone 15 Plus', 145),
                    ('Samsung Galaxy Z Fold7', 145),
                    ('Samsung Galaxy S24 Ultra', 144),
                    ('Google Pixel 9', 143),
                    ('Huawei P50 Pro', 143),
                    ('Apple iPhone Air', 141),
                    ('Apple iPhone 13 Pro Max', 141),
                    ('Apple iPhone 13 Pro', 141),
                    ('Xiaomi Mi 11 Ultra', 141),
                    ('Google Pixel 7', 140),
                    ('Samsung Galaxy S23 Ultra', 140),
                    ('Xiaomi 13 Ultra', 140),
                    ('Huawei Mate 40 Pro+', 139),
                    ('Xiaomi 14', 138),
                    ('Honor 200 Pro', 137),
                    ('Samsung Galaxy Z Flip7', 137),
                    ('Google Pixel 8a', 136),
                    ('Xiaomi 13 Pro', 136),
                    ('Huawei Mate 40 Pro', 135),
                    ('Samsung Galaxy S22 Ultra', 135),
                    ('Google Pixel 10a', 134),
                    ('Google Pixel 6 Pro', 134),
                    ('Apple iPhone 14 Plus', 133),
                    ('Apple iPhone 14', 133),
                    ('Samsung Galaxy S24', 133),
                    ('Samsung Galaxy S23', 133),
                    ('Apple iPhone 12 Pro Max', 131),
                    ('Samsung Galaxy S22 Ultra', 131),
                    ('Xiaomi 13T Pro', 131),
                    ('Honor 200', 130),
                    ('Motorola Edge 40 Pro', 130),
                    ('Samsung Galaxy Z Fold6', 130),
                    ('Xiaomi 13', 130),
                    ('Google Pixel 9 Pro Fold', 129),
                    ('Huawei P40 Pro', 129),
                    ('Samsung Galaxy Z Flip6', 129),
                    ('Xiaomi 12 Pro', 129),
                    ('Google Pixel 9a', 128),
                    ('Oppo Find X3 Pro', 128),
                    ('Samsung Galaxy Z Fold5', 128),
                    ('Apple iPhone 12 Pro', 127),
                    ('OnePlus 11', 127),
                    ('Samsung Galaxy S23 FE', 127),
                    ('Google Pixel 6', 126),
                    ('Honor Magic4 Pro', 126),
                    ('Apple iPhone 13', 125),
                    ('Samsung Galaxy S22+', 125),
                    ('Samsung Galaxy Z Fold4', 124),
                    ('Xiaomi 13T', 123),
                    ('Apple iPhone 11 Pro Max', 122),
                    ('Google Pixel 6a', 122),
                    ('OnePlus 10 Pro', 122),
                    ('Xiaomi Redmi Note 13 Pro Plus 5G', 121),
                    ('Samsung Galaxy S22', 120),
                    ('Samsung Galaxy Z Fold3', 120),
                    ('Honor Magic Vs', 119),
                    ('Sony Xperia 5 IV', 119),
                    ('Samsung Galaxy S25 FE', 118),
                    ('Sony Xperia 5 V', 118),
                    ('Apple iPhone 12', 117),
                    ('Samsung Galaxy S21 Ultra', 117),
                    ('Apple iPhone 11', 116),
                    ('Samsung Galaxy S21+', 115),
                    ('Xiaomi 12T', 115),
                    ('Nothing Phone(1)', 114),
                    ('Samsung Galaxy A56', 114),
                    ('OnePlus 8 Pro', 113),
                    ('Xiaomi Redmi Note 12 Pro+ 5G', 113),
                    ('Samsung Galaxy Z Flip4', 112),
                    ('Samsung Galaxy Z Flip3', 111),
                    ('Google Pixel 5', 109),
                    ('Samsung Galaxy A55 5G', 108),
                    ('Samsung Galaxy A54 5G', 107),
                    ('Oppo Find X3 Neo', 106),
                    ('Sony Xperia 1 III', 105),
                    ('Samsung Galaxy A35 5G', 104),
                    ('Motorola Edge 40 Neo', 103),
                    ('Huawei P40', 102),
                    ('Black Shark 5 Pro', 101),
                    ('Apple iPhone SE (2022)', 100),
                    ('Motorola Moto g75 5G', 96),
                    ('ZTE Axon 30 Ultra', 96),
                    ('Oppo Find X5 Lite', 95),
                    ('Oppo Reno4 5G', 94),
                    ('Oppo A94 5G', 93),
                    ('Vivo X80 Lite 5G', 93),
                    ('Motorola Razr 50', 92),
                    ('Samsung Galaxy A25 5G', 92),
                    ('Samsung Galaxy A34 5G', 92),
                    ('Samsung Galaxy A72', 92),
                    ('Xiaomi Redmi Note 13 5G', 91),
                    ('Oppo Reno6 5G', 89),
                    ('Motorola Moto g85 5G', 88),
                    ('Samsung Galaxy A52s 5G', 88),
                    ('Samsung Galaxy A52 5G', 88),
                    ('Honor 200 Lite', 86),
                    ('Motorola moto g54 5G', 85),
                    ('Samsung Galaxy A16 LTE', 85),
                    ('Samsung Galaxy A33 5G', 85),
                    ('Honor Magic6 Lite', 84),
                    ('OnePlus Nord CE 5G', 84),
                    ('Xiaomi Redmi Note 14', 84),
                    ('Samsung Galaxy A15 5G', 83),
                    ('Vivo Y76 5G', 83),
                    ('Samsung Galaxy A15 LTE', 81),
                    ('Honor 90 Smart', 79),
                    ('Samsung Galaxy A53 5G', 79),
                    ('Sony Xperia 10 V', 78),
                    ('Xiaomi Redmi Note 11 Pro 5G', 78),
                    ('Samsung Galaxy A16 5G', 77),
                    ('TCL 40R 5G', 76),
                    ('Motorola Moto G35 5G', 75),
                    ('Realme 9i 5G', 75),
                    ('Xiaomi Redmi Note 13', 75),
                    ('Honor Magic5 Lite 5G', 74),
                    ('Honor 90 Lite', 73),
                    ('Samsung Galaxy A23 5G', 70),
                    ('Fairphone 4', 69),
                    ('Oppo A78 5G', 69),
                    ('Xiaomi Redmi Note 12 5G', 69),
                    ('Motorola Moto G53 5G', 68),
                    ('Motorola moto g34 5G', 67),
                    ('Samsung Galaxy A14 5G', 67),
                    ('Motorola Moto G62 5G', 66),
                    ('Xiaomi Redmi Note 11S 5G', 65),
                    ('Oppo Reno8 Lite 5G', 64),
                    ('Sony Xperia 10 IV', 63),
                    ('Xiaomi Redmi 14C', 63),
                    ('Xiaomi Redmi 13C', 63),
                    ('Xiaomi Redmi 12 5G', 63),
                    ('Xiaomi Redmi Note 12', 63),
                    ('Honor Magic4 Lite 5G', 61),
                    ('Honor X7', 61),
                    ('Xiaomi Redmi 13C 5G', 60),
                    ('Xiaomi Redmi Note 11', 60),
                    ('Crosscall Stellar-M6', 59),
                    ('Honor 70 Lite', 58),
                    ('Honor 200 Smart', 55),
                    ('Motorola Moto G23', 54),
                    ('Oppo A77 5G', 53),
                    ('Honor X8 5G', 52),
                    ('TCL 406', 52),
                    ('Xiaomi Redmi 10 2022', 51),
                    ('Crosscall Action-X5', 50),
                    ('Samsung Galaxy A22 5G', 48),
                    ('Crosscall Core-Z5', 47),
                    ('Oppo A57', 46),
                    ('Oppo A16s 5G', 46),
                    ('Samsung Galaxy A05s', 45),
                    ('Xiaomi Redmi A3', 45),
                    ('Xiaomi Redmi 12C', 45);
                ])
            
            conn.commit()
            print("SQLite база данных инициализирована")
    
    def save_analysis(self, data: Dict[str, Any]) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM analysis_results WHERE file_path = ?", (data['file_path'],))
            existing = cursor.fetchone()
            
            # Удаляем поля с датами если они есть
            save_data = {k: v for k, v in data.items() }
            
            if existing:
                analysis_id = existing[0]
                set_clause = ", ".join([f"{k} = ?" for k in save_data.keys()])
                values = list(save_data.values()) + [analysis_id]
                cursor.execute(f"UPDATE analysis_results SET {set_clause} WHERE id = ?", values)
            else:
                columns = ", ".join(save_data.keys())
                placeholders = ", ".join(["?"] * len(save_data))
                cursor.execute(f"INSERT INTO analysis_results ({columns}) VALUES ({placeholders})", list(save_data.values()))
                analysis_id = cursor.lastrowid
            
            conn.commit()
            return analysis_id
    
    def get_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_results WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_analyses(self, limit: int = 100, offset: int = 0, sort_by: str = "id") -> List[Dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, filename, file_path, overall_score, user_rating, 
                       sharpness_score, noise_level, camera_model, iso
                FROM analysis_results 
                ORDER BY {sort_by} DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_rating(self, analysis_id: int, rating: int, notes: str = None, tags: str = None):
        with self._connect() as conn:
            cursor = conn.cursor()
            updates = {"user_rating": rating}
            if notes:
                updates["user_notes"] = notes
            if tags:
                updates["user_tags"] = tags
            
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(f"UPDATE analysis_results SET {set_clause} WHERE id = ?", list(updates.values()) + [analysis_id])
            conn.commit()
    
    def delete_analysis(self, analysis_id: int):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM photo_categories WHERE photo_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM analysis_results WHERE id = ?", (analysis_id,))
            conn.commit()

    def get_statistics(self) -> Dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.cursor()
            
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM analysis_results")
            stats['total_photos'] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT AVG(overall_score), AVG(sharpness_score), AVG(noise_level), AVG(user_rating)
                FROM analysis_results WHERE overall_score IS NOT NULL
            """)
            row = cursor.fetchone()
            stats['avg_overall_score'] = round(row[0], 2) if row[0] else 0
            stats['avg_sharpness'] = round(row[1], 2) if row[1] else 0
            stats['avg_noise'] = round(row[2], 2) if row[2] else 0
            stats['avg_user_rating'] = round(row[3], 2) if row[3] else 0
            
            cursor.execute("""
                SELECT camera_model, COUNT(*) as count 
                FROM analysis_results 
                WHERE camera_model IS NOT NULL AND camera_model != ''
                GROUP BY camera_model ORDER BY count DESC LIMIT 5
            """)
            stats['top_cameras'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def add_category(self, name: str, description: str = "") -> Optional[int]:        
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categories (name, description) VALUES (?, ?)", (name, description))
                conn.commit()
                cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
                row = cursor.fetchone()
                return row[0] if row else None
            except sqlite3.IntegrityError:
                return None
    
    def add_photo_to_category(self, photo_id: int, category_id: int):       
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO photo_categories (photo_id, category_id) VALUES (?, ?)", (photo_id, category_id))
            conn.commit()
    
    def search_photos(self, query: str) -> List[Dict[str, Any]]:      
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, file_path, overall_score, user_rating, user_tags, user_notes
                FROM analysis_results 
                WHERE filename LIKE ? OR user_tags LIKE ? OR user_notes LIKE ?
                ORDER BY id DESC
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        pass

class MSSQLDatabase(DatabaseInterface):
    def __init__(self, server: str, database: str, username: str = None, password: str = None, 
                 use_windows_auth: bool = True, port: int = 1433):
        if not PYODBC_AVAILABLE:
            raise ImportError("pyodbc не установлен. Установите: pip install pyodbc")
        
        self.server = server
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.use_windows_auth = use_windows_auth
        self.conn = None
        self._init_database()
    
    def _get_connection_string(self) -> str:
        driver = "{ODBC Driver 17 for SQL Server}"
        
        if self.use_windows_auth:
            conn_str = (f"DRIVER={driver};"
                       f"SERVER={self.server},{self.port};"
                       f"DATABASE={self.database};"
                       f"Trusted_Connection=yes;")
        else:
            conn_str = (f"DRIVER={driver};"
                       f"SERVER={self.server},{self.port};"
                       f"DATABASE={self.database};"
                       f"UID={self.username};"
                       f"PWD={self.password};")
        return conn_str
    
    def _get_connection(self):
        if self.conn is None:
            conn_str = self._get_connection_string()
            self.conn = pyodbc.connect(conn_str)
        return self.conn
    
    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='analysis_results' AND xtype='U')
            CREATE TABLE analysis_results (
                id INT IDENTITY(1,1) PRIMARY KEY,
                file_path NVARCHAR(500) NOT NULL UNIQUE,
                filename NVARCHAR(255) NOT NULL,
                file_size INT,
                image_width INT,
                image_height INT,
                sharpness_score FLOAT,
                noise_level FLOAT,
                brightness FLOAT,
                contrast FLOAT,
                saturation FLOAT,
                dynamic_range FLOAT,
                avg_red FLOAT,
                avg_green FLOAT,
                avg_blue FLOAT,
                exposure_score FLOAT,
                composition_score FLOAT,
                overall_score FLOAT,
                user_rating INT,
                user_tags NVARCHAR(500),
                user_notes NVARCHAR(MAX),
                camera_make NVARCHAR(255),
                camera_model NVARCHAR(255),
                iso INT,
                exposure_time NVARCHAR(50),
                aperture FLOAT,
                focal_length FLOAT
            )
        """)
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='categories' AND xtype='U')
            CREATE TABLE categories (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(255) UNIQUE NOT NULL,
                description NVARCHAR(MAX)
            )
        """)
        
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='photo_categories' AND xtype='U')
            CREATE TABLE photo_categories (
                photo_id INT,
                category_id INT,
                PRIMARY KEY (photo_id, category_id),
                FOREIGN KEY (photo_id) REFERENCES analysis_results(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        
        conn.commit()
        print("База данных MS SQL Server инициализирована")
    
    def save_analysis(self, data: Dict[str, Any]) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Конвертируем numpy типы
        data = convert_numpy_types(data)
        
        # Удаляем поля с датами
        cleaned_data = {k: v for k, v in data.items() }
        
        # Очищаем данные
        for key, value in list(cleaned_data.items()):
            if value is None:
                continue
            elif isinstance(value, float):
                if np.isnan(value) or np.isinf(value):
                    cleaned_data[key] = None
            elif isinstance(value, (int, np.int32, np.int64)):
                cleaned_data[key] = int(value)
        
        cursor.execute("SELECT id FROM analysis_results WHERE file_path = ?", (cleaned_data['file_path'],))
        existing = cursor.fetchone()
        
        if existing:
            analysis_id = existing[0]
            
            if 'id' in cleaned_data:
                del cleaned_data['id']
            
            if cleaned_data:
                set_clause = ", ".join([f"{k} = ?" for k in cleaned_data.keys()])
                values = list(cleaned_data.values()) + [analysis_id]
                cursor.execute(f"UPDATE analysis_results SET {set_clause} WHERE id = ?", values)
        else:
            columns = ", ".join(cleaned_data.keys())
            placeholders = ", ".join(["?"] * len(cleaned_data))
            cursor.execute(f"INSERT INTO analysis_results ({columns}) VALUES ({placeholders})", list(cleaned_data.values()))
            
            cursor.execute("SELECT SCOPE_IDENTITY()")
            row = cursor.fetchone()
            analysis_id = int(row[0]) if row and row[0] is not None else 0
        
        conn.commit()
        return analysis_id
    
    def get_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM analysis_results WHERE id = ?", (analysis_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_all_analyses(self, limit: int = 100, offset: int = 0, sort_by: str = "id") -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, filename, file_path, overall_score, user_rating, 
                   sharpness_score, noise_level, camera_model, iso
            FROM analysis_results 
            ORDER BY {sort_by} DESC 
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, limit))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def update_rating(self, analysis_id: int, rating: int, notes: str = None, tags: str = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = {"user_rating": rating}
        if notes:
            updates["user_notes"] = notes
        if tags:
            updates["user_tags"] = tags
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        cursor.execute(f"UPDATE analysis_results SET {set_clause} WHERE id = ?", list(updates.values()) + [analysis_id])
        conn.commit()
    
    def delete_analysis(self, analysis_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM photo_categories WHERE photo_id = ?", (analysis_id,))
        cursor.execute("DELETE FROM analysis_results WHERE id = ?", (analysis_id,))
        conn.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM analysis_results")
        stats['total_photos'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT AVG(overall_score), AVG(sharpness_score), AVG(noise_level), AVG(user_rating)
            FROM analysis_results WHERE overall_score IS NOT NULL
        """)
        row = cursor.fetchone()
        stats['avg_overall_score'] = round(row[0], 2) if row[0] else 0
        stats['avg_sharpness'] = round(row[1], 2) if row[1] else 0
        stats['avg_noise'] = round(row[2], 2) if row[2] else 0
        stats['avg_user_rating'] = round(row[3], 2) if row[3] else 0
        
        cursor.execute("""
            SELECT camera_model, COUNT(*) as count 
            FROM analysis_results 
            WHERE camera_model IS NOT NULL AND camera_model != ''
            GROUP BY camera_model ORDER BY count DESC
            OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY
        """)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        stats['top_cameras'] = [dict(zip(columns, row)) for row in rows]
        
        return stats
    
    def add_category(self, name: str, description: str = "") -> Optional[int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM categories WHERE name = ?)
                INSERT INTO categories (name, description) VALUES (?, ?)
            """, (name, name, description))
            conn.commit()
            
            cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None
    
    def add_photo_to_category(self, photo_id: int, category_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM photo_categories WHERE photo_id = ? AND category_id = ?)
            INSERT INTO photo_categories (photo_id, category_id) VALUES (?, ?)
        """, (photo_id, category_id, photo_id, category_id))
        conn.commit()
    
    def search_photos(self, query: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, filename, file_path, overall_score, user_rating, user_tags, user_notes
            FROM analysis_results 
            WHERE filename LIKE ? OR user_tags LIKE ? OR user_notes LIKE ?
            ORDER BY id DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def close(self):
        if self.conn:
            self.conn.close()
            print("Соединение с MS SQL Server закрыто")

class Database:   
    def __init__(self, db_type: str = "sqlite", **kwargs):
        """        
        Args:
            db_type: "sqlite" или "mssql"
            Для SQLite: db_path
            Для MS SQL Server: server, database, username, password, use_windows_auth, port
        """
        self.db_type = db_type
        
        if db_type == "sqlite":
            db_path = kwargs.get('db_path', "photo_analysis.db")
            self._db = SQLiteDatabase(db_path)
            print(f"Подключена локальная SQLite БД: {db_path}")
        elif db_type == "mssql":
            if not PYODBC_AVAILABLE:
                raise ImportError("pyodbc не установлен. Установите: pip install pyodbc")
            
            server = kwargs.get('server', 'localhost')
            database = kwargs.get('database', 'photo_analyzer')
            username = kwargs.get('username')
            password = kwargs.get('password')
            use_windows_auth = kwargs.get('use_windows_auth', username is None and password is None)
            port = kwargs.get('port', 1433)
            
            self._db = MSSQLDatabase(server, database, username, password, use_windows_auth, port)
            auth_type = "Windows аутентификация" if use_windows_auth else f"аутентификация SQL Server ({username})"
            print(f"Подключена удалённая MS SQL Server БД: {server}:{port}/{database} ({auth_type})")
        else:
            raise ValueError(f"Неизвестный тип БД: {db_type}")
    
    def __getattr__(self, name):
        return getattr(self._db, name)
    
    def close(self):
        self._db.close()
