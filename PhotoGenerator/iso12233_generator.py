import numpy as np
from PIL import Image, ImageDraw
import math
import argparse
import sys

def generate_iso_12233_pattern(width, height, rows, cols, angle=5, 
                               bg_color=128, square_color=76, 
                               square_scale=0.5, show_grid=True, 
                               output_path="iso_12233_pattern.png"):
    """
    Генерирует изображение с квадратами под углом по стандарту ISO 12233
    
    Args:
        width: ширина изображения
        height: высота изображения
        rows: количество строк квадратов
        cols: количество столбцов квадратов
        angle: угол поворота квадратов в градусах
        bg_color: цвет фона (0-255)
        square_color: цвет квадратов (0-255)
        square_scale: масштаб квадратов (0.1-1.0, где 1.0 - максимальный размер)
        show_grid: показывать ли фоновую сетку (линии)
        output_path: путь для сохранения изображения
    """
    # Создаём фон
    img = Image.new('L', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Вычисляем размер квадрата
    available_width = width - 40
    available_height = height - 40
    
    max_square_size = min(available_width // cols, available_height // rows)
    square_size = int(max_square_size * square_scale)
    
    # Отступы для равномерного распределения
    spacing_x = (available_width - square_size * cols) // (cols + 1)
    spacing_y = (available_height - square_size * rows) // (rows + 1)
    margin_x = spacing_x + 20
    margin_y = spacing_y + 20
    
    def draw_rotated_square(draw_obj, center, size, angle_deg, color):
        """Рисует повёрнутый квадрат"""
        half_size = size / 2
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        corners = [
            (-half_size, -half_size),
            (half_size, -half_size),
            (half_size, half_size),
            (-half_size, half_size)
        ]
        
        rotated_corners = []
        for x, y in corners:
            x_rot = x * cos_a - y * sin_a
            y_rot = x * sin_a + y * cos_a
            rotated_corners.append((center[0] + x_rot, center[1] + y_rot))
        
        draw_obj.polygon(rotated_corners, fill=color)
    
    # Рисуем сетку квадратов
    total_squares = 0
    for row in range(rows):
        for col in range(cols):
            center_x = margin_x + col * (square_size + spacing_x) + square_size // 2
            center_y = margin_y + row * (square_size + spacing_y) + square_size // 2
            
            if (center_x - square_size//2 > 0 and center_x + square_size//2 < width and
                center_y - square_size//2 > 0 and center_y + square_size//2 < height):
                draw_rotated_square(draw, (center_x, center_y), square_size, angle, square_color)
                total_squares += 1
    
    # Добавляем тестовые элементы ISO 12233 (только если включена сетка)
    if show_grid:
        # Тонкие линии для проверки разрешения
        line_spacing = max(20, min(width, height) // 40)
        light_gray = 180
        for x in range(line_spacing, width, line_spacing):
            draw.line([(x, 0), (x, height)], fill=light_gray, width=1)
        for y in range(line_spacing, height, line_spacing):
            draw.line([(0, y), (width, y)], fill=light_gray, width=1)
    
    # Рамка (всегда добавляется)
    border_width = max(2, min(width, height) // 500)
    draw.rectangle([(0, 0), (width-1, height-1)], outline=0, width=border_width)
    
    # Центральный крест (всегда добавляется)
    cross_size = min(width, height) // 15
    center_x, center_y = width // 2, height // 2
    draw.line([(center_x - cross_size, center_y), (center_x + cross_size, center_y)], fill=0, width=2)
    draw.line([(center_x, center_y - cross_size), (center_x, center_y + cross_size)], fill=0, width=2)
    
    # Мишени в углах (всегда добавляются)
    target_radius = min(width, height) // 25
    corner_offset = border_width * 3
    corners = [(corner_offset, corner_offset), 
               (width - corner_offset, corner_offset),
               (corner_offset, height - corner_offset),
               (width - corner_offset, height - corner_offset)]
    
    for corner_x, corner_y in corners:
        for r in [target_radius, target_radius//2, target_radius//4]:
            if r >= 2:
                draw.ellipse([(corner_x - r, corner_y - r), (corner_x + r, corner_y + r)], outline=0, width=1)
        draw.ellipse([(corner_x - 2, corner_y - 2), (corner_x + 2, corner_y + 2)], fill=0)
    
    # Сохраняем изображение
    img.save(output_path)
    print(f"✓ Изображение сохранено: {output_path}")
    print(f"  Размер: {width}x{height}")
    print(f"  Сетка квадратов: {rows}x{cols} = {total_squares} квадратов")
    print(f"  Размер квадрата: {square_size}px (масштаб: {square_scale:.0%})")
    print(f"  Угол поворота: {angle}°")
    print(f"  Цвет фона: {bg_color}, Цвет квадратов: {square_color}")
    print(f"  Фоновая сетка: {'включена' if show_grid else 'выключена'}")
    
    return img

def main():
    parser = argparse.ArgumentParser(
        description='Генерация тестового изображения ISO 12233 с сеткой темно-серых квадратов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Стандартная генерация с фоновой сеткой
  python generate_iso.py 1920 1080
  
  # Без фоновой сетки (только квадраты, рамка, крест и мишени)
  python generate_iso.py 1920 1080 --no-grid
  
  # Квадратное изображение без сетки
  python generate_iso.py 1024 --no-grid
  
  # С настройкой количества квадратов и без сетки
  python generate_iso.py 1920 1080 -r 20 -c 30 -s 0.4 --no-grid
  
  # Полный контроль всех параметров
  python generate_iso.py 1920 1080 -r 15 -c 20 -a 10 -s 0.6 --no-grid -o test.png

Цветовая схема:
  - Фон: серый (128, 128, 128)
  - Квадраты: темно-серый (76, 76, 76)
  - Рамка, крест и мишени: чёрный (0, 0, 0)
  - Фоновая сетка (если включена): светло-серый (180, 180, 180)
        """
    )
    
    parser.add_argument('width', type=int, help='Ширина изображения')
    parser.add_argument('height', type=int, nargs='?', default=None, 
                       help='Высота изображения (если не указана, будет равна ширине)')
    parser.add_argument('-r', '--rows', type=int, default=12, 
                       help='Количество строк квадратов (по умолчанию: 12)')
    parser.add_argument('-c', '--cols', type=int, default=16, 
                       help='Количество столбцов квадратов (по умолчанию: 16)')
    parser.add_argument('-a', '--angle', type=float, default=5, 
                       help='Угол поворота квадратов в градусах (по умолчанию: 5)')
    parser.add_argument('-s', '--scale', type=float, default=0.5, 
                       help='Масштаб квадратов 0.1-1.0 (по умолчанию: 0.5)')
    parser.add_argument('--no-grid', action='store_true', 
                       help='Отключить фоновую сетку (линии)')
    parser.add_argument('-o', '--output', type=str, default='iso_12233_pattern.png',
                       help='Путь для сохранения изображения (по умолчанию: iso_12233_pattern.png)')
    
    args = parser.parse_args()
    
    if args.height is None:
        height = args.width
        width = args.width
    else:
        width = args.width
        height = args.height
    
    if width <= 0 or height <= 0:
        print("Ошибка: Размеры изображения должны быть положительными числами")
        sys.exit(1)
    
    # Показываем предупреждение если сетка отключена и масштаб очень маленький
    if args.no_grid and args.scale < 0.3:
        print("Предупреждение: Квадраты очень маленькие и фоновая сетка отключена. Квадраты могут быть плохо видны.")
    
    try:
        generate_iso_12233_pattern(
            width=width,
            height=height,
            rows=args.rows,
            cols=args.cols,
            angle=args.angle,
            bg_color=128,
            square_color=76,
            square_scale=args.scale,
            show_grid=not args.no_grid,  # Инвертируем, так как --no-grid отключает сетку
            output_path=args.output
        )
    except Exception as e:
        print(f"Ошибка при генерации изображения: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()