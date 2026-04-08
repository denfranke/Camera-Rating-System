"""
tui_interface.py - TUI интерфейс для анализа фотографий
"""

import os
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich import box

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static, Input, ListView, ListItem, Label
from textual.screen import Screen
from textual import events

from database import Database
from analyzer import ImageAnalyzer


class PhotoAnalyzerApp(App):
    """Главное приложение TUI для анализа фотографий"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    DataTable {
        height: 60%;
        border: solid $primary;
    }
    
    Button {
        margin: 1;
    }
    
    .info-box {
        border: solid $secondary;
        padding: 1;
        margin: 1;
        height: 40%;
    }
    
    .status-bar {
        background: $panel;
        height: 3;
    }
    
    Horizontal {
        height: 5;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.analyzer = ImageAnalyzer()
        self.current_photo = None
        self.search_results = []
    
    def compose(self) -> ComposeResult:
        """Компоновка интерфейса"""
        yield Header(show_clock=True)
        
        with Container():
            yield Label("📸 Photo Quality Analyzer", classes="title")
            
            with Horizontal():
                yield Button("📁 Анализировать фото", variant="primary", id="analyze")
                yield Button("📊 Статистика", variant="default", id="stats")
                yield Button("🔍 Поиск", variant="default", id="search")
                yield Button("⭐ Оценить", variant="warning", id="rate")
                yield Button("🗑️ Удалить", variant="error", id="delete")
                yield Button("🚪 Выход", variant="default", id="exit")
            
            with ScrollableContainer():
                yield DataTable(id="photo_table")
            
            with ScrollableContainer():
                yield Static("📋 Детали фото:\n\nВыберите фото из таблицы для просмотра деталей", classes="info-box", id="details_panel")
        
        yield Footer()
    
    def on_mount(self):
        """При загрузке приложения"""
        table = self.query_one("#photo_table", DataTable)
        table.add_columns("ID", "Файл", "Камера", "Оценка", "Резкость", "Шум", "ISO", "Дата")
        table.cursor_type = "row"
        self.refresh_table()
    
    def refresh_table(self):
        """Обновляет таблицу с фото"""
        table = self.query_one("#photo_table", DataTable)
        table.clear()
        
        analyses = self.db.get_all_analyses(limit=50)
        
        for analysis in analyses:
            overall = f"{analysis.get('overall_score', 0):.0f}%" if analysis.get('overall_score') else "N/A"
            sharpness = f"{analysis.get('sharpness_score', 0):.0f}" if analysis.get('sharpness_score') else "N/A"
            noise = f"{analysis.get('noise_level', 0):.1f}" if analysis.get('noise_level') else "N/A"
            camera = analysis.get('camera_model', 'Unknown')[:20]
            date = analysis.get('analyzed_at', '')[:10] if analysis.get('analyzed_at') else ''
            
            table.add_row(
                str(analysis['id']),
                analysis['filename'][:30],
                camera,
                overall,
                sharpness,
                noise,
                str(analysis.get('iso', 'N/A')),
                date
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """При выборе строки в таблице показываем детали"""
        row = event.row
        if row is not None:
            photo_id = int(row[0])
            photo = self.db.get_analysis(photo_id)
            if photo:
                self.show_photo_details(photo)
    
    def on_button_pressed(self, event: Button.Pressed):
        """Обработка нажатий кнопок"""
        if event.button.id == "analyze":
            self.action_analyze()
        elif event.button.id == "stats":
            self.show_statistics()
        elif event.button.id == "search":
            self.show_search()
        elif event.button.id == "rate":
            self.action_rate()
        elif event.button.id == "delete":
            self.action_delete()
        elif event.button.id == "exit":
            self.exit()
    
    def action_analyze(self):
        """Анализ нового фото"""
        from rich.prompt import Prompt
        
        file_path = Prompt.ask("📁 Введите путь к фото")
        
        if not os.path.exists(file_path):
            self.show_error("Файл не найден!")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task("[cyan]Анализ фото...", total=100)
            
            try:
                result = self.analyzer.analyze(file_path)
                progress.update(task, completed=50)
                
                # Сохраняем в БД
                analysis_id = self.db.save_analysis(result)
                progress.update(task, completed=100)
                
                self.show_success(f"Фото проанализировано! ID: {analysis_id}")
                self.refresh_table()
                
                # Показываем детали
                self.show_photo_details(result)
                
            except Exception as e:
                self.show_error(f"Ошибка анализа: {str(e)}")
    
    def show_photo_details(self, photo: Dict[str, Any]):
        """Показывает детали фото"""
        panel = self.query_one("#details_panel", Static)
        
        # Оценка качества в виде прогресс-бара
        overall_score = photo.get('overall_score', 0)
        if overall_score >= 80:
            rating_icon = "🌟 Отлично"
        elif overall_score >= 60:
            rating_icon = "👍 Хорошо"
        elif overall_score >= 40:
            rating_icon = "📷 Средне"
        else:
            rating_icon = "⚠️ Плохо"
        
        details = f"""
[bold cyan]📷 {photo.get('filename', 'Unknown')}[/bold cyan]

[bold]Общая оценка: {overall_score:.1f}/100[/bold] {rating_icon}

[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]

[bold]📊 Метрики качества:[/bold]
  🎯 Общая оценка: [{'█' * int(overall_score/10)}{'░' * (10 - int(overall_score/10))}] {overall_score:.0f}%
  🔍 Резкость: {photo.get('sharpness_score', 0):.1f}
  🔊 Шум: {photo.get('noise_level', 0):.1f}
  ☀️ Динамический диапазон: {photo.get('dynamic_range', 0):.1f} EV
  🎨 Насыщенность: {photo.get('saturation', 0):.2f}
  💡 Яркость: {photo.get('brightness', 0):.2f}
  
[bold]🎨 Цветовой баланс:[/bold]
  🔴 Красный: {'█' * int(photo.get('avg_red', 0) * 20)}{'░' * (20 - int(photo.get('avg_red', 0) * 20))} {photo.get('avg_red', 0):.2f}
  🟢 Зеленый: {'█' * int(photo.get('avg_green', 0) * 20)}{'░' * (20 - int(photo.get('avg_green', 0) * 20))} {photo.get('avg_green', 0):.2f}
  🔵 Синий: {'█' * int(photo.get('avg_blue', 0) * 20)}{'░' * (20 - int(photo.get('avg_blue', 0) * 20))} {photo.get('avg_blue', 0):.2f}
  
[bold]📷 Информация о камере:[/bold]
  🏭 Производитель: {photo.get('camera_make', 'N/A')}
  📷 Модель: {photo.get('camera_model', 'N/A')}
  ⚡ ISO: {photo.get('iso', 'N/A')}
  🎞️ Выдержка: {photo.get('exposure_time', 'N/A')}
  🔭 Диафрагма: {photo.get('aperture', 'N/A')}
  📏 Фокусное: {photo.get('focal_length', 'N/A')}mm
  
[bold]📐 Размеры:[/bold]
  📏 Разрешение: {photo.get('image_width', 0)}x{photo.get('image_height', 0)} px
  💾 Размер файла: {photo.get('file_size', 0) // 1024} KB
        """
        
        panel.update(details)
    
    def show_statistics(self):
        """Показывает статистику"""
        stats = self.db.get_statistics()
        
        # Создаем rich таблицу для вывода в консоль (не в TUI)
        console = Console()
        console.clear()
        
        table = Table(title="📊 СТАТИСТИКА ПО ФОТОГРАФИЯМ", box=box.ROUNDED, style="bold")
        table.add_column("Показатель", style="cyan", width=30)
        table.add_column("Значение", style="green", width=30)
        
        table.add_row("📸 Всего фото", str(stats.get('total_photos', 0)))
        table.add_row("🎯 Средняя общая оценка", f"{stats.get('avg_overall_score', 0):.1f}/100")
        table.add_row("🔍 Средняя резкость", f"{stats.get('avg_sharpness', 0):.1f}")
        table.add_row("🔊 Средний уровень шума", f"{stats.get('avg_noise', 0):.1f}")
        table.add_row("⭐ Средняя оценка пользователя", f"{stats.get('avg_user_rating', 0):.1f}/5")
        
        console.print("\n")
        console.print(table)
        
        if stats.get('top_cameras'):
            cam_table = Table(title="🏆 ТОП-5 КАМЕР", box=box.SIMPLE)
            cam_table.add_column("Камера", style="cyan", width=30)
            cam_table.add_column("Количество фото", style="green", width=20)
            
            for cam in stats['top_cameras']:
                cam_table.add_row(cam['camera_model'], str(cam['count']))
            
            console.print(cam_table)
        
        console.print("\n[dim]Нажмите Enter для возврата в меню...[/dim]")
        input()
        
        # Обновляем интерфейс
        self.refresh_table()
    
    def show_search(self):
        """Поиск фото"""
        from rich.prompt import Prompt
        
        console = Console()
        query = Prompt.ask("🔍 Введите поисковый запрос (имя файла или тег)")
        
        if query:
            results = self.db.search_photos(query)
            
            console.clear()
            console.print(f"\n[bold cyan]🔍 РЕЗУЛЬТАТЫ ПОИСКА: '{query}'[/bold cyan]")
            console.print(f"[dim]Найдено {len(results)} фото[/dim]\n")
            
            if results:
                for r in results:
                    rating_stars = "⭐" * (r.get('user_rating') or 0) + "☆" * (5 - (r.get('user_rating') or 0))
                    console.print(f"  📸 [cyan]{r['filename']}[/cyan]")
                    console.print(f"     Оценка: {r.get('overall_score', 0):.0f}% | Пользователь: {rating_stars}")
                    console.print(f"     Теги: [yellow]{r.get('user_tags', '-')}[/yellow]")
                    console.print()
            else:
                console.print("[yellow]Фото не найдены[/yellow]")
            
            console.print("\n[dim]Нажмите Enter для возврата...[/dim]")
            input()
            
            self.refresh_table()
    
    def action_rate(self):
        """Оценка фото пользователем"""
        # Получаем выбранное фото из таблицы
        table = self.query_one("#photo_table", DataTable)
        if not table.cursor_row:
            self.show_error("Сначала выберите фото в таблице (нажмите Enter на строке)!")
            return
        
        row = table.cursor_row
        if row is None:
            self.show_error("Сначала выберите фото в таблице!")
            return
        
        photo_id = int(row[0])
        
        from rich.prompt import IntPrompt, Prompt
        rating = IntPrompt.ask("⭐ Оцените фото (1-5)", default=3, choices=["1", "2", "3", "4", "5"])
        
        if 1 <= rating <= 5:
            notes = Prompt.ask("📝 Заметки (опционально)", default="")
            tags = Prompt.ask("🏷️ Теги через запятую (опционально)", default="")
            
            self.db.update_rating(photo_id, rating, notes, tags)
            self.show_success("Оценка сохранена!")
            self.refresh_table()
    
    def action_delete(self):
        """Удаление фото из БД"""
        table = self.query_one("#photo_table", DataTable)
        if not table.cursor_row:
            self.show_error("Сначала выберите фото в таблице!")
            return
        
        row = table.cursor_row
        if row is None:
            self.show_error("Сначала выберите фото в таблице!")
            return
        
        photo_id = int(row[0])
        filename = row[1]
        
        from rich.prompt import Confirm
        if Confirm.ask(f"🗑️ Удалить фото '{filename}' из базы данных?"):
            self.db.delete_analysis(photo_id)
            self.refresh_table()
            self.show_success("Фото удалено!")
            
            # Очищаем панель деталей
            panel = self.query_one("#details_panel", Static)
            panel.update("📋 Детали фото:\n\nФото удалено. Выберите другое фото из таблицы.")
    
    def show_error(self, message: str):
        """Показывает ошибку"""
        from rich.prompt import Prompt
        console = Console()
        console.print(f"\n[bold red]❌ ОШИБКА: {message}[/bold red]")
        console.print("[dim]Нажмите Enter для продолжения...[/dim]")
        input()
    
    def show_success(self, message: str):
        """Показывает успех"""
        from rich.prompt import Prompt
        console = Console()
        console.print(f"\n[bold green]✅ {message}[/bold green]")
        console.print("[dim]Нажмите Enter для продолжения...[/dim]")
        input()


def run_tui():
    """Запускает TUI приложение"""
    app = PhotoAnalyzerApp()
    app.run()


if __name__ == "__main__":
    run_tui()