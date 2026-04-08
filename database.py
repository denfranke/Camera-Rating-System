"""
database.py - Работа с SQLite базой данных
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any


class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str = "photo_analysis.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
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
                    focal_length REAL,
                    created_at TIMESTAMP,
                    analyzed_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    field_name TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    changed_at TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP
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
    
    def save_analysis(self, data: Dict[str, Any]) -> int:
        """Сохраняет результат анализа"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM analysis_results WHERE file_path = ?", (data['file_path'],))
            existing = cursor.fetchone()
            
            if existing:
                analysis_id = existing[0]
                data['updated_at'] = now
                
                set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
                values = list(data.values()) + [analysis_id]
                cursor.execute(f"UPDATE analysis_results SET {set_clause} WHERE id = ?", values)
            else:
                data['created_at'] = now
                data['analyzed_at'] = now
                data['updated_at'] = now
                
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["?"] * len(data))
                cursor.execute(f"INSERT INTO analysis_results ({columns}) VALUES ({placeholders})", list(data.values()))
                analysis_id = cursor.lastrowid
            
            conn.commit()
            return analysis_id
    
    def get_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Получает анализ по ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_results WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_analyses(self, limit: int = 100, offset: int = 0, sort_by: str = "analyzed_at") -> List[Dict[str, Any]]:
        """Получает список всех анализов"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, filename, file_path, overall_score, user_rating, 
                    sharpness_score, noise_level, camera_model, iso, analyzed_at
                FROM analysis_results 
                ORDER BY {sort_by} DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # Конвертируем bytes в числа где нужно
                for key in ['overall_score', 'sharpness_score', 'noise_level']:
                    if key in row_dict and isinstance(row_dict[key], bytes):
                        try:
                            row_dict[key] = float(row_dict[key].decode('utf-8'))
                        except:
                            row_dict[key] = 0
                results.append(row_dict)
            return results
    
    def update_rating(self, analysis_id: int, rating: int, notes: str = None, tags: str = None):
        """Обновляет пользовательскую оценку"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            updates = {"user_rating": rating, "updated_at": datetime.now().isoformat()}
            if notes:
                updates["user_notes"] = notes
            if tags:
                updates["user_tags"] = tags
            
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            cursor.execute(f"UPDATE analysis_results SET {set_clause} WHERE id = ?", list(updates.values()) + [analysis_id])
            conn.commit()
    
    def delete_analysis(self, analysis_id: int):
        """Удаляет анализ"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_history WHERE analysis_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM photo_categories WHERE photo_id = ?", (analysis_id,))
            cursor.execute("DELETE FROM analysis_results WHERE id = ?", (analysis_id,))
            conn.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM analysis_results")
            stats['total_photos'] = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT 
                    AVG(overall_score),
                    AVG(sharpness_score),
                    AVG(noise_level),
                    AVG(user_rating)
                FROM analysis_results
                WHERE overall_score IS NOT NULL
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
                GROUP BY camera_model 
                ORDER BY count DESC
                LIMIT 5
            """)
            stats['top_cameras'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def add_category(self, name: str, description: str = "") -> Optional[int]:
        """Добавляет категорию"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO categories (name, description, created_at)
                    VALUES (?, ?, ?)
                """, (name, description, datetime.now().isoformat()))
                conn.commit()
                
                cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
                row = cursor.fetchone()
                return row[0] if row else None
            except sqlite3.IntegrityError:
                return None
    
    def add_photo_to_category(self, photo_id: int, category_id: int):
        """Добавляет фото в категорию"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO photo_categories (photo_id, category_id) VALUES (?, ?)", (photo_id, category_id))
            conn.commit()
    
    def search_photos(self, query: str) -> List[Dict[str, Any]]:
        """Поиск фотографий"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, file_path, overall_score, user_rating, user_tags, user_notes, analyzed_at
                FROM analysis_results 
                WHERE filename LIKE ? OR user_tags LIKE ? OR user_notes LIKE ?
                ORDER BY analyzed_at DESC
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
            return [dict(row) for row in cursor.fetchall()]


# Вспомогательный класс для Confirm (чтобы не зависеть от rich)
class Confirm:
    @staticmethod
    def ask(question: str) -> bool:
        answer = input(f"{question} (да/нет): ").strip().lower()
        return answer in ['да', 'yes', 'y', 'д']