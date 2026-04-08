import os
import sys
from pathlib import Path

from database import Database
from analyzer import ImageAnalyzer


def clear_screen():
    """Очищает экран консоли"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Выводит заголовок программы"""
    print("=" * 60)
    print("   📸 PHOTO QUALITY ANALYZER - Анализ качества фотографий")
    print("=" * 60)
    print()


def print_menu():
    """Выводит главное меню"""
    print("\n" + "-" * 40)
    print("ГЛАВНОЕ МЕНЮ:")
    print("-" * 40)
    print(" 1. 📁 Анализировать новое фото")
    print(" 2. 📋 Показать все фото")
    print(" 3. 🔍 Поиск по фото")
    print(" 4. ⭐ Оценить фото")
    print(" 5. 📊 Показать статистику")
    print(" 6. 🏷️ Добавить категорию")
    print(" 7. 🗑️ Удалить фото из БД")
    print(" 0. 🚪 Выход")
    print("-" * 40)


def analyze_photo(db: Database, analyzer: ImageAnalyzer):
    """Анализ нового фото"""
    clear_screen()
    print_header()
    print("📁 АНАЛИЗ ФОТОГРАФИИ\n")
    
    file_path = input("Введите путь к фото: ").strip().strip('"').strip("'")
    
    if not file_path:
        print("❌ Путь не указан!")
        input("\nНажмите Enter для продолжения...")
        return
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\n🔄 Анализ: {os.path.basename(file_path)}")
    print("⏳ Пожалуйста, подождите...\n")
    
    try:
        result = analyzer.analyze(file_path)
        analysis_id = db.save_analysis(result)
        
        print("✅ Анализ завершен!\n")
        print("=" * 50)
        print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
        print("=" * 50)
        
        # Выводим результаты
        overall = result.get('overall_score', 0)
        if overall >= 80:
            rating = "🌟 ОТЛИЧНО"
        elif overall >= 60:
            rating = "👍 ХОРОШО"
        elif overall >= 40:
            rating = "📷 СРЕДНЕ"
        else:
            rating = "⚠️ ПЛОХО"
        
        print(f"  ID в базе: {analysis_id}")
        print(f"  Файл: {result.get('filename', 'Unknown')}")
        print(f"  Общая оценка: {overall:.1f}/100 {rating}")
        print()
        print("  Метрики качества:")
        print(f"    🔍 Резкость: {result.get('sharpness_score', 0):.1f}")
        print(f"    🔊 Шум: {result.get('noise_level', 0):.1f}")
        print(f"    ☀️ Динамический диапазон: {result.get('dynamic_range', 0):.1f} EV")
        print(f"    💡 Яркость: {result.get('brightness', 0):.2f}")
        print(f"    🎨 Насыщенность: {result.get('saturation', 0):.2f}")
        print()
        print("  Цветовой баланс (RGB):")
        print(f"    🔴 Красный: {result.get('avg_red', 0):.3f}")
        print(f"    🟢 Зеленый: {result.get('avg_green', 0):.3f}")
        print(f"    🔵 Синий: {result.get('avg_blue', 0):.3f}")
        print()
        
        if result.get('camera_model'):
            print("  Информация о камере:")
            print(f"    📷 Модель: {result.get('camera_model', 'N/A')}")
            print(f"    ⚡ ISO: {result.get('iso', 'N/A')}")
            print(f"    🎞️ Выдержка: {result.get('exposure_time', 'N/A')}")
            print(f"    🔭 Диафрагма: {result.get('aperture', 'N/A')}")
            print(f"    📏 Фокусное: {result.get('focal_length', 'N/A')}mm")
            print()
        
        print(f"  Размер: {result.get('image_width', 0)}x{result.get('image_height', 0)} px")
        print(f"  Размер файла: {result.get('file_size', 0) // 1024} KB")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {str(e)}")
    
    input("\nНажмите Enter для продолжения...")


def list_photos(db: Database):
    """Показывает список всех фото"""
    clear_screen()
    print_header()
    print("📋 СПИСОК ВСЕХ ФОТОГРАФИЙ\n")
    
    analyses = db.get_all_analyses(limit=100)
    
    if not analyses:
        print("📭 В базе данных нет фотографий.")
        print("Добавьте фото через пункт меню 'Анализировать новое фото'.")
    else:
        print(f"Всего фото: {len(analyses)}\n")
        print("-" * 110)
        print(f"{'ID':<5} {'Файл':<35} {'Камера':<20} {'Оценка':<8} {'Резкость':<8} {'Шум':<8} {'ISO':<6}")
        print("-" * 110)
        
        for analysis in analyses:
            # Безопасное получение значений с преобразованием типов
            try:
                overall = analysis.get('overall_score', 0)
                if overall is None:
                    overall = 0
                overall_str = f"{float(overall):.0f}%" if overall != 0 else "N/A"
            except (ValueError, TypeError):
                overall_str = "N/A"
            
            try:
                sharpness_val = analysis.get('sharpness_score', 0)
                if sharpness_val is None:
                    sharpness_val = 0
                sharpness_str = f"{float(sharpness_val):.0f}" if sharpness_val != 0 else "N/A"
            except (ValueError, TypeError):
                sharpness_str = "N/A"
            
            try:
                noise_val = analysis.get('noise_level', 0)
                if noise_val is None:
                    noise_val = 0
                noise_str = f"{float(noise_val):.1f}" if noise_val != 0 else "N/A"
            except (ValueError, TypeError):
                noise_str = "N/A"
            
            camera = str(analysis.get('camera_model') or 'Unknown')[:20]
            filename = str(analysis['filename'])[:35] if analysis.get('filename') else "Unknown"
            iso = str(analysis.get('iso') or 'N/A')
            
            print(f"{analysis['id']:<5} {filename:<35} {camera:<20} {overall_str:<8} {sharpness_str:<8} {noise_str:<8} {iso:<6}")
        
        print("-" * 110)
    
    input("\nНажмите Enter для продолжения...")


def search_photos(db: Database):
    """Поиск фото"""
    clear_screen()
    print_header()
    print("🔍 ПОИСК ФОТОГРАФИЙ\n")
    
    query = input("Введите поисковый запрос (имя файла или тег): ").strip()
    
    if not query:
        print("❌ Запрос не может быть пустым!")
        input("\nНажмите Enter для продолжения...")
        return
    
    results = db.search_photos(query)
    
    clear_screen()
    print_header()
    print(f"🔍 РЕЗУЛЬТАТЫ ПОИСКА: '{query}'\n")
    
    if not results:
        print("📭 Фотографии не найдены.")
    else:
        print(f"Найдено фото: {len(results)}\n")
        
        for r in results:
            rating_stars = "⭐" * (r.get('user_rating') or 0) + "☆" * (5 - (r.get('user_rating') or 0))
            print(f"📸 [{r['id']}] {r['filename']}")
            print(f"   Оценка: {r.get('overall_score', 0):.0f}% | Пользователь: {rating_stars}")
            print(f"   Теги: {r.get('user_tags', '-')}")
            print()
    
    input("\nНажмите Enter для продолжения...")


def rate_photo(db: Database):
    """Оценка фото пользователем"""
    clear_screen()
    print_header()
    print("⭐ ОЦЕНКА ФОТОГРАФИИ\n")
    
    try:
        photo_id = int(input("Введите ID фото для оценки: ").strip())
    except ValueError:
        print("❌ ID должен быть числом!")
        input("\nНажмите Enter для продолжения...")
        return
    
    photo = db.get_analysis(photo_id)
    
    if not photo:
        print(f"❌ Фото с ID {photo_id} не найдено!")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\n📸 Фото: {photo['filename']}")
    print(f"📊 Текущая оценка: {photo.get('overall_score', 0):.0f}%\n")
    
    try:
        rating = int(input("Ваша оценка (1-5): ").strip())
        if rating < 1 or rating > 5:
            print("❌ Оценка должна быть от 1 до 5!")
            input("\nНажмите Enter для продолжения...")
            return
    except ValueError:
        print("❌ Введите число от 1 до 5!")
        input("\nНажмите Enter для продолжения...")
        return
    
    notes = input("Заметки (опционально, Enter для пропуска): ").strip()
    tags = input("Теги через запятую (опционально, Enter для пропуска): ").strip()
    
    db.update_rating(photo_id, rating, notes if notes else None, tags if tags else None)
    
    print("\n✅ Оценка сохранена!")
    input("\nНажмите Enter для продолжения...")


def show_statistics(db: Database):
    """Показывает статистику"""
    clear_screen()
    print_header()
    print("📊 СТАТИСТИКА ПО ФОТОГРАФИЯМ\n")
    
    stats = db.get_statistics()
    
    print("=" * 50)
    print("ОБЩАЯ СТАТИСТИКА:")
    print("=" * 50)
    print(f"  📸 Всего фото: {stats.get('total_photos', 0)}")
    print(f"  🎯 Средняя общая оценка: {stats.get('avg_overall_score', 0):.1f}/100")
    print(f"  🔍 Средняя резкость: {stats.get('avg_sharpness', 0):.1f}")
    print(f"  🔊 Средний уровень шума: {stats.get('avg_noise', 0):.1f}")
    print(f"  ⭐ Средняя оценка пользователя: {stats.get('avg_user_rating', 0):.1f}/5")
    
    if stats.get('top_cameras'):
        print("\n" + "=" * 50)
        print("ТОП КАМЕР:")
        print("=" * 50)
        for cam in stats['top_cameras']:
            bar = "█" * min(20, cam['count'])
            print(f"  {cam['camera_model']:<25} {cam['count']:>3} фото {bar}")
    
    print("\n" + "=" * 50)
    
    # Показываем распределение оценок
    analyses = db.get_all_analyses(limit=1000)
    if analyses:
        ratings_dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for a in analyses:
            user_rating = a.get('user_rating') or 0
            ratings_dist[user_rating] = ratings_dist.get(user_rating, 0) + 1
        
        print("\nРАСПРЕДЕЛЕНИЕ ПОЛЬЗОВАТЕЛЬСКИХ ОЦЕНОК:")
        print("-" * 40)
        for rating in range(1, 6):
            count = ratings_dist.get(rating, 0)
            bar = "█" * min(20, count)
            stars = "⭐" * rating
            print(f"  {stars:<10} {count:>3} фото {bar}")
    
    input("\nНажмите Enter для продолжения...")


def add_category(db: Database):
    """Добавляет новую категорию"""
    clear_screen()
    print_header()
    print("🏷️ ДОБАВЛЕНИЕ КАТЕГОРИИ\n")
    
    name = input("Название категории: ").strip()
    if not name:
        print("❌ Название не может быть пустым!")
        input("\nНажмите Enter для продолжения...")
        return
    
    description = input("Описание (опционально): ").strip()
    
    category_id = db.add_category(name, description)
    
    if category_id:
        print(f"\n✅ Категория '{name}' добавлена! ID: {category_id}")
    else:
        print(f"\n⚠️ Категория '{name}' уже существует или произошла ошибка.")
    
    # Спрашиваем, добавить ли фото в категорию
    if Confirm.ask("\nДобавить фото в эту категорию?"):
        try:
            photo_id = int(input("Введите ID фото: ").strip())
            db.add_photo_to_category(photo_id, category_id)
            print("✅ Фото добавлено в категорию!")
        except ValueError:
            print("❌ Неверный ID фото!")
    
    input("\nНажмите Enter для продолжения...")


def delete_photo(db: Database):
    """Удаляет фото из базы данных"""
    clear_screen()
    print_header()
    print("🗑️ УДАЛЕНИЕ ФОТОГРАФИИ\n")
    
    try:
        photo_id = int(input("Введите ID фото для удаления: ").strip())
    except ValueError:
        print("❌ ID должен быть числом!")
        input("\nНажмите Enter для продолжения...")
        return
    
    photo = db.get_analysis(photo_id)
    
    if not photo:
        print(f"❌ Фото с ID {photo_id} не найдено!")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\n📸 Фото: {photo['filename']}")
    print(f"📊 Оценка: {photo.get('overall_score', 0):.0f}%")
    
    confirm = input("\n⚠️ Вы уверены, что хотите удалить это фото? (да/нет): ").strip().lower()
    
    if confirm in ['да', 'yes', 'y', 'д']:
        db.delete_analysis(photo_id)
        print("\n✅ Фото удалено из базы данных!")
    else:
        print("\n❌ Удаление отменено.")
    
    input("\nНажмите Enter для продолжения...")


def main():
    """Главная функция"""
    db = Database("photo_analysis.db")
    analyzer = ImageAnalyzer()
    
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        choice = input("\nВыберите действие (0-7): ").strip()
        
        if choice == '1':
            analyze_photo(db, analyzer)
        elif choice == '2':
            list_photos(db)
        elif choice == '3':
            search_photos(db)
        elif choice == '4':
            rate_photo(db)
        elif choice == '5':
            show_statistics(db)
        elif choice == '6':
            add_category(db)
        elif choice == '7':
            delete_photo(db)
        elif choice == '0':
            clear_screen()
            print("\n👋 До свидания!\n")
            sys.exit(0)
        else:
            print("\n❌ Неверный выбор! Пожалуйста, выберите пункт от 0 до 7.")
            input("\nНажмите Enter для продолжения...")


if __name__ == "__main__":
    main()