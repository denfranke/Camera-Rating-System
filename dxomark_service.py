import sqlite3
import re
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
        
        # Нормализуем названия iPhone
        if "iPhone" in model and "," in model:
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
        """Поиск моделей по строке запроса (улучшенный)"""
        if not query:
            return []
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Точное совпадение
                cursor.execute("""
                    SELECT model FROM dxomark 
                    WHERE LOWER(model) = LOWER(?)
                    ORDER BY model
                    LIMIT 20
                """, (query,))
                rows = cursor.fetchall()
                results = [row[0] for row in rows]
                
                if results:
                    return results
                
                # 2. Частичное совпадение
                cursor.execute("""
                    SELECT model FROM dxomark 
                    WHERE LOWER(model) LIKE LOWER(?)
                    ORDER BY model
                    LIMIT 20
                """, (f"%{query}%",))
                rows = cursor.fetchall()
                results = [row[0] for row in rows]
                
                if results:
                    return results
                
                # 3. Улучшенный поиск с разбивкой на слова
                # Например, "Samsung S23" → ищем "S23" и "Galaxy S23"
                query_lower = query.lower()
                keywords = query_lower.split()
                
                # Расширяем поисковые запросы
                search_variants = []
                
                # Оригинальный запрос
                search_variants.append(query)
                
                # Для Samsung: "S23" → "Galaxy S23", "S23 Ultra"
                if "s23" in query_lower or "s22" in query_lower or "s24" in query_lower or "s25" in query_lower:
                    s_number = re.search(r's(\d+)', query_lower)
                    if s_number:
                        s_num = s_number.group(0).upper()
                        search_variants.append(f"Galaxy {s_num}")
                        search_variants.append(f"Samsung Galaxy {s_num}")
                        if "ultra" in query_lower:
                            search_variants.append(f"Galaxy {s_num} Ultra")
                        elif "plus" in query_lower:
                            search_variants.append(f"Galaxy {s_num}+")
                        else:
                            search_variants.append(f"Galaxy {s_num}")
                
                # Для iPhone: "iPhone 15" → "iPhone 15 Pro", "iPhone 15 Pro Max"
                if "iphone" in query_lower:
                    iphone_num = re.search(r'iphone\s*(\d+)', query_lower)
                    if iphone_num:
                        num = iphone_num.group(1)
                        search_variants.append(f"iPhone {num}")
                        search_variants.append(f"Apple iPhone {num}")
                
                # Для Google Pixel: "Pixel 8" → "Google Pixel 8 Pro"
                if "pixel" in query_lower:
                    pixel_num = re.search(r'pixel\s*(\d+)', query_lower)
                    if pixel_num:
                        num = pixel_num.group(1)
                        search_variants.append(f"Google Pixel {num}")
                        search_variants.append(f"Pixel {num}")
                        if "pro" in query_lower:
                            search_variants.append(f"Google Pixel {num} Pro")
                
                # Для Xiaomi: "Xiaomi 14" → "Xiaomi 14 Ultra"
                if "xiaomi" in query_lower:
                    xiaomi_num = re.search(r'xiaomi\s*(\d+)', query_lower)
                    if xiaomi_num:
                        num = xiaomi_num.group(1)
                        search_variants.append(f"Xiaomi {num}")
                        if "ultra" in query_lower:
                            search_variants.append(f"Xiaomi {num} Ultra")
                        elif "pro" in query_lower:
                            search_variants.append(f"Xiaomi {num} Pro")
                
                # Поиск по всем вариантам
                for variant in search_variants:
                    if variant == query:
                        continue
                    cursor.execute("""
                        SELECT model FROM dxomark 
                        WHERE LOWER(model) LIKE LOWER(?)
                        ORDER BY model
                        LIMIT 20
                    """, (f"%{variant}%",))
                    rows = cursor.fetchall()
                    if rows:
                        return [row[0] for row in rows]
                
                return results
                
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return []

    def get_score(self, camera_model: str) -> Optional[int]:
        """Ищет DxOMark оценку по модели камеры (улучшенный)"""
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
                
                # 2. Частичное совпадение
                cursor.execute("""
                    SELECT score FROM dxomark
                    WHERE LOWER(model) LIKE LOWER(?)
                    LIMIT 1
                """, (f"%{camera_model}%",))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # 3. Улучшенный поиск с ключевыми словами
                query_lower = camera_model.lower()
                
                # Для Samsung: "s23" → ищем "Galaxy S23"
                if "s23" in query_lower or "s22" in query_lower or "s24" in query_lower:
                    s_number = re.search(r's(\d+)', query_lower)
                    if s_number:
                        s_num = s_number.group(0).upper()
                        search_terms = [f"Galaxy {s_num}", f"Samsung Galaxy {s_num}"]
                        for term in search_terms:
                            cursor.execute("""
                                SELECT score FROM dxomark
                                WHERE LOWER(model) LIKE LOWER(?)
                                LIMIT 1
                            """, (f"%{term}%",))
                            row = cursor.fetchone()
                            if row:
                                return row[0]
                
                # 4. Поиск нормализованной модели
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
                
                # 5. Если название содержит "iPhone"
                if "iphone" in query_lower:
                    iphone_num = re.search(r'iphone\s*(\d+)', query_lower)
                    if iphone_num:
                        num = iphone_num.group(1)
                        search_terms = [f"iPhone {num}", f"Apple iPhone {num}"]
                        for term in search_terms:
                            cursor.execute("""
                                SELECT score FROM dxomark
                                WHERE LOWER(model) LIKE LOWER(?)
                                LIMIT 1
                            """, (f"%{term}%",))
                            row = cursor.fetchone()
                            if row:
                                return row[0]
                
                # 6. Если название содержит "Pixel"
                if "pixel" in query_lower:
                    pixel_num = re.search(r'pixel\s*(\d+)', query_lower)
                    if pixel_num:
                        num = pixel_num.group(1)
                        search_terms = [f"Pixel {num}", f"Google Pixel {num}"]
                        for term in search_terms:
                            cursor.execute("""
                                SELECT score FROM dxomark
                                WHERE LOWER(model) LIKE LOWER(?)
                                LIMIT 1
                            """, (f"%{term}%",))
                            row = cursor.fetchone()
                            if row:
                                return row[0]
                
                return None
                
        except Exception as e:
            print(f"Ошибка поиска DxOMark оценки: {e}")
            return None

    def get_score_by_model(self, camera_model: str) -> Optional[int]:
        """Точный поиск DxOMark оценки по точному названию модели"""
        if not camera_model:
            return None
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT score FROM dxomark
                    WHERE model = ?
                    LIMIT 1
                """, (camera_model,))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                # Если точного нет, пробуем частичное
                cursor.execute("""
                    SELECT score FROM dxomark
                    WHERE LOWER(model) LIKE LOWER(?)
                    LIMIT 1
                """, (f"%{camera_model}%",))
                row = cursor.fetchone()
                if row:
                    return row[0]
                
                return None
        except Exception:
            return None
    
    def suggest_models(self, query: str) -> List[str]:
        """Предлагает модели по частичному вводу (автодополнение)"""
        if not query or len(query) < 2:
            return []
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Поиск по началу названия
                cursor.execute("""
                    SELECT model FROM dxomark 
                    WHERE LOWER(model) LIKE LOWER(?)
                    ORDER BY model
                    LIMIT 10
                """, (f"{query}%",))
                rows = cursor.fetchall()
                results = [row[0] for row in rows]
                
                if len(results) < 5:
                    # Поиск по вхождению
                    cursor.execute("""
                        SELECT model FROM dxomark 
                        WHERE LOWER(model) LIKE LOWER(?)
                        ORDER BY model
                        LIMIT 10
                    """, (f"%{query}%",))
                    rows = cursor.fetchall()
                    results.extend([row[0] for row in rows if row[0] not in results])
                
                return results[:10]
                
        except Exception as e:
            print(f"Ошибка предложения моделей: {e}")
            return []