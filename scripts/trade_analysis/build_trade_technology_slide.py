from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "baci_russia_africa_products.csv"

OUTPUT_DIR = BASE_DIR / "reports" / "trade_technology_slide"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Последние пять лет для анализа технологической торговли
START_YEAR = 2020
END_YEAR = 2024

# Число стран и товарных позиций для тепловой карты
TOP_COUNTRIES = 15
TOP_PRODUCTS = 12

# BACI: стоимость указана в тысячах долларов США
# Перевод в миллионы долларов: делим на 1000
# Перевод в миллиарды долларов: делим на 1 000 000

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 10


# ============================================================
# 2. ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ
# ============================================================

print("=" * 75)
print("ТЕХНОЛОГИЧЕСКАЯ ТОРГОВЛЯ РОССИИ И АФРИКИ")
print("=" * 75)

df = pd.read_csv(INPUT_FILE)

print(f"\nИсходная база: {df.shape}")

# Приведение кодов HS6 к единому формату
df["hs6"] = (
    df["hs6"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(6)
)

df["hs2"] = df["hs6"].str[:2]

# Направления торговли
flow_mapping = {
    "exports_to_russia": "Africa_to_Russia",
    "imports_from_russia": "Russia_to_Africa"
}

df["direction"] = df["trade_flow"].map(flow_mapping)

df = df[df["direction"].notna()].copy()

# Выбираем технологический сегмент HS84–HS90
df["hs2_num"] = pd.to_numeric(df["hs2"], errors="coerce")

df = df[
    df["hs2_num"].between(84, 90)
].copy()

# Период анализа
df = df[
    df["year"].between(START_YEAR, END_YEAR)
].copy()

# Убираем нулевые и отрицательные значения
df = df[df["value_thousand_usd"] > 0].copy()

print(f"Технологическая база: {df.shape}")
print(f"Период: {START_YEAR}–{END_YEAR}")

# Названия товарных глав HS2
hs2_names = {
    "84": "Машины и механическое оборудование",
    "85": "Электрические машины и аппаратура",
    "86": "Железнодорожное оборудование",
    "87": "Автомобили и транспортные средства",
    "88": "Летательные аппараты",
    "89": "Суда и плавучие конструкции",
    "90": "Оптические и измерительные приборы"
}


# ============================================================
# 3. ВИЗУАЛИЗАЦИЯ №1
# ОБЪЁМ ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ ПО ГРУППАМ HS2
# ============================================================

print("\n" + "=" * 75)
print("1. СТРУКТУРА ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ")
print("=" * 75)

structure = (
    df.groupby(["hs2", "direction"])["value_thousand_usd"]
    .sum()
    .reset_index()
)

structure["value_billion_usd"] = (
    structure["value_thousand_usd"] / 1_000_000
)

structure_pivot = (
    structure.pivot(
        index="hs2",
        columns="direction",
        values="value_billion_usd"
    )
    .fillna(0)
)

structure_pivot = structure_pivot.reindex(
    [str(i) for i in range(84, 91)],
    fill_value=0
)

structure_pivot["Africa_to_Russia"] *= -1

labels = [
    hs2_names.get(code, code)
    for code in structure_pivot.index
]

fig, ax = plt.subplots(figsize=(13, 7))

y = np.arange(len(structure_pivot))

ax.barh(
    y,
    structure_pivot["Africa_to_Russia"],
    color="#4C91C7",
    label="Экспорт Африки в Россию"
)

ax.barh(
    y,
    structure_pivot["Russia_to_Africa"],
    color="#E39A45",
    label="Экспорт России в Африку"
)

ax.set_yticks(y)
ax.set_yticklabels(labels)

ax.axvline(0, color="black", linewidth=0.9)

ax.set_xlabel("Млрд долл. США")
ax.set_ylabel("")

ax.legend(loc="lower right", frameon=False)

ax.grid(axis="x", alpha=0.2)
ax.set_axisbelow(True)

# Подписи значений
for i, code in enumerate(structure_pivot.index):

    africa_value = abs(
        structure_pivot.loc[code, "Africa_to_Russia"]
    )

    russia_value = (
        structure_pivot.loc[code, "Russia_to_Africa"]
    )

    if africa_value > 0:
        ax.text(
            -africa_value,
            i,
            f" {africa_value:.2f}",
            ha="right",
            va="center",
            fontsize=8
        )

    if russia_value > 0:
        ax.text(
            russia_value,
            i,
            f"{russia_value:.2f} ",
            ha="left",
            va="center",
            fontsize=8
        )

fig.tight_layout()

fig.savefig(
    OUTPUT_DIR / "01_technology_trade_structure.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print("\nОбъёмы торговли по направлениям:")
print(structure_pivot)


# ============================================================
# 4. ВИЗУАЛИЗАЦИЯ №2
# ТЕПЛОВАЯ КАРТА: СТРАНЫ × ТОВАРЫ HS6
# ============================================================

print("\n" + "=" * 75)
print("2. ТЕПЛОВАЯ КАРТА ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ")
print("=" * 75)

# Общий объём торговли по странам и товарам
heatmap_data = (
    df.groupby(["country_name", "hs6"])["value_thousand_usd"]
    .sum()
    .reset_index()
)

# Выбираем наиболее значимые товарные позиции
top_products = (
    heatmap_data.groupby("hs6")["value_thousand_usd"]
    .sum()
    .nlargest(TOP_PRODUCTS)
    .index
)

# Выбираем наиболее значимые страны
top_countries = (
    heatmap_data.groupby("country_name")["value_thousand_usd"]
    .sum()
    .nlargest(TOP_COUNTRIES)
    .index
)

heatmap_data = heatmap_data[
    heatmap_data["hs6"].isin(top_products)
    & heatmap_data["country_name"].isin(top_countries)
]

heatmap_pivot = (
    heatmap_data.pivot(
        index="country_name",
        columns="hs6",
        values="value_thousand_usd"
    )
    .fillna(0)
)

# Переводим в миллионы долларов
heatmap_pivot = heatmap_pivot / 1000

# Логарифмируем значения для читаемости:
# иначе несколько крупных сделок могут визуально подавить остальные
heatmap_log = np.log1p(heatmap_pivot)

fig, ax = plt.subplots(figsize=(14, 8))

im = ax.imshow(
    heatmap_log,
    aspect="auto",
    cmap="YlOrRd"
)

ax.set_yticks(np.arange(len(heatmap_pivot.index)))
ax.set_yticklabels(heatmap_pivot.index)

ax.set_xticks(np.arange(len(heatmap_pivot.columns)))
ax.set_xticklabels(
    heatmap_pivot.columns,
    rotation=45,
    ha="right"
)

ax.set_xlabel("Товарные позиции HS6")
ax.set_ylabel("Африканские страны")

cbar = fig.colorbar(im, ax=ax)
cbar.set_label("ln(1 + объём торговли, млн долл. США)")

fig.tight_layout()

fig.savefig(
    OUTPUT_DIR / "02_technology_trade_heatmap.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print("\nСтраны и товары для тепловой карты:")
print(heatmap_pivot)


# ============================================================
# 5. ВИЗУАЛИЗАЦИЯ №3
# УСТОЙЧИВОСТЬ ТЕХНОЛОГИЧЕСКИХ ТОРГОВЫХ СВЯЗЕЙ
# ============================================================

print("\n" + "=" * 75)
print("3. УСТОЙЧИВОСТЬ ТОРГОВЫХ СВЯЗЕЙ")
print("=" * 75)

# Единица анализа: страна × товар HS6 × направление.
# Считаем, в скольких годах из пяти наблюдалась торговля.

persistence = (
    df.groupby(
        ["country_name", "hs6", "direction"]
    )["year"]
    .nunique()
    .reset_index(name="years_with_trade")
)

# Стабильная связь: торговля наблюдалась минимум в 4 годах из 5
persistence["stable"] = (
    persistence["years_with_trade"] >= 4
)

persistence_summary = (
    persistence.groupby("direction")
    .agg(
        total_links=("hs6", "count"),
        stable_links=("stable", "sum")
    )
    .reset_index()
)

persistence_summary["stable_share_pct"] = (
    persistence_summary["stable_links"]
    / persistence_summary["total_links"]
    * 100
)

persistence_summary["direction"] = (
    persistence_summary["direction"].map({
        "Africa_to_Russia": "Экспорт Африки в Россию",
        "Russia_to_Africa": "Экспорт России в Африку"
    })
)

print("\nРезультаты устойчивости:")
print(persistence_summary)


# Диаграмма
fig, ax = plt.subplots(figsize=(9, 5))

colors = ["#4C91C7", "#E39A45"]

bars = ax.bar(
    persistence_summary["direction"],
    persistence_summary["stable_share_pct"],
    color=colors,
    width=0.55
)

ax.set_ylabel("Доля устойчивых связей, %")
ax.set_ylim(0, 100)

ax.grid(axis="y", alpha=0.2)
ax.set_axisbelow(True)

for bar, value in zip(
    bars,
    persistence_summary["stable_share_pct"]
):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 2,
        f"{value:.1f}%",
        ha="center",
        va="bottom",
        fontsize=11
    )

fig.tight_layout()

fig.savefig(
    OUTPUT_DIR / "03_technology_trade_persistence.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)


# ============================================================
# 6. ЭКСПОРТ ДАННЫХ В EXCEL
# ============================================================

print("\n" + "=" * 75)
print("4. СОХРАНЕНИЕ ДАННЫХ")
print("=" * 75)

# Динамика технологической торговли по годам
dynamics = (
    df.groupby(["year", "direction"])["value_thousand_usd"]
    .sum()
    .reset_index()
)

dynamics["value_billion_usd"] = (
    dynamics["value_thousand_usd"] / 1_000_000
)

dynamics_pivot = (
    dynamics.pivot(
        index="year",
        columns="direction",
        values="value_billion_usd"
    )
    .fillna(0)
    .reset_index()
)

# Подготовка структуры для Excel
structure_excel = structure_pivot.copy()

structure_excel["Africa_to_Russia"] = (
    structure_excel["Africa_to_Russia"].abs()
)

structure_excel = structure_excel.reset_index()

structure_excel["Товарная группа"] = (
    structure_excel["hs2"].map(hs2_names)
)

# Сохраняем таблицы
excel_path = OUTPUT_DIR / "technology_trade_data.xlsx"

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:

    dynamics_pivot.to_excel(
        writer,
        sheet_name="Динамика",
        index=False
    )

    structure_excel.to_excel(
        writer,
        sheet_name="Структура_HS2",
        index=False
    )

    heatmap_pivot.to_excel(
        writer,
        sheet_name="Тепловая карта"
    )

    persistence.to_excel(
        writer,
        sheet_name="Устойчивость_по_связям",
        index=False
    )

    persistence_summary.to_excel(
        writer,
        sheet_name="Устойчивость_итог",
        index=False
    )

    # Полная детализация HS6 для дальнейшего анализа
    product_detail = (
        df.groupby(
            ["country_name", "hs6", "direction"]
        )["value_thousand_usd"]
        .sum()
        .reset_index()
    )

    product_detail["value_million_usd"] = (
        product_detail["value_thousand_usd"] / 1000
    )

    product_detail.to_excel(
        writer,
        sheet_name="Детализация_HS6",
        index=False
    )


# ============================================================
# 7. ИТОГ
# ============================================================

print("\n" + "=" * 75)
print("ГОТОВО")
print("=" * 75)

print(f"\nВсе результаты сохранены в папке:")
print(OUTPUT_DIR)

print("\nСозданы визуализации:")
print("1. 01_technology_trade_structure.png")
print("2. 02_technology_trade_heatmap.png")
print("3. 03_technology_trade_persistence.png")

print("\nСоздан Excel-файл:")
print("technology_trade_data.xlsx")

print("\nПериод анализа:", START_YEAR, "–", END_YEAR)
print("Количество стран:", df["country_name"].nunique())
print("Количество товарных позиций HS6:", df["hs6"].nunique())