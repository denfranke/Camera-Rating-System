"""
Photo Quality Analyzer - GUI приложение
Анализ качества фотографий с определением камеры и DxOMark оценкой
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import os
import sys
import io
import numpy as np
from datetime import datetime

from RefMetrics import ColorDeltaEMetric
from RefMetrics import BaseReferenceMetric
from RefMetrics import SimpleReferenceMetric

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analyzer import ImageAnalyzer
from database import Database
from dxomark_service import DxOMarkService


# Настройка темы customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PhotoQualityAnalyzerApp:
    """Главное окно приложения"""
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Camera Quality Analyzer - Анализ качества фотографий")
        self.root.geometry("1400x850")
        self.root.minsize(1200, 750)
        
        # Инициализация сервисов
        self.analyzer = ImageAnalyzer()
        self.db = None
        self.dxo_service = DxOMarkService("photo_analysis.db")
        self.current_db_type = "sqlite"
        
        # Переменные состояния
        self.current_image_paths = []  # Список путей к загруженным файлам
        self.current_images = []  # Список загруженных изображений
        self.current_photo_images = []  # Список PhotoImage объектов
        self.analysis_results = []
        self.is_analyzing = False
        self.selected_camera_model = None
        self.selected_dxomark_score = None
        
        # Инициализация БД
        self.init_database()
        
        # Создание интерфейса
        self.create_widgets()
        
        # Загрузка последних анализов
        self.load_recent_analyses()
        self.load_cameras_analysis()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            import json
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding='utf-8') as f:
                    config = json.load(f)
                    db_config = config.get('database', {})
                    db_type = db_config.get('type', 'sqlite')
                    self.current_db_type = db_type
                    
                    if db_type == "mssql":
                        mssql_config = db_config.get('mssql', {})
                        self.db = Database(
                            db_type='mssql',
                            server=mssql_config.get('server', 'localhost'),
                            port=mssql_config.get('port', 1433),
                            database=mssql_config.get('database', 'photo_analyzer'),
                            username=mssql_config.get('username'),
                            password=mssql_config.get('password'),
                            use_windows_auth=mssql_config.get('use_windows_auth', True)
                        )
                    else:
                        self.db = Database(db_type="sqlite", db_path="photo_analysis.db")
            else:
                self.db = Database(db_type="sqlite", db_path="photo_analysis.db")
                self.current_db_type = "sqlite"
                
            print(f"База данных подключена: {self.current_db_type}")
        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            print("Переключаемся на SQLite...")
            try:
                self.db = Database(db_type="sqlite", db_path="photo_analysis.db")
                self.current_db_type = "sqlite"
            except Exception as e2:
                print(f"Критическая ошибка: {e2}")
                self.db = None
    
    def create_widgets(self):
        """Создание всех виджетов"""
        
        # Основной контейнер
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ========== ВЕРХНЯЯ ПАНЕЛЬ ==========
        self.top_frame = ctk.CTkFrame(self.main_frame)
        self.top_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Заголовок
        self.title_label = ctk.CTkLabel(
            self.top_frame, 
            text="CAMERA QUALITY ANALYZER", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(side="left", padx=10)
        
        # Статус БД
        db_status = f"БД: {self.current_db_type.upper()}"
        self.db_status_label = ctk.CTkLabel(
            self.top_frame,
            text=db_status,
            font=ctk.CTkFont(size=12)
        )
        self.db_status_label.pack(side="right", padx=10)
        
        # Кнопка настроек БД
        self.db_btn = ctk.CTkButton(
            self.top_frame, 
            text="Настройки БД", 
            width=120,
            command=self.open_db_settings
        )
        self.db_btn.pack(side="right", padx=5)
        
        # ========== ОСНОВНОЙ КОНТЕНТ ==========
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Левая панель - загрузка и предпросмотр
        self.left_panel = ctk.CTkFrame(self.content_frame, width=400)
        self.left_panel.pack(side="left", fill="both", expand=False, padx=(0, 5))
        self.left_panel.pack_propagate(False)
        
        # Правая панель - результаты
        self.right_panel = ctk.CTkFrame(self.content_frame, width=900)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self.right_panel.pack_propagate(False)
        
        # ========== ЛЕВАЯ ПАНЕЛЬ ==========
        self.create_left_panel()
        
        # ========== ПРАВАЯ ПАНЕЛЬ ==========
        self.create_right_panel()
        
        # ========== НИЖНЯЯ ПАНЕЛЬ (Статус) ==========
        self.bottom_frame = ctk.CTkFrame(self.main_frame)
        self.bottom_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.status_label = ctk.CTkLabel(
            self.bottom_frame, 
            text="Готов к работе. Загрузите фотографию для анализа.",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10)
        
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, width=300)
        self.progress_bar.pack(side="right", padx=10)
        self.progress_bar.set(0)
    
    def create_left_panel(self):
        """Создание левой панели с загрузкой и предпросмотром"""
        
        # Заголовок
        ctk.CTkLabel(
            self.left_panel, 
            text="ЗАГРУЗКА ФОТОГРАФИЙ",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))
        
        # Кнопки загрузки
        self.btn_frame = ctk.CTkFrame(self.left_panel)
        self.btn_frame.pack(pady=10)
        
        self.load_btn = ctk.CTkButton(
            self.btn_frame,
            text="ДОБАВИТЬ",
            command=self.load_images,
            width=80,
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self.load_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(
            self.btn_frame,
            text="ОЧИСТИТЬ",
            command=self.clear_images,
            width=100,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#e74c3c",
            hover_color="#c0392b"
        )
        self.clear_btn.pack(side="left", padx=5)
        
        self.analyze_btn = ctk.CTkButton(
            self.btn_frame,
            text="АНАЛИЗ",
            command=self.start_analysis,
            width=80,
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#009900",
            hover_color="#009900"
        )
        self.analyze_btn.pack(side="left", padx=5)
        self.analyze_btn.configure(state="disabled")
        
        # Список загруженных файлов
        self.files_frame = ctk.CTkFrame(self.left_panel)
        self.files_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            self.files_frame,
            text="ЗАГРУЖЕННЫЕ ФАЙЛЫ",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 0))
        
        # Таблица с файлами
        self.files_tree = ttk.Treeview(
            self.files_frame,
            columns=("file"),
            show="headings",
            height=8
        )
        
        self.files_tree.heading("file", text="Файл")
        self.files_tree.column("file", width=350)
        
        scrollbar = ttk.Scrollbar(self.files_frame, orient="vertical", command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=scrollbar.set)
        
        self.files_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", padx=5, pady=5)
        
        # Предпросмотр выбранного изображения
        self.preview_frame = ctk.CTkFrame(self.left_panel)
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            self.preview_frame,
            text="ПРЕДПРОСМОТР",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(5, 0))
        
        self.preview_label = ctk.CTkLabel(
            self.preview_frame, 
            text="Выберите файл для предпросмотра",
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.preview_label.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Привязываем событие выбора файла
        self.files_tree.bind("<<TreeviewSelect>>", self.on_file_select)
    
    def create_right_panel(self):
        """Создание правой панели с результатами"""
        
        # ========== ВКЛАДКИ ==========
        self.tabview = ctk.CTkTabview(self.right_panel)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Вкладка результатов
        self.tab_results = self.tabview.add("Результаты анализа")
        
        # Вкладка метрик
        self.tab_metrics = self.tabview.add("Детальные метрики")
        
        # Вкладка камеры
        self.tab_camera = self.tabview.add("Информация о камере")
        
        # Вкладка истории
        self.tab_history = self.tabview.add("История анализов")
        
        # ========== ВКЛАДКА РЕЗУЛЬТАТОВ ==========
        self.create_results_tab()
        
        # ========== ВКЛАДКА МЕТРИК ==========
        self.create_metrics_tab()
        
        # ========== ВКЛАДКА КАМЕРЫ ==========
        self.create_camera_tab()
        
        # ========== ВКЛАДКА ИСТОРИИ ==========
        self.create_history_tab()
    
    def create_results_tab(self):
        """Создание вкладки с основными результатами"""
        
        # Общая оценка
        self.score_frame = ctk.CTkFrame(self.tab_results)
        self.score_frame.pack(pady=20)
        
        self.score_label = ctk.CTkLabel(
            self.score_frame,
            text="ОБЩАЯ ОЦЕНКА",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.score_label.pack()
        
        self.score_value = ctk.CTkLabel(
            self.score_frame,
            text="---",
            font=ctk.CTkFont(size=48, weight="bold")
        )
        self.score_value.pack()
        
        self.score_rating = ctk.CTkLabel(
            self.score_frame,
            text="",
            font=ctk.CTkFont(size=16)
        )
        self.score_rating.pack()
        
        # Круговая диаграмма
        self.gauge_frame = ctk.CTkFrame(self.tab_results)
        self.gauge_frame.pack(pady=10)
        
        self.gauge_canvas = tk.Canvas(
            self.gauge_frame, 
            width=200, 
            height=200, 
            bg='#2b2b2b', 
            highlightthickness=0
        )
        self.gauge_canvas.pack()
        
        # Рекомендации
        self.recommendations_frame = ctk.CTkFrame(self.tab_results)
        self.recommendations_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            self.recommendations_frame,
            text="РЕКОМЕНДАЦИИ",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(10, 5))
        
        self.recommendations_text = ctk.CTkTextbox(self.recommendations_frame, height=150)
        self.recommendations_text.pack(fill="both", expand=True, padx=10, pady=5)
    
    def create_metrics_tab(self):
        """Создание вкладки с детальными метриками"""
        
        # Сетка метрик
        metrics = [
            ("Резкость", "sharpness", 0, 100, False),
            ("Уровень шума", "noise", 0, 100, True),
            ("Динамический диапазон", "dynamic_range", 0, 16, False),
            ("Яркость", "brightness", 0, 100, False),
            ("Контраст", "contrast", 0, 100, False),
            ("Насыщенность", "saturation", 0, 100, False),
            ("Экспозиция", "exposure", 0, 100, False),
        ]
        
		# метрики с эталоном 
        reference_metrics = [
            ("Цветопередача (ΔE2000)", "DeltaE", 0, 100, False, ColorDeltaEMetric),
        ]
        
        self.metric_bars = {}
        
        metrics_title = ctk.CTkLabel(self.tab_metrics, text="📊 Метрики без эталона", font=("Arial", 14, "bold"))
        metrics_title.pack(anchor="w", padx=10, pady=5)
        
        for name, key, min_val, max_val, invert in metrics:
            frame = ctk.CTkFrame(self.tab_metrics)
            frame.pack(fill="x", padx=10, pady=5)
            
            label = ctk.CTkLabel(frame, text=name, width=160, anchor="w")
            label.pack(side="left", padx=10)
            
            value_label = ctk.CTkLabel(frame, text="---", width=120)
            value_label.pack(side="left")
            
            bar = ctk.CTkProgressBar(frame, width=240)
            bar.pack(side="left", padx=10)
            bar.set(0)
            
            self.metric_bars[key] = {
                "label": value_label,
                "bar": bar,
                "min": min_val,
                "max": max_val,
                "invert": invert
            }
            
        reference_metrics_title = ctk.CTkLabel(self.tab_metrics, text="🎯 метрики с эталоном", font=("Arial", 14, "bold"))
        reference_metrics_title.pack(anchor="w", padx=10, pady=5)
        
        self.metric_instances = {}
        
        for name, key, min_val, max_val, invert, metric_class in reference_metrics:
            if not metric_class:
                continue
                
            # Автоматически создаем единственный ЭКЗЕМПЛЯР класса прямо здесь
            if key not in self.metric_instances:
                self.metric_instances[key] = metric_class(name, key)
            
            instance = self.metric_instances[key]

            frame = ctk.CTkFrame(self.tab_metrics)
            frame.pack(fill="x", padx=10, pady=5)
            
            label = ctk.CTkLabel(frame, text=name, width=160, anchor="w")
            label.pack(side="left", padx=10)
            
            # Меняем текст в зависимости от того, загружен ли уже файл
            status_text = "Загрузите эталон" if not instance.file_path else "Эталон готов"
            value_label = ctk.CTkLabel(frame, text=status_text, width=120)
            value_label.pack(side="left")
            
            bar = ctk.CTkProgressBar(frame, width=240)
            bar.pack(side="left", padx=10)
            bar.set(0)
            
            def make_updater(lbl, progress_bar, mn_v=min_val, mx_v=max_val):
                def update_ui(updated_instance):
                    if updated_instance.file_path == "error":
                        lbl.configure(text="❌ Ошибка файла", text_color="red")
                        progress_bar.set(0)
                        return
                        
                    # Берем универсальное значение, которое гарантированно обновлено
                    metric_value = updated_instance.get_calculation_value()
                    lbl.configure(text=f"{metric_value:.2f}", text_color="white")
                    
                    denom = (mx_v - mn_v) if (mx_v - mn_v) != 0 else 100
                    normalized_value = (metric_value - mn_v) / denom
                    progress_bar.set(max(0.0, min(normalized_value, 1.0)))
                return update_ui


            # Подписываем созданную функцию на изменения экземпляра
            instance.subscribe(make_updater(value_label, bar))
            
            # ИСПРАВЛЕНИЕ 1: Если эталон уже загружен, сразу отображаем его значение в GUI
            if instance.file_path and instance.file_path != "error":
                instance._notify_subscribers()
            
            # ИСПРАВЛЕНИЕ 2: Кнопка загрузки эталона теперь передает только self
            ctk.CTkButton(
                frame, 
                text="📥 Эталон", 
                width=90,
                command=lambda inst=instance: inst.load_reference_action(self)
            ).pack(side="left", padx=5)

            # Кнопка ДЕТАЛИЗАЦИИ: появляется ТОЛЬКО если метод переопределен в дочернем классе
            if hasattr(instance, "open_details_modal") and type(instance).open_details_modal != BaseReferenceMetric.open_details_modal:
                
                parent_window = getattr(self, "root", getattr(self, "window", self))
                
                ctk.CTkButton(
                    frame, 
                    text="🔍 Детали", 
                    width=90,
                    command=lambda inst=instance, pw=parent_window: inst.open_details_modal(pw)
                ).pack(side="left", padx=5)

                
    def create_camera_tab(self):
        """Создание вкладки с информацией о камере"""
        
        self.camera_info_frame = ctk.CTkFrame(self.tab_camera)
        self.camera_info_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.camera_info_text = ctk.CTkTextbox(self.camera_info_frame, font=ctk.CTkFont(size=13))
        self.camera_info_text.pack(fill="both", expand=True)
        
        # Панель для выбора камеры
        self.camera_select_frame = ctk.CTkFrame(self.tab_camera)
        self.camera_select_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(self.camera_select_frame, text="Модель камеры:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=10)
        
        self.camera_entry = ctk.CTkEntry(self.camera_select_frame, width=300, placeholder_text="Выберите или введите модель камеры")
        self.camera_entry.pack(side="left", padx=10)
        
        self.select_camera_btn = ctk.CTkButton(
            self.camera_select_frame,
            text="Выбрать из списка",
            command=self.select_camera_from_list,
            width=150
        )
        self.select_camera_btn.pack(side="left", padx=5)
        
        self.apply_camera_btn = ctk.CTkButton(
            self.camera_select_frame,
            text="Применить",
            command=self.apply_camera_to_analysis,
            width=100,
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        self.apply_camera_btn.pack(side="left", padx=5)
        
        # Информация о выбранной камере
        self.selected_camera_info = ctk.CTkLabel(self.camera_select_frame, text="", text_color="#3498db")
        self.selected_camera_info.pack(side="left", padx=10)
    
    def create_history_tab(self):
        """Создание вкладки с расширенной историей анализов"""
        
        # Создаём вкладки внутри истории
        self.history_tabview = ctk.CTkTabview(self.tab_history)
        self.history_tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Вкладка "Все фото"
        self.history_all_tab = self.history_tabview.add("📸 Все фото")
        
        # Вкладка "Анализ по камерам"
        self.history_cameras_tab = self.history_tabview.add("📊 Анализ по камерам")
        
        # Создаём содержимое вкладок
        self.create_all_photos_tab()
        self.create_cameras_analysis_tab()
    
    def create_all_photos_tab(self):
        """Создание вкладки со всеми фото"""
        
        # Таблица с историей
        columns = (
            "id", "filename", "overall", "sharpness", "noise", 
            "dynamic_range", "brightness", "contrast", "saturation", 
            "exposure", "camera", "dxo"
        )
        
        self.history_tree = ttk.Treeview(
            self.history_all_tab,
            columns=columns,
            show="headings",
            height=18
        )
        
        # Заголовки
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("filename", text="Файл")
        self.history_tree.heading("overall", text="Оценка")
        self.history_tree.heading("sharpness", text="Резкость")
        self.history_tree.heading("noise", text="Шум")
        self.history_tree.heading("dynamic_range", text="Дин.диап.")
        self.history_tree.heading("brightness", text="Яркость")
        self.history_tree.heading("contrast", text="Контраст")
        self.history_tree.heading("saturation", text="Насыщ.")
        self.history_tree.heading("exposure", text="Экспоз.")
        self.history_tree.heading("camera", text="Камера")
        self.history_tree.heading("dxo", text="DxO")
        
        # Ширина колонок
        self.history_tree.column("id", width=40)
        self.history_tree.column("filename", width=180)
        self.history_tree.column("overall", width=60)
        self.history_tree.column("sharpness", width=60)
        self.history_tree.column("noise", width=60)
        self.history_tree.column("dynamic_range", width=70)
        self.history_tree.column("brightness", width=60)
        self.history_tree.column("contrast", width=60)
        self.history_tree.column("saturation", width=60)
        self.history_tree.column("exposure", width=60)
        self.history_tree.column("camera", width=180)
        self.history_tree.column("dxo", width=50)
        
        # Скроллбары
        scrollbar_y = ttk.Scrollbar(self.history_all_tab, orient="vertical", command=self.history_tree.yview)
        scrollbar_x = ttk.Scrollbar(self.history_all_tab, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar_y.pack(side="right", fill="y", padx=5, pady=5)
        scrollbar_x.pack(side="bottom", fill="x", padx=5, pady=5)
        
        # Кнопки
        btn_frame = ctk.CTkFrame(self.history_all_tab)
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Обновить",
            command=self.load_recent_analyses,
            width=80
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Удалить",
            command=self.delete_selected_photo,
            width=80,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)
    
    def create_cameras_analysis_tab(self):
        """Создание вкладки с агрегированным анализом по камерам"""
        
        # Таблица с агрегированными данными по камерам
        columns = (
            "camera", "count", "avg_overall", "avg_sharpness", "avg_noise",
            "avg_dynamic_range", "avg_brightness", "avg_contrast", 
            "avg_saturation", "avg_exposure", "dxo_score"
        )
        
        self.cameras_tree = ttk.Treeview(
            self.history_cameras_tab,
            columns=columns,
            show="headings",
            height=18
        )
        
        # Заголовки
        self.cameras_tree.heading("camera", text="Модель камеры")
        self.cameras_tree.heading("count", text="Кол-во фото")
        self.cameras_tree.heading("avg_overall", text="Ср. оценка")
        self.cameras_tree.heading("avg_sharpness", text="Ср. резкость")
        self.cameras_tree.heading("avg_noise", text="Ср. шум")
        self.cameras_tree.heading("avg_dynamic_range", text="Ср. ДР")
        self.cameras_tree.heading("avg_brightness", text="Ср. яркость")
        self.cameras_tree.heading("avg_contrast", text="Ср. контраст")
        self.cameras_tree.heading("avg_saturation", text="Ср. насыщ.")
        self.cameras_tree.heading("avg_exposure", text="Ср. экспоз.")
        self.cameras_tree.heading("dxo_score", text="DxOMark")
        
        # Ширина колонок
        self.cameras_tree.column("camera", width=250)
        self.cameras_tree.column("count", width=80)
        self.cameras_tree.column("avg_overall", width=80)
        self.cameras_tree.column("avg_sharpness", width=80)
        self.cameras_tree.column("avg_noise", width=80)
        self.cameras_tree.column("avg_dynamic_range", width=80)
        self.cameras_tree.column("avg_brightness", width=80)
        self.cameras_tree.column("avg_contrast", width=80)
        self.cameras_tree.column("avg_saturation", width=80)
        self.cameras_tree.column("avg_exposure", width=80)
        self.cameras_tree.column("dxo_score", width=80)
        
        # Скроллбары
        scrollbar_y = ttk.Scrollbar(self.history_cameras_tab, orient="vertical", command=self.cameras_tree.yview)
        scrollbar_x = ttk.Scrollbar(self.history_cameras_tab, orient="horizontal", command=self.cameras_tree.xview)
        self.cameras_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.cameras_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar_y.pack(side="right", fill="y", padx=5, pady=5)
        scrollbar_x.pack(side="bottom", fill="x", padx=5, pady=5)
        
        # Кнопки
        btn_frame = ctk.CTkFrame(self.history_cameras_tab)
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Обновить",
            command=self.load_cameras_analysis,
            width=80,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)
        
        # ctk.CTkButton(
        #     btn_frame,
        #     text="Показать сравнение",
        #     command=self.show_cameras_comparison,
        #     width=200,
        #     fg_color="#2ecc71",
        #     hover_color="#27ae60"
        # ).pack(side="left", padx=5)
    
    def load_cameras_analysis(self):
        """Загрузка агрегированного анализа по камерам"""
        if not hasattr(self, 'cameras_tree') or not self.cameras_tree:
            return
        
        for item in self.cameras_tree.get_children():
            self.cameras_tree.delete(item)
        
        if not self.db:
            return
        
        try:
            analyses = self.db.get_all_analyses(limit=1000)
            
            # Группируем по камерам
            cameras_data = {}
            
            for analysis in analyses:
                camera = analysis.get('camera_model')
                if not camera or camera == 'Unknown':
                    camera = "Неизвестная камера"
                
                if camera not in cameras_data:
                    cameras_data[camera] = {
                        'count': 0,
                        'overall_sum': 0,
                        'sharpness_sum': 0,
                        'noise_sum': 0,
                        'dynamic_range_sum': 0,
                        'brightness_sum': 0,
                        'contrast_sum': 0,
                        'saturation_sum': 0,
                        'exposure_sum': 0,
                        'dxo_score': analysis.get('dxomark_score')
                    }
                
                data = cameras_data[camera]
                data['count'] += 1
                
                # Функция безопасного сложения
                def safe_add(val, sum_val):
                    if val is not None and val != 'N/A':
                        try:
                            return sum_val + float(val)
                        except (ValueError, TypeError):
                            return sum_val
                    return sum_val
                
                data['overall_sum'] = safe_add(analysis.get('overall_score'), data['overall_sum'])
                data['sharpness_sum'] = safe_add(analysis.get('sharpness_score'), data['sharpness_sum'])
                data['noise_sum'] = safe_add(analysis.get('noise_level'), data['noise_sum'])
                data['dynamic_range_sum'] = safe_add(analysis.get('dynamic_range'), data['dynamic_range_sum'])
                
                # Процентные метрики
                brightness = analysis.get('brightness')
                if brightness and brightness != 'N/A':
                    try:
                        data['brightness_sum'] += float(brightness) * 100
                    except (ValueError, TypeError):
                        pass
                
                contrast = analysis.get('contrast')
                if contrast and contrast != 'N/A':
                    try:
                        data['contrast_sum'] += float(contrast) * 100
                    except (ValueError, TypeError):
                        pass
                
                saturation = analysis.get('saturation')
                if saturation and saturation != 'N/A':
                    try:
                        data['saturation_sum'] += float(saturation) * 100
                    except (ValueError, TypeError):
                        pass
                
                exposure = analysis.get('exposure_score')
                if exposure and exposure != 'N/A':
                    try:
                        data['exposure_sum'] += float(exposure) * 100
                    except (ValueError, TypeError):
                        pass
                
                # DxOMark
                dxo = analysis.get('dxomark_score')
                if dxo and dxo != 'N/A' and dxo is not None:
                    try:
                        data['dxo_score'] = dxo
                    except:
                        pass
            
            # Заполняем таблицу
            for camera, data in sorted(cameras_data.items(), key=lambda x: x[1]['count'], reverse=True):
                count = data['count']
                
                avg_overall = data['overall_sum'] / count if data['overall_sum'] > 0 else 0
                avg_sharpness = data['sharpness_sum'] / count if data['sharpness_sum'] > 0 else 0
                avg_noise = data['noise_sum'] / count if data['noise_sum'] > 0 else 0
                avg_dr = data['dynamic_range_sum'] / count if data['dynamic_range_sum'] > 0 else 0
                avg_brightness = data['brightness_sum'] / count if data['brightness_sum'] > 0 else 0
                avg_contrast = data['contrast_sum'] / count if data['contrast_sum'] > 0 else 0
                avg_saturation = data['saturation_sum'] / count if data['saturation_sum'] > 0 else 0
                avg_exposure = data['exposure_sum'] / count if data['exposure_sum'] > 0 else 0
                
                dxo = data['dxo_score'] if data['dxo_score'] else '-'
                
                # Цветовая индикация
                if avg_overall >= 80:
                    color_icon = "🟢"
                elif avg_overall >= 60:
                    color_icon = "🔵"
                elif avg_overall >= 40:
                    color_icon = "🟡"
                else:
                    color_icon = "🔴"
                
                self.cameras_tree.insert("", "end", values=(
                    f"{color_icon} {camera}",
                    count,
                    f"{avg_overall:.1f}%",
                    f"{avg_sharpness:.1f}",
                    f"{avg_noise:.1f}",
                    f"{avg_dr:.1f} EV",
                    f"{avg_brightness:.1f}%",
                    f"{avg_contrast:.1f}%",
                    f"{avg_saturation:.1f}%",
                    f"{avg_exposure:.1f}%",
                    dxo
                ))
            
            # Добавляем итоговую строку
            if len(cameras_data) > 1:
                total_count = sum(d['count'] for d in cameras_data.values())
                total_overall = sum(d['overall_sum'] for d in cameras_data.values()) / total_count if total_count > 0 else 0
                
                self.cameras_tree.insert("", "end", values=(
                    "ИТОГО ПО ВСЕМ КАМЕРАМ",
                    total_count,
                    f"{total_overall:.1f}%",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    ""
                ))
            
        except Exception as e:
            print(f"Ошибка загрузки анализа камер: {e}")
    
    def show_cameras_comparison(self):
        """Показывает окно сравнения камер"""
        if not hasattr(self, 'cameras_tree') or not self.cameras_tree:
            return
        
        # Собираем данные из таблицы
        cameras_data = []
        for item in self.cameras_tree.get_children():
            values = self.cameras_tree.item(item)['values']
            if not values[0].startswith("📊"):
                cameras_data.append({
                    'name': values[0].replace(" ", "").replace(" ", "").replace(" ", "").replace(" ", ""),
                    'count': values[1],
                    'overall': values[2].replace('%', ''),
                    'sharpness': values[3],
                    'noise': values[4],
                    'dr': values[5].replace(' EV', ''),
                    'dxo': values[10]
                })
        
        if not cameras_data:
            messagebox.showinfo("Информация", "Нет данных для сравнения")
            return
        
        # Создаём окно сравнения
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Сравнение камер")
        dialog.geometry("1000x600")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="СРАВНЕНИЕ КАМЕР", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        # Таблица сравнения
        columns = ("camera", "count", "overall", "sharpness", "noise", "dr", "dxo")
        
        tree = ttk.Treeview(dialog, columns=columns, show="headings", height=15)
        
        tree.heading("camera", text="Модель камеры")
        tree.heading("count", text="Фото")
        tree.heading("overall", text="Ср. оценка")
        tree.heading("sharpness", text="Резкость")
        tree.heading("noise", text="Шум")
        tree.heading("dr", text="Дин.диап.")
        tree.heading("dxo", text="DxO")
        
        tree.column("camera", width=250)
        tree.column("count", width=60)
        tree.column("overall", width=80)
        tree.column("sharpness", width=80)
        tree.column("noise", width=80)
        tree.column("dr", width=80)
        tree.column("dxo", width=80)
        
        # Сортируем по общей оценке
        cameras_data.sort(key=lambda x: float(x['overall']), reverse=True)
        
        for cam in cameras_data:
            overall_val = float(cam['overall'])
            if overall_val >= 80:
                overall_display = f"{cam['overall']}%"
            elif overall_val >= 60:
                overall_display = f"{cam['overall']}%"
            elif overall_val >= 40:
                overall_display = f"{cam['overall']}%"
            else:
                overall_display = f"{cam['overall']}%"
            
            tree.insert("", "end", values=(
                cam['name'],
                cam['count'],
                overall_display,
                cam['sharpness'],
                cam['noise'],
                cam['dr'],
                cam['dxo']
            ))
        
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", padx=5, pady=10)
        
        ctk.CTkButton(dialog, text="Закрыть", command=dialog.destroy, width=150).pack(pady=10)
    
    def load_images(self):
        """Загрузка одного или нескольких изображений"""
        file_paths = filedialog.askopenfilenames(
            title="Выберите фотографии",
            filetypes=[
                ("Изображения", "*.jpg *.jpeg *.png *.bmp *.tiff *.dng *.cr2 *.nef *.arw *.cr3 *.raf *.orf *.rw2"),
                ("Все файлы", "*.*")
            ]
        )
        
        for file_path in file_paths:
            if file_path not in self.current_image_paths:
                self.current_image_paths.append(file_path)
                self.files_tree.insert("", "end", values=(os.path.basename(file_path),))
        
        if self.current_image_paths:
            self.analyze_btn.configure(state="normal")
            self.status_label.configure(text=f"Загружено файлов: {len(self.current_image_paths)}")
            
            # Автоматически определяем камеру из первого файла
            self.detect_camera_from_files()
    
    def detect_camera_from_files(self):
        """Автоматическое определение камеры из загруженных файлов"""
        if not self.current_image_paths:
            return
        
        cameras_found = {}
        
        for file_path in self.current_image_paths[:5]:  # Проверяем первые 5 файлов
            try:
                # Быстрый анализ только для определения камеры
                result = self.analyzer.analyze(file_path)
                camera = result.get('camera_model')
                if camera and camera != 'Unknown':
                    cameras_found[camera] = cameras_found.get(camera, 0) + 1
            except:
                pass
        
        if cameras_found:
            # Находим наиболее часто встречающуюся камеру
            best_camera = max(cameras_found.items(), key=lambda x: x[1])[0]
            self.camera_entry.delete(0, "end")
            self.camera_entry.insert(0, best_camera)
            
            # Ищем DxOMark оценку
            dxo_score = self.dxo_service.get_score(best_camera)
            if dxo_score:
                self.selected_dxomark_score = dxo_score
                self.selected_camera_info.configure(text=f"✅ DxOMark: {dxo_score}")
            else:
                self.selected_camera_info.configure(text=f"⚠️ DxOMark не найден")
            
            self.selected_camera_model = best_camera
            self.status_label.configure(text=f"Автоматически определена камера: {best_camera}")
        else:
            self.camera_entry.delete(0, "end")
            self.camera_entry.insert(0, "")
            self.selected_camera_info.configure(text="❓ Камера не определена, выберите вручную")
            self.status_label.configure(text="Камера не определена, выберите вручную из списка")
    
    def select_camera_from_list(self):
        """Выбор камеры из списка с поиском по вводу пользователя"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Выбор модели камеры")
        dialog.geometry("650x550")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Поиск модели камеры:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        search_frame = ctk.CTkFrame(dialog)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        # Поле для ввода поискового запроса
        search_entry = ctk.CTkEntry(search_frame, width=400, placeholder_text="Введите название для поиска (например 'iPhone 15' или 'S23')")
        search_entry.pack(side="left", padx=5)
        
        # Берём текст из поля ввода камеры, если он есть
        current_camera = self.camera_entry.get().strip()
        if current_camera:
            search_entry.delete(0, "end")
            search_entry.insert(0, current_camera)
        
        def do_search():
            query = search_entry.get().strip()
            if not query:
                messagebox.showwarning("Внимание", "Введите текст для поиска!")
                return
            
            listbox.delete(0, "end")
            
            # Получаем все модели из базы
            all_models = self.dxo_service.get_all_models()
            query_lower = query.lower()
            found_models = []
            
            for model in all_models:
                model_lower = model.lower()
                # Проверяем, содержит ли модель введённый текст
                if query_lower in model_lower:
                    found_models.append(model)
                # Также проверяем по отдельным словам
                elif any(word in model_lower for word in query_lower.split()):
                    if model not in found_models:
                        found_models.append(model)
            
            if found_models:
                for model in found_models[:50]:  # Не более 50 результатов
                    dxo = self.dxo_service.get_score(model)
                    if dxo:
                        display_text = f"{model} (DxOMark: {dxo})"
                    else:
                        display_text = f"{model} (DxOMark: ?)"
                    listbox.insert("end", display_text)
                
                # Обновляем информацию о количестве найденных
                result_label.configure(text=f"Найдено моделей: {len(found_models)}")
            else:
                listbox.insert("end", "Ничего не найдено. Попробуйте другой запрос.")
                result_label.configure(text="Ничего не найдено")
        
        # Кнопка поиска
        ctk.CTkButton(search_frame, text="🔍 Найти", command=do_search, width=100).pack(side="left", padx=5)
        
        # Метка с количеством найденных
        result_label = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=12))
        result_label.pack()
        
        # Список результатов
        listbox_frame = ctk.CTkFrame(dialog)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ctk.CTkScrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, font=("Consolas", 11), yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=listbox.yview)
        
        # Загружаем модели при открытии (если есть текст)
        if current_camera:
            query_lower = current_camera.lower()
            all_models = self.dxo_service.get_all_models()
            found_models = []
            for model in all_models:
                model_lower = model.lower()
                if query_lower in model_lower:
                    found_models.append(model)
            if found_models:
                for model in found_models[:50]:
                    dxo = self.dxo_service.get_score(model)
                    if dxo:
                        display_text = f"{model} (DxOMark: {dxo})"
                    else:
                        display_text = f"{model} (DxOMark: ?)"
                    listbox.insert("end", display_text)
                result_label.configure(text=f"Найдено моделей: {len(found_models)}")
            else:
                # Если по текущему тексту ничего не найдено, показываем все модели
                all_models = self.dxo_service.get_all_models()
                for model in all_models[:50]:
                    dxo = self.dxo_service.get_score(model)
                    if dxo:
                        display_text = f"{model} (DxOMark: {dxo})"
                    else:
                        display_text = f"{model} (DxOMark: ?)"
                    listbox.insert("end", display_text)
                result_label.configure(text=f"Все модели: {len(all_models)} (показаны первые 50)")
        else:
            # Если нет текста, показываем все модели
            all_models = self.dxo_service.get_all_models()
            for model in all_models[:50]:
                dxo = self.dxo_service.get_score(model)
                if dxo:
                    display_text = f"{model} (DxOMark: {dxo})"
                else:
                    display_text = f"{model} (DxOMark: ?)"
                listbox.insert("end", display_text)
            result_label.configure(text=f"Все модели: {len(all_models)} (показаны первые 50)")
        
        def select_model():
            selection = listbox.curselection()
            if selection:
                selected_text = listbox.get(selection[0])
                if "Ничего не найдено" in selected_text:
                    return
                # Извлекаем название модели (без DxOMark)
                selected_model = selected_text.split(" (DxOMark:")[0]
                dxo_score = self.dxo_service.get_score(selected_model)
                
                self.camera_entry.delete(0, "end")
                self.camera_entry.insert(0, selected_model)
                self.selected_camera_model = selected_model
                self.selected_dxomark_score = dxo_score
                
                if dxo_score:
                    self.selected_camera_info.configure(text=f"DxOMark: {dxo_score}")
                    self.status_label.configure(text=f"Выбрана камера: {selected_model} (DxOMark: {dxo_score})")
                else:
                    self.selected_camera_info.configure(text=f"DxOMark не найден")
                    self.status_label.configure(text=f"Выбрана камера: {selected_model} (DxOMark не найден)")
                
                # Обновляем информацию в правой панели
                info = f"Модель камеры: {selected_model}\n\n"
                if dxo_score:
                    info += f"DxOMark оценка: {dxo_score}\n"
                    if dxo_score >= 160:
                        info += "   Элитная камера (топ-уровень)\n"
                    elif dxo_score >= 150:
                        info += "   Отличная камера\n"
                    elif dxo_score >= 140:
                        info += "   Очень хорошая камера\n"
                    elif dxo_score >= 120:
                        info += "   Хорошая камера\n"
                    elif dxo_score >= 100:
                        info += "   Средняя камера\n"
                    else:
                        info += "   Бюджетная камера\n"
                else:
                    info += "DxOMark оценка не найдена для этой модели\n"
                
                self.camera_info_text.delete("1.0", "end")
                self.camera_info_text.insert("1.0", info)
                
                dialog.destroy()
            else:
                messagebox.showwarning("Внимание", "Выберите модель из списка!")
        
        def apply_current():
            """Применить текущий введённый текст"""
            current_text = search_entry.get().strip()
            if current_text:
                self.camera_entry.delete(0, "end")
                self.camera_entry.insert(0, current_text)
                self.selected_camera_model = current_text
                self.selected_dxomark_score = None
                self.selected_camera_info.configure(text=f"⚠️ DxOMark не найден")
                self.status_label.configure(text=f"Выбрана камера: {current_text} (DxOMark не найден)")
                
                info = f"Модель камеры: {current_text}\n\nDxOMark оценка не найдена для этой модели\n"
                self.camera_info_text.delete("1.0", "end")
                self.camera_info_text.insert("1.0", info)
                dialog.destroy()
            else:
                messagebox.showwarning("Внимание", "Введите название модели!")
        
        # Кнопки
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="Выбрать", command=select_model, width=120, fg_color="#2ecc71").pack(side="left", padx=10)
        # ctk.CTkButton(btn_frame, text="Использовать введённое", command=apply_current, width=180, fg_color="#f39c12").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy, width=100, fg_color="#e74c3c").pack(side="left", padx=10)
    
    def apply_camera_to_analysis(self):
        """Применить выбранную камеру для анализа с проверкой и предложением вариантов"""
        camera_model = self.camera_entry.get().strip()
        if not camera_model:
            messagebox.showwarning("Внимание", "Введите или выберите модель камеры!")
            return
        
        # Получаем список возможных совпадений (не только точное)
        all_matches = self.get_camera_matches(camera_model)
        
        if len(all_matches) == 1:
            # Только одно совпадение - используем его
            exact_match = all_matches[0]
            model = exact_match['model']
            score = exact_match['score']
            
            self.selected_camera_model = model
            self.selected_dxomark_score = score
            self.selected_camera_info.configure(text=f"DxOMark: {score}")
            self.status_label.configure(text=f"Выбрана камера: {model} (DxOMark: {score})")
            
            # Обновляем информацию в правой панели
            info = f"Модель камеры: {model}\n\n"
            info += f"DxOMark оценка: {score}\n"
            if score >= 160:
                info += "   Элитная камера (топ-уровень)\n"
            elif score >= 150:
                info += "   Отличная камера\n"
            elif score >= 140:
                info += "   Очень хорошая камера\n"
            elif score >= 120:
                info += "   Хорошая камера\n"
            elif score >= 100:
                info += "   Средняя камера\n"
            else:
                info += "   Бюджетная камера\n"
            
            self.camera_info_text.delete("1.0", "end")
            self.camera_info_text.insert("1.0", info)
            
        elif len(all_matches) > 1:
            # Несколько совпадений - показываем диалог выбора
            self.show_camera_selection_dialog(camera_model, all_matches)
        else:
            # Нет совпадений - показываем диалог с предложением поискать
            self.show_no_match_dialog(camera_model)

    def get_camera_matches(self, query):
        """Получает список всех совпадений для запроса (не только точных)"""
        if not query:
            return []
        
        matches = []
        query_lower = query.lower()
        
        # Получаем все модели
        all_models = self.dxo_service.get_all_models()
        
        for model in all_models:
            model_lower = model.lower()
            
            # Проверяем на точное совпадение
            if model_lower == query_lower:
                score = self.dxo_service.get_score_by_model(model)
                matches.append({'model': model, 'score': score, 'match_type': 'exact'})
            # Проверяем на вхождение запроса в название
            elif query_lower in model_lower:
                score = self.dxo_service.get_score_by_model(model)
                matches.append({'model': model, 'score': score, 'match_type': 'partial'})
            # Проверяем на вхождение слов
            else:
                words = query_lower.split()
                match_count = 0
                for word in words:
                    if len(word) >= 2 and word in model_lower:
                        match_count += 1
                if match_count >= len(words) * 0.5:  # 50% совпадение слов
                    score = self.dxo_service.get_score_by_model(model)
                    matches.append({'model': model, 'score': score, 'match_type': 'word'})
        
        # Сортируем: сначала точные, потом частичные, потом по словам
        priority = {'exact': 0, 'partial': 1, 'word': 2}
        matches.sort(key=lambda x: (priority[x['match_type']], -x['score'] if x['score'] else 0))
        
        return matches[:15]  # Не более 15 вариантов

    def show_camera_selection_dialog(self, search_query, matches):
        """Показывает диалог выбора модели камеры из найденных вариантов"""
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Выбор модели камеры")
        dialog.geometry("650x500")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"Найдено {len(matches)} вариантов для '{search_query}':", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(dialog, text="Выберите подходящую модель из списка:", font=ctk.CTkFont(size=12)).pack()
        
        # Фрейм для списка
        listbox_frame = ctk.CTkFrame(dialog)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ctk.CTkScrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(listbox_frame, font=("Consolas", 11), yscrollcommand=scrollbar.set, height=12)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=listbox.yview)
        
        # Заполняем список найденными моделями
        for match in matches:
            model = match['model']
            score = match['score']
            match_type = match['match_type']
            
            if match_type == 'exact':
                prefix = "✓ "
            elif match_type == 'partial':
                prefix = "→ "
            else:
                prefix = "  "
            
            if score:
                display_text = f"{prefix}{model} (DxOMark: {score})"
            else:
                display_text = f"{prefix}{model} (DxOMark: ?)"
            listbox.insert("end", display_text)
        
        # Фрейм для кнопок
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_text = listbox.get(selection[0])
                # Извлекаем название модели (без префикса и DxOMark)
                selected_model = selected_text.split(" (DxOMark:")[0]
                # Убираем префикс
                if selected_model.startswith("✓ "):
                    selected_model = selected_model[2:]
                elif selected_model.startswith("→ "):
                    selected_model = selected_model[2:]
                elif selected_model.startswith("  "):
                    selected_model = selected_model[2:]
                
                score = self.dxo_service.get_score_by_model(selected_model)
                
                self.camera_entry.delete(0, "end")
                self.camera_entry.insert(0, selected_model)
                self.selected_camera_model = selected_model
                self.selected_dxomark_score = score
                
                if score:
                    self.selected_camera_info.configure(text=f"DxOMark: {score}")
                    self.status_label.configure(text=f"Выбрана камера: {selected_model} (DxOMark: {score})")
                else:
                    self.selected_camera_info.configure(text=f"DxOMark не найден")
                    self.status_label.configure(text=f"Выбрана камера: {selected_model} (DxOMark не найден)")
                
                # Обновляем информацию в правой панели
                info = f"Модель камеры: {selected_model}\n\n"
                if score:
                    info += f"DxOMark оценка: {score}\n"
                    if score >= 160:
                        info += "   Элитная камера (топ-уровень)\n"
                    elif score >= 150:
                        info += "   Отличная камера\n"
                    elif score >= 140:
                        info += "   Очень хорошая камера\n"
                    elif score >= 120:
                        info += "   Хорошая камера\n"
                    elif score >= 100:
                        info += "   Средняя камера\n"
                    else:
                        info += "   Бюджетная камера\n"
                else:
                    info += "DxOMark оценка не найдена для этой модели\n"
                
                self.camera_info_text.delete("1.0", "end")
                self.camera_info_text.insert("1.0", info)
                
                dialog.destroy()
            else:
                messagebox.showwarning("Внимание", "Выберите модель из списка!")
        
        def use_as_is():
            self.selected_camera_model = search_query
            self.selected_dxomark_score = None
            self.selected_camera_info.configure(text=f"DxOMark не найден")
            self.status_label.configure(text=f"Выбрана камера: {search_query} (DxOMark не найден)")
            
            info = f"Модель камеры: {search_query}\n\nDxOMark оценка не найдена для этой модели\n"
            self.camera_info_text.delete("1.0", "end")
            self.camera_info_text.insert("1.0", info)
            dialog.destroy()
        
        ctk.CTkButton(btn_frame, text="Выбрать", command=on_select, width=120, fg_color="#2ecc71").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Использовать введённое", command=use_as_is, width=180, fg_color="#f39c12").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy, width=100, fg_color="#e74c3c").pack(side="left", padx=10)

    def show_no_match_dialog(self, search_query):
        """Показывает диалог когда ничего не найдено"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Модель не найдена")
        dialog.geometry("500x300")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"Модель '{search_query}' не найдена в базе DxOMark.", 
                    font=ctk.CTkFont(size=14)).pack(pady=15)
        ctk.CTkLabel(dialog, text="Возможные причины:", font=ctk.CTkFont(size=12)).pack()
        ctk.CTkLabel(dialog, text="• Неполное или неточное название\n• Модель отсутствует в базе данных", font=ctk.CTkFont(size=12)).pack()
        
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=20)
        
        def use_as_is():
            self.selected_camera_model = search_query
            self.selected_dxomark_score = None
            self.selected_camera_info.configure(text=f"DxOMark не найден")
            self.status_label.configure(text=f"Выбрана камера: {search_query} (DxOMark не найден)")
            
            info = f"Модель камеры: {search_query}\n\nDxOMark оценка не найдена для этой модели\n"
            self.camera_info_text.delete("1.0", "end")
            self.camera_info_text.insert("1.0", info)
            dialog.destroy()
        
        def search_again():
            dialog.destroy()
            self.select_camera_from_list()
        
        ctk.CTkButton(btn_frame, text="Использовать введённое название", command=use_as_is, width=200, fg_color="#f39c12").pack(pady=5)
        ctk.CTkButton(btn_frame, text="Поискать вручную", command=search_again, width=200).pack(pady=5)
        ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy, width=100).pack(pady=5)

    def show_camera_selection_dialog(self, search_query):
        """Показывает диалог выбора модели камеры из найденных вариантов"""
        
        # Ищем модели по запросу
        exact_matches = self.dxo_service.search_models(search_query)
        
        # Если не нашли по прямому поиску, ищем по частям
        if not exact_matches:
            all_models = self.dxo_service.get_all_models()
            search_lower = search_query.lower()
            for model in all_models:
                model_lower = model.lower()
                # Проверяем вхождение слов
                words = search_lower.split()
                score = 0
                for word in words:
                    if word in model_lower:
                        score += 1
                if score >= len(words) * 0.6:  # 60% совпадение слов
                    exact_matches.append(model)
            exact_matches = list(dict.fromkeys(exact_matches))[:15]  # Убираем дубликаты, берём 15
        
        if exact_matches:
            # Создаём диалог выбора
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Выбор модели камеры")
            dialog.geometry("600x500")
            dialog.grab_set()
            
            ctk.CTkLabel(dialog, text=f"Найдено несколько вариантов для '{search_query}':", 
                        font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
            
            ctk.CTkLabel(dialog, text="Выберите подходящую модель из списка:", font=ctk.CTkFont(size=12)).pack()
            
            # Фрейм для списка
            listbox_frame = ctk.CTkFrame(dialog)
            listbox_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            scrollbar = ctk.CTkScrollbar(listbox_frame)
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(listbox_frame, font=("Consolas", 11), yscrollcommand=scrollbar.set, height=12)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.configure(command=listbox.yview)
            
            # Заполняем список найденными моделями
            for model in exact_matches:
                dxo = self.dxo_service.get_score(model)
                if dxo:
                    display_text = f"{model} (DxOMark: {dxo})"
                else:
                    display_text = f"{model} (DxOMark: ?)"
                listbox.insert("end", display_text)
            
            # Фрейм для кнопок
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(pady=10)
            
            def on_select():
                selection = listbox.curselection()
                if selection:
                    selected_text = listbox.get(selection[0])
                    # Извлекаем название модели (без DxOMark)
                    selected_model = selected_text.split(" (DxOMark:")[0]
                    dxo_score = self.dxo_service.get_score(selected_model)
                    
                    self.camera_entry.delete(0, "end")
                    self.camera_entry.insert(0, selected_model)
                    self.selected_camera_model = selected_model
                    self.selected_dxomark_score = dxo_score
                    
                    if dxo_score:
                        self.selected_camera_info.configure(text=f"✅ DxOMark: {dxo_score}")
                        self.status_label.configure(text=f"Выбрана камера: {selected_model} (DxOMark: {dxo_score})")
                    else:
                        self.selected_camera_info.configure(text=f"⚠️ DxOMark не найден")
                        self.status_label.configure(text=f"Выбрана камера: {selected_model} (DxOMark не найден)")
                    
                    # Обновляем информацию в правой панели
                    info = f"Модель камеры: {selected_model}\n\n"
                    if dxo_score:
                        info += f"DxOMark оценка: {dxo_score}\n"
                        if dxo_score >= 160:
                            info += "   Элитная камера (топ-уровень)\n"
                        elif dxo_score >= 150:
                            info += "   Отличная камера\n"
                        elif dxo_score >= 140:
                            info += "   Очень хорошая камера\n"
                        elif dxo_score >= 120:
                            info += "   Хорошая камера\n"
                        elif dxo_score >= 100:
                            info += "   Средняя камера\n"
                        else:
                            info += "   Бюджетная камера\n"
                    else:
                        info += "DxOMark оценка не найдена для этой модели\n"
                    
                    self.camera_info_text.delete("1.0", "end")
                    self.camera_info_text.insert("1.0", info)
                    
                    dialog.destroy()
                else:
                    messagebox.showwarning("Внимание", "Выберите модель из списка!")
            
            def on_cancel():
                dialog.destroy()
            
            ctk.CTkButton(btn_frame, text="Выбрать", command=on_select, width=120, fg_color="#2ecc71").pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="Отмена", command=on_cancel, width=120, fg_color="#e74c3c").pack(side="left", padx=10)
            
            # Кнопка для ручного ввода
            def manual_entry():
                manual_model = self.camera_entry.get().strip()
                if manual_model:
                    self.selected_camera_model = manual_model
                    self.selected_dxomark_score = None
                    self.selected_camera_info.configure(text=f"⚠️ DxOMark не найден")
                    self.status_label.configure(text=f"Выбрана камера: {manual_model} (DxOMark не найден)")
                    
                    info = f"Модель камеры: {manual_model}\n\nDxOMark оценка не найдена для этой модели\n"
                    self.camera_info_text.delete("1.0", "end")
                    self.camera_info_text.insert("1.0", info)
                    dialog.destroy()
                else:
                    messagebox.showwarning("Внимание", "Введите название модели!")
            
            ctk.CTkButton(btn_frame, text="Использовать введённое название", command=manual_entry, width=200).pack(side="left", padx=10)
            
        else:
            # Совсем ничего не найдено - предлагаем использовать введённое название или поискать по-другому
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Модель не найдена")
            dialog.geometry("500x250")
            dialog.grab_set()
            
            ctk.CTkLabel(dialog, text=f"Модель '{search_query}' не найдена в базе DxOMark.", 
                        font=ctk.CTkFont(size=14)).pack(pady=15)
            ctk.CTkLabel(dialog, text="Возможные причины:", font=ctk.CTkFont(size=12)).pack()
            ctk.CTkLabel(dialog, text="• Неполное или неточное название\n• Модель отсутствует в базе данных", font=ctk.CTkFont(size=12)).pack()
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(pady=20)
            
            def use_as_is():
                self.selected_camera_model = search_query
                self.selected_dxomark_score = None
                self.selected_camera_info.configure(text=f"⚠️ DxOMark не найден")
                self.status_label.configure(text=f"Выбрана камера: {search_query} (DxOMark не найден)")
                
                info = f"Модель камеры: {search_query}\n\nDxOMark оценка не найдена для этой модели\n"
                self.camera_info_text.delete("1.0", "end")
                self.camera_info_text.insert("1.0", info)
                dialog.destroy()
            
            def search_again():
                dialog.destroy()
                # Открываем диалог поиска
                self.select_camera_from_list()
            
            ctk.CTkButton(btn_frame, text="Использовать введённое название", command=use_as_is, width=200, fg_color="#f39c12").pack(pady=5)
            ctk.CTkButton(btn_frame, text="Поискать вручную", command=search_again, width=200).pack(pady=5)
            ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy, width=100).pack(pady=5)
    
    def clear_images(self):
        """Очистка списка загруженных файлов"""
        if messagebox.askyesno("Подтверждение", "Очистить список загруженных файлов?"):
            self.current_image_paths = []
            self.current_images = []
            self.current_photo_images = []
            self.analysis_results = []
            self.selected_camera_model = None
            self.selected_dxomark_score = None
            
            for item in self.files_tree.get_children():
                self.files_tree.delete(item)
            
            self.preview_label.configure(text="Выберите файл для предпросмотра")
            self.analyze_btn.configure(state="disabled")
            self.camera_entry.delete(0, "end")
            self.selected_camera_info.configure(text="")
            self.status_label.configure(text="Список очищен")
            
            # Очищаем панель результатов
            self.score_value.configure(text="---")
            self.score_rating.configure(text="")
            self.recommendations_text.delete("1.0", "end")
            self.camera_info_text.delete("1.0", "end")
            for key in self.metric_bars:
                self.metric_bars[key]["label"].configure(text="---")
                self.metric_bars[key]["bar"].set(0)
            self.gauge_canvas.delete("all")
    
    def on_file_select(self, event):
        """Обработка выбора файла для предпросмотра"""
        selection = self.files_tree.selection()
        if selection:
            index = self.files_tree.index(selection[0])
            if index < len(self.current_image_paths):
                self.display_preview(self.current_image_paths[index])
    
    def display_preview(self, file_path):
        """Отображение предпросмотра изображения"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            raw_extensions = {'.dng', '.cr2', '.nef', '.arw', '.crw', '.raf', '.orf', '.rw2'}
            
            img = None
            
            if ext in raw_extensions:
                try:
                    import rawpy
                    with rawpy.imread(file_path) as raw:
                        try:
                            rgb = raw.extract_thumb()
                            if isinstance(rgb, rawpy.Thumb):
                                img = Image.open(io.BytesIO(rgb.data))
                            else:
                                rgb = raw.postprocess(
                                    half_size=True,
                                    use_camera_wb=True,
                                    output_bps=8,
                                    no_auto_bright=False
                                )
                                img = Image.fromarray(rgb)
                        except:
                            rgb = raw.postprocess(
                                half_size=True,
                                use_camera_wb=True,
                                output_bps=8
                            )
                            img = Image.fromarray(rgb)
                except ImportError:
                    self.preview_label.configure(
                        text=f"RAW файл: {os.path.basename(file_path)}\n\n"
                             f"Для предпросмотра RAW установите:\n"
                             f"pip install rawpy\n\n"
                             f"Анализ всё равно будет выполнен."
                    )
                    return
                except Exception as e:
                    print(f"RAW preview error: {e}")
                    self.preview_label.configure(
                        text=f"RAW файл: {os.path.basename(file_path)}\n\n"
                             f"Предпросмотр недоступен,\n"
                             f"но анализ будет выполнен."
                    )
                    return
            
            if img is None:
                img = Image.open(file_path)
            
            max_size = (350, 350)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            photo_image = ImageTk.PhotoImage(img)
            self.current_photo_images.append(photo_image)
            self.preview_label.configure(image=photo_image, text="")
            
        except Exception as e:
            print(f"Preview error: {e}")
            self.preview_label.configure(
                text=f"Не удалось загрузить изображение\n\n"
                     f"{os.path.basename(file_path)}\n"
                     f"Анализ будет выполнен."
            )
    
    def start_analysis(self):
        """Запуск анализа всех загруженных файлов"""
        if not self.current_image_paths:
            messagebox.showwarning("Внимание", "Нет файлов для анализа!")
            return
        
        if not self.selected_camera_model:
            # Проверяем, выбрана ли камера
            camera_model = self.camera_entry.get().strip()
            if camera_model:
                self.selected_camera_model = camera_model
                dxo_score = self.dxo_service.get_score(camera_model)
                if dxo_score:
                    self.selected_dxomark_score = dxo_score
                    self.selected_camera_info.configure(text=f"DxOMark: {dxo_score}")
            else:
                messagebox.showwarning("Внимание", "Выберите модель камеры для анализа!")
                return
        
        if self.is_analyzing:
            messagebox.showwarning("Внимание", "Анализ уже выполняется!")
            return
        
        self.is_analyzing = True
        self.analyze_btn.configure(state="disabled", text="Анализируем...")
        self.progress_bar.start()
        self.status_label.configure(text="Анализ изображений...")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self.perform_mass_analysis)
        thread.daemon = True
        thread.start()
    
    def perform_mass_analysis(self):
        """Выполнение анализа всех загруженных файлов"""
        total = len(self.current_image_paths)
        results = []
        
        for i, file_path in enumerate(self.current_image_paths):
            self.root.after(0, lambda p=i: self.progress_bar.set((p + 1) / total))
            self.root.after(0, lambda p=i: self.status_label.configure(
                text=f"Анализ {i+1}/{total}: {os.path.basename(file_path)}"))
            
            try:
                # Анализируем изображение
                result = self.analyzer.analyze(file_path)
                
                # Применяем выбранную камеру
                result['camera_model'] = self.selected_camera_model
                if self.selected_dxomark_score:
                    result['dxomark_score'] = self.selected_dxomark_score
                
                # Сохраняем результат
                if self.db:
                    analysis_id = self.db.save_analysis(result)
                    result['id'] = analysis_id
                
                results.append(result)
                
            except Exception as e:
                print(f"Ошибка анализа {file_path}: {e}")
                results.append({
                    'filename': os.path.basename(file_path),
                    'overall_score': 0,
                    'sharpness_score': 0,
                    'noise_level': 0,
                    'dynamic_range': 0,
                    'brightness': 0.5,
                    'contrast': 0.5,
                    'saturation': 0.5,
                    'exposure_score': 0.5,
                    'composition_score': 0.5,
                    'camera_model': self.selected_camera_model,
                    'dxomark_score': self.selected_dxomark_score,
                    'error': True
                })
        
        self.analysis_results = results
        
        # Обновляем интерфейс
        self.root.after(0, self.update_analysis_results)
        self.root.after(0, self.load_recent_analyses)
        self.root.after(0, self.load_cameras_analysis)
        
        self.is_analyzing = False
        self.analyze_btn.configure(state="normal", text="АНАЛИЗ")
        self.progress_bar.stop()
        self.progress_bar.set(1)
        self.status_label.configure(text=f"Анализ завершён. Обработано {len(results)} файлов")
        
        self.root.after(2000, lambda: self.progress_bar.set(0))
    
    def update_analysis_results(self):
        """Обновление отображения результатов анализа"""
        if not self.analysis_results:
            return
        
        # Показываем результаты последнего проанализированного файла
        result = self.analysis_results[-1]
        
        # Общая оценка
        overall = result.get('overall_score', 0)
        self.score_value.configure(text=f"{overall:.1f}/100")
        
        if overall >= 85:
            rating = "ПРЕВОСХОДНО"
            color = "#2ecc71"
        elif overall >= 70:
            rating = "ОТЛИЧНО"
            color = "#3498db"
        elif overall >= 55:
            rating = "ХОРОШО"
            color = "#f39c12"
        elif overall >= 40:
            rating = "УДОВЛЕТВОРИТЕЛЬНО"
            color = "#e67e22"
        else:
            rating = "ТРЕБУЕТ УЛУЧШЕНИЯ"
            color = "#e74c3c"
        
        self.score_rating.configure(text=rating, text_color=color)
        self.draw_gauge(overall)
        
        # Детальные метрики
        self.update_metric_bar("sharpness", result.get('sharpness_score', 0))
        self.update_metric_bar("noise", result.get('noise_level', 0))
        self.update_metric_bar("dynamic_range", result.get('dynamic_range', 8))
        self.update_metric_bar("brightness", result.get('brightness', 0) * 100)
        self.update_metric_bar("contrast", result.get('contrast', 0) * 100)
        self.update_metric_bar("saturation", result.get('saturation', 0) * 100)
        self.update_metric_bar("exposure", result.get('exposure_score', 0) * 100)
        
        # Информация о камере
        self.update_camera_info(result)
        
        # Рекомендации
        self.update_recommendations(result)
        
        # Показываем сводку по всем файлам
        if len(self.analysis_results) > 1:
            avg_overall = sum(r.get('overall_score', 0) for r in self.analysis_results) / len(self.analysis_results)
            self.status_label.configure(
                text=f"Анализ завершён. Обработано {len(self.analysis_results)} файлов. "
                     f"Средняя оценка: {avg_overall:.1f}%")
    
    def update_metric_bar(self, key, value):
        """Обновление полосы метрики"""
        if key in self.metric_bars:
            metric = self.metric_bars[key]
            norm_value = (value - metric["min"]) / (metric["max"] - metric["min"])
            norm_value = max(0, min(1, norm_value))
            
            if metric.get("invert"):
                norm_value = 1 - norm_value
            
            metric["bar"].set(norm_value)
            
            if key == "dynamic_range":
                metric["label"].configure(text=f"{value:.1f} EV")
            else:
                metric["label"].configure(text=f"{value:.1f}")
    
    def update_camera_info(self, result):
        """Обновление информации о камере"""
        info = ""
        
        camera_make = result.get('camera_make', 'Не определено')
        camera_model = result.get('camera_model', 'Не определена')
        
        info += f"Модель камеры: {camera_model}\n\n"
        
        dxo_score = result.get('dxomark_score')
        if dxo_score:
            info += f"DxOMark оценка: {dxo_score}\n"
            if dxo_score >= 160:
                info += "   Элитная камера (топ-уровень)\n"
            elif dxo_score >= 150:
                info += "   Отличная камера\n"
            elif dxo_score >= 140:
                info += "   Очень хорошая камера\n"
            elif dxo_score >= 120:
                info += "   Хорошая камера\n"
            elif dxo_score >= 100:
                info += "   Средняя камера\n"
            else:
                info += "   Бюджетная камера\n"
        else:
            info += "DxOMark оценка не найдена для этой модели\n"
        
        iso = result.get('iso')
        exposure_time = result.get('exposure_time')
        aperture = result.get('aperture')
        focal_length = result.get('focal_length')
        
        if iso or exposure_time or aperture or focal_length:
            info += "\nТехнические параметры:\n"
            if iso:
                info += f"   • ISO: {iso}\n"
            if exposure_time:
                info += f"   • Выдержка: {exposure_time}\n"
            if aperture:
                info += f"   • Диафрагма: f/{aperture:.1f}\n"
            if focal_length:
                info += f"   • Фокусное расстояние: {focal_length} mm\n"
        
        self.camera_info_text.delete("1.0", "end")
        self.camera_info_text.insert("1.0", info)
    
    def update_recommendations(self, result):
        """Обновление рекомендаций"""
        recommendations = []
        
        sharpness = result.get('sharpness_score', 0)
        if sharpness < 50:
            recommendations.append("Низкая резкость - используйте штатив или улучшите фокусировку")
        
        noise = result.get('noise_level', 0)
        if noise > 40:
            recommendations.append("Высокий уровень шума - снизьте ISO или используйте шумоподавление")
        
        dynamic_range = result.get('dynamic_range', 0)
        if dynamic_range < 5:
            recommendations.append("Низкий динамический диапазон - избегайте сцен с большим контрастом")
        
        brightness = result.get('brightness', 0.5)
        if brightness < 0.3:
            recommendations.append("Фото слишком тёмное - увеличьте экспозицию")
        elif brightness > 0.8:
            recommendations.append("Фото пересвечено - уменьшите экспозицию")
        
        saturation = result.get('saturation', 0.5)
        if saturation < 0.3:
            recommendations.append("Низкая насыщенность - фото выглядит блеклым")
        elif saturation > 0.8:
            recommendations.append("Высокая насыщенность - цвета могут быть неестественными")
        
        exposure = result.get('exposure_score', 0.5)
        if exposure < 0.4:
            recommendations.append("Недоэкспонировано - добавьте +0.7 EV")
        elif exposure > 0.8:
            recommendations.append("Переэкспонировано - уменьшите на -0.7 EV")
        
        if not recommendations:
            recommendations.append("Отличное фото! Технические параметры в норме")
        
        self.recommendations_text.delete("1.0", "end")
        for rec in recommendations:
            self.recommendations_text.insert("end", f"• {rec}\n")
    
    def draw_gauge(self, value):
        """Рисование круговой диаграммы"""
        self.gauge_canvas.delete("all")
        
        width = 200
        height = 200
        cx, cy = width // 2, height // 2
        radius = 80
        
        if value >= 80:
            color = "#2ecc71"
        elif value >= 60:
            color = "#3498db"
        elif value >= 40:
            color = "#f39c12"
        else:
            color = "#e74c3c"
        
        import math
        end_angle = (value / 100) * 360 - 90
        start_angle = -90
        
        def get_point(angle_deg, r):
            rad = math.radians(angle_deg)
            return (cx + r * math.cos(rad), cy + r * math.sin(rad))
        
        if value > 0:
            points = [(cx, cy)]
            step = max(1, int((end_angle - start_angle) / 50))
            for a in range(int(start_angle), int(end_angle) + 1, step):
                points.append(get_point(a, radius))
            points.append(get_point(end_angle, radius))
            self.gauge_canvas.create_polygon(points, fill=color, outline="")
        
        self.gauge_canvas.create_oval(cx - 50, cy - 50, cx + 50, cy + 50, fill="#2b2b2b", outline="")
        self.gauge_canvas.create_text(cx, cy, text=f"{value:.0f}%", fill="white", font=("Arial", 20, "bold"))
    
    def load_recent_analyses(self):
        """Загрузка последних анализов из БД"""
        if not hasattr(self, 'history_tree') or not self.history_tree:
            return
        
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        if not self.db:
            return
        
        try:
            analyses = self.db.get_all_analyses(limit=100)
            for analysis in analyses:
                def get_val(key, default=0, is_percent=False):
                    v = analysis.get(key, default)
                    if v is None or v == 'N/A':
                        return default
                    if isinstance(v, (int, float)):
                        if is_percent:
                            return v * 100
                        return v
                    return default
                
                overall = get_val('overall_score')
                sharpness = get_val('sharpness_score')
                noise = get_val('noise_level')
                dr = get_val('dynamic_range')
                brightness = get_val('brightness', is_percent=True)
                contrast = get_val('contrast', is_percent=True)
                saturation = get_val('saturation', is_percent=True)
                exposure = get_val('exposure_score', is_percent=True)
                camera = (analysis.get('camera_model') or '-')[:25]
                dxo = analysis.get('dxomark_score') or '-'
                
                def fmt(val, decimals=1):
                    if isinstance(val, float):
                        return f"{val:.{decimals}f}"
                    return str(val)
                
                self.history_tree.insert("", "end", values=(
                    analysis.get('id', '-'),
                    (analysis.get('filename') or '-')[:30],
                    fmt(overall, 1),
                    fmt(sharpness, 1),
                    fmt(noise, 1),
                    fmt(dr, 1),
                    fmt(brightness, 1),
                    fmt(contrast, 1),
                    fmt(saturation, 1),
                    fmt(exposure, 1),
                    camera,
                    dxo
                ))
        except Exception as e:
            print(f"Ошибка загрузки истории: {e}")
    
    def delete_selected_photo(self):
        """Удаление выбранной фотографии из БД"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите фотографию для удаления")
            return
        
        if messagebox.askyesno("Подтверждение", "Удалить выбранную фотографию из базы данных?"):
            try:
                item = self.history_tree.item(selection[0])
                photo_id = item['values'][0]
                self.db.delete_analysis(photo_id)
                self.load_recent_analyses()
                self.load_cameras_analysis()
                messagebox.showinfo("Успех", "Фотография удалена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")
    
    def open_db_settings(self):
        """Открытие настроек базы данных"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Настройки базы данных")
        dialog.geometry("600x500")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Настройка подключения к БД", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
        
        type_frame = ctk.CTkFrame(dialog)
        type_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(type_frame, text="Тип базы данных:", font=ctk.CTkFont(size=13)).pack(side="left", padx=10)
        
        db_type_var = ctk.StringVar(value=self.current_db_type)
        sqlite_radio = ctk.CTkRadioButton(type_frame, text="SQLite", variable=db_type_var, value="sqlite")
        sqlite_radio.pack(side="left", padx=10)
        mssql_radio = ctk.CTkRadioButton(type_frame, text="MS SQL Server", variable=db_type_var, value="mssql")
        mssql_radio.pack(side="left", padx=10)
        
        sqlite_frame = ctk.CTkFrame(dialog)
        sqlite_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(sqlite_frame, text="SQLite:").pack(anchor="w")
        ctk.CTkEntry(sqlite_frame, placeholder_text="photo_analysis.db", width=300).pack(fill="x", pady=5)
        
        mssql_frame = ctk.CTkFrame(dialog)
        mssql_frame.pack(fill="x", padx=20, pady=10)
        
        mssql_entries = {}
        labels = [
            ("Сервер (IP):", "server", "192.168.199.148"),
            ("Порт:", "port", "42145"),
            ("База данных:", "database", "PhotoQualityAnalyzer"),
            ("Пользователь (логин):", "username", "sa"),
            ("Пароль:", "password", "123")
        ]
        
        for label, key, default in labels:
            row = ctk.CTkFrame(mssql_frame)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, width=120).pack(side="left", padx=5)
            entry = ctk.CTkEntry(row, width=250)
            entry.insert(0, default)
            entry.pack(side="left", padx=5)
            mssql_entries[key] = entry
        
        def apply_settings():
            new_type = db_type_var.get()
            success = False
            
            if new_type == "sqlite":
                try:
                    self.db = Database(db_type="sqlite", db_path="photo_analysis.db")
                    self.current_db_type = "sqlite"
                    success = True
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось подключиться к SQLite: {e}")
            else:
                try:
                    self.db = Database(
                        db_type="mssql",
                        server=mssql_entries["server"].get(),
                        port=int(mssql_entries["port"].get()),
                        database=mssql_entries["database"].get(),
                        username=mssql_entries["username"].get(),
                        password=mssql_entries["password"].get(),
                        use_windows_auth=False
                    )
                    self.current_db_type = "mssql"
                    success = True
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось подключиться к MS SQL: {e}")
            
            if success:
                import json
                config = {
                    "database": {
                        "type": new_type,
                        "sqlite": {"db_path": "photo_analysis.db"},
                        "mssql": {
                            "server": mssql_entries["server"].get(),
                            "port": int(mssql_entries["port"].get()),
                            "database": mssql_entries["database"].get(),
                            "username": mssql_entries["username"].get(),
                            "password": mssql_entries["password"].get(),
                            "use_windows_auth": False
                        }
                    }
                }
                with open("config.json", "w", encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                
                self.db_status_label.configure(text=f"БД: {new_type.upper()}")
                self.load_recent_analyses()
                self.load_cameras_analysis()
                messagebox.showinfo("Успех", f"База данных переключена на {new_type.upper()}")
                dialog.destroy()
        
        ctk.CTkButton(dialog, text="Применить", command=apply_settings, width=150).pack(pady=20)
    
    def run(self):
        """Запуск приложения"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        """Обработка закрытия окна"""
        if self.db:
            self.db.close()
        self.root.destroy()


if __name__ == "__main__":
    app = PhotoQualityAnalyzerApp()
    app.run()