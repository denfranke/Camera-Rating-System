#!/usr/bin/env python3
"""
Генератор ступенчатого перехода от чёрного к белому.
Создаёт последовательность равномерных серых полос.
"""

import argparse
from PIL import Image

def create_stepped_gradient(width, height, steps, vertical=False):
    """
    Args:
        width: ширина изображения
        height: высота изображения
        steps: количество ступеней (от 2 до 256, например)
        vertical: если True, полосы вертикальные, иначе горизонтальные
    Returns:
        PIL.Image (L mode)
    """
    # Вычисляем уровни яркости (от 0 до 255)
    levels = [int(round(i * 255 / (steps - 1))) for i in range(steps)]
    
    img = Image.new('L', (width, height))
    
    if vertical:
        # Каждая полоса занимает равную часть ширины
        strip_w = width // steps
        for i, level in enumerate(levels):
            x0 = i * strip_w
            # последняя полоса до правого края
            x1 = x0 + strip_w if i < steps - 1 else width
            img.paste(level, (x0, 0, x1, height))
    else:
        # Горизонтальные полосы: каждая занимает равную часть высоты
        strip_h = height // steps
        for i, level in enumerate(levels):
            y0 = i * strip_h
            y1 = y0 + strip_h if i < steps - 1 else height
            img.paste(level, (0, y0, width, y1))
    
    return img

def main():
    parser = argparse.ArgumentParser(
        description='Создаёт изображение с равномерными ступенями серого',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # 10 горизонтальных полос, Full HD
  python gen_steps.py 1920 1080 --steps 10 -o steps10.png

  # 32 вертикальные полосы
  python gen_steps.py 1280 720 --steps 32 --vertical -o steps32_vert.png
        """
    )
    parser.add_argument('width', type=int, help='Ширина изображения')
    parser.add_argument('height', type=int, help='Высота изображения')
    parser.add_argument('--steps', type=int, required=True, help='Количество ступеней (полос)')
    parser.add_argument('--vertical', action='store_true', help='Вертикальные полосы (по умолчанию горизонтальные)')
    parser.add_argument('-o', '--output', default='stepped_gradient.png', help='Выходной файл')
    args = parser.parse_args()

    img = create_stepped_gradient(args.width, args.height, args.steps, args.vertical)
    img.save(args.output)
    orient = 'вертикальные' if args.vertical else 'горизонтальные'
    print(f"✅ Создано изображение {args.width}x{args.height} с {args.steps} ступенями ({orient} полосы): {args.output}")

if __name__ == '__main__':
    main()