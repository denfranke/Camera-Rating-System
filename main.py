import os
import sys
import json
import signal
from pathlib import Path

from database import Database
from analyzer import ImageAnalyzer


def signal_handler(sig, frame):
    print("\n\n👋 Прерывание работы. До свидания!")
    sys.exit(0)


def load_config():
    config_file = "config.json"
    default_config = {
        "database": {
            "type": "sqlite",
            "sqlite": {
                "db_path": "photo_analysis.db"
            },
            "mssql": {
                "server": "localhost",
                "port": 1433,
                "database": "photo_analyzer",
                "use_windows_auth": True,
                "username": "",
                "password": ""
            }
        }
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Ошибка чтения {config_file}, создаю новый...")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    else:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print(f"Создан файл конфигурации: {config_file}")
        return default_config


def save_config(config):
    with open("config.json", "w", encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def safe_input(prompt: str, default: str = None) -> str:
    try:
        result = input(prompt).strip()
        if not result and default is not None:
            return default
        return result
    except KeyboardInterrupt:
        print("\n")
        return None


def safe_int_input(prompt: str, default: int = None) -> int:
    try:
        result = input(prompt).strip()
        if not result and default is not None:
            return default
        return int(result)
    except KeyboardInterrupt:
        print("\n")
        return None
    except ValueError:
        print("Введите число!")
        return safe_int_input(prompt, default)


def configure_database():
    clear_screen()
    print_header()
    print("НАСТРОЙКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ\n")
    
    print("Выберите тип базы данных:")
    print(" 1. Локальная SQLite (просто, не требует сервера)")
    print(" 2. Удалённый MS SQL Server (требует сервер Microsoft SQL Server)")
    print(" 0. Отмена")
    
    choice = safe_input("\nВыберите (0-2): ")
    
    if choice is None:
        return None
    
    if choice == '1':
        db_path = safe_input("Путь к файлу БД (Enter для photo_analysis.db): ", "photo_analysis.db")
        if db_path is None:
            return None
        
        config = {
            "database": {
                "type": "sqlite",
                "sqlite": {"db_path": db_path},
                "mssql": {}
            }
        }
        save_config(config)
        
        print(f"\nКонфигурация сохранена. БД: {db_path}")
        return Database(db_type="sqlite", db_path=db_path)
    
    elif choice == '2':
        print("\nВведите параметры подключения к MS SQL Server:")
        
        server = safe_input("Сервер (IP или hostname): ")
        if server is None:
            return None
        if not server:
            print("Адрес сервера обязателен!")
            safe_input("\nНажмите Enter для продолжения...")
            return None
        
        port_input = safe_input("Порт (Enter для 1433): ", "1433")
        if port_input is None:
            return None
        port = int(port_input) if port_input else 1433
        
        database = safe_input("Имя базы данных: ")
        if database is None:
            return None
        if not database:
            print("Имя базы данных обязательно!")
            safe_input("\nНажмите Enter для продолжения...")
            return None
        
        print("\nТип аутентификации:")
        print(" 1. Windows аутентификация (Trusted Connection)")
        print(" 2. SQL Server аутентификация (логин/пароль)")
        auth_choice = safe_input("\nВыберите (1-2): ", "1")
        
        if auth_choice is None:
            return None
        
        use_windows_auth = auth_choice == '1'
        username = None
        password = None
        
        if not use_windows_auth:
            username = safe_input("Логин: ")
            if username is None:
                return None
            if not username:
                print("Логин обязателен!")
                safe_input("\nНажмите Enter для продолжения...")
                return None
            
            password = safe_input("Пароль: ")
            if password is None:
                return None
        
        config = {
            "database": {
                "type": "mssql",
                "sqlite": {},
                "mssql": {
                    "server": server,
                    "port": port,
                    "database": database,
                    "use_windows_auth": use_windows_auth,
                    "username": username or "",
                    "password": password or ""
                }
            }
        }
        save_config(config)
        
        print(f"\nКонфигурация сохранена.")
        
        try:
            db = Database(
                db_type="mssql",
                server=server,
                port=port,
                database=database,
                username=username if not use_windows_auth else None,
                password=password if not use_windows_auth else None,
                use_windows_auth=use_windows_auth
            )
            return db
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            safe_input("\nНажмите Enter для продолжения...")
            return None
    
    return None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print("=" * 60)
    print("   PHOTO QUALITY ANALYZER - Анализ качества фотографий")
    print("=" * 60)
    print()


def print_menu(db: Database):
    db_type = "SQLite" if db.db_type == "sqlite" else "MS SQL Server"
    print("\n" + "-" * 40)
    print(f"БД: {db_type}")
    print("-" * 40)
    print("ГЛАВНОЕ МЕНЮ:")
    print("-" * 40)
    print(" 1. Анализировать новое фото")
    print(" 2. Показать все фото")
    print(" 3. Поиск по фото")
    print(" 4. Оценить фото")
    print(" 5. Показать статистику")
    print(" 6. Добавить категорию")
    print(" 7. Удалить фото из БД")
    print(" 8. Сменить БД")
    print(" 0. Выход")
    print("-" * 40)


def wait_for_enter():
    print("\nНажмите Enter для продолжения...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n")
        return False
    return True


def analyze_photo(db: Database, analyzer: ImageAnalyzer):
    clear_screen()
    print_header()
    print("АНАЛИЗ ФОТОГРАФИИ\n")

    print(f"Тип БД: {db.db_type}")
    
    file_path = safe_input("Введите путь к фото: ")
    
    if file_path is None:
        return
    
    file_path = file_path.strip('"').strip("'")
    
    if not file_path:
        print("Путь не указан!")
        wait_for_enter()
        return
    
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        wait_for_enter()
        return
    
    print(f"\nАнализ: {os.path.basename(file_path)}")
    print("Пожалуйста, подождите...\n")
    
    try:
        result = analyzer.analyze(file_path)
        analysis_id = db.save_analysis(result)
        
        print("Анализ завершен!\n")
        print("=" * 50)
        print("РЕЗУЛЬТАТЫ АНАЛИЗА:")
        print("=" * 50)
        
        overall = result.get('overall_score', 0)
        if overall >= 80:
            rating = "ОТЛИЧНО"
        elif overall >= 60:
            rating = "ХОРОШО"
        elif overall >= 40:
            rating = "СРЕДНЕ"
        else:
            rating = "ПЛОХО"
        
        print(f"  ID в базе: {analysis_id}")
        print(f"  Файл: {result.get('filename', 'Unknown')}")
        print(f"  Общая оценка: {overall:.1f}/100 {rating}")
        print()
        print("  Метрики качества:")
        print(f"    Резкость: {result.get('sharpness_score', 0):.1f}")
        print(f"    Шум: {result.get('noise_level', 0):.1f}")
        print(f"    Динамический диапазон: {result.get('dynamic_range', 0):.1f} EV")
        print(f"    Яркость: {result.get('brightness', 0):.2f}")
        print(f"    Насыщенность: {result.get('saturation', 0):.2f}")
        print()
        
        if result.get('camera_model'):
            print("  Информация о камере:")
            print(f"    Модель: {result.get('camera_model', 'N/A')}")
            print(f"    ISO: {result.get('iso', 'N/A')}")
            print(f"    Выдержка: {result.get('exposure_time', 'N/A')}")
            print(f"    Диафрагма: {result.get('aperture', 'N/A')}")
            print(f"    Фокусное: {result.get('focal_length', 'N/A')}mm")
            print()
        
        print(f"  Размер: {result.get('image_width', 0)}x{result.get('image_height', 0)} px")
        print(f"  Размер файла: {result.get('file_size', 0) // 1024} KB")
        print("=" * 50)
        
    except Exception as e:
        print(f"Ошибка при анализе: {str(e)}")
    
    wait_for_enter()


def list_photos(db: Database):
    clear_screen()
    print_header()
    print("СПИСОК ВСЕХ ФОТОГРАФИЙ\n")
    
    try:
        analyses = db.get_all_analyses(limit=100)
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        wait_for_enter()
        return
    
    if not analyses:
        print("В базе данных нет фотографий.")
    else:
        print(f"Всего фото: {len(analyses)}\n")
        print("-" * 110)
        print(f"{'ID':<5} {'Файл':<35} {'Камера':<20} {'Оценка':<8} {'Резкость':<8} {'Шум':<8} {'ISO':<6}")
        print("-" * 110)
        
        for analysis in analyses:
            try:
                overall = analysis.get('overall_score', 0) or 0
                overall_str = f"{float(overall):.0f}%" if overall else "N/A"
            except:
                overall_str = "N/A"
            
            try:
                sharpness = analysis.get('sharpness_score', 0) or 0
                sharpness_str = f"{float(sharpness):.0f}" if sharpness else "N/A"
            except:
                sharpness_str = "N/A"
            
            try:
                noise = analysis.get('noise_level', 0) or 0
                noise_str = f"{float(noise):.1f}" if noise else "N/A"
            except:
                noise_str = "N/A"
            
            camera = str(analysis.get('camera_model') or 'Unknown')[:20]
            filename = str(analysis.get('filename', 'Unknown'))[:35]
            iso = str(analysis.get('iso') or 'N/A')
            
            print(f"{analysis['id']:<5} {filename:<35} {camera:<20} {overall_str:<8} {sharpness_str:<8} {noise_str:<8} {iso:<6}")
        
        print("-" * 110)
    
    wait_for_enter()


def search_photos(db: Database):
    clear_screen()
    print_header()
    print("ПОИСК ФОТОГРАФИЙ\n")
    
    query = safe_input("Введите поисковый запрос: ")
    
    if query is None:
        return
    
    if not query:
        print("Запрос не может быть пустым!")
        wait_for_enter()
        return
    
    try:
        results = db.search_photos(query)
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        wait_for_enter()
        return
    
    clear_screen()
    print_header()
    print(f"РЕЗУЛЬТАТЫ ПОИСКА: '{query}'\n")
    
    if not results:
        print("Фотографии не найдены.")
    else:
        print(f"Найдено фото: {len(results)}\n")
        for r in results:
            stars = "[*]" * (r.get('user_rating') or 0) + "[ ]" * (5 - (r.get('user_rating') or 0))
            print(f"[{r['id']}] {r['filename']}")
            print(f"   Оценка: {r.get('overall_score', 0):.0f}% | {stars}")
            print(f"   Теги: {r.get('user_tags', '-')}")
            print()
    
    wait_for_enter()


def rate_photo(db: Database):
    clear_screen()
    print_header()
    print("ОЦЕНКА ФОТОГРАФИИ\n")
    
    photo_id = safe_int_input("Введите ID фото: ")
    
    if photo_id is None:
        return
    
    try:
        photo = db.get_analysis(photo_id)
    except Exception as e:
        print(f"Ошибка: {e}")
        wait_for_enter()
        return
    
    if not photo:
        print(f"Фото с ID {photo_id} не найдено!")
        wait_for_enter()
        return
    
    print(f"\nФото: {photo['filename']}")
    print(f"Текущая оценка: {photo.get('overall_score', 0):.0f}%\n")
    
    rating = safe_int_input("Ваша оценка (1-5): ")
    
    if rating is None:
        return
    
    if rating < 1 or rating > 5:
        print("Оценка от 1 до 5!")
        wait_for_enter()
        return
    
    notes = safe_input("Заметки (Enter для пропуска): ")
    if notes is None:
        return
    
    tags = safe_input("Теги (Enter для пропуска): ")
    if tags is None:
        return
    
    try:
        db.update_rating(photo_id, rating, notes if notes else None, tags if tags else None)
        print("\nОценка сохранена!")
    except Exception as e:
        print(f"\nОшибка сохранения: {e}")
    
    wait_for_enter()


def show_statistics(db: Database):
    clear_screen()
    print_header()
    print("СТАТИСТИКА ПО ФОТОГРАФИЯМ\n")
    
    try:
        stats = db.get_statistics()
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        wait_for_enter()
        return
    
    print("=" * 50)
    print("ОБЩАЯ СТАТИСТИКА:")
    print("=" * 50)
    print(f"Всего фото: {stats.get('total_photos', 0)}")
    print(f"Средняя общая оценка: {stats.get('avg_overall_score', 0):.1f}/100")
    print(f"Средняя резкость: {stats.get('avg_sharpness', 0):.1f}")
    print(f"Средний уровень шума: {stats.get('avg_noise', 0):.1f}")
    print(f"Средняя оценка пользователя: {stats.get('avg_user_rating', 0):.1f}/5")
    
    if stats.get('top_cameras'):
        print("\n" + "=" * 50)
        print("ТОП КАМЕР:")
        print("=" * 50)
        for cam in stats['top_cameras']:
            bar = "█" * min(20, cam['count'])
            print(f"  {cam['camera_model']:<25} {cam['count']:>3} фото {bar}")
    
    wait_for_enter()


def add_category(db: Database):
    clear_screen()
    print_header()
    print("ДОБАВЛЕНИЕ КАТЕГОРИИ\n")
    
    name = safe_input("Название категории: ")
    
    if name is None:
        return
    
    if not name:
        print("Название не может быть пустым!")
        wait_for_enter()
        return
    
    description = safe_input("Описание: ")
    if description is None:
        return
    
    try:
        category_id = db.add_category(name, description or "")
    except Exception as e:
        print(f"Ошибка: {e}")
        wait_for_enter()
        return
    
    if category_id:
        print(f"\nКатегория '{name}' добавлена! ID: {category_id}")
    else:
        print(f"\nКатегория '{name}' уже существует или произошла ошибка.")
    
    confirm = safe_input("\nДобавить фото в категорию? (да/нет): ")
    if confirm and confirm.lower() in ['да', 'yes', 'y', 'д']:
        photo_id = safe_int_input("Введите ID фото: ")
        if photo_id:
            try:
                db.add_photo_to_category(photo_id, category_id)
                print("Фото добавлено в категорию!")
            except Exception as e:
                print(f"Ошибка: {e}")
    
    wait_for_enter()


def delete_photo(db: Database):
    clear_screen()
    print_header()
    print("УДАЛЕНИЕ ФОТОГРАФИИ\n")
    
    photo_id = safe_int_input("Введите ID фото: ")
    
    if photo_id is None:
        return
    
    try:
        photo = db.get_analysis(photo_id)
    except Exception as e:
        print(f"Ошибка: {e}")
        wait_for_enter()
        return
    
    if not photo:
        print(f"Фото с ID {photo_id} не найдено!")
        wait_for_enter()
        return
    
    print(f"\nФото: {photo['filename']}")
    confirm = safe_input("\nУдалить? (да/нет): ")
    
    if confirm and confirm.lower() in ['да', 'yes', 'y', 'д']:
        try:
            db.delete_analysis(photo_id)
            print("\nФото удалено!")
        except Exception as e:
            print(f"\nОшибка удаления: {e}")
    else:
        print("\nОтменено")
    
    wait_for_enter()


def main():
    # Устанавливаем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    
    analyzer = ImageAnalyzer()
    db = None
    
    config = load_config()
    db_config = config.get('database', {})
    db_type = db_config.get('type', 'sqlite')
    
    try:
        if db_type == 'sqlite':
            sqlite_config = db_config.get('sqlite', {})
            db_path = sqlite_config.get('db_path', 'photo_analysis.db')
            db = Database(db_type='sqlite', db_path=db_path)
        elif db_type == 'mssql':
            mssql_config = db_config.get('mssql', {})
            db = Database(
                db_type='mssql',
                server=mssql_config.get('server', 'localhost'),
                port=mssql_config.get('port', 1433),
                database=mssql_config.get('database', 'photo_analyzer'),
                username=mssql_config.get('username') if not mssql_config.get('use_windows_auth', True) else None,
                password=mssql_config.get('password') if not mssql_config.get('use_windows_auth', True) else None,
                use_windows_auth=mssql_config.get('use_windows_auth', True)
            )
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        db = configure_database()
    
    while True:
        if db is None:
            db = configure_database()
            if db is None:
                break
            continue
        
        clear_screen()
        print_header()
        print_menu(db)
        
        choice = safe_input("\nВыберите действие (0-8): ")
        
        if choice is None:
            continue
        
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
        elif choice == '8':
            db.close()
            db = configure_database()
        elif choice == '0':
            db.close()
            clear_screen()
            sys.exit(0)
        else:
            print("\nОшибка, введите число от 0 до 8.")
            wait_for_enter()


if __name__ == "__main__":
    main()



# 42145
# PhotoQualityAnalyzer
# RawPhotos\img1.dng