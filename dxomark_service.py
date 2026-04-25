import sqlite3


class DxOMarkService:
    def __init__(self, db_path="photo_analysis.db"):
        self.db_path = db_path

    def normalize(self, model: str):
        if not model:
            return None
        return model.replace("Apple", "").replace("Samsung", "").strip()

    def get_score(self, camera_model: str):
        if not camera_model:
            return None

        camera_model = self.normalize(camera_model)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT score FROM dxomark
                WHERE LOWER(model) LIKE ?
                LIMIT 1
            """, (f"%{camera_model.lower()}%",))

            row = cursor.fetchone()

            if row:
                return row[0]

        return None