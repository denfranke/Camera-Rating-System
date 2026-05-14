"""
analyzer.py - Анализ качества изображений
"""

import os
import numpy as np
from PIL import Image, ImageStat
from typing import Dict, Any, Tuple, Optional

# Пробуем импортировать rawpy, если он установлен
try:
    import rawpy
    RAWPY_AVAILABLE = True
except ImportError:
    RAWPY_AVAILABLE = False
    print("⚠️ rawpy не установлен. RAW файлы будут обрабатываться как обычные изображения.")


class ImageAnalyzer:
    """Класс для анализа качества изображений"""
    
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.dng', '.cr2', '.nef', '.arw'}
    
    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Полный анализ изображения
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с метриками качества
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        # Определяем тип файла
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in {'.dng', '.cr2', '.nef', '.arw'} and RAWPY_AVAILABLE:
            return self._analyze_raw(file_path)
        else:
            return self._analyze_raster(file_path)
    
    def _analyze_raster(self, file_path: str) -> Dict[str, Any]:
        """Анализ растровых изображений (JPEG, PNG и т.д.)"""
        try:
            img = Image.open(file_path)
        except Exception as e:
            raise Exception(f"Не удалось открыть изображение: {e}")
        
        # Основная информация
        width, height = img.size
        file_size = os.path.getsize(file_path)
        
        # Конвертируем в RGB для анализа
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Получаем данные пикселей
        pixels = np.array(img).astype(np.float32)
        
        # Основные метрики
        sharpness = self._calculate_sharpness(pixels)
        noise = self._calculate_noise(pixels)
        brightness = self._calculate_brightness(pixels)
        contrast = self._calculate_contrast(pixels)
        saturation = self._calculate_saturation(pixels)
        dynamic_range = self._calculate_dynamic_range(pixels)
        
        # Цветовые каналы
        avg_r, avg_g, avg_b = self._get_color_averages(pixels)
        
        # Экспозиция
        exposure_score = self._calculate_exposure_score(pixels)
        
        # Композиция (простая оценка)
        composition_score = self._calculate_composition_score(pixels)
        
        # Общая оценка
        overall_score = self._calculate_overall_score({
            'sharpness': sharpness,
            'noise': noise,
            'brightness': brightness,
            'contrast': contrast,
            'saturation': saturation,
            'dynamic_range': dynamic_range,
            'exposure_score': exposure_score
        })
        
        # Извлекаем EXIF данные
        exif_data = self._extract_exif(img)
        
        return {
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'file_size': file_size,
            'image_width': width,
            'image_height': height,
            'sharpness_score': round(sharpness, 2),
            'noise_level': round(noise, 2),
            'brightness': round(brightness, 2),
            'contrast': round(contrast, 2),
            'saturation': round(saturation, 2),
            'dynamic_range': round(dynamic_range, 2),
            'avg_red': round(avg_r, 2),
            'avg_green': round(avg_g, 2),
            'avg_blue': round(avg_b, 2),
            'exposure_score': round(exposure_score, 2),
            'composition_score': round(composition_score, 2),
            'overall_score': round(overall_score, 2),
            **exif_data
        }
    
    def _analyze_raw(self, file_path: str) -> Dict[str, Any]:
        """Анализ RAW изображений с использованием сырых байер-данных"""
        try:
            with rawpy.imread(file_path) as raw:
                # ============================================
                # 1. Анализ сырых байер-данных (до демозаики)
                # ============================================
                raw_array = raw.raw_image_visible.astype(np.float32)
                
                # Получаем уровни черного и белого
                black_level = getattr(raw, 'black_level_per_channel', [0])[0]
                white_level = getattr(raw, 'white_level', 16383)
                
                # Метрики из сырых данных
                raw_sharpness = self._calculate_raw_sharpness(raw_array)
                raw_noise = self._calculate_raw_noise(raw_array, white_level)
                raw_dynamic_range = self._calculate_raw_dynamic_range(raw_array, black_level, white_level)
                
                # ============================================
                # 2. Получение RGB preview для цветовых метрик
                # ============================================
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    output_color=rawpy.ColorSpace.sRGB,
                    gamma=(2.222, 4.5),
                    no_auto_bright=False,
                    auto_bright_thr=0.01
                )
                
                preview_pixels = np.array(rgb).astype(np.float32)
                height, width = preview_pixels.shape[:2]
                
                # Цветовые метрики (только из RGB)
                brightness = self._calculate_brightness(preview_pixels)
                contrast = self._calculate_contrast(preview_pixels)
                saturation = self._calculate_saturation(preview_pixels)
                exposure_score = self._calculate_exposure_score(preview_pixels)
                composition_score = self._calculate_composition_score(preview_pixels)
                avg_r, avg_g, avg_b = self._get_color_averages(preview_pixels)
                
                # ============================================
                # 3. Общая оценка (комбинируем метрики)
                # ============================================
                overall_score = self._calculate_overall_score_raw({
                    'sharpness': raw_sharpness,
                    'noise': raw_noise,
                    'dynamic_range': raw_dynamic_range,
                    'brightness': brightness,
                    'contrast': contrast,
                    'saturation': saturation,
                    'exposure_score': exposure_score
                })
                
                # print(f"  [DEBUG RAW] sharpness={raw_sharpness:.1f}, noise={raw_noise:.1f}, dr={raw_dynamic_range:.1f}EV")
                
                # ============================================
                # 4. Метаданные камеры
                # ============================================
                file_size = os.path.getsize(file_path)
                
                camera_make = None
                camera_model = None
                iso = None
                exposure_time = None
                aperture = None
                focal_length = None
                
                if hasattr(raw, 'metadata') and raw.metadata:
                    camera_make = getattr(raw.metadata, 'make', None)
                    camera_model = getattr(raw.metadata, 'model', None)
                    iso = getattr(raw.metadata, 'iso_speed', None)
                    
                    shutter = getattr(raw.metadata, 'shutter', None)
                    if shutter:
                        if shutter < 1:
                            exposure_time = f"1/{int(1/shutter)}"
                        else:
                            exposure_time = f"{shutter}"
                    
                    aperture = getattr(raw.metadata, 'aperture', None)
                    focal_length = getattr(raw.metadata, 'focal_length', None)
                
                # ============================================
                # 5. Формирование результата
                # ============================================
                result = {
                    'file_path': file_path,
                    'filename': os.path.basename(file_path),
                    'file_size': file_size,
                    'image_width': width,
                    'image_height': height,
                    'sharpness_score': float(round(raw_sharpness, 2)),
                    'noise_level': float(round(raw_noise, 2)),
                    'brightness': float(round(brightness, 2)),
                    'contrast': float(round(contrast, 2)),
                    'saturation': float(round(saturation, 2)),
                    'dynamic_range': float(round(raw_dynamic_range, 2)),
                    'avg_red': float(round(avg_r, 2)),
                    'avg_green': float(round(avg_g, 2)),
                    'avg_blue': float(round(avg_b, 2)),
                    'exposure_score': float(round(exposure_score, 2)),
                    'composition_score': float(round(composition_score, 2)),
                    'overall_score': float(round(overall_score, 2)),
                    'camera_make': camera_make,
                    'camera_model': camera_model,
                    'iso': iso,
                    'exposure_time': exposure_time,
                    'aperture': round(aperture, 1) if aperture else None,
                    'focal_length': round(focal_length, 1) if focal_length else None
                }
                
                return result
                        
        except Exception as e:
            print(f"  ⚠️ RAW обработка не удалась: {e}")
            import traceback
            traceback.print_exc()
            print(f"  🔄 Пробуем обработать как обычное изображение...")
            return self._analyze_raster(file_path)
    
    def _calculate_sharpness(self, pixels: np.ndarray) -> float:
        """Вычисляет резкость"""
        try:
            if len(pixels.shape) == 3:
                gray = np.mean(pixels, axis=2)
            else:
                gray = pixels
            
            if gray.shape[0] < 3 or gray.shape[1] < 3:
                return 0.0
            
            # Градиенты по X и Y
            grad_x = np.diff(gray, axis=1)
            grad_y = np.diff(gray, axis=0)
            
            if grad_x.size == 0 or grad_y.size == 0:
                return 0.0
            
            # Дисперсия градиентов как мера резкости
            sharpness = (np.var(grad_x) + np.var(grad_y)) / 2
            
            # Нормализуем в диапазон 0-100
            normalized = min(100, sharpness / 10)
            
            return max(0, normalized)
        except Exception:
            return 0.0
    
    def _calculate_noise(self, pixels: np.ndarray) -> float:
        """Вычисляет уровень шума с учётом яркости"""
        if len(pixels.shape) == 3:
            gray = np.mean(pixels, axis=2)
        else:
            gray = pixels
        
        mean_val = np.mean(gray)
        std_val = np.std(gray)
        
        if mean_val > 0:
            # Коэффициент вариации (относительный шум)
            cv = std_val / mean_val  # Coefficient of Variation
            
            # При низкой яркости корректируем оценку
            brightness_factor = min(1.0, mean_val / 128.0)  # mean_val 0-255
            if brightness_factor < 0.3:  # Фото тёмное
                # Шум кажется выше из-за темноты, корректируем
                adjusted_cv = cv * (1 + (0.3 - brightness_factor))
            else:
                adjusted_cv = cv
            
            # Преобразуем в оценку 0-100 (чем меньше шум, тем выше оценка)
            # Для хорошего фото cv ~ 0.05-0.15
            noise_score = max(0, min(100, 100 - (adjusted_cv * 200)))
            
            # Доп. корректировка: даже в темноте шум не может быть 100%
            if mean_val < 30:  # Очень тёмное фото
                noise_score = min(noise_score, 70)
            
            return noise_score
        
        return 50.0  # Значение по умолчанию
    
    def _calculate_brightness(self, pixels: np.ndarray) -> float:
        """Вычисляет среднюю яркость (0-1)"""
        try:
            if len(pixels.shape) == 3:
                brightness = np.mean(pixels) / 255.0
            else:
                brightness = np.mean(pixels) / 255.0
            
            return min(1.0, max(0.0, brightness))
        except Exception:
            return 0.5
    
    def _calculate_contrast(self, pixels: np.ndarray) -> float:
        """Вычисляет контраст"""
        try:
            if len(pixels.shape) == 3:
                gray = np.mean(pixels, axis=2)
            else:
                gray = pixels
            
            if gray.size == 0:
                return 0.0
            
            contrast = np.std(gray) / 255.0
            
            return min(1.0, max(0.0, contrast))
        except Exception:
            return 0.5
    
    def _calculate_saturation(self, pixels: np.ndarray) -> float:
        """Вычисляет насыщенность"""
        try:
            if len(pixels.shape) != 3:
                return 0.0
            
            pixels_norm = pixels / 255.0
            max_rgb = np.max(pixels_norm, axis=2)
            min_rgb = np.min(pixels_norm, axis=2)
            
            saturation = np.mean((max_rgb - min_rgb) / (max_rgb + 1e-6))
            
            return min(1.0, max(0.0, saturation))
        except Exception:
            return 0.5
    
    def _calculate_dynamic_range(self, pixels: np.ndarray) -> float:
        """Вычисляет динамический диапазон с компенсацией экспозиции"""
        try:
            if len(pixels.shape) == 3:
                gray = np.mean(pixels, axis=2)
            else:
                gray = pixels
            
            gray_norm = gray / 255.0
            
            # Оценка яркости фото
            mean_brightness = np.mean(gray_norm)
            
            # Расширяем гистограмму для корректного расчёта
            p99 = np.percentile(gray_norm, 99)
            p5 = np.percentile(gray_norm, 5)
            
            # Корректируем очень тёмные изображения
            if p99 < 0.3 or mean_brightness < 0.2:  # Фото слишком тёмное
                # Компенсируем экспозицию для оценки ДР
                target_brightness = 0.5
                exposure_correction = target_brightness / (mean_brightness + 0.01)
                exposure_correction = min(exposure_correction, 4.0)  # Не более 4 стопов
                
                gray_corrected = np.clip(gray_norm * exposure_correction, 0, 1)
                p99 = np.percentile(gray_corrected, 99)
                p5 = np.percentile(gray_corrected, 5)
            
            # Защита от вырожденных случаев
            if p5 < 0.001:
                p5 = 0.001
            
            dr = np.log2(p99 / p5)
            
            # Ограничиваем реалистичными значениями
            if mean_brightness < 0.15:
                # Для очень тёмных фото даём базовую оценку ДР камеры
                return min(12, max(8, dr))
            
            return min(14, max(4, dr))
            
        except Exception:
            return 8.0
    
    def _calculate_raw_dynamic_range(self, raw_array: np.ndarray, black_level: int, white_level: int) -> float:
        """Вычисляет динамический диапазон из сырых байер-данных"""
        try:
            # Применяем чёрный уровень
            raw_centered = raw_array - black_level
            raw_centered = np.maximum(raw_centered, 0)
            
            # Анализируем теневую область (нижние 10% от максимального)
            max_val = np.percentile(raw_centered, 99)
            threshold = max_val * 0.1
            dark_pixels = raw_centered[raw_centered <= threshold]
            
            if len(dark_pixels) < 100:
                dark_pixels = raw_centered[raw_centered <= np.percentile(raw_centered, 5)]
            
            noise_std = np.std(dark_pixels) if len(dark_pixels) > 0 else 1.0
            
            # Максимальный сигнал (99-й перцентиль)
            max_signal = np.percentile(raw_centered, 99)
            
            if noise_std > 0 and max_signal > 0:
                dr = np.log2(max_signal / noise_std)
                return min(16, max(4, dr))
            
            return 8.0
        except Exception:
            return 8.0
    
    def _calculate_raw_noise(self, raw_array: np.ndarray, white_level: int) -> float:
        """Вычисляет уровень шума из сырых байер-данных"""
        try:
            # Анализируем теневую область
            shadow_threshold = np.percentile(raw_array, 10)
            shadow_pixels = raw_array[raw_array <= shadow_threshold]
            
            if len(shadow_pixels) > 0:
                noise_std = np.std(shadow_pixels)
                # Нормализуем в процентах относительно белого уровня
                normalized = (noise_std / white_level) * 100
                # Шум в RAW обычно 0.5-5%, нормализуем в шкалу 0-100
                # где 0% шума = 0, 5% шума = 50, 10%+ шума = 100
                noise_score = min(100, normalized * 10)
                return max(0, noise_score)
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_raw_sharpness(self, raw_array: np.ndarray) -> float:
        """Вычисляет резкость из сырых байер-данных"""
        try:
            h, w = raw_array.shape
            if h < 200 or w < 200:
                return 50.0  # Значение по умолчанию
            
            # Берем центральную область и нормализуем
            cy, cx = h // 2, w // 2
            crop = raw_array[cy-100:cy+100, cx-100:cx+100]
            
            # Нормализуем яркость для корректного расчёта градиентов
            crop_norm = (crop - np.min(crop)) / (np.max(crop) - np.min(crop) + 1e-6)
            
            # Градиенты
            grad_x = np.diff(crop_norm, axis=1)
            grad_y = np.diff(crop_norm, axis=0)
            
            if grad_x.size == 0 or grad_y.size == 0:
                return 50.0
            
            # Дисперсия градиентов
            sharpness = (np.var(grad_x) + np.var(grad_y)) / 2
            
            # Нормализация: типичные значения 0.001-0.01 для нормальных фото
            normalized = min(100, sharpness * 5000)
            
            return max(0, normalized)
        except Exception:
            return 50.0
    
    def _get_color_averages(self, pixels: np.ndarray) -> Tuple[float, float, float]:
        """Получает средние значения цветовых каналов"""
        try:
            if len(pixels.shape) != 3:
                return 0.33, 0.33, 0.33
            
            r = np.mean(pixels[:, :, 0]) / 255.0
            g = np.mean(pixels[:, :, 1]) / 255.0
            b = np.mean(pixels[:, :, 2]) / 255.0
            
            total = r + g + b
            if total > 0:
                return r/total, g/total, b/total
            return 0.33, 0.33, 0.33
        except Exception:
            return 0.33, 0.33, 0.33
    
    def _calculate_exposure_score(self, pixels: np.ndarray) -> float:
        """Оценивает правильность экспозиции"""
        try:
            if len(pixels.shape) == 3:
                gray = np.mean(pixels, axis=2)
            else:
                gray = pixels
            
            if gray.size == 0:
                return 0.5
            
            hist, _ = np.histogram(gray, bins=256, range=(0, 255))
            total = np.sum(hist)
            
            if total == 0:
                return 0.5
            
            overexposed = np.sum(hist[245:]) / total
            underexposed = np.sum(hist[:10]) / total
            
            score = 1.0 - (overexposed + underexposed * 2)
            
            return max(0, min(1, score))
        except Exception:
            return 0.5
    
    def _calculate_composition_score(self, pixels: np.ndarray) -> float:
        """Простая оценка композиции"""
        try:
            h, w = pixels.shape[:2] if len(pixels.shape) > 2 else pixels.shape
            
            if h < 3 or w < 3:
                return 0.5
            
            h_step, w_step = h // 3, w // 3
            
            if h_step == 0 or w_step == 0:
                return 0.5
            
            center_zone = pixels[h_step:2*h_step, w_step:2*w_step]
            
            if len(center_zone.shape) == 3:
                center_interest = np.std(center_zone)
            else:
                center_interest = np.std(center_zone)
            
            score = min(1.0, center_interest / 50)
            
            return max(0, score)
        except Exception:
            return 0.5
    
    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """Исправленная общая оценка с учётом недоэкспозиции"""
        try:
            weights = {
                'sharpness': 0.30,
                'noise': 0.20,
                'dynamic_range': 0.25,
                'brightness': 0.10,
                'saturation': 0.10,
                'exposure_score': 0.05
            }
            
            total = 0
            for metric, weight in weights.items():
                if metric in metrics:
                    if metric == 'noise':
                        # Шум: инвертируем
                        value = max(0, min(100, 100 - metrics[metric]))
                    elif metric == 'brightness':
                        brightness = metrics[metric] * 100
                        # Мягкая оценка яркости (не штрафуем сильно за недоэкспозицию)
                        if brightness < 20:
                            # Очень тёмное фото, но не штрафуем сильно
                            value = 50
                        elif brightness < 30:
                            value = 60
                        elif brightness < 40:
                            value = 70
                        elif 40 <= brightness <= 60:
                            value = 100
                        elif brightness <= 80:
                            value = 80
                        else:
                            value = 60
                    elif metric == 'exposure_score':
                        exp_val = metrics[metric] * 100
                        # Тёмное фото может иметь низкий exposure_score, не штрафуем сильно
                        if exp_val < 30:
                            value = 50
                        else:
                            value = exp_val
                    elif metric == 'dynamic_range':
                        # ДР уже скорректирован в _calculate_dynamic_range
                        value = metrics[metric] * 7  # Поднимаем вес ДР в оценке
                        value = min(100, value)
                    elif metric == 'saturation':
                        # Для RAW насыщенность всегда низкая, не штрафуем сильно
                        value = max(50, metrics[metric])
                    else:
                        value = metrics[metric]
                    
                    # Нормализуем в 0-100
                    value = max(0, min(100, value))
                    total += value * weight
            
            # Бонус за хорошую камеру (если есть DxOMark)
            # Этот бонус нужно добавить при вызове, передавая dxomark_score
            # Пока просто корректируем
            
            # Для очень тёмных фото поднимаем минимальную оценку
            if metrics.get('brightness', 0.5) < 0.2:
                total = max(total, 45)  # Минимум 45% для тёмных фото хорошей камеры
            
            return total
            
        except Exception:
            return 50.0
    
    def _calculate_overall_score_raw(self, metrics: Dict[str, float]) -> float:
        """Специальная общая оценка для RAW изображений"""
        try:
            weights = {
                'sharpness': 0.25,
                'noise': 0.20,
                'dynamic_range': 0.30,  # ДР важнее для RAW
                'brightness': 0.10,
                'saturation': 0.10,
                'exposure_score': 0.05
            }
            
            total = 0
            for metric, weight in weights.items():
                if metric in metrics:
                    if metric == 'noise':
                        # Шум: инвертируем (меньше шума = выше оценка)
                        value = max(0, min(100, 100 - metrics[metric]))
                    elif metric == 'brightness':
                        brightness = metrics[metric] * 100
                        if brightness < 20:
                            value = 50
                        elif brightness < 30:
                            value = 60
                        elif brightness < 40:
                            value = 70
                        elif 40 <= brightness <= 60:
                            value = 100
                        elif brightness <= 80:
                            value = 80
                        else:
                            value = 60
                    elif metric == 'exposure_score':
                        exp_val = metrics[metric] * 100
                        if exp_val < 30:
                            value = 50
                        else:
                            value = exp_val
                    elif metric == 'dynamic_range':
                        # ДР уже скорректирован в сыром виде
                        value = metrics[metric] * 7
                        value = min(100, value)
                    elif metric == 'saturation':
                        # Для RAW насыщенность всегда низкая, не штрафуем сильно
                        value = max(50, metrics[metric])
                    else:
                        value = metrics[metric]
                    
                    value = max(0, min(100, value))
                    total += value * weight
            
            # Для очень тёмных фото поднимаем минимальную оценку
            if metrics.get('brightness', 0.5) < 0.2:
                total = max(total, 45)
            
            return total
            
        except Exception:
            return 50.0

    def _extract_exif(self, img: Image.Image) -> Dict[str, Any]:
        """Извлекает EXIF данные из изображения"""
        exif_data = {
            'camera_make': None,
            'camera_model': None,
            'iso': None,
            'exposure_time': None,
            'aperture': None,
            'focal_length': None
        }
        
        try:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    if tag_id == 271:  # Make
                        exif_data['camera_make'] = str(value)
                    elif tag_id == 272:  # Model
                        exif_data['camera_model'] = str(value)
                    elif tag_id == 34855:  # ISO
                        exif_data['iso'] = int(value) if isinstance(value, (int, float)) else None
                    elif tag_id == 33434:  # Exposure Time
                        if isinstance(value, tuple) and len(value) == 2:
                            exif_data['exposure_time'] = f"{value[0]}/{value[1]}"
                        else:
                            exif_data['exposure_time'] = str(value)
                    elif tag_id == 37386:  # Focal Length
                        if isinstance(value, tuple) and len(value) == 2:
                            exif_data['focal_length'] = value[0] / value[1]
                        else:
                            exif_data['focal_length'] = float(value) if value else None
                    elif tag_id == 33437:  # Aperture
                        exif_data['aperture'] = float(value) if value else None
        except Exception:
            pass
        
        return exif_data