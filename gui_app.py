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
        self.current_image_path = None
        self.current_image = None
        self.current_photo_image = None  # Для хранения PhotoImage
        self.analysis_result = None
        self.is_analyzing = False
        
        # Инициализация БД
        self.init_database()
        
        # Создание интерфейса
        self.create_widgets()
        
        # Загрузка последних анализов
        self.load_recent_analyses()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            # Пробуем загрузить конфиг
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
            text="ЗАГРУЗКА ФОТОГРАФИИ",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 5))
        
        # Кнопки загрузки
        self.btn_frame = ctk.CTkFrame(self.left_panel)
        self.btn_frame.pack(pady=10)
        
        self.load_btn = ctk.CTkButton(
            self.btn_frame,
            text="Загрузить файл",
            command=self.load_image,
            width=180,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.load_btn.pack(side="left", padx=5)
        
        self.analyze_btn = ctk.CTkButton(
            self.btn_frame,
            text="АНАЛИЗИРОВАТЬ",
            command=self.start_analysis,
            width=180,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        self.analyze_btn.pack(side="left", padx=5)
        self.analyze_btn.configure(state="disabled")
        
        # Предпросмотр изображения
        self.preview_frame = ctk.CTkFrame(self.left_panel)
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.preview_label = ctk.CTkLabel(
            self.preview_frame, 
            text="Изображение не загружено",
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.preview_label.pack(fill="both", expand=True)
    
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
        
        # Вкладка истории (расширенная)
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
        """Создание вкладки с детальными метриками (без композиции)"""
        
        # Сетка метрик (убрана композиция)
        metrics = [
            ("Резкость", "sharpness", 0, 100, False),
            ("Уровень шума", "noise", 0, 100, True),  # инвертируем
            ("Динамический диапазон", "dynamic_range", 0, 16, False),
            ("Яркость", "brightness", 0, 100, False),
            ("Контраст", "contrast", 0, 100, False),
            ("Насыщенность", "saturation", 0, 100, False),
            ("Экспозиция", "exposure", 0, 100, False),
        ]
        
        self.metric_bars = {}
        
        for name, key, min_val, max_val, invert in metrics:
            frame = ctk.CTkFrame(self.tab_metrics)
            frame.pack(fill="x", padx=10, pady=5)
            
            label = ctk.CTkLabel(frame, text=name, width=160, anchor="w")
            label.pack(side="left", padx=10)
            
            value_label = ctk.CTkLabel(frame, text="---", width=60)
            value_label.pack(side="left")
            
            bar = ctk.CTkProgressBar(frame, width=350)
            bar.pack(side="left", padx=10)
            bar.set(0)
            
            self.metric_bars[key] = {
                "label": value_label,
                "bar": bar,
                "min": min_val,
                "max": max_val,
                "invert": invert
            }
    
    def create_camera_tab(self):
        """Создание вкладки с информацией о камере"""
        
        self.camera_info_frame = ctk.CTkFrame(self.tab_camera)
        self.camera_info_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.camera_info_text = ctk.CTkTextbox(self.camera_info_frame, font=ctk.CTkFont(size=13))
        self.camera_info_text.pack(fill="both", expand=True)
        
        # Кнопка поиска вручную
        self.manual_search_frame = ctk.CTkFrame(self.tab_camera)
        self.manual_search_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(self.manual_search_frame, text="Поиск модели вручную:").pack(side="left", padx=5)
        
        self.search_entry = ctk.CTkEntry(self.manual_search_frame, width=300)
        self.search_entry.pack(side="left", padx=5)
        
        self.search_btn = ctk.CTkButton(
            self.manual_search_frame,
            text="Найти",
            command=self.search_camera_model,
            width=100
        )
        self.search_btn.pack(side="left", padx=5)
    
    def create_history_tab(self):
        """Создание вкладки с расширенной историей анализов (все метрики)"""
        
        # Таблица с историей (расширенная)
        columns = (
            "id", "filename", "overall", "sharpness", "noise", 
            "dynamic_range", "brightness", "contrast", "saturation", 
            "exposure", "camera", "dxo"
        )
        
        self.history_tree = ttk.Treeview(
            self.tab_history,
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
        scrollbar_y = ttk.Scrollbar(self.tab_history, orient="vertical", command=self.history_tree.yview)
        scrollbar_x = ttk.Scrollbar(self.tab_history, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar_y.pack(side="right", fill="y", padx=5, pady=5)
        scrollbar_x.pack(side="bottom", fill="x", padx=5, pady=5)
        
        # Кнопка обновления
        btn_frame = ctk.CTkFrame(self.tab_history)
        btn_frame.pack(pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Обновить",
            command=self.load_recent_analyses,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Удалить",
            command=self.delete_selected_photo,
            width=150,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)
    
    def load_image(self):
        """Загрузка изображения из файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите фотографию",
            filetypes=[
                ("Изображения", "*.jpg *.jpeg *.png *.bmp *.tiff *.dng *.cr2 *.nef *.arw"),
                ("Все файлы", "*.*")
            ]
        )
        
        if file_path:
            self.current_image_path = file_path
            self.display_preview(file_path)
            self.analyze_btn.configure(state="normal")
            self.status_label.configure(text=f"Загружено: {os.path.basename(file_path)}")
    
    def display_preview(self, file_path):
        """Отображение предпросмотра изображения (с поддержкой RAW)"""
        try:
            # Проверяем расширение файла
            ext = os.path.splitext(file_path)[1].lower()
            raw_extensions = {'.dng', '.cr2', '.nef', '.arw', '.crw', '.raf', '.orf', '.rw2'}
            
            img = None
            
            # Если это RAW файл
            if ext in raw_extensions:
                try:
                    import rawpy
                    # Пробуем открыть через rawpy
                    with rawpy.imread(file_path) as raw:
                        # Извлекаем preview (быстро)
                        try:
                            # Пробуем получить встроенный preview (быстрее)
                            rgb = raw.extract_thumb()
                            if isinstance(rgb, rawpy.Thumb):
                                img = Image.open(io.BytesIO(rgb.data))
                            else:
                                # Если нет preview, делаем конвертацию с низким качеством
                                rgb = raw.postprocess(
                                    half_size=True,  # Уменьшаем размер для скорости
                                    use_camera_wb=True,
                                    output_bps=8,
                                    no_auto_bright=False
                                )
                                img = Image.fromarray(rgb)
                        except:
                            # Полная конвертация с уменьшением размера
                            rgb = raw.postprocess(
                                half_size=True,
                                use_camera_wb=True,
                                output_bps=8
                            )
                            img = Image.fromarray(rgb)
                except ImportError:
                    # Если rawpy не установлен, показываем сообщение
                    self.preview_label.configure(
                        text=f"RAW файл: {os.path.basename(file_path)}\n\n"
                            f"Для предпросмотра RAW установите:\n"
                            f"pip install rawpy\n\n"
                            f"Анализ всё равно будет выполнен."
                    )
                    return
                except Exception as e:
                    print(f"RAW preview error: {e}")
                    # Показываем информационное сообщение вместо ошибки
                    self.preview_label.configure(
                        text=f"RAW файл: {os.path.basename(file_path)}\n\n"
                            f"Предпросмотр недоступен,\n"
                            f"но анализ будет выполнен."
                    )
                    return
            
            # Если это обычное изображение или RAW уже конвертирован
            if img is None:
                img = Image.open(file_path)
            
            # Изменяем размер для предпросмотра
            max_size = (350, 350)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Конвертируем в RGB если нужно
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Конвертируем в формат для tkinter и сохраняем ссылку
            self.current_photo_image = ImageTk.PhotoImage(img)
            
            # Обновляем метку
            self.preview_label.configure(image=self.current_photo_image, text="")
            
        except Exception as e:
            print(f"Preview error: {e}")
            self.preview_label.configure(
                text=f"Не удалось загрузить изображение\n\n"
                    f"{os.path.basename(file_path)}\n"
                    f"Анализ будет выполнен."
            )
            self.current_photo_image = None
    
    def start_analysis(self):
        """Запуск анализа в отдельном потоке"""
        if not self.current_image_path:
            messagebox.showwarning("Внимание", "Сначала загрузите фотографию!")
            return
        
        self.is_analyzing = True
        self.analyze_btn.configure(state="disabled", text="Анализируем...")
        self.progress_bar.start()
        self.status_label.configure(text="Анализ изображения...")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self.perform_analysis)
        thread.daemon = True
        thread.start()
    
    def perform_analysis(self):
        """Выполнение анализа изображения"""
        try:
            # Анализ
            result = self.analyzer.analyze(self.current_image_path)
            
            # Поиск DxOMark оценки
            camera_model = result.get('camera_model')
            dxomark_score = None
            
            if camera_model:
                dxomark_score = self.dxo_service.get_score(camera_model)
                if dxomark_score:
                    result['dxomark_score'] = dxomark_score
            
            # Сохранение в БД
            if self.db:
                analysis_id = self.db.save_analysis(result)
                result['id'] = analysis_id
            
            self.analysis_result = result
            
            # Обновление UI в основном потоке
            self.root.after(0, self.update_results_display)
            
        except Exception as e:
            self.root.after(0, lambda: self.show_analysis_error(str(e)))
    
    def update_results_display(self):
        """Обновление отображения результатов"""
        
        if not self.analysis_result:
            return
        
        result = self.analysis_result
        
        # ========== ОБЩАЯ ОЦЕНКА ==========
        overall = result.get('overall_score', 0)
        self.score_value.configure(text=f"{overall:.1f}/100")
        
        # Рейтинг
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
        
        # Круговая диаграмма
        self.draw_gauge(overall)
        
        # ========== ДЕТАЛЬНЫЕ МЕТРИКИ ==========
        self.update_metric_bar("sharpness", result.get('sharpness_score', 0))
        self.update_metric_bar("noise", result.get('noise_level', 0))
        self.update_metric_bar("dynamic_range", result.get('dynamic_range', 8))
        self.update_metric_bar("brightness", result.get('brightness', 0) * 100)
        self.update_metric_bar("contrast", result.get('contrast', 0) * 100)
        self.update_metric_bar("saturation", result.get('saturation', 0) * 100)
        self.update_metric_bar("exposure", result.get('exposure_score', 0) * 100)
        
        # ========== ИНФОРМАЦИЯ О КАМЕРЕ ==========
        self.update_camera_info(result)
        
        # ========== РЕКОМЕНДАЦИИ ==========
        self.update_recommendations(result)
        
        # ========== ОБНОВЛЕНИЕ ИСТОРИИ ==========
        self.load_recent_analyses()
        
        # ========== ЗАВЕРШЕНИЕ ==========
        self.is_analyzing = False
        self.analyze_btn.configure(state="normal", text="АНАЛИЗИРОВАТЬ")
        self.progress_bar.stop()
        self.progress_bar.set(1)
        self.status_label.configure(text="Анализ завершён!")
        
        self.root.after(2000, lambda: self.progress_bar.set(0))
    
    def update_metric_bar(self, key, value):
        """Обновление полосы метрики"""
        if key in self.metric_bars:
            metric = self.metric_bars[key]
            norm_value = (value - metric["min"]) / (metric["max"] - metric["min"])
            norm_value = max(0, min(1, norm_value))
            
            if metric.get("invert"):
                norm_value = 1 - norm_value
            
            metric["bar"].set(norm_value)
            
            # Форматирование вывода
            if key == "dynamic_range":
                metric["label"].configure(text=f"{value:.1f} EV")
            else:
                metric["label"].configure(text=f"{value:.1f}")
    
    def update_camera_info(self, result):
        """Обновление информации о камере"""
        info = ""
        
        camera_make = result.get('camera_make', 'Не определено')
        camera_model = result.get('camera_model', 'Не определена')
        
        # info += f"Производитель: {camera_make}\n"
        info += f"Модель камеры: {camera_model}\n\n"
        
        # DxOMark оценка
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
        
        # Технические параметры
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
    
    def search_camera_model(self):
        """Поиск модели камеры вручную (с подсказками)"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Внимание", "Введите название модели для поиска")
            return
        
        # Сначала пробуем прямой поиск
        models = self.dxo_service.search_models(query)
        
        if not models:
            # Если ничего не нашли, показываем диалог с подсказками
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Поиск модели")
            dialog.geometry("600x500")
            dialog.grab_set()
            
            ctk.CTkLabel(dialog, text=f"Модель '{query}' не найдена.", font=ctk.CTkFont(size=14)).pack(pady=10)
            ctk.CTkLabel(dialog, text="Попробуйте один из вариантов ниже:", font=ctk.CTkFont(size=12)).pack()
            
            # Показываем список всех моделей для выбора
            all_models = self.dxo_service.get_all_models()
            
            # Фильтруем модели, содержащие ключевые слова из запроса
            query_lower = query.lower()
            keywords = query_lower.split()
            
            filtered_models = []
            for model in all_models:
                model_lower = model.lower()
                score = 0
                for kw in keywords:
                    if kw in model_lower:
                        score += 1
                    # Дополнительные соответствия
                    if kw == "s23" and "galaxy s23" in model_lower:
                        score += 2
                    if kw == "s24" and "galaxy s24" in model_lower:
                        score += 2
                    if kw == "iphone" and "iphone" in model_lower:
                        score += 1
                    if kw == "pixel" and "pixel" in model_lower:
                        score += 1
                if score > 0:
                    filtered_models.append((score, model))
            
            # Сортируем по релевантности
            filtered_models.sort(key=lambda x: x[0], reverse=True)
            suggested_models = [m[1] for m in filtered_models[:15]]
            
            if not suggested_models:
                suggested_models = all_models[:50]
            
            # Создаём список для выбора
            listbox_frame = ctk.CTkFrame(dialog)
            listbox_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            scrollbar = ctk.CTkScrollbar(listbox_frame)
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(listbox_frame, font=("Consolas", 11), yscrollcommand=scrollbar.set)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.configure(command=listbox.yview)
            
            for model in suggested_models:
                listbox.insert("end", model)
            
            def select_model():
                selection = listbox.curselection()
                if selection:
                    model = suggested_models[selection[0]]
                    dxo_score = self.dxo_service.get_score(model)
                    
                    if self.analysis_result:
                        self.analysis_result['camera_model'] = model
                        self.analysis_result['dxomark_score'] = dxo_score
                        self.update_camera_info(self.analysis_result)
                        
                        if self.db and self.analysis_result.get('id'):
                            self.db.save_analysis(self.analysis_result)
                    
                    messagebox.showinfo("Успех", f"Модель {model} (DxOMark: {dxo_score}) установлена")
                    dialog.destroy()
            
            def search_again():
                new_query = search_entry.get().strip()
                if new_query:
                    dialog.destroy()
                    self.search_camera_model()
            
            # Поле для нового поиска
            search_frame = ctk.CTkFrame(dialog)
            search_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(search_frame, text="Новый поиск:").pack(side="left", padx=5)
            search_entry = ctk.CTkEntry(search_frame, width=250)
            search_entry.pack(side="left", padx=5)
            ctk.CTkButton(search_frame, text="🔍 Найти", command=search_again, width=80).pack(side="left", padx=5)
            
            btn_frame = ctk.CTkFrame(dialog)
            btn_frame.pack(pady=10)
            
            ctk.CTkButton(btn_frame, text="Выбрать", command=select_model, width=120).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Отмена", command=dialog.destroy, width=120).pack(side="left", padx=5)
            
        else:
            # Нашли модели - показываем диалог выбора
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Выбор модели камеры")
            dialog.geometry("500x400")
            dialog.grab_set()
            
            ctk.CTkLabel(dialog, text="Найденные модели:", font=ctk.CTkFont(size=14)).pack(pady=10)
            
            listbox_frame = ctk.CTkFrame(dialog)
            listbox_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            scrollbar = ctk.CTkScrollbar(listbox_frame)
            scrollbar.pack(side="right", fill="y")
            
            listbox = tk.Listbox(listbox_frame, font=("Consolas", 11), yscrollcommand=scrollbar.set)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.configure(command=listbox.yview)
            
            for model in models:
                listbox.insert("end", model)
            
            def select_model():
                selection = listbox.curselection()
                if selection:
                    model = models[selection[0]]
                    dxo_score = self.dxo_service.get_score(model)
                    
                    if self.analysis_result:
                        self.analysis_result['camera_model'] = model
                        self.analysis_result['dxomark_score'] = dxo_score
                        self.update_camera_info(self.analysis_result)
                        
                        if self.db and self.analysis_result.get('id'):
                            self.db.save_analysis(self.analysis_result)
                    
                    messagebox.showinfo("Успех", f"Модель {model} (DxOMark: {dxo_score}) установлена")
                    dialog.destroy()
            
            ctk.CTkButton(dialog, text="Выбрать", command=select_model, width=150).pack(pady=10)
    
    def load_recent_analyses(self):
        """Загрузка последних анализов из БД (все метрики - с дробными значениями)"""
        if not self.history_tree:
            return
        
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        if not self.db:
            return
        
        try:
            analyses = self.db.get_all_analyses(limit=100)
            for analysis in analyses:
                # Извлекаем значения с обработкой None - без округления
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
                
                # Форматирование с сохранением дробной части
                def fmt(val, decimals=1):
                    if isinstance(val, float):
                        return f"{val:.{decimals}f}"
                    return str(val)
                
                self.history_tree.insert("", "end", values=(
                    analysis.get('id', '-'),
                    (analysis.get('filename') or '-')[:30],
                    fmt(overall, 1),           # общая оценка (например: 75.5)
                    fmt(sharpness, 1),         # резкость (например: 62.3)
                    fmt(noise, 1),             # шум (например: 28.7)
                    fmt(dr, 1),                # динамический диапазон (например: 8.2)
                    fmt(brightness, 1),        # яркость (например: 45.6)
                    fmt(contrast, 1),          # контраст (например: 52.1)
                    fmt(saturation, 1),        # насыщенность (например: 38.4)
                    fmt(exposure, 1),          # экспозиция (например: 71.2)
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
        
        # Выбор типа БД
        type_frame = ctk.CTkFrame(dialog)
        type_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(type_frame, text="Тип базы данных:", font=ctk.CTkFont(size=13)).pack(side="left", padx=10)
        
        db_type_var = ctk.StringVar(value=self.current_db_type)
        sqlite_radio = ctk.CTkRadioButton(type_frame, text="SQLite", variable=db_type_var, value="sqlite")
        sqlite_radio.pack(side="left", padx=10)
        mssql_radio = ctk.CTkRadioButton(type_frame, text="MS SQL Server", variable=db_type_var, value="mssql")
        mssql_radio.pack(side="left", padx=10)
        
        # SQLite настройки
        sqlite_frame = ctk.CTkFrame(dialog)
        sqlite_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(sqlite_frame, text="SQLite:").pack(anchor="w")
        ctk.CTkEntry(sqlite_frame, placeholder_text="photo_analysis.db", width=300).pack(fill="x", pady=5)
        
        # MS SQL настройки
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
                # Сохраняем конфиг
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
                messagebox.showinfo("Успех", f"База данных переключена на {new_type.upper()}")
                dialog.destroy()
        
        ctk.CTkButton(dialog, text="Применить", command=apply_settings, width=150).pack(pady=20)
    
    def show_analysis_error(self, error_msg):
        """Показ ошибки анализа"""
        self.is_analyzing = False
        self.analyze_btn.configure(state="normal", text="🔍 АНАЛИЗИРОВАТЬ")
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.status_label.configure(text=f"Ошибка: {error_msg[:80]}")
        messagebox.showerror("Ошибка", f"Не удалось проанализировать изображение:\n{error_msg}")
    
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