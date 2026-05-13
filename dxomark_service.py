import sqlite3
from typing import List, Optional

class DxOMarkService:
    def __init__(self, db_path: str = "photo_analysis.db"):
        self.db_path = db_path
    
    def _get_connection(self):
        """Создаёт соединение с базой данных"""
        return sqlite3.connect(self.db_path)

    def normalize_model(self, model: str) -> str:
        """Нормализует название модели для поиска в базе"""
        if not model:
            return ""
        
        # Убираем производителей
        model = model.replace("Apple", "").replace("Samsung", "").replace("Google", "").replace("Xiaomi", "").strip()
        
        # Нормализуем названия iPhone (например, "iPhone15,3" -> "iPhone 15 Pro")
        if "iPhone" in model and "," in model:
            # Это внутренний идентификатор Apple, пробуем сопоставить
            iphone_mapping = {
                "iPhone15,3": "iPhone 15 Pro",
                "iPhone15,2": "iPhone 15 Pro Max",
                "iPhone14,2": "iPhone 14 Pro",
                "iPhone14,3": "iPhone 14 Pro Max",
                "iPhone13,2": "iPhone 13 Pro",
                "iPhone13,3": "iPhone 13 Pro Max",
            }
            if model in iphone_mapping:
                return iphone_mapping[model]
        
        return model

    def get_all_models(self) -> List[str]:
        """Возвращает список всех моделей из базы DxOMark"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT model FROM dxomark ORDER BY model")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            print(f"Ошибка получения списка моделей: {e}")
            return []

    def search_models(self, query: str) -> List[str]:
        """Поиск моделей по строке запроса"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT model FROM dxomark 
                    WHERE LOWER(model) LIKE LOWER(?)
                    ORDER BY model
                    LIMIT 20
                """, (f"%{query}%",))
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return []

    def get_score(self, camera_model: str) -> Optional[int]:
        """Ищет DxOMark оценку по модели камеры"""
        if not camera_model:
            return None
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Точное совпадение
                cursor.execute("""
                    SELECT score FROM dxomark
                    WHERE LOWER(model) = LOWER(?)
                    LIMIT 1
                """, (camera_model,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # 2. Частичное совпадение (модель содержится в названии)
                cursor.execute("""
                    SELECT score FROM dxomark
                    WHERE LOWER(model) LIKE LOWER(?)
                    LIMIT 1
                """, (f"%{camera_model}%",))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # 3. Поиск нормализованной модели
                normalized = self.normalize_model(camera_model)
                if normalized and normalized != camera_model:
                    cursor.execute("""
                        SELECT score FROM dxomark
                        WHERE LOWER(model) LIKE LOWER(?)
                        LIMIT 1
                    """, (f"%{normalized}%",))
                    row = cursor.fetchone()
                    if row:
                        return row[0]
                
                # 4. Если название содержит "iPhone", пробуем найти по части "iPhone X"
                if "iPhone" in camera_model:
                    # Извлекаем номер iPhone (например, "iPhone 15 Pro" -> "iPhone 15")
                    import re
                    match = re.search(r"iPhone\s*(\d+)", camera_model, re.IGNORECASE)
                    if match:
                        iphone_num = f"iPhone {match.group(1)}"
                        cursor.execute("""
                            SELECT score FROM dxomark
                            WHERE LOWER(model) LIKE LOWER(?)
                            LIMIT 1
                        """, (f"%{iphone_num}%",))
                        row = cursor.fetchone()
                        if row:
                            return row[0]
                
                return None
                
        except Exception as e:
            print(f"Ошибка поиска DxOMark оценки: {e}")
            return None

    def get_score_by_model(self, camera_model: str) -> Optional[int]:
        """Алиас для get_score"""
        return self.get_score(camera_model)