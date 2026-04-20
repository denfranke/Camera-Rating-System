import argparse
import numpy as np
from PIL import Image

def create_checkerboard(width, height, square_size=50):
    """
    Создает шахматную доску (черно-белые клетки).
    
    Args:
        width (int): Ширина изображения в пикселях
        height (int): Высота изображения в пикселях
        square_size (int): Размер одной клетки в пикселях
    
    Returns:
        PIL.Image: Изображение в градациях серого (mode 'L')
    """
    # Создаем массив индексов клеток
    cols = np.arange(width) // square_size
    rows = np.arange(height) // square_size
    
    # Создаем сетку
    col_grid, row_grid = np.meshgrid(cols, rows)
    
    # Чередование черного и белого: сумма индексов четная - белый, нечетная - черный
    checkerboard = (col_grid + row_grid) % 2 == 0
    
    # Преобразуем в 8-битное изображение (255 - белый, 0 - черный)
    img_array = np.where(checkerboard, 255, 0).astype(np.uint8)
    
    return Image.fromarray(img_array, mode='L')

def create_zebra(width, height, stripe_width=20, orientation='horizontal'):
    """
    Создает зебру (чередующиеся черно-белые полосы).
    
    Args:
        width (int): Ширина изображения в пикселях
        height (int): Высота изображения в пикселях
        stripe_width (int): Ширина одной полосы в пикселях
        orientation (str): 'horizontal' или 'vertical'
    
    Returns:
        PIL.Image: Изображение в градациях серого (mode 'L')
    """
    if orientation == 'horizontal':
        # Создаем индексы для строк
        indices = np.arange(height) // stripe_width
        # Расширяем на всю ширину
        zebra = (indices % 2 == 0)
        img_array = np.where(zebra[:, np.newaxis], 255, 0).astype(np.uint8)
    else:  # vertical
        # Создаем индексы для столбцов
        indices = np.arange(width) // stripe_width
        zebra = (indices % 2 == 0)
        img_array = np.where(zebra[np.newaxis, :], 255, 0).astype(np.uint8)
        # Повторяем для всех строк
        img_array = np.tile(img_array, (height, 1))
    
    return Image.fromarray(img_array, mode='L')

def add_siemens_star(img, center_x, center_y, radius, num_spokes=36):
    """
    Опционально: добавляет звезду Сименса в центр для оценки MTF.
    Работает только с RGB изображениями.
    """
    img_array = np.array(img.convert('RGB'))
    y, x = np.ogrid[:img.height, :img.width]
    
    # Расстояние от центра
    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
    # Угол
    angle = np.arctan2(y - center_y, x - center_x)
    
    # Создаем маску звезды
    mask = dist <= radius
    spoke_angle = np.mod(angle * num_spokes / (2 * np.pi), 2)
    star_pattern = np.mod(spoke_angle, 2) < 1
    
    # Накладываем звезду (белые/черные сектора)
    img_array[mask] = np.where(star_pattern[mask, np.newaxis], [255, 255, 255], [0, 0, 0])
    
    return Image.fromarray(img_array)

def main():
    parser = argparse.ArgumentParser(
        description='Генератор тестовых мишеней для оценки резкости камеры',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python chart_generator.py checkerboard 1920 1080 -s 80 -o chart.png
  python chart_generator.py zebra 3840 2160 -w 40 --vertical -o zebra_4k.png
  python chart_generator.py zebra 1280 720 -w 30 -o zebra_hd.png
        """
    )
    
    parser.add_argument('type', choices=['checkerboard', 'zebra'], 
                       help='Тип тестовой мишени')
    parser.add_argument('width', type=int, 
                       help='Ширина изображения в пикселях')
    parser.add_argument('height', type=int, 
                       help='Высота изображения в пикселях')
    parser.add_argument('-s', '--square-size', type=int, default=50,
                       help='Размер клетки для шахматной доски (по умолчанию: 50)')
    parser.add_argument('-w', '--stripe-width', type=int, default=30,
                       help='Ширина полосы для зебры (по умолчанию: 30)')
    parser.add_argument('--vertical', action='store_true',
                       help='Вертикальные полосы для зебры (по умолчанию: горизонтальные)')
    parser.add_argument('-o', '--output', type=str, default='test_chart.png',
                       help='Имя выходного файла (по умолчанию: test_chart.png)')
    parser.add_argument('--add-star', action='store_true',
                       help='Добавить звезду Сименса в центр (только для шахматной доски)')
    parser.add_argument('--star-radius', type=int, default=200,
                       help='Радиус звезды Сименса (по умолчанию: 200)')
    
    args = parser.parse_args()
    
    # Генерируем изображение в зависимости от типа
    if args.type == 'checkerboard':
        img = create_checkerboard(args.width, args.height, args.square_size)
        title = f"Checkerboard {args.width}x{args.height} (cell: {args.square_size}px)"
    else:  # zebra
        orientation = 'vertical' if args.vertical else 'horizontal'
        img = create_zebra(args.width, args.height, args.stripe_width, orientation)
        title = f"Zebra {args.width}x{args.height} (stripe: {args.stripe_width}px, {orientation})"
    
    # Опционально добавляем звезду Сименса
    if args.add_star and args.type == 'checkerboard':
        img = add_siemens_star(
            img, 
            args.width // 2, 
            args.height // 2, 
            args.star_radius
        )
        title += f" + Siemens star (r={args.star_radius})"
    
    # Сохраняем изображение
    img.save(args.output)
    
    print(f"✅ Создано изображение: {args.output}")
    print(f"📐 Размер: {args.width}x{args.height} пикселей")
    print(f"📊 {title}")

if __name__ == "__main__":
    main()