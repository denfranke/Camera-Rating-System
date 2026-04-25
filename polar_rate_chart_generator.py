import matplotlib.pyplot as plt
import numpy as np


def create_radar_chart(categories, values, title, color="green"):
    """
    Создает лепестковую диаграмму с настройками

    Parameters:
    - categories: список названий категорий
    - values: список значений (0-100)
    - title: заголовок диаграммы
    - color: цвет диаграммы
    """
    N = len(categories)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()

    # Замыкаем данные
    values_plot = values + values[:1]
    angles_plot = angles + angles[:1]

    # Создаем диаграмму
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})

    # Строим график
    ax.plot(angles_plot, values_plot, "o-", linewidth=3, color=color)
    ax.fill(angles_plot, values_plot, alpha=0.3, color=color)

    # Настройка меток
    ax.set_xticks(angles)
    ax.set_xticklabels(categories, fontsize=10)

    # Настройка шкалы
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8)

    # Добавляем сетку
    ax.grid(True, linestyle="--", alpha=0.7)

    # Настройка внешнего вида
    ax.set_facecolor("#f5f5f5")
    ax.spines["polar"].set_visible(True)
    ax.spines["polar"].set_color("gray")

    # Заголовок
    plt.title(title, fontsize=16, pad=20, fontweight="bold")

    # Добавляем аннотации с значениями
    for angle, value, category in zip(angles, values, categories):
        ax.annotate(
            str(value),
            xy=(angle, value + 3),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
        )

    return fig, ax


# Использование функции
categories = [
    "Resolution",
    "Sharpness",
    "Color convetion",
    "Noise",
    "DXOMark rate",
]
values = [88, 76, 92, 81, 55]

fig, ax = create_radar_chart(categories, values, "Camera rate", "purple")
plt.show()
