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
        """Анализ RAW изображений"""
        try:
            with rawpy.imread(file_path) as raw:
                # Получаем сырые данные
                raw_array = raw.raw_image_visible.astype(np.float32)
                
                # Основная информация
                file_size = os.path.getsize(file_path)
                height, width = raw_array.shape
                
                # Получаем уровни черного и белого
                black_level = getattr(raw, 'black_level_per_channel', [0])[0]
                white_level = getattr(raw, 'white_level', 16383)
                
                # RAW-специфичные метрики
                dynamic_range = self._calculate_raw_dynamic_range(raw_array, black_level, white_level)
                noise = self._calculate_raw_noise(raw_array, white_level)
                sharpness = self._calculate_raw_sharpness(raw_array)
                
                # Извлекаем метаданные камеры
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
                    exposure_time = getattr(raw.metadata, 'shutter', None)
                    aperture = getattr(raw.metadata, 'aperture', None)
                    focal_length = getattr(raw.metadata, 'focal_length', None)
                
                # Получаем JPEG preview для дополнительного анализа
                try:
                    preview = raw.postprocess(use_camera_wb=True)
                    preview_pixels = np.array(preview).astype(np.float32)
                    brightness = self._calculate_brightness(preview_pixels)
                    saturation = self._calculate_saturation(preview_pixels)
                    exposure_score = self._calculate_exposure_score(preview_pixels)
                    avg_r, avg_g, avg_b = self._get_color_averages(preview_pixels)
                except:
                    brightness = 0.5
                    saturation = 0.5
                    exposure_score = 0.5
                    avg_r, avg_g, avg_b = 0.33, 0.33, 0.33
                
                overall_score = self._calculate_overall_score({
                    'sharpness': sharpness,
                    'noise': noise,
                    'brightness': brightness,
                    'saturation': saturation,
                    'dynamic_range': dynamic_range,
                    'exposure_score': exposure_score
                })
                
                return {
                    'file_path': file_path,
                    'filename': os.path.basename(file_path),
                    'file_size': file_size,
                    'image_width': width,
                    'image_height': height,
                    'sharpness_score': round(sharpness, 2),
                    'noise_level': round(noise, 2),
                    'brightness': round(brightness, 2),
                    'contrast': 0.5,
                    'saturation': round(saturation, 2),
                    'dynamic_range': round(dynamic_range, 2),
                    'avg_red': round(avg_r, 2),
                    'avg_green': round(avg_g, 2),
                    'avg_blue': round(avg_b, 2),
                    'exposure_score': round(exposure_score, 2),
                    'composition_score': 0.5,
                    'overall_score': round(overall_score, 2),
                    'camera_make': camera_make,
                    'camera_model': camera_model,
                    'iso': iso,
                    'exposure_time': str(exposure_time) if exposure_time else None,
                    'aperture': aperture,
                    'focal_length': focal_length
                }
        except Exception as e:
            # Если RAW не удалось обработать, пробуем как обычное изображение
            print(f"  ⚠️ RAW обработка не удалась: {e}")
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
            normalized = min(100, sharpness / 100)
            
            return max(0, normalized)
        except Exception:
            return 0.0
    
    def _calculate_noise(self, pixels: np.ndarray) -> float:
        """Вычисляет уровень шума"""
        try:
            if len(pixels.shape) == 3:
                gray = np.mean(pixels, axis=2)
            else:
                gray = pixels
            
            if gray.size == 0:
                return 0.0
            
            # Упрощенная оценка шума через стандартное отклонение
            noise_level = np.std(gray) / 255.0 * 100
            
            return min(100, max(0, noise_level))
        except Exception:
            return 0.0
    
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
        """Вычисляет динамический диапазон (в EV)"""
        try:
            if len(pixels.shape) == 3:
                gray = np.mean(pixels, axis=2)
            else:
                gray = pixels
            
            if gray.size == 0:
                return 0.0
            
            p99 = np.percentile(gray, 99)
            p1 = np.percentile(gray, 1)
            
            if p1 > 0:
                dr = np.log2(p99 / p1)
            else:
                dr = 0
            
            return min(12, max(0, dr))
        except Exception:
            return 0.0
    
    def _calculate_raw_dynamic_range(self, raw_array: np.ndarray, black_level: int, white_level: int) -> float:
        """Вычисляет динамический диапазон для RAW"""
        try:
            dark_pixels = raw_array[raw_array <= np.percentile(raw_array, 10)]
            noise_std = np.std(dark_pixels) if len(dark_pixels) > 0 else 1.0
            
            max_signal = np.percentile(raw_array, 99) - black_level
            
            if noise_std > 0 and max_signal > 0:
                dr = np.log2(max_signal / noise_std)
                return min(16, max(0, dr))
            
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_raw_noise(self, raw_array: np.ndarray, white_level: int) -> float:
        """Вычисляет уровень шума для RAW"""
        try:
            shadow_pixels = raw_array[raw_array <= np.percentile(raw_array, 10)]
            if len(shadow_pixels) > 0:
                noise_std = np.std(shadow_pixels)
                normalized = (noise_std / white_level) * 100
                return min(100, max(0, normalized))
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_raw_sharpness(self, raw_array: np.ndarray) -> float:
        """Вычисляет резкость для RAW"""
        try:
            h, w = raw_array.shape
            if h < 200 or w < 200:
                return 0.0
            
            cy, cx = h // 2, w // 2
            crop = raw_array[cy-100:cy+100, cx-100:cx+100]
            
            grad_x = np.diff(crop, axis=1)
            grad_y = np.diff(crop, axis=0)
            
            sharpness = (np.var(grad_x) + np.var(grad_y)) / 2
            normalized = min(100, sharpness / 10000)
            
            return max(0, normalized)
        except Exception:
            return 0.0
    
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
        """Вычисляет общую оценку на основе всех метрик"""
        try:
            weights = {
                'sharpness': 0.25,
                'noise': 0.15,
                'brightness': 0.10,
                'contrast': 0.10,
                'saturation': 0.10,
                'dynamic_range': 0.20,
                'exposure_score': 0.10
            }
            
            total = 0
            for metric, weight in weights.items():
                if metric in metrics:
                    if metric == 'noise':
                        # Шум: чем меньше, тем лучше
                        value = max(0, 100 - metrics[metric]) / 100
                    else:
                        value = min(1.0, max(0.0, metrics[metric]))
                    total += value * weight
            
            return total * 100
        except Exception:
            return 0.0
    
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