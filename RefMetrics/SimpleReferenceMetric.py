import random
from .base import BaseReferenceMetric

class SimpleReferenceMetric(BaseReferenceMetric):
    """Класс-демонстрация: эталон загрузить можно, но окна детализации нет."""
    
    def __init__(self, name: str, key: str):
        super().__init__(name, key)
        self.last_calculated_value = 0.0

    def process_reference_file(self, file_path: str) -> bool:
        self.reference_data = {"simple_mode": True}
        # Имитируем расчет другой метрики (например от 10 до 90)
        self.last_calculated_value = round(random.uniform(10.0, 90.0), 2)
        return True

    def get_calculation_value(self) -> float:
        return self.last_calculated_value
