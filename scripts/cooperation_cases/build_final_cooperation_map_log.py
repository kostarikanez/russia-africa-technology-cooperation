
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRADE_FILE = (
    BASE_DIR / "data" / "processed"
    / "baci_russia_africa_products.csv"
)

CLUSTERS_FILE = (
    BASE_DIR / "reports"
    / "country_clusters.csv"
)

OUTPUT_DIR = (
    BASE_DIR / "reports"
    / "final_cooperation_map_log"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_YEAR = 2020
END_YEAR = 2024

STABLE_YEARS = 4

CASE_COUNTRIES = [
    "South Africa",
    "Egypt",
    "Morocco",
    "Algeria",
    "Angola",
    "Gabon"
]

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 10


# ============================================================
# 2. ЗАГРУЗКА ДАННЫХ
# ============================================================

print("=" * 75)
print("КАРТА ТЕХНОЛОГИЧЕСКОГО СОТРУДНИЧЕСТВА")
print("АЛЬТЕРНАТИВНАЯ ВЕРСИЯ: ЛОГАРИФМИЧЕСКАЯ ШКАЛА")
print("=" * 75)

trade = pd.read_csv(TRADE_FILE)
clusters = pd.read_csv(CLUSTERS_FILE)

print("Торговая база:", trade.shape)
print("База кластеризации:", clusters.shape)

required_trade = {
    "year",
    "country_iso3",
    "country_name",
    "hs6",
    "trade_flow",
    "value_thousand_usd"
}

required_clusters = {
    "country_iso3",
    "country_name",
    "mean_index",
    "kmeans_cluster"
}

assert required_trade.issubset(trade.columns), (
    f"Не хватает столбцов в торговой базе: "
    f"{required_trade - set(trade.columns)}"
)

assert required_clusters.issubset(clusters.columns), (
    f"Не хватает столбцов в базе кластеризации: "
    f"{required_clusters - set(clusters.columns)}"
)


# ============================================================
# 3. ФИЛЬТРАЦИЯ ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ
# ============================================================

trade["hs6"] = (
    trade["hs6"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(6)
)

trade["hs2"] = trade["hs6"].str[:2]

trade["hs2_num"] = pd.to_numeric(
    trade["hs2"],
    errors="coerce"
)

trade = trade[
    trade["hs2_num"].between(84, 90)
].copy()

trade = trade[
    trade["year"].between(START_YEAR, END_YEAR)
].copy()

trade = trade[
    trade["value_thousand_usd"] > 0
].copy()

trade["country_iso3"] = (
    trade["country_iso3"].astype(str).str.upper()
)

clusters["country_iso3"] = (
    clusters["country_iso3"].astype(str).str.upper()
)

print("\nПериод:", START_YEAR, "-", END_YEAR)
print("Количество торговых записей:", len(trade))


# ============================================================
# 4. ОБЪЁМ ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ ПО СТРАНАМ
# ============================================================

country_trade = (
    trade.groupby(
        ["country_iso3", "country_name"]
    )["value_thousand_usd"]
    .sum()
    .reset_index()
)

country_trade["technology_trade_mln_usd"] = (
    country_trade["value_thousand_usd"] / 1000
)


# ============================================================
# 5. УСТОЙЧИВЫЕ ТОРГОВЫЕ СВЯЗИ
# ============================================================

links = (
    trade.groupby(
        [
            "country_iso3",
            "country_name",
            "hs6",
            "trade_flow"
        ]
    )["year"]
    .nunique()
    .reset_index(name="years_with_trade")
)

links["stable"] = (
    links["years_with_trade"] >= STABLE_YEARS
)

country_stability = (
    links.groupby("country_iso3")
    .agg(
        total_links=("hs6", "count"),
        stable_links=("stable", "sum")
    )
    .reset_index()
)

print("\nУстойчивые связи по странам:")
print(
    country_stability.sort_values(
        "stable_links",
        ascending=False
    ).head(15).to_string(index=False)
)


# ============================================================
# 6. ОБЪЕДИНЕНИЕ С ИНДЕКСОМ ТЕХНОЛОГИЧЕСКОЙ ГОТОВНОСТИ
# ============================================================

data = clusters.merge(
    country_trade[
        ["country_iso3", "technology_trade_mln_usd"]
    ],
    on="country_iso3",
    how="left"
)

data = data.merge(
    country_stability[
        ["country_iso3", "total_links", "stable_links"]
    ],
    on="country_iso3",
    how="left"
)

data["technology_trade_mln_usd"] = (
    data["technology_trade_mln_usd"].fillna(0)
)

data["total_links"] = (
    data["total_links"].fillna(0)
)

data["stable_links"] = (
    data["stable_links"].fillna(0).astype(int)
)

data = data.dropna(
    subset=["mean_index", "kmeans_cluster"]
).copy()

print("\nКоличество стран в итоговой матрице:", len(data))


# ============================================================
# 7. ГРАНИЦЫ КВАДРАНТОВ
# ============================================================

x_median = data["mean_index"].median()

positive_stability = data.loc[
    data["stable_links"] > 0,
    "stable_links"
]

if len(positive_stability) > 0:
    y_median = positive_stability.median()
else:
    y_median = 1

print("\nГраницы квадрантов:")
print("Медиана индекса готовности:", round(x_median, 2))
print("Медиана устойчивых связей:", round(y_median, 2))


# ============================================================
# 8. ПОДГОТОВКА РАЗМЕРОВ И ЦВЕТОВ ПУЗЫРЕЙ
# ============================================================

cluster_values = sorted(
    data["kmeans_cluster"].unique(),
    key=lambda x: str(x)
)

palette = plt.get_cmap("Set2")

cluster_colors = {
    cluster: palette(i % 8)
    for i, cluster in enumerate(cluster_values)
}

max_trade = data["technology_trade_mln_usd"].max()

if max_trade > 0:
    bubble_sizes = (
        35
        + 450 * np.sqrt(
            data["technology_trade_mln_usd"] / max_trade
        )
    )
else:
    bubble_sizes = pd.Series(
        35,
        index=data.index
    )


# ============================================================
# 9. ПОСТРОЕНИЕ ДИАГРАММЫ
# ============================================================

fig, ax = plt.subplots(figsize=(16, 10))

for cluster in cluster_values:

    subset = data[
        data["kmeans_cluster"] == cluster
    ]

    ax.scatter(
        subset["mean_index"],
        subset["stable_links"],
        s=bubble_sizes.loc[subset.index],
        color=cluster_colors[cluster],
        alpha=0.78,
        edgecolors="white",
        linewidths=1.1,
        label=f"Кластер {cluster}",
        zorder=3
    )


# ============================================================
# 10. ЛОГАРИФМИЧЕСКАЯ ШКАЛА Y
# ============================================================

# Symmetrical log scale позволяет сохранить нулевые значения.
# linthresh=1: участок от 0 до 1 отображается линейно.
# Значения выше 1 отображаются логарифмически.

ax.set_yscale(
    "symlog",
    linthresh=1,
    linscale=1,
    base=10
)

# Границы осей
x_min = max(0, data["mean_index"].min() - 5)
x_max = min(100, data["mean_index"].max() + 10)

y_max = max(
    10,
    data["stable_links"].max() * 1.3
)

ax.set_xlim(x_min, x_max)
ax.set_ylim(0, y_max)

# Задаём понятные деления оси Y
y_ticks = [
    value
    for value in [0, 1, 2, 5, 10, 20, 50, 100, 200, 500]
    if value <= y_max
]

ax.set_yticks(y_ticks)
ax.set_yticklabels([str(value) for value in y_ticks])


# ============================================================
# 11. ЛИНИИ КВАДРАНТОВ
# ============================================================

ax.axvline(
    x_median,
    color="#555555",
    linestyle="--",
    linewidth=1.2,
    alpha=0.75
)

ax.axhline(
    y_median,
    color="#555555",
    linestyle="--",
    linewidth=1.2,
    alpha=0.75
)


# ============================================================
# 12. ПОДПИСИ КВАДРАНТОВ
# ============================================================

# Координаты в долях области построения.
# Поэтому подписи не зависят от логарифмической шкалы.

ax.text(
    0.56, 0.94,
    "ПЛАТФОРМА ДЛЯ\nСОВМЕСТНЫХ ПРОЕКТОВ",
    transform=ax.transAxes,
    fontsize=10,
    weight="bold",
    color="#426B54",
    ha="left",
    va="top"
)

ax.text(
    0.09, 0.94,
    "АДАПТАЦИЯ\nИ ОБУЧЕНИЕ",
    transform=ax.transAxes,
    fontsize=10,
    weight="bold",
    color="#8A633C",
    ha="left",
    va="top"
)

ax.text(
    0.56, 0.20,
    "РАСШИРЕНИЕ\nТЕХНОЛОГИЧЕСКОГО ОБМЕНА",
    transform=ax.transAxes,
    fontsize=9,
    weight="bold",
    color="#536C8B",
    ha="left",
    va="bottom"
)

ax.text(
    0.09, 0.20,
    "ДОЛГОСРОЧНОЕ\nРАЗВИТИЕ",
    transform=ax.transAxes,
    fontsize=9,
    weight="bold",
    color="#777777",
    ha="left",
    va="bottom"
)


# ============================================================
# 13. ПОДПИСИ ВЫБРАННЫХ СТРАН
# ============================================================

case_data = data[
    data["country_name"].isin(CASE_COUNTRIES)
]

for _, row in case_data.iterrows():

    ax.annotate(
        row["country_name"],
        (
            row["mean_index"],
            row["stable_links"]
        ),
        xytext=(7, 7),
        textcoords="offset points",
        fontsize=9,
        weight="bold",
        arrowprops={
            "arrowstyle": "-",
            "color": "#444444",
            "linewidth": 0.7
        },
        zorder=5
    )


# ============================================================
# 14. ОФОРМЛЕНИЕ ОСЕЙ
# ============================================================

ax.set_xlabel(
    "Индекс технологической готовности страны (0–100)",
    fontsize=12,
    labelpad=12
)

ax.set_ylabel(
    "Количество устойчивых технологических торговых связей (логарифмическая шкала)",
    fontsize=12,
    labelpad=12
)

ax.grid(
    alpha=0.17,
    linestyle=":"
)

ax.set_axisbelow(True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)


# ============================================================
# 15. ЛЕГЕНДА КЛАСТЕРОВ
# ============================================================

cluster_handles = [
    Line2D(
        [0], [0],
        marker="o",
        color="w",
        markerfacecolor=cluster_colors[c],
        markersize=10,
        label=f"Кластер {c}"
    )
    for c in cluster_values
]

cluster_legend = ax.legend(
    handles=cluster_handles,
    title="Группы технологической зрелости",
    loc="upper right",
    frameon=False
)

ax.add_artist(cluster_legend)


# ============================================================
# 16. ЛЕГЕНДА ОБЪЁМА ТОРГОВЛИ
# ============================================================

if max_trade > 0:

    reference_values = sorted(
        set([
            data["technology_trade_mln_usd"].quantile(0.25),
            data["technology_trade_mln_usd"].quantile(0.50),
            data["technology_trade_mln_usd"].quantile(0.75)
        ])
    )

    size_handles = []

    for value in reference_values:

        size = (
            35
            + 450 * np.sqrt(value / max_trade)
        )

        handle = ax.scatter(
            [],
            [],
            s=size,
            color="#777777",
            alpha=0.55,
            edgecolors="white",
            label=f"{value:.1f} млн $"
        )

        size_handles.append(handle)

    ax.legend(
        handles=size_handles,
        title="Объём торговли",
        loc="lower right",
        frameon=False
    )


# ============================================================
# 17. СОХРАНЕНИЕ
# ============================================================

fig.tight_layout()

output_png = (
    OUTPUT_DIR
    / "final_technology_cooperation_map_log.png"
)

fig.savefig(
    output_png,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)


# ============================================================
# 18. ЭКСПОРТ ДАННЫХ
# ============================================================

data.to_csv(
    OUTPUT_DIR / "final_cooperation_map_data.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 19. ИТОГОВАЯ ИНФОРМАЦИЯ
# ============================================================

print("\n" + "=" * 75)
print("ГОТОВО")
print("=" * 75)

print("\nВизуализация:")
print(output_png)

print("\nТаблица данных:")
print(
    OUTPUT_DIR / "final_cooperation_map_data.csv"
)

print("\nСтраны с наибольшим числом устойчивых связей:")

print(
    data[
        [
            "country_name",
            "mean_index",
            "stable_links",
            "technology_trade_mln_usd"
        ]
    ]
    .sort_values(
        "stable_links",
        ascending=False
    )
    .head(15)
    .to_string(index=False)
)

print("\nИспользована симметричная логарифмическая шкала Y.")
