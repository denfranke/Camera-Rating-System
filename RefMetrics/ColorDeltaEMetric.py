import os
import cv2
import numpy as np
import random
from PIL import Image, ImageDraw
import customtkinter as ctk
from .base import BaseReferenceMetric

class ColorDeltaEMetric(BaseReferenceMetric):
    
    # === ГИБКИЕ НАСТРОЙКИ ГЕОМЕТРИИ СЕТКИ (ИЗМЕНЯЙТЕ ТУТ) ===
    GRID_ROWS = 4          # Количество строк в сетке (например, 1 или 2)
    GRID_COLS = 6          # Количество колонок (например, 6)
    
    MARGIN_LEFT = 0       # Отступ от левого края выпрямленного листа (в пикселях)
    MARGIN_RIGHT = 0      # Отступ от правого края
    MARGIN_TOP = 0        # Отступ от верхнего края
    MARGIN_BOTTOM = 0     # Отступ от нижнего края
    
    SPACING_X = 0         # Зазор между ячейками сетки по горизонтали
    SPACING_Y = 0         # Зазор между ячейками сетки по вертикали
    
    # Размер квадрата внутри его ячейки в процентах (например, 80% от максимума)
    # Это позволяет сделать квадраты меньше, не ломая структуру шага сетки!
    SCALE_PERCENT = 60    

    REFERENCE_LAB_COLORS = [
        # --- СТРОКА 1 (Натуральные цвета) ---
        [37.98, 13.55, 14.05],    # 1. Dark Skin (Темная кожа)
        [65.71, 18.13, 18.67],    # 2. Light Skin (Светлая кожа)
        [49.92, -4.88, -21.94],   # 3. Blue Sky (Голубое небо)
        [43.13, -13.09, 21.90],   # 4. Foliage (Листва)
        [55.11, 8.84, -25.40],    # 5. Blue Flower (Синий цветок)
        [70.71, -33.39, -0.18],   # 6. Bluish Green (Голубовато-зеленый)

        # --- СТРОКА 2 (Яркие цвета) ---
        [62.66, 36.07, 57.10],    # 7. Orange (Оранжевый)
        [40.02, 10.41, -45.96],   # 8. Purplish Blue (Пурпурно-синий)
        [51.12, 48.24, 16.25],    # 9. Moderate Red (Умеренно красный)
        [30.26, 22.54, -20.87],   # 10. Purple (Пурпурный)
        [72.53, -23.71, 57.26],   # 11. Yellow Green (Желто-зеленый)
        [71.94, 19.34, 67.86],    # 12. Orange Yellow (Оранжево-желтый)

        # --- СТРОКА 3 (Основные и вторичные цвета) ---
        [28.78, 14.18, -50.30],   # 13. Blue (Синий)
        [55.48, -38.40, 31.33],   # 14. Green (Зеленый)
        [42.10, 53.38, 28.19],    # 15. Red (Красный)
        [81.73, 4.04, 79.82],     # 16. Yellow (Желтый)
        [51.90, 49.99, -14.57],   # 17. Magenta (Маджента)
        [51.01, -28.63, -28.64],  # 18. Cyan (Циан)

        # --- СТРОКА 4 (Серая шкала / Градиент от белого к черному) ---
        [96.54, -0.42, 1.18],     # 19. White 9.5 (Белый)
        [81.26, -0.33, 0.27],     # 20. Neutral 8 (Светло-серый)
        [66.77, -0.33, 0.44],     # 21. Neutral 6.5 (Средне-светлый серый)
        [50.87, -0.16, 0.15],     # 22. Neutral 5 (Серый)
        [35.66, -0.42, -0.46],    # 23. Neutral 3.5 (Темно-серый)
        [20.46, -0.46, -0.92]      # 24. Black 2 (Черный)
    ]

    
    PATCH_NAMES = [
        # --- СТРОКА 1 (Натуральные цвета) ---
        "1. Темная кожа (Dark skin)",
        "2. Светлая кожа (Light skin)",
        "3. Голубое небо (Blue sky)",
        "4. Листва (Foliage)",
        "5. Синий цветок (Blue flower)",
        "6. Голубовато-зеленый (Bluish green)",

        # --- СТРОКА 2 (Яркие цвета) ---
        "7. Оранжевый (Orange)",
        "8. Пурпурно-синий (Purplish blue)",
        "9. Умеренно красный (Moderate red)",
        "10. Пурпурный (Purple)",
        "11. Желто-зеленый (Yellow green)",
        "12. Оранжево-желтый (Orange yellow)",

        # --- СТРОКА 3 (Основные и вторичные цвета) ---
        "13. Синий (Blue)",
        "14. Зеленый (Green)",
        "15. Красный (Red)",
        "16. Желтый (Yellow)",
        "17. Маджента (Magenta)",
        "18. Циан (Cyan)",

        # --- СТРОКА 4 (Серая шкала / Градиент) ---
        "19. Белый (White 9.5)",
        "20. Светло-серый (Neutral 8)",
        "21. Средне-светлый серый (Neutral 6.5)",
        "22. Серый (Neutral 5)",
        "23. Темно-серый (Neutral 3.5)",
        "24. Черный (Black 2)"
    ]


    def __init__(self, name: str, key: str):
        super().__init__(name, key)
        self.last_mean_de = 0.0
        self.calculated_data = [] 
        self.annotated_image_pil = None
        self.image_to_analyze = None
        
        # Переменные для интерактивного холста
        self.manual_corners = None   # Координаты 4 углов [[x,y], [x,y], [x,y], [x,y]]
        self.canvas_corners = []     # Координаты маркеров на самом экране
        self.selected_point_idx = None
        self.display_scale = 1.0     # Коэффициент сжатия фото под размер экрана


    def process_reference_file(self, file_path: str) -> bool:
        return self.analyze_scanned_image(file_path)

    def get_calculation_value(self) -> float:
        return self.last_mean_de

   
    def analyze_scanned_image(self, image_path: str) -> bool:
        if not os.path.exists(image_path):
            print(f"[ОШИБКА] Файл не существует по пути: {image_path}")
            return False
            
        try:
            with open(image_path, "rb") as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"[ОШИБКА] Не удалось прочитать байты файла: {e}")
            return False
            
        if image is None:
            return False

        orig = image.copy()

        # Фиксированные размеры телефонного скана А4
        width_scan = 842
        height_scan = 595

        # === ЖЕЛЕЗНОЕ ИСПРАВЛЕНИЕ ГЕОМЕТРИИ (УБИРАЕТ ИГНОРИРОВАНИЕ РУЧНЫХ ТОЧЕК) ===
        # Если углы ЕЩЕ НЕ заданы (самый первый запуск), то ищем их автоматически через OpenCV
        if self.manual_corners is None or len(self.manual_corners) != 4:
            # 1. ОБРАБОТКА И ПОИСК КОНТУРОВ
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(gray, 75, 200)

            # 2. ПОИСК КОНТУРА ЛИСТА
            cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

            screen_cnt = None
            for c in cnts:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:
                    screen_cnt = approx
                    break

            if screen_cnt is not None:
                pts = screen_cnt.reshape(4, 2)
                rect = np.zeros((4, 2), dtype="float32")
                s = pts.sum(axis=1)
                rect[0] = pts[np.argmin(s)]
                rect[2] = pts[np.argmax(s)]
                diff = np.diff(pts, axis=1)
                rect[1] = pts[np.argmin(diff)]
                rect[3] = pts[np.argmax(diff)]
                self.manual_corners = rect.tolist()
            else:
                # Если автопоиск провалился, ставим дефолтную рамку
                h, w, _ = image.shape
                self.manual_corners = [
                    [int(w * 0.1), int(h * 0.1)],
                    [int(w * 0.9), int(h * 0.1)],
                    [int(w * 0.9), int(h * 0.9)],
                    [int(w * 0.1), int(h * 0.9)]
                ]

        # Теперь мы на 100% уверены, что в self.manual_corners лежат нужные точки 
        # (либо автоматически найденные, либо измененные вами вручную на холсте)
        pts1 = np.float32(self.manual_corners)
        pts2 = np.float32([[0, 0], [width_scan, 0], [width_scan, height_scan], [0, height_scan]])

        # Выполняем точное перспективное преобразование строго по выбранным координатам
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        scanned_sheet = cv2.warpPerspective(orig, matrix, (width_scan, height_scan))
        print("[УСПЕХ] Трансформация выполнена строго по координатам manual_corners.")

        # === АНАЛИЗ ЦВЕТА С АВТОМАТИЧЕСКИМ РАСЧЕТОМ ГЕОМЕТРИИ СЕТКИ ===
        img_rgb = cv2.cvtColor(scanned_sheet, cv2.COLOR_BGR2RGB)
        img_lab = cv2.cvtColor(scanned_sheet, cv2.COLOR_BGR2Lab)
        
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        
        self.calculated_data = []
        total_de = 0.0
        patch_counter = 0

        # Вычисляем доступную ширину и высоту для сетки с учетом полей
        available_w = width_scan - self.MARGIN_LEFT - self.MARGIN_RIGHT
        available_h = height_scan - self.MARGIN_TOP - self.MARGIN_BOTTOM
        
        # Вычисляем базовый размер одной ячейки (шаг сетки)
        cell_w = (available_w - (self.SPACING_X * (self.GRID_COLS - 1))) / self.GRID_COLS
        cell_h = (available_h - (self.SPACING_Y * (self.GRID_ROWS - 1))) / self.GRID_ROWS

        # Рассчитываем итоговый размер квадрата с учетом процентного масштабирования
        factor = self.SCALE_PERCENT / 100.0
        patch_w = cell_w * factor
        patch_h = cell_h * factor
        
        # Дельта для центрирования уменьшенного квадрата внутри его большой ячейки
        shift_x = (cell_w - patch_w) / 2
        shift_y = (cell_h - patch_h) / 2

        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                # Находим левый верхний угол самой ячейки сетки
                cell_x1 = self.MARGIN_LEFT + c * (cell_w + self.SPACING_X)
                cell_y1 = self.MARGIN_TOP + r * (cell_h + self.SPACING_Y)
                
                # Накладываем масштаб и центрируем квадрат внутри ячейки
                x1 = int(cell_x1 + shift_x)
                y1 = int(cell_y1 + shift_y)
                x2 = int(x1 + patch_w)
                y2 = int(y1 + patch_h)
                
                # Зажимаем координаты строго в рамки кадра 842х595 (защита от вылета при MARGIN=0)
                x1 = max(0, min(x1, width_scan - 1))
                y1 = max(0, min(y1, height_scan - 1))
                x2 = max(1, min(x2, width_scan))
                y2 = max(1, min(y2, height_scan))
                
                # Кропаем патч и вычисляем средний цвет в Lab
                patch_lab = img_lab[y1:y2, x1:x2]
                if patch_lab.size == 0:
                    patch_counter += 1
                    continue
                    
                mean_opencv_lab = np.mean(patch_lab, axis=(0, 1))
                
                detected_l = mean_opencv_lab[0] * 100.0 / 255.0
                detected_a = mean_opencv_lab[1] - 128.0
                detected_b = mean_opencv_lab[2] - 128.0
                
                # Защита от выхода за рамки списков эталонов (для сетки 3х3)
                if patch_counter < len(self.REFERENCE_LAB_COLORS):
                    ref_lab = self.REFERENCE_LAB_COLORS[patch_counter]
                else:
                    ref_lab = [50.0, 0.0, 0.0]

                if patch_counter < len(self.PATCH_NAMES):
                    patch_name = self.PATCH_NAMES[patch_counter]
                else:
                    patch_name = f"Плашка {patch_counter + 1}"
                
                # Расчет Delta E 1976
                delta_e = float(np.sqrt((ref_lab[0]-detected_l)**2 + (ref_lab[1]-detected_a)**2 + (ref_lab[2]-detected_b)**2))
                total_de += delta_e
                
                # Цвет для таблицы
                patch_rgb = img_rgb[y1:y2, x1:x2]
                mean_rgb = np.mean(patch_rgb, axis=(0, 1))
                hex_color = '#%02x%02x%02x' % (int(mean_rgb[0]), int(mean_rgb[1]), int(mean_rgb[2]))
                
                # Отрисовка рамок и номеров на скане
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                draw.text((x1 + 5, y1 + 5), str(patch_counter + 1), fill="red")
                
                self.calculated_data.append({
                    "id": patch_counter + 1,
                    "name": patch_name,
                    "hex": hex_color,
                    "delta_e": round(delta_e, 2)
                })
                patch_counter += 1

        valid_patches = len(self.calculated_data)
        self.last_mean_de = round(total_de / valid_patches, 2) if valid_patches > 0 else 0.0
        self.value = self.last_mean_de
        self.annotated_image_pil = pil_img
        return True

    def open_details_modal(self, parent_window: ctk.CTk) -> None:
        """Модальное окно детализации с кнопкой переключения в режим разметки"""
        from PIL import ImageTk

        # Гарантируем первичный расчет по вашей функции
        if self.image_to_analyze and os.path.exists(str(self.image_to_analyze)):
            self.analyze_scanned_image(str(self.image_to_analyze))
        else:
            modal = ctk.CTkToplevel(parent_window)
            modal.geometry("400x100")
            modal.attributes("-topmost", True)
            ctk.CTkLabel(modal, text="Загрузите изображение на главной панели").pack(pady=30)
            return

        # Подготовка оригинального фото для разметки
        try:
            with open(self.image_to_analyze, "rb") as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            orig_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            raw_h, raw_w, _ = orig_bgr.shape
            
            if self.manual_corners is None or len(self.manual_corners) != 4:
                self.manual_corners = [
                    [int(raw_w * 0.1), int(raw_h * 0.1)],
                    [int(raw_w * 0.9), int(raw_h * 0.1)],
                    [int(raw_w * 0.9), int(raw_h * 0.9)],
                    [int(raw_w * 0.1), int(raw_h * 0.9)]
                ]
            
            max_canvas_w, max_canvas_h = 480, 360
            self.display_scale = min(max_canvas_w / raw_w, max_canvas_h / raw_h)
            self.c_width = int(raw_w * self.display_scale)
            self.c_height = int(raw_h * self.display_scale)
            
            orig_rgb = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB)
            self.pil_raw_base = Image.fromarray(orig_rgb)
        except Exception as e:
            print(f"[ОШИБКА ИНИЦИАЛИЗАЦИИ ФОТО]: {e}")
            return

        # Инициализируем окно
        modal = ctk.CTkToplevel(parent_window)
        modal.title(f"Детализация цветопередачи: {self.name}")
        modal.geometry("950x570")
        modal.attributes("-topmost", True)
        modal.focus_set()
        modal.grab_set()

        main_container = ctk.CTkFrame(modal)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ctk.CTkFrame(main_container)
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        right_frame = ctk.CTkFrame(main_container, width=380)
        right_frame.pack(side="right", fill="both", padx=5, pady=5)
        right_frame.pack_propagate(False)

        title_label = ctk.CTkLabel(left_frame, text="Отсканированная мишень (Сетка патчей)", font=("Arial", 13, "bold"))
        title_label.pack(pady=5)

        canvas_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        canvas_container.pack(pady=10, expand=True, fill="both")

        self.edit_mode = False  
        self.canvas = None
        self.mode_btn_ref = None  

        de_summary_label = ctk.CTkLabel(
            left_frame, 
            text=f"СРЕДНЯЯ МЕТРИКА ОТКЛОНЕНИЯ: Средняя ΔE2000 = {self.last_mean_de}", 
            font=("Arial", 14, "bold")
        )
        de_summary_label.pack(pady=10)

        ctk.CTkLabel(right_frame, text="📊 Сравнительная таблица", font=("Arial", 13, "bold")).pack(pady=5)
        scroll_table = ctk.CTkScrollableFrame(right_frame, width=350, height=360)
        scroll_table.pack(fill="both", expand=True, pady=5)

        def render_table_rows():
            for widget in scroll_table.winfo_children():
                widget.destroy()

            header_frame = ctk.CTkFrame(scroll_table, fg_color="gray30", height=25)
            header_frame.pack(fill="x", pady=2)
            header_frame.pack_propagate(False)
            ctk.CTkLabel(header_frame, text="№", width=30, font=("Arial", 11, "bold")).pack(side="left", padx=2)
            ctk.CTkLabel(header_frame, text="Название", width=120, anchor="w", font=("Arial", 11, "bold")).pack(side="left", padx=2)
            ctk.CTkLabel(header_frame, text="Цвет", width=50, font=("Arial", 11, "bold")).pack(side="left", padx=2)
            ctk.CTkLabel(header_frame, text="ΔE 2000", width=60, font=("Arial", 11, "bold")).pack(side="left", padx=2)

            for data in self.calculated_data:
                row_frame = ctk.CTkFrame(scroll_table, height=30)
                row_frame.pack(fill="x", pady=2)
                row_frame.pack_propagate(False)

                ctk.CTkLabel(row_frame, text=str(data["id"]), width=30).pack(side="left", padx=2)
                ctk.CTkLabel(row_frame, text=data["name"], width=120, anchor="w").pack(side="left", padx=2)
                
                color_box = ctk.CTkFrame(row_frame, width=40, height=18, fg_color=data["hex"], corner_radius=2)
                color_box.pack(side="left", padx=8, pady=6)
                color_box.pack_propagate(False)
                
                de_val = data["delta_e"]
                item_color = "green" if de_val <= 2.0 else ("yellow" if de_val <= 4.0 else "red")
                ctk.CTkLabel(row_frame, text=str(de_val), width=60, text_color=item_color, font=("Arial", 11, "bold")).pack(side="left", padx=2)

            m_color = "green" if self.last_mean_de <= 2.0 else ("yellow" if self.last_mean_de <= 4.0 else "red")
            de_summary_label.configure(text=f"СРЕДНЯЯ МЕТРИКА ОТКЛОНЕНИЯ: Средняя ΔE2000 = {self.last_mean_de}", text_color=m_color)

        def redraw_canvas_nodes():
            """ Очищает старые векторные линии и маркеры и принудительно рисует новые """
            if not self.canvas:
                return
            self.canvas.delete("overlay")
            
            self.canvas_corners = [[int(x * self.display_scale), int(y * self.display_scale)] for x, y in self.manual_corners]
            
            # Рисуем линии
            for i in range(4):
                x1, y1 = self.canvas_corners[i]
                x2, y2 = self.canvas_corners[(i + 1) % 4]
                self.canvas.create_line(x1, y1, x2, y2, fill="#00FFFF", width=3, tags="overlay")
                
            # Рисуем маркеры
            for i, (cx, cy) in enumerate(self.canvas_corners):
                r = 10
                self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#1F6AA5", outline="#00FF00", width=3, tags="overlay")
                self.canvas.create_text(cx, cy, text=str(i+1), fill="white", font=("Arial", 11, "bold"), tags="overlay")

        def draw_view_or_edit_mode():
            for widget in canvas_container.winfo_children():
                widget.destroy()

            if not self.edit_mode:
                title_label.configure(text="Отсканированная мишень (Сетка патчей)")
                if self.annotated_image_pil:
                    orig_w, orig_h = self.annotated_image_pil.size
                    aspect = orig_h / orig_w
                    new_w = 480
                    new_h = int(new_w * aspect)
                    
                    ctk_img = ctk.CTkImage(light_image=self.annotated_image_pil, dark_image=self.annotated_image_pil, size=(new_w, new_h))
                    img_label = ctk.CTkLabel(canvas_container, text="", image=ctk_img)
                    img_label.image = ctk_img
                    img_label.pack(pady=10, expand=True)
            else:
                title_label.configure(text="Перетаскивайте маркеры с зеленой обводкой по углам листа")
                
                pil_resized = self.pil_raw_base.resize((self.c_width, self.c_height), Image.Resampling.LANCZOS)
                tk_img_raw = ImageTk.PhotoImage(pil_resized)

                # Используем СТАНДАРТНЫЙ Tkinter Canvas для идеальной отработки мыши
                # Задаем highlightthickness=0, чтобы убрать белые рамки вокруг холста
                self.canvas = ctk.CTkCanvas(canvas_container, width=self.c_width, height=self.c_height, highlightthickness=0, bd=0)
                self.canvas.pack(pady=5, expand=True)
                
                # Помещаем картинку на фон
                self.canvas.create_image(0, 0, anchor="nw", image=tk_img_raw)
                self.canvas.image = tk_img_raw # Ссылка от сборщика мусора

                # --- ПРАВИЛЬНАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ КЛИКА И СВОБОДНОГО ДВИЖЕНИЯ ---
                def on_click(event):
                    self.selected_point_idx = None
                    click_x, click_y = event.x, event.y
                    # Считаем расстояние до каждого маркера на холсте
                    for i, (mx, my) in enumerate(self.canvas_corners):
                        if np.sqrt((click_x - mx)**2 + (click_y - my)**2) < 25: 
                            self.selected_point_idx = i
                            break

                def on_drag(event):
                    if self.selected_point_idx is not None:
                        nx = max(0, min(event.x, self.c_width))
                        ny = max(0, min(event.y, self.c_height))
                        
                        # Сохраняем новые оригинальные координаты
                        self.manual_corners[self.selected_point_idx] = [
                            int(nx / self.display_scale), 
                            int(ny / self.display_scale)
                        ]
                        # Стираем и рисуем заново на холсте
                        redraw_canvas_nodes()

                # Привязываем события
                self.canvas.bind("<Button-1>", on_click)
                self.canvas.bind("<B1-Motion>", on_drag)
                self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, 'selected_point_idx', None))
                
                # Отрисовываем маркеры первый раз с микрозадержкой для стабильности в Windows
                self.canvas.after(50, redraw_canvas_nodes)

        render_table_rows()
        draw_view_or_edit_mode()

        def toggle_mode_action():
            if not self.edit_mode:
                self.edit_mode = True
                if self.mode_btn_ref:
                    self.mode_btn_ref.configure(text="✅ Применить углы", fg_color="#2E8B57", hover_color="#246B43")
                draw_view_or_edit_mode()
            else:
                self.edit_mode = False
                if self.mode_btn_ref:
                    self.mode_btn_ref.configure(text="🔧 Режим разметки углов", fg_color="gray25", hover_color="gray30")
                
                self.analyze_scanned_image(str(self.image_to_analyze))
                render_table_rows()
                draw_view_or_edit_mode()

        mode_btn = ctk.CTkButton(right_frame, text="🔧 Режим разметки углов", fg_color="gray25", hover_color="gray30", command=toggle_mode_action)
        mode_btn.pack(pady=5, fill="x", padx=5)
        self.mode_btn_ref = mode_btn

        def close_and_sync():
            if hasattr(parent_window, "metric_bars") and self.key in parent_window.metric_bars:
                gui_elements = parent_window.metric_bars[self.key]
                gui_elements["label"].configure(text=f"{self.last_mean_de:.2f}")
                gui_elements["bar"].set(min(self.last_mean_de / 10.0, 1.0))
            modal.destroy()

        ctk.CTkButton(right_frame, text="Готово", command=close_and_sync).pack(pady=10, fill="x", padx=5)
