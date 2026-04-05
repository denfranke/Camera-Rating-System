#!/usr/bin/env python3
"""
RAW Image Quality Analyzer
Сравнение качества RAW-файлов от разных камер с эталонными показателями.
"""

import os
import sys
import json
import argparse
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict

import numpy as np
import rawpy

# Подавление предупреждений rawpy
warnings.filterwarnings("ignore", category=UserWarning)


# ============================================================================
# Конвертеры для JSON сериализации
# ============================================================================

def convert_to_serializable(obj: Any) -> Any:
    """Рекурсивно конвертирует numpy типы в стандартные Python типы для JSON."""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    return obj


# ============================================================================
# Структуры данных
# ============================================================================

@dataclass
class QualityMetrics:
    """Метрики качества для одного RAW-файла."""
    filename: str
    camera_model: str = "Unknown"
    
    # Основные метрики
    dynamic_range_ev: float = 0.0
    noise_level: float = 0.0
    noise_type: str = "unknown"
    sharpness_score: float = 0.0
    color_depth_bits: float = 0.0
    
    # Детальные метрики
    clip_ratio_percent: float = 0.0
    shadow_noise_std: float = 0.0
    highlights_clipped: float = 0.0
    iso_speed: Optional[int] = None
    bit_depth: int = 14
    
    # Raw-специфичные
    black_level: int = 0
    white_level: int = 16383
    
    # Итоговая оценка
    overall_score: float = 0.0
    verdict: str = "Not evaluated"
    
    def to_dict(self) -> Dict:
        """Конвертирует в словарь с конвертацией типов."""
        return convert_to_serializable(asdict(self))


@dataclass
class ReferenceStandards:
    """Эталонные показатели качества (Panasonic LUMIX S1II benchmark)."""
    dynamic_range_excellent: float = 12.0
    dynamic_range_good: float = 10.0
    dynamic_range_poor: float = 8.0
    noise_excellent: float = 5.0
    noise_good: float = 15.0
    noise_poor: float = 30.0
    color_depth_excellent: float = 22.0
    color_depth_good: float = 20.0
    sharpness_excellent: float = 500.0
    sharpness_good: float = 200.0
    max_clip_ratio: float = 1.0
    max_shadow_noise_pct: float = 3.0


# ============================================================================
# Анализ метаданных
# ============================================================================

def parse_camera_model(filename: str, raw_obj=None) -> str:
    """Извлечение модели камеры из метаданных или имени файла."""
    # Сначала пробуем из метаданных RAW
    if raw_obj and hasattr(raw_obj, 'metadata') and raw_obj.metadata:
        if hasattr(raw_obj.metadata, 'camera_model') and raw_obj.metadata.camera_model:
            return raw_obj.metadata.camera_model
        if hasattr(raw_obj.metadata, 'make') and hasattr(raw_obj.metadata, 'model'):
            if raw_obj.metadata.make and raw_obj.metadata.model:
                return f"{raw_obj.metadata.make} {raw_obj.metadata.model}"
    
    # Затем по имени файла
    patterns = {
        'DSC': 'Sony',
        'IMG': 'Sony',
        '_MG': 'Canon',
        'CR2': 'Canon',
        'NEF': 'Nikon',
        'ARW': 'Sony',
        'P100': 'Panasonic',
        'LUMIX': 'Panasonic',
        'DNG': 'Unknown (DNG)'
    }
    
    filename_upper = filename.upper()
    for pattern, camera in patterns.items():
        if pattern in filename_upper:
            return camera
    return "Unknown"


# ============================================================================
# Основные метрики
# ============================================================================

def compute_dynamic_range(raw_array: np.ndarray, black_level: int, white_level: int) -> float:
    """Вычисление динамического диапазона в EV."""
    dark_pixels = raw_array[raw_array <= np.percentile(raw_array, 10)]
    noise_std = np.std(dark_pixels) if len(dark_pixels) > 0 else 1.0
    max_signal = np.percentile(raw_array, 99) - black_level
    
    if noise_std <= 0 or max_signal <= 0:
        return 0.0
    
    dr_ev = np.log2(max_signal / noise_std)
    return min(float(dr_ev), 16.0)


def compute_noise_level(raw_array: np.ndarray, black_level: int, white_level: int) -> Tuple[float, str]:
    """Вычисление уровня шума и определение его типа."""
    shadow_mask = raw_array <= np.percentile(raw_array, 10)
    shadow_pixels = raw_array[shadow_mask]
    
    if len(shadow_pixels) == 0:
        return 0.0, "unknown"
    
    noise_std = np.std(shadow_pixels)
    normalized_noise = float((noise_std / white_level) * 100)
    
    # Определяем тип шума
    if normalized_noise < 5:
        noise_type = "low (чистые тени)"
    elif normalized_noise < 12:
        noise_type = "gaussian (мелкозернистый)"
    elif normalized_noise < 20:
        noise_type = "color_pattern (цветной шум)"
    else:
        noise_type = "high (сильный шум)"
    
    return normalized_noise, noise_type


def compute_sharpness_simple(raw_array: np.ndarray) -> float:
    """Простая оценка резкости через градиенты (без OpenCV)."""
    if raw_array.shape[0] < 20 or raw_array.shape[1] < 20:
        return 0.0
    
    # Берем центральную область для оценки
    h, w = raw_array.shape
    cy, cx = h // 2, w // 2
    crop_size = min(200, min(h, w) // 2)
    crop = raw_array[cy-crop_size//2:cy+crop_size//2, cx-crop_size//2:cx+crop_size//2]
    
    # Простые градиенты
    grad_x = np.diff(crop, axis=1)
    grad_y = np.diff(crop, axis=0)
    
    sharpness = (np.var(grad_x) + np.var(grad_y)) / 2
    return float(min(sharpness / 1000, 1000))


def compute_color_depth(raw_array: np.ndarray, black_level: int, white_level: int) -> float:
    """Приблизительная оценка эффективной глубины цвета."""
    dark_pixels = raw_array[raw_array <= np.percentile(raw_array, 10)]
    noise_std = np.std(dark_pixels) if len(dark_pixels) > 0 else 1.0
    
    if noise_std <= 0:
        return 0.0
    
    effective_range = (white_level - black_level) / noise_std
    effective_bits = np.log2(effective_range)
    return float(min(effective_bits, 16.0))


def detect_clipping(raw_array: np.ndarray, white_level: int) -> float:
    """Определение процента пересвеченных пикселей."""
    clipped = np.sum(raw_array >= (white_level * 0.99))
    total = raw_array.size
    return float((clipped / total) * 100)


# ============================================================================
# Основной анализатор RAW
# ============================================================================

class RAWAnalyzer:
    """Основной класс для анализа RAW-файлов."""
    
    def __init__(self, reference: Optional[ReferenceStandards] = None):
        self.reference = reference or ReferenceStandards()
    
    def analyze_file(self, filepath: str) -> QualityMetrics:
        """Полный анализ одного RAW-файла."""
        metrics = QualityMetrics(filename=os.path.basename(filepath))
        
        try:
            with rawpy.imread(filepath) as raw:
                # Получаем сырые данные (Bayer pattern)
                raw_array = raw.raw_image_visible.astype(np.float32)
                
                # Получаем уровни черного и белого
                metrics.black_level = getattr(raw, 'black_level_per_channel', [0])[0]
                metrics.white_level = getattr(raw, 'white_level', 16383)
                if metrics.white_level > 0:
                    metrics.bit_depth = int(np.log2(metrics.white_level + 1))
                
                # Определяем камеру из метаданных
                metrics.camera_model = parse_camera_model(metrics.filename, raw)
                
                # Основные метрики
                metrics.dynamic_range_ev = compute_dynamic_range(
                    raw_array, metrics.black_level, metrics.white_level
                )
                
                noise_val, noise_type = compute_noise_level(
                    raw_array, metrics.black_level, metrics.white_level
                )
                metrics.noise_level = noise_val
                metrics.noise_type = noise_type
                
                metrics.clip_ratio_percent = detect_clipping(raw_array, metrics.white_level)
                metrics.color_depth_bits = compute_color_depth(
                    raw_array, metrics.black_level, metrics.white_level
                )
                
                # ISO и другие метаданные
                if hasattr(raw, 'metadata') and raw.metadata:
                    metrics.iso_speed = getattr(raw.metadata, 'iso_speed', None)
                
                # Оценка резкости
                metrics.sharpness_score = compute_sharpness_simple(raw_array)
                
                # Вычисление общей оценки
                metrics.overall_score = self._compute_overall_score(metrics)
                metrics.verdict = self._get_verdict(metrics)
                
        except Exception as e:
            metrics.verdict = f"Error: {str(e)[:100]}"
            metrics.overall_score = 0
        
        return metrics
    
    def _compute_overall_score(self, metrics: QualityMetrics) -> float:
        """Вычисление общей оценки (0-100) на основе эталонов."""
        score = 0.0
        weights = {'dynamic_range': 0.35, 'noise': 0.30, 'sharpness': 0.20, 'color_depth': 0.15}
        
        # Оценка динамического диапазона
        dr = metrics.dynamic_range_ev
        if dr >= self.reference.dynamic_range_excellent:
            score += weights['dynamic_range'] * 100
        elif dr >= self.reference.dynamic_range_good:
            ratio = (dr - self.reference.dynamic_range_good) / (self.reference.dynamic_range_excellent - self.reference.dynamic_range_good)
            score += weights['dynamic_range'] * (50 + ratio * 50)
        elif dr >= self.reference.dynamic_range_poor:
            ratio = (dr - self.reference.dynamic_range_poor) / (self.reference.dynamic_range_good - self.reference.dynamic_range_poor)
            score += weights['dynamic_range'] * ratio * 50
        
        # Оценка шума
        noise = metrics.noise_level
        if noise <= self.reference.noise_excellent:
            score += weights['noise'] * 100
        elif noise <= self.reference.noise_good:
            ratio = 1 - (noise - self.reference.noise_excellent) / (self.reference.noise_good - self.reference.noise_excellent)
            score += weights['noise'] * (50 + ratio * 50)
        elif noise <= self.reference.noise_poor:
            ratio = 1 - (noise - self.reference.noise_good) / (self.reference.noise_poor - self.reference.noise_good)
            score += weights['noise'] * ratio * 50
        
        # Оценка резкости
        sharp = metrics.sharpness_score
        if sharp >= self.reference.sharpness_excellent:
            score += weights['sharpness'] * 100
        elif sharp >= self.reference.sharpness_good:
            ratio = (sharp - self.reference.sharpness_good) / (self.reference.sharpness_excellent - self.reference.sharpness_good)
            score += weights['sharpness'] * (50 + ratio * 50)
        else:
            ratio = sharp / self.reference.sharpness_good
            score += weights['sharpness'] * ratio * 50
        
        # Оценка цветовой глубины
        cd = metrics.color_depth_bits
        if cd >= self.reference.color_depth_excellent:
            score += weights['color_depth'] * 100
        elif cd >= self.reference.color_depth_good:
            ratio = (cd - self.reference.color_depth_good) / (self.reference.color_depth_excellent - self.reference.color_depth_good)
            score += weights['color_depth'] * (50 + ratio * 50)
        else:
            ratio = cd / self.reference.color_depth_good
            score += weights['color_depth'] * ratio * 50
        
        # Штраф за пересветы
        if metrics.clip_ratio_percent > self.reference.max_clip_ratio:
            score *= max(0, 1 - (metrics.clip_ratio_percent - self.reference.max_clip_ratio) / 100)
        
        return float(min(score, 100.0))
    
    def _get_verdict(self, metrics: QualityMetrics) -> str:
        """Формирование текстового вердикта."""
        if metrics.overall_score >= 85:
            return "Excellent: Качество соответствует эталонному уровню"
        elif metrics.overall_score >= 70:
            return "Good: Хорошее качество, незначительные отклонения от эталона"
        elif metrics.overall_score >= 50:
            return "Average: Среднее качество, заметные отличия от эталона"
        elif metrics.overall_score >= 30:
            return "Poor: Низкое качество, существенные проблемы"
        else:
            return "Bad: Критически низкое качество, анализ невозможен"


# ============================================================================
# Сравнение камер
# ============================================================================

class CameraComparator:
    """Сравнение нескольких камер по результатам анализа RAW."""
    
    def __init__(self, analyzer: RAWAnalyzer):
        self.analyzer = analyzer
        self.results: List[QualityMetrics] = []
    
    def add_file(self, filepath: str) -> QualityMetrics:
        """Добавить файл для анализа."""
        result = self.analyzer.analyze_file(filepath)
        self.results.append(result)
        return result
    
    def add_files(self, filepaths: List[str]) -> List[QualityMetrics]:
        """Добавить несколько файлов."""
        for fp in filepaths:
            self.add_file(fp)
        return self.results
    
    def compare(self) -> Dict[str, Any]:
        """Сравнение всех добавленных файлов."""
        if not self.results:
            return {"error": "No files added"}
        
        sorted_results = sorted(self.results, key=lambda x: x.overall_score, reverse=True)
        
        comparison = {
            "total_files": len(self.results),
            "best_camera": sorted_results[0].camera_model if sorted_results else None,
            "best_file": sorted_results[0].filename if sorted_results else None,
            "best_score": float(sorted_results[0].overall_score) if sorted_results else 0,
            "ranking": [],
            "summary": self._generate_summary()
        }
        
        for i, res in enumerate(sorted_results, 1):
            comparison["ranking"].append({
                "rank": i,
                "filename": res.filename,
                "camera": res.camera_model,
                "score": float(round(res.overall_score, 1)),
                "verdict": res.verdict,
                "dr_ev": float(round(res.dynamic_range_ev, 1)),
                "noise_pct": float(round(res.noise_level, 1)),
                "sharpness": int(res.sharpness_score),
                "clip_pct": float(round(res.clip_ratio_percent, 2))
            })
        
        return convert_to_serializable(comparison)
    
    def _generate_summary(self) -> str:
        """Генерация текстового резюме сравнения."""
        if not self.results:
            return "Нет данных для анализа"
        
        best = max(self.results, key=lambda x: x.overall_score)
        worst = min(self.results, key=lambda x: x.overall_score)
        avg_score = np.mean([r.overall_score for r in self.results])
        avg_dr = np.mean([r.dynamic_range_ev for r in self.results])
        
        summary = f"""
=== Резюме сравнения камер ===
Лучшая камера: {best.camera_model} ({best.filename}) - оценка {best.overall_score:.1f}/100
Худшая камера: {worst.camera_model} ({worst.filename}) - оценка {worst.overall_score:.1f}/100
Средняя оценка по всем: {avg_score:.1f}/100
Средний динамический диапазон: {avg_dr:.1f} EV

Проблемы, обнаруженные при анализе:
"""
        issues = []
        for r in self.results:
            if r.clip_ratio_percent > 3:
                issues.append(f"  - {r.camera_model}: пересветы ({r.clip_ratio_percent:.1f}% пикселей)")
            if "banding" in r.noise_type.lower():
                issues.append(f"  - {r.camera_model}: полосы (banding) в тенях")
            if r.noise_level > 20:
                issues.append(f"  - {r.camera_model}: высокий уровень шума ({r.noise_level:.1f}%)")
        
        if issues:
            summary += "\n".join(issues)
        else:
            summary += "  - Критических проблем не обнаружено\n"
        
        return summary
    
    def export_results(self, output_path: Optional[str], format: str = "json"):
        """Экспорт результатов в файл."""
        if not output_path:
            return
        
        comparison = self.compare()
        
        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
        elif format == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(comparison["summary"])
                f.write("\n\n=== Детальный рейтинг ===\n")
                for item in comparison["ranking"]:
                    f.write(f"\n{item['rank']}. {item['camera']} - {item['filename']}\n")
                    f.write(f"   Score: {item['score']}/100 | DR: {item['dr_ev']} EV | Noise: {item['noise_pct']}%\n")
                    f.write(f"   Verdict: {item['verdict']}\n")


# ============================================================================
# CLI Интерфейс
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RAW Image Quality Analyzer - Сравнение качества RAW-файлов от разных камер"
    )
    parser.add_argument(
        "files", nargs="+", 
        help="Пути к RAW-файлам для анализа (.CR2, .NEF, .ARW, .DNG и др.)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Путь для сохранения результатов (JSON или TXT)"
    )
    parser.add_argument(
        "--format", "-f", choices=["json", "txt"], default="json",
        help="Формат выходного файла"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Подробный вывод в консоль"
    )
    
    args = parser.parse_args()
    
    # Проверка существования файлов
    for filepath in args.files:
        if not os.path.exists(filepath):
            print(f"Ошибка: файл не найден - {filepath}")
            sys.exit(1)
    
    print(f"RAW Image Quality Analyzer v1.0")
    print(f"Анализируемые файлы: {len(args.files)}")
    print("-" * 50)
    
    # Создание анализатора и компаратора
    analyzer = RAWAnalyzer()
    comparator = CameraComparator(analyzer)
    
    # Анализ каждого файла
    for i, filepath in enumerate(args.files, 1):
        print(f"[{i}/{len(args.files)}] Анализ: {os.path.basename(filepath)}")
        
        try:
            result = analyzer.analyze_file(filepath)
            
            if args.verbose:
                print(f"  Камера: {result.camera_model}")
                print(f"  Динамический диапазон: {result.dynamic_range_ev:.1f} EV")
                print(f"  Уровень шума: {result.noise_level:.1f}% ({result.noise_type})")
                print(f"  Резкость: {result.sharpness_score:.0f}")
                print(f"  Пересветы: {result.clip_ratio_percent:.2f}%")
                print(f"  Цветовая глубина: {result.color_depth_bits:.1f} бит")
                if result.iso_speed:
                    print(f"  ISO: {result.iso_speed}")
                print(f"  Общая оценка: {result.overall_score:.1f}/100")
                print(f"  Вердикт: {result.verdict}")
            
            comparator.add_file(filepath)
            
        except Exception as e:
            print(f"  ОШИБКА: {str(e)}")
    
    print("-" * 50)
    
    # Сравнение и экспорт
    comparison = comparator.compare()
    
    print(f"\nРезультаты сравнения:")
    print(f"Лучшая камера: {comparison['best_camera']} (оценка {comparison['best_score']:.1f}/100)")
    print(f"Всего проанализировано: {comparison['total_files']} файлов")
    
    # Сохранение результатов
    if args.output:
        comparator.export_results(args.output, args.format)
        print(f"\nРезультаты сохранены в: {args.output}")
    
    # Вывод ранжирования
    print("\n=== Ранжирование камер ===")
    for item in comparison["ranking"]:
        print(f"{item['rank']}. {item['camera']:15} | Score: {item['score']:5.1f} | DR: {item['dr_ev']:4.1f}EV | Noise: {item['noise_pct']:5.1f}%")
        print(f"   {item['verdict'][:60]}")


if __name__ == "__main__":
    main()