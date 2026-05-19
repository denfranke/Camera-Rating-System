from abc import ABC, abstractmethod
import customtkinter as ctk
from tkinter import filedialog

class BaseReferenceMetric(ABC):
    """Абстрактный базовый класс для всех эталонных метрик"""
    def __init__(self, name: str, key: str):
        self.name = name
        self.key = key
        self.reference_data = None
        self._file_path = None
        self.image_to_analyze = None  
        
        self._value = 0.0              # Универсальное хранилище итогового значения
        self._subscribers = []         # Список подписчиков интерфейса

    @property
    def value(self) -> float:
        """Универсальное свойство для получения текущего значения метрики"""
        return self._value

    @value.setter
    def value(self, new_val: float) -> None:
        """Сеттер: автоматически обновляет GUI при изменении значения"""
        self._value = float(new_val)
        self._notify_subscribers()

    @property
    def file_path(self):
        """Геттер для пути файла"""
        return self._file_path

    def subscribe(self, callback) -> None:
        """Регистрация подписчика из GUI"""
        self._subscribers.append(callback)

    def _notify_subscribers(self) -> None:
        """Оповещение интерфейса об изменениях"""
        for callback in self._subscribers:
            callback(self)

    @abstractmethod
    def process_reference_file(self, file_path: str) -> bool:
        pass

    def get_calculation_value(self) -> float:
        """Возвращает текущую метрику"""
        return self.value

    def load_reference_action(self, main_app) -> None:
        """Метод САМ открывает диалог выбора файла, ни от кого не завися"""
        selected_path = filedialog.askopenfilename(
            title=f"Загрузка отсканированной мишени для: {self.name}",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.tiff *.JPG *.PNG")]
        )
        if not selected_path:
            return
            
        self.image_to_analyze = selected_path
        
        # Запускаем обработку (вызовет analyze_scanned_image в дочернем классе)
        if self.process_reference_file(selected_path):
            self._file_path = selected_path 
            self._notify_subscribers()
        else:
            self._file_path = "error"
            self._notify_subscribers()

    def open_details_modal(self, parent_window: ctk.CTk) -> None:
        """Базовый пустой метод. Переопределяется в дочерних классах, если нужно окно."""
        pass
