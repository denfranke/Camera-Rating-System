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