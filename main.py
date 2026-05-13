import os
import sys
import json
import signal
import time
from pathlib import Path

from database import Database
from analyzer import ImageAnalyzer
from dxomark_service import DxOMarkService


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
    except EOFError:
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
    
    print(f"\n📷 Анализ: {os.path.basename(file_path)}")
    print("⏳ Пожалуйста, подождите...\n")
    
    try:
        # Анализируем изображение
        result = analyzer.analyze(file_path)
        
        # --- АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ КАМЕРЫ И DxOMark ---
        dxo_service = DxOMarkService(db.db_path if hasattr(db, 'db_path') else "photo_analysis.db")
        
        # Получаем модель камеры из результата анализа
        camera_model = result.get('camera_model')
        camera_make = result.get('camera_make')
        dxomark_score = None
        
        print("\n" + "=" * 60)
        print("📷 ОПРЕДЕЛЕНИЕ КАМЕРЫ")
        print("=" * 60)
        
        # Флаг, была ли выбрана модель вручную
        manual_model_selected = False
        
        if camera_model and camera_model != 'Unknown':
            # Показываем определённую модель
            if camera_make:
                print(f"  📱 Производитель: {camera_make}")
            print(f"  📱 Модель: {camera_model}")
            
            # Пробуем найти DxOMark оценку
            dxomark_score = dxo_service.get_score(camera_model)
            
            # Если не нашли, пробуем с производителем
            if not dxomark_score and camera_make:
                full_name = f"{camera_make} {camera_model}"
                print(f"  🔍 Пробуем найти: {full_name}")
                dxomark_score = dxo_service.get_score(full_name)
            
            # Если нашли DxOMark оценку
            if dxomark_score:
                result['dxomark_score'] = dxomark_score
                print(f"\n  ✅ Найдена оценка DxOMark: {dxomark_score}")
                
                # Интерпретация DxOMark
                if dxomark_score >= 160:
                    dxo_rating = "🌟 Элитная камера (топ-уровень)"
                elif dxomark_score >= 150:
                    dxo_rating = "⭐ Отличная камера"
                elif dxomark_score >= 140:
                    dxo_rating = "👍 Очень хорошая камера"
                elif dxomark_score >= 120:
                    dxo_rating = "✅ Хорошая камера"
                elif dxomark_score >= 100:
                    dxo_rating = "👌 Средняя камера"
                else:
                    dxo_rating = "📱 Бюджетная камера"
                print(f"  {dxo_rating}")
            else:
                # Модель определена, но не найдена в базе DxOMark
                print(f"\n  ⚠️ Модель '{camera_model}' не найдена в базе DxOMark")
                print("  🔧 Желаете указать модель вручную?")
                
                manual_choice = safe_input("\n  Введите 'y' для ручного выбора или Enter для пропуска: ")
                
                if manual_choice and manual_choice.lower() in ['y', 'yes', 'д', 'да']:
                    # Получаем список моделей из базы DxOMark
                    all_models = dxo_service.get_all_models()
                    
                    if all_models:
                        print("\n  📋 Доступные модели в базе DxOMark:")
                        print("  " + "-" * 50)
                        
                        # Показываем модели постранично
                        page_size = 15
                        total_pages = (len(all_models) + page_size - 1) // page_size
                        current_page = 0
                        
                        while True:
                            start_idx = current_page * page_size
                            end_idx = min(start_idx + page_size, len(all_models))
                            
                            print(f"\n  Страница {current_page + 1}/{total_pages}:")
                            for i, model in enumerate(all_models[start_idx:end_idx], start=1):
                                print(f"    {start_idx + i}. {model}")
                            
                            print(f"\n  Действия:")
                            print(f"    • Введите номер модели для выбора")
                            print(f"    • 'n' - следующая страница")
                            print(f"    • 'p' - предыдущая страница")
                            print(f"    • 's' - поиск по названию")
                            print(f"    • Enter - пропустить")
                            
                            choice = safe_input("\n  Ваш выбор: ")
                            
                            if choice is None or choice == '':
                                break
                            elif choice.lower() == 'n' and current_page < total_pages - 1:
                                current_page += 1
                                continue
                            elif choice.lower() == 'p' and current_page > 0:
                                current_page -= 1
                                continue
                            elif choice.lower() == 's':
                                search_term = safe_input("  Введите текст для поиска: ")
                                if search_term:
                                    search_results = [m for m in all_models if search_term.lower() in m.lower()]
                                    if search_results:
                                        print(f"\n  Найдено {len(search_results)} моделей:")
                                        for i, model in enumerate(search_results[:20], start=1):
                                            print(f"    {i}. {model}")
                                        
                                        idx_choice = safe_input("\n  Выберите номер модели (или Enter для отмены): ")
                                        if idx_choice and idx_choice.isdigit():
                                            idx = int(idx_choice) - 1
                                            if 0 <= idx < len(search_results):
                                                manual_model = search_results[idx]
                                                dxomark_score = dxo_service.get_score(manual_model)
                                                if dxomark_score:
                                                    result['dxomark_score'] = dxomark_score
                                                    result['camera_model'] = manual_model
                                                    manual_model_selected = True
                                                    print(f"\n  ✅ Выбрана модель: {manual_model} (DxOMark: {dxomark_score})")
                                                    break
                                    else:
                                        print("  ❌ Ничего не найдено")
                            elif choice.isdigit():
                                idx = int(choice) - 1
                                if 0 <= idx < len(all_models):
                                    manual_model = all_models[idx]
                                    dxomark_score = dxo_service.get_score(manual_model)
                                    if dxomark_score:
                                        result['dxomark_score'] = dxomark_score
                                        result['camera_model'] = manual_model
                                        manual_model_selected = True
                                        print(f"\n  ✅ Выбрана модель: {manual_model} (DxOMark: {dxomark_score})")
                                        break
                            else:
                                break
                    else:
                        print("  ❌ Нет доступных моделей в базе данных")
        else:
            # Модель не определилась автоматически
            print("  ⚠️ Не удалось автоматически определить модель камеры из метаданных")
            print("  💡 Возможные причины:")
            print("     • Файл не содержит EXIF данных")
            print("     • Недостаточно прав для чтения метаданных")
            print("\n  🔧 Желаете указать модель вручную?")
            
            manual_choice = safe_input("\n  Введите 'y' для ручного выбора или Enter для пропуска: ")
            
            if manual_choice and manual_choice.lower() in ['y', 'yes', 'д', 'да']:
                # Получаем список моделей из базы DxOMark
                all_models = dxo_service.get_all_models()
                
                if all_models:
                    print("\n  📋 Доступные модели в базе DxOMark:")
                    print("  " + "-" * 50)
                    
                    # Постраничный вывод
                    page_size = 15
                    total_pages = (len(all_models) + page_size - 1) // page_size
                    current_page = 0
                    
                    while True:
                        start_idx = current_page * page_size
                        end_idx = min(start_idx + page_size, len(all_models))
                        
                        print(f"\n  Страница {current_page + 1}/{total_pages}:")
                        for i, model in enumerate(all_models[start_idx:end_idx], start=1):
                            print(f"    {start_idx + i}. {model}")
                        
                        print(f"\n  Действия:")
                        print(f"    • Введите номер модели для выбора")
                        print(f"    • 'n' - следующая страница")
                        print(f"    • 'p' - предыдущая страница")
                        print(f"    • 's' - поиск по названию")
                        print(f"    • Enter - пропустить")
                        
                        choice = safe_input("\n  Ваш выбор: ")
                        
                        if choice is None or choice == '':
                            break
                        elif choice.lower() == 'n' and current_page < total_pages - 1:
                            current_page += 1
                            continue
                        elif choice.lower() == 'p' and current_page > 0:
                            current_page -= 1
                            continue
                        elif choice.lower() == 's':
                            search_term = safe_input("  Введите текст для поиска: ")
                            if search_term:
                                search_results = [m for m in all_models if search_term.lower() in m.lower()]
                                if search_results:
                                    print(f"\n  Найдено {len(search_results)} моделей:")
                                    for i, model in enumerate(search_results[:20], start=1):
                                        print(f"    {i}. {model}")
                                    
                                    idx_choice = safe_input("\n  Выберите номер модели (или Enter для отмены): ")
                                    if idx_choice and idx_choice.isdigit():
                                        idx = int(idx_choice) - 1
                                        if 0 <= idx < len(search_results):
                                            manual_model = search_results[idx]
                                            dxomark_score = dxo_service.get_score(manual_model)
                                            if dxomark_score:
                                                result['dxomark_score'] = dxomark_score
                                                result['camera_model'] = manual_model
                                                manual_model_selected = True
                                                print(f"\n  ✅ Выбрана модель: {manual_model} (DxOMark: {dxomark_score})")
                                                break
                                else:
                                    print("  ❌ Ничего не найдено")
                        elif choice.isdigit():
                            idx = int(choice) - 1
                            if 0 <= idx < len(all_models):
                                manual_model = all_models[idx]
                                dxomark_score = dxo_service.get_score(manual_model)
                                if dxomark_score:
                                    result['dxomark_score'] = dxomark_score
                                    result['camera_model'] = manual_model
                                    manual_model_selected = True
                                    print(f"\n  ✅ Выбрана модель: {manual_model} (DxOMark: {dxomark_score})")
                                    break
                else:
                    # Если список пуст, предлагаем ввести вручную
                    print("  📝 База DxOMark пуста или недоступна")
                    manual_model = safe_input("\n  Введите название модели вручную: ")
                    if manual_model:
                        dxomark_score = dxo_service.get_score(manual_model)
                        if dxomark_score:
                            result['dxomark_score'] = dxomark_score
                            result['camera_model'] = manual_model
                            manual_model_selected = True
                            print(f"\n  ✅ Установлена модель: {manual_model} (DxOMark: {dxomark_score})")
                        else:
                            print(f"  ⚠️ Модель '{manual_model}' не найдена в базе DxOMark")
                            print("  💡 Оценка DxOMark не будет добавлена")
        
        # Если модель была выбрана вручную, обновляем camera_model в result
        if manual_model_selected:
            print(f"\n  📱 Выбранная модель: {result.get('camera_model')}")
        
        # Сохраняем результат в БД
        analysis_id = db.save_analysis(result)
        
        # --- ВЫВОД РЕЗУЛЬТАТОВ АНАЛИЗА ---
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА")
        print("=" * 60)
        
        # Общая оценка
        overall = result.get('overall_score', 0)
        if overall >= 80:
            rating_emoji = "🏆"
            rating_text = "ОТЛИЧНО"
        elif overall >= 60:
            rating_emoji = "✅"
            rating_text = "ХОРОШО"
        elif overall >= 40:
            rating_emoji = "⚠️"
            rating_text = "СРЕДНЕ"
        else:
            rating_emoji = "❌"
            rating_text = "ПЛОХО"
        
        print(f"\n{rating_emoji} Общая оценка: {overall:.1f}/100 [{rating_text}]")
        print(f"🆔 ID в базе: {analysis_id}")
        print(f"📁 Файл: {result.get('filename', 'Unknown')}")
        
        # Метрики качества с визуализацией
        print("\n" + "-" * 40)
        print("📈 МЕТРИКИ КАЧЕСТВА:")
        print("-" * 40)
        
        sharpness = result.get('sharpness_score', 0)
        sharpness_bar = "█" * int(sharpness / 10) + "░" * (10 - int(sharpness / 10))
        print(f"  Резкость:        {sharpness:5.1f}  {sharpness_bar}")
        
        noise = result.get('noise_level', 0)
        noise_bar = "█" * int(noise / 10) + "░" * (10 - int(noise / 10))
        print(f"  Шум:             {noise:5.1f}  {noise_bar} (чем меньше, тем лучше)")
        
        dynamic_range = result.get('dynamic_range', 0)
        dr_bar = "█" * int(dynamic_range / 1.2) + "░" * (10 - int(dynamic_range / 1.2))
        print(f"  Динамический:    {dynamic_range:5.1f} EV {dr_bar}")
        
        brightness = result.get('brightness', 0) * 100
        brightness_bar = "█" * int(brightness / 10) + "░" * (10 - int(brightness / 10))
        print(f"  Яркость:         {brightness:5.1f}% {brightness_bar}")
        
        contrast = result.get('contrast', 0) * 100
        contrast_bar = "█" * int(contrast / 10) + "░" * (10 - int(contrast / 10))
        print(f"  Контраст:        {contrast:5.1f}% {contrast_bar}")
        
        saturation = result.get('saturation', 0) * 100
        saturation_bar = "█" * int(saturation / 10) + "░" * (10 - int(saturation / 10))
        print(f"  Насыщенность:    {saturation:5.1f}% {saturation_bar}")
        
        exposure = result.get('exposure_score', 0) * 100
        exposure_bar = "█" * int(exposure / 10) + "░" * (10 - int(exposure / 10))
        print(f"  Экспозиция:      {exposure:5.1f}% {exposure_bar}")
        
        composition = result.get('composition_score', 0) * 100
        composition_bar = "█" * int(composition / 10) + "░" * (10 - int(composition / 10))
        print(f"  Композиция:      {composition:5.1f}% {composition_bar}")
        
        # Информация о камере
        print("\n" + "-" * 40)
        print("📷 ИНФОРМАЦИЯ О КАМЕРЕ:")
        print("-" * 40)
        
        if result.get('camera_model'):
            print(f"  Модель:    {result.get('camera_make', '')} {result.get('camera_model', 'N/A')}".strip())
        else:
            print(f"  Модель:    Не определена")
        
        if dxomark_score:
            print(f"\n  🏆 DxOMark оценка: {dxomark_score}")
        else:
            print(f"\n  ❓ DxOMark оценка: не найдена для этой модели")
        
        # Информация о файле
        print("\n" + "-" * 40)
        print("ℹ️ ИНФОРМАЦИЯ О ФАЙЛЕ:")
        print("-" * 40)
        print(f"  Размер:    {result.get('image_width', 0)} x {result.get('image_height', 0)} px")
        print(f"  Объём:     {result.get('file_size', 0) // 1024} KB")
        
        # Цветовой баланс
        avg_r = result.get('avg_red', 0)
        avg_g = result.get('avg_green', 0)
        avg_b = result.get('avg_blue', 0)
        print(f"\n  Цветовой баланс:")
        print(f"    R: {avg_r:.2f}  G: {avg_g:.2f}  B: {avg_b:.2f}")
        
        # Проверка цветового сдвига
        if abs(avg_r - avg_g) > 0.1 or abs(avg_b - avg_g) > 0.1:
            print(f"    ⚠️ Заметен цветовой сдвиг")
        else:
            print(f"    ✅ Нейтральный баланс")
        
        # Технические параметры (если есть)
        if result.get('iso') or result.get('exposure_time') or result.get('aperture'):
            print("\n" + "-" * 40)
            print("🎯 ТЕХНИЧЕСКИЕ ПАРАМЕТРЫ:")
            print("-" * 40)
            if result.get('iso'):
                print(f"  ISO:          {result['iso']}")
            if result.get('exposure_time'):
                print(f"  Выдержка:     {result['exposure_time']}")
            if result.get('aperture'):
                print(f"  Диафрагма:    f/{result['aperture']:.1f}")
            if result.get('focal_length'):
                print(f"  Фокусное:     {result['focal_length']} mm")
        
        # Рекомендации
        print("\n" + "=" * 60)
        print("💡 РЕКОМЕНДАЦИИ:")
        print("=" * 60)
        
        recommendations = []
        
        if sharpness < 50:
            recommendations.append("  • 🔍 Низкая резкость - используйте штатив или улучшите фокусировку")
        elif sharpness > 85:
            recommendations.append("  • ✨ Отличная резкость - изображение очень детализированное")
        
        if noise > 40:
            recommendations.append("  • 🌫️ Высокий уровень шума - снизьте ISO или используйте шумоподавление")
        elif noise < 15:
            recommendations.append("  • ✨ Низкий уровень шума - отличное качество")
        
        if dynamic_range < 5:
            recommendations.append("  • 🌅 Низкий динамический диапазон - избегайте сцен с большим контрастом")
        elif dynamic_range > 9:
            recommendations.append("  • 🌈 Отличный динамический диапазон - хорошая детализация в тенях и светах")
        
        if brightness < 0.3:
            recommendations.append("  • 🌑 Фото слишком тёмное - увеличьте экспозицию")
        elif brightness > 0.8:
            recommendations.append("  • ☀️ Фото пересвечено - уменьшите экспозицию")
        elif 0.4 <= brightness <= 0.6:
            recommendations.append("  • 💡 Правильная экспозиция - отличная работа")
        
        if saturation < 0.3:
            recommendations.append("  • 🎨 Низкая насыщенность - фото выглядит блеклым")
        elif saturation > 0.8:
            recommendations.append("  • 🎨 Высокая насыщенность - цвета могут быть неестественными")
        
        if exposure < 0.4:
            recommendations.append("  • 📸 Недоэкспонировано - добавьте +0.7 EV")
        elif exposure > 0.8:
            recommendations.append("  • 📸 Переэкспонировано - уменьшите на -0.7 EV")
        
        if not recommendations:
            recommendations.append("  • 👍 Отличное фото! Технические параметры в норме")
        
        for rec in recommendations:
            print(rec)
        
        # Общая оценка качества
        print("\n" + "=" * 60)
        quality_score = overall
        if quality_score >= 85:
            quality_text = "🏆 ПРЕВОСХОДНОЕ КАЧЕСТВО"
            quality_color = "\033[92m"  # Зеленый
        elif quality_score >= 70:
            quality_text = "✅ ХОРОШЕЕ КАЧЕСТВО"
            quality_color = "\033[94m"  # Синий
        elif quality_score >= 50:
            quality_text = "⚠️ УДОВЛЕТВОРИТЕЛЬНОЕ"
            quality_color = "\033[93m"  # Желтый
        else:
            quality_text = "❌ ТРЕБУЕТ УЛУЧШЕНИЯ"
            quality_color = "\033[91m"  # Красный
        
        print(f"{quality_color}ИТОГО: {quality_text}\033[0m")
        
    except Exception as e:
        print(f"\n❌ Ошибка при анализе: {str(e)}")
        import traceback
        traceback.print_exc()
    
    wait_for_enter()

def list_photos(db: Database):
    clear_screen()
    print_header()
    print("СПИСОК ВСЕХ ФОТОГРАФИЙ\n")
    
    try:
        analyses = db.get_all_analyses(limit=100)
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        import traceback
        traceback.print_exc()
        wait_for_enter()
        return
    
    if not analyses:
        print("В базе данных нет фотографий.")
    else:
        print(f"Всего фото: {len(analyses)}\n")
        
        # Расширенный заголовок
        print("-" * 160)
        print(f"{'ID':<4} {'Файл':<20} {'Камера':<18} {'Оценка':<7} {'DxO':<5} "
              f"{'Резк':<6} {'Шум':<6} {'Дин. диап.':<5} {'Ярк':<5} {'Конт':<6} "
              f"{'Насыщ':<6} {'Эксп':<6} {'ISO':<5}")
        print("-" * 160)
        
        for analysis in analyses:
            try:
                pid = analysis.get('id', '?')
                filename = str(analysis.get('filename', 'Unknown'))[:20]
                camera = str(analysis.get('camera_model') or 'Unknown')[:18]
                
                # Общая оценка
                overall = analysis.get('overall_score', 0) or 0
                overall_str = f"{float(overall):.0f}%" if overall else "N/A"
                
                # DxOMark
                dxo = analysis.get('dxomark_score')
                dxo_str = str(dxo) if dxo else "-"
                
                # Резкость
                sharpness = analysis.get('sharpness_score')
                sharpness_str = f"{float(sharpness):.1f}" if sharpness and sharpness != 'N/A' else "N/A"
                
                # Шум
                noise = analysis.get('noise_level')
                noise_str = f"{float(noise):.1f}" if noise and noise != 'N/A' else "N/A"
                
                # Динамический диапазон
                dr = analysis.get('dynamic_range')
                dr_str = f"{float(dr):.1f}" if dr and dr != 'N/A' else "N/A"
                
                # Яркость
                brightness = analysis.get('brightness')
                if brightness and brightness != 'N/A':
                    brightness_str = f"{float(brightness) * 100:.0f}%"
                else:
                    brightness_str = "N/A"
                
                # Контраст
                contrast = analysis.get('contrast')
                if contrast and contrast != 'N/A':
                    contrast_str = f"{float(contrast) * 100:.0f}%"
                else:
                    contrast_str = "N/A"
                
                # Насыщенность
                saturation = analysis.get('saturation')
                if saturation and saturation != 'N/A':
                    saturation_str = f"{float(saturation) * 100:.0f}%"
                else:
                    saturation_str = "N/A"
                
                # Экспозиция
                exposure = analysis.get('exposure_score')
                if exposure and exposure != 'N/A':
                    exposure_str = f"{float(exposure) * 100:.0f}%"
                else:
                    exposure_str = "N/A"
                
                # ISO
                iso = analysis.get('iso')
                iso_str = str(iso) if iso and iso != 'N/A' else "-"
                
                print(f"{pid:<4} {filename:<20} {camera:<18} {overall_str:<7} {dxo_str:<5} "
                      f"{sharpness_str:<6} {noise_str:<6} {dr_str:<5} {brightness_str:<5} "
                      f"{contrast_str:<6} {saturation_str:<6} {exposure_str:<6} {iso_str:<5}")
                
            except Exception as e:
                print(f"Ошибка отображения: {e}")
                continue
        
        print("-" * 160)
    
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
    signal.signal(signal.SIGINT, signal_handler)
    
    analyzer = ImageAnalyzer()
    db = None
    
    # Задержка для стабилизации драйверов
    time.sleep(0.3)
    
    config = load_config()
    db_config = config.get('database', {})
    db_type = db_config.get('type', 'sqlite')
    
    # Если MS SQL Server - пробуем с повторными попытками
    if db_type == 'mssql':
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
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
                break
            except Exception as e:
                print(f"⚠️ Попытка {attempt + 1} подключения к MS SQL: {e}")
                if attempt < max_attempts - 1:
                    print("🔄 Переключаемся на SQLite...")
                    db = Database(db_type='sqlite', db_path='photo_analysis.db')
                    db_type = 'sqlite'  # Меняем тип для последующих попыток
                else:
                    print("❌ Не удалось подключиться к MS SQL, используем SQLite")
                    db = Database(db_type='sqlite', db_path='photo_analysis.db')
    else:
        # SQLite
        try:
            sqlite_config = db_config.get('sqlite', {})
            db_path = sqlite_config.get('db_path', 'photo_analysis.db')
            db = Database(db_type='sqlite', db_path=db_path)
        except Exception as e:
            print(f"⚠️ Ошибка SQLite: {e}")
            db = None
    
    # Если всё ещё нет подключения - создаём новую SQLite
    if db is None:
        print("📁 Создаём новую SQLite базу данных...")
        db = Database(db_type='sqlite', db_path='photo_analysis.db')
    
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

# 172.23.48.73
# 192.168.1.11
# 42145
# PhotoQualityAnalyzer


# RawPhotos\img1.dng
