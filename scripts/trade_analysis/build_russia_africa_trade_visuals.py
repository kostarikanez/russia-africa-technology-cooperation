
from pathlib import Path
import re

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 1. ПУТИ И ПАРАМЕТРЫ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "reports" / "trade_visuals"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

ANNUAL_FILE = DATA_DIR / "baci_russia_africa_annual.csv"
PRODUCT_FILE = DATA_DIR / "baci_russia_africa_products.csv"

OUTPUT_EXCEL = REPORT_DIR / "russia_africa_trade_data.xlsx"
OUTPUT_PNG = REPORT_DIR / "russia_africa_trade_structure.png"

START_YEAR = 2000
END_YEAR = 2024

# BACI: стоимость в тысячах долларов США
USD_TO_BILLION = 1_000_000


# ============================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def normalize_columns(df):
    df.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    ]
    return df


def check_file(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Не найден файл: {path}"
        )


def normalize_hs6(value):
    """Приведение кода товара к шести цифрам HS6."""
    if pd.isna(value):
        return None

    code = re.sub(r"\D", "", str(value))

    if not code:
        return None

    return code.zfill(6)[-6:]


def classify_flow(value):
    """
    Определяет направление торговли.

    Africa_to_Russia:
        экспорт африканских стран в Россию.

    Russia_to_Africa:
        экспорт России в африканские страны.
    """

    value = str(value).strip().lower()
    value = value.replace(" ", "_").replace("-", "_")

    # Африка -> Россия
    africa_to_russia_variants = {
        "exports_to_russia",
        "export_to_russia",
        "africa_to_russia",
        "africa_exports_to_russia",
        "export_africa_to_russia",
        "africa_exports",
        "africa_to_rus",
    }

    # Россия -> Африка
    russia_to_africa_variants = {
        "imports_from_russia",
        "import_from_russia",
        "russia_to_africa",
        "russia_exports_to_africa",
        "export_russia_to_africa",
        "russia_exports",
        "rus_to_africa",
    }

    if value in africa_to_russia_variants:
        return "Africa_to_Russia"

    if value in russia_to_africa_variants:
        return "Russia_to_Africa"

    # Дополнительное распознавание распространенных вариантов
    compact = re.sub(r"[^a-z]", "", value)

    if (
        "africa" in compact and "russia" in compact
        and (
            "to" in compact
            or "export" in compact
        )
    ):
        if compact.find("africa") < compact.find("russia"):
            return "Africa_to_Russia"

        return "Russia_to_Africa"

    if "exportstorussia" in compact:
        return "Africa_to_Russia"

    if "importsfromrussia" in compact:
        return "Russia_to_Africa"

    return None


def classify_complexity(chapter):
    """
    Условная группировка товарных глав HS
    по характеру продукции и технологической сложности.
    """

    # Блок 1. Первичные товары и сырье
    if 1 <= chapter <= 27:
        return "1. Первичные товары и сырье"

    # Блок 2. Переработанные материалы и химическая продукция
    elif 28 <= chapter <= 83:
        return "2. Переработанные материалы и продукция"

    # Блок 3. Машины, оборудование и транспорт
    elif 84 <= chapter <= 89:
        return "3. Машины, оборудование и транспорт"

    # Блок 4. Точные приборы и специальные товары
    elif 90 <= chapter <= 97:
        return "4. Точные приборы и специальные товары"

    return "Прочие товары"


# ============================================================
# 3. ПРОВЕРКА И ЗАГРУЗКА БАЗ
# ============================================================

print("=" * 75)
print("АНАЛИЗ ТОРГОВЛИ РОССИИ И АФРИКИ")
print("=" * 75)

check_file(ANNUAL_FILE)
check_file(PRODUCT_FILE)

annual = pd.read_csv(ANNUAL_FILE, low_memory=False)

products = pd.read_csv(
    PRODUCT_FILE,
    low_memory=False,
    dtype={"hs6": str}
)

annual = normalize_columns(annual)
products = normalize_columns(products)

print("\nГодовая база:", annual.shape)
print("Товарная база:", products.shape)

print("\nКолонки годовой базы:")
print(list(annual.columns))

print("\nКолонки товарной базы:")
print(list(products.columns))


# Проверка обязательных колонок
annual_required = [
    "year",
    "exports_to_russia_thousand_usd",
    "imports_from_russia_thousand_usd",
]

product_required = [
    "year",
    "country_iso3",
    "country_name",
    "hs6",
    "trade_flow",
    "value_thousand_usd",
    "quantity_tons",
]

for col in annual_required:
    if col not in annual.columns:
        raise ValueError(
            f"В годовой базе отсутствует колонка {col}"
        )

for col in product_required:
    if col not in products.columns:
        raise ValueError(
            f"В товарной базе отсутствует колонка {col}"
        )


# ============================================================
# 4. ДИНАМИКА ДВУСТОРОННЕЙ ТОРГОВЛИ
# ============================================================

print("\n" + "=" * 75)
print("1. ДИНАМИКА ТОРГОВЛИ")
print("=" * 75)

annual["year"] = pd.to_numeric(
    annual["year"], errors="coerce"
)

annual["exports_to_russia_thousand_usd"] = pd.to_numeric(
    annual["exports_to_russia_thousand_usd"],
    errors="coerce"
).fillna(0)

annual["imports_from_russia_thousand_usd"] = pd.to_numeric(
    annual["imports_from_russia_thousand_usd"],
    errors="coerce"
).fillna(0)

annual = annual[
    annual["year"].between(START_YEAR, END_YEAR)
].copy()

dynamics = (
    annual.groupby("year", as_index=False)
    .agg({
        "exports_to_russia_thousand_usd": "sum",
        "imports_from_russia_thousand_usd": "sum",
    })
)

dynamics = dynamics.rename(columns={
    "year": "Год",
    "exports_to_russia_thousand_usd":
        "Экспорт Африки в Россию, тыс. USD",
    "imports_from_russia_thousand_usd":
        "Экспорт России в Африку, тыс. USD",
})

dynamics["Товарооборот, тыс. USD"] = (
    dynamics["Экспорт Африки в Россию, тыс. USD"]
    + dynamics["Экспорт России в Африку, тыс. USD"]
)

dynamics["Сальдо торговли в пользу России, тыс. USD"] = (
    dynamics["Экспорт России в Африку, тыс. USD"]
    - dynamics["Экспорт Африки в Россию, тыс. USD"]
)

dynamics["Экспорт Африки в Россию, млрд USD"] = (
    dynamics["Экспорт Африки в Россию, тыс. USD"]
    / USD_TO_BILLION
)

dynamics["Экспорт России в Африку, млрд USD"] = (
    dynamics["Экспорт России в Африку, тыс. USD"]
    / USD_TO_BILLION
)

dynamics["Товарооборот, млрд USD"] = (
    dynamics["Товарооборот, тыс. USD"]
    / USD_TO_BILLION
)

dynamics = dynamics.sort_values("Год")

print("\nГодовая динамика:")
print(dynamics.to_string(index=False))

print("\nИТОГО ЗА ПЕРИОД:")

print(
    "Экспорт Африки в Россию:",
    round(
        dynamics["Экспорт Африки в Россию, млрд USD"].sum(),
        2
    ),
    "млрд USD"
)

print(
    "Экспорт России в Африку:",
    round(
        dynamics["Экспорт России в Африку, млрд USD"].sum(),
        2
    ),
    "млрд USD"
)

print(
    "Общий товарооборот:",
    round(
        dynamics["Товарооборот, млрд USD"].sum(),
        2
    ),
    "млрд USD"
)


# ============================================================
# 5. ПОДГОТОВКА ТОВАРНОЙ БАЗЫ
# ============================================================

print("\n" + "=" * 75)
print("2. ПОДГОТОВКА ТОВАРНОЙ СТРУКТУРЫ")
print("=" * 75)

products["year"] = pd.to_numeric(
    products["year"], errors="coerce"
)

products["value_thousand_usd"] = pd.to_numeric(
    products["value_thousand_usd"],
    errors="coerce"
).fillna(0)

products["quantity_tons"] = pd.to_numeric(
    products["quantity_tons"],
    errors="coerce"
).fillna(0)

products = products[
    products["year"].between(START_YEAR, END_YEAR)
].copy()

products["hs6_normalized"] = products["hs6"].apply(
    normalize_hs6
)

products = products[
    products["hs6_normalized"].notna()
].copy()

products["chapter"] = products["hs6_normalized"].apply(
    lambda x: int(x[:2])
)

# Определение направления торговли
products["direction"] = products["trade_flow"].apply(
    classify_flow
)

print("\nРаспределение исходных значений trade_flow:")
print(products["trade_flow"].value_counts(dropna=False))

print("\nРаспределение распознанных направлений:")
print(products["direction"].value_counts(dropna=False))

# Проверяем, не остались ли неизвестные направления
unknown_flows = products.loc[
    products["direction"].isna(),
    "trade_flow"
].drop_duplicates().tolist()

if unknown_flows:
    raise ValueError(
        "Не удалось распознать следующие значения trade_flow: "
        f"{unknown_flows}. Добавь их в функцию classify_flow."
    )

# Проверка наличия обоих направлений
if products["direction"].nunique() != 2:
    raise ValueError(
        "В товарной базе обнаружено не два направления торговли. "
        "Проверь значения trade_flow."
    )


# ============================================================
# 6. ФОРМИРОВАНИЕ ДВУСТОРОННИХ ПОТОКОВ
# ============================================================

products["Africa_to_Russia"] = np.where(
    products["direction"] == "Africa_to_Russia",
    products["value_thousand_usd"],
    0
)

products["Russia_to_Africa"] = np.where(
    products["direction"] == "Russia_to_Africa",
    products["value_thousand_usd"],
    0
)

print("\nПроверка направлений:")

print(
    "Африка -> Россия:",
    round(products["Africa_to_Russia"].sum() / USD_TO_BILLION, 2),
    "млрд USD"
)

print(
    "Россия -> Африка:",
    round(products["Russia_to_Africa"].sum() / USD_TO_BILLION, 2),
    "млрд USD"
)


# ============================================================
# 7. КЛАССИФИКАЦИЯ ПО ТОВАРНЫМ БЛОКАМ
# ============================================================

products["complexity_block"] = products["chapter"].apply(
    classify_complexity
)

block_order = [
    "1. Первичные товары и сырье",
    "2. Переработанные материалы и продукция",
    "3. Машины, оборудование и транспорт",
    "4. Точные приборы и специальные товары",
    "Прочие товары",
]


# ============================================================
# 8. СТРУКТУРА ТОРГОВЛИ ПО БЛОКАМ
# ============================================================

structure = (
    products.groupby("complexity_block", as_index=False)
    .agg({
        "Africa_to_Russia": "sum",
        "Russia_to_Africa": "sum",
    })
)

structure["complexity_block"] = pd.Categorical(
    structure["complexity_block"],
    categories=block_order,
    ordered=True
)

structure = structure.sort_values(
    "complexity_block"
).reset_index(drop=True)

structure["Товарооборот, тыс. USD"] = (
    structure["Africa_to_Russia"]
    + structure["Russia_to_Africa"]
)

africa_total = structure["Africa_to_Russia"].sum()
russia_total = structure["Russia_to_Africa"].sum()

structure["Доля экспорта Африки, %"] = (
    structure["Africa_to_Russia"]
    / africa_total * 100
    if africa_total > 0 else 0
)

structure["Доля экспорта России, %"] = (
    structure["Russia_to_Africa"]
    / russia_total * 100
    if russia_total > 0 else 0
)

structure["Экспорт Африки в Россию, млрд USD"] = (
    structure["Africa_to_Russia"] / USD_TO_BILLION
)

structure["Экспорт России в Африку, млрд USD"] = (
    structure["Russia_to_Africa"] / USD_TO_BILLION
)

structure["Товарооборот, млрд USD"] = (
    structure["Товарооборот, тыс. USD"] / USD_TO_BILLION
)

print("\nСтруктура торговли:")
print(structure.to_string(index=False))


# ============================================================
# 9. СТРУКТУРА ПО ГЛАВАМ HS2
# ============================================================

hs2_structure = (
    products.groupby("chapter", as_index=False)
    .agg({
        "Africa_to_Russia": "sum",
        "Russia_to_Africa": "sum",
    })
)

hs2_structure["Глава HS2"] = hs2_structure["chapter"].apply(
    lambda x: f"{int(x):02d}"
)

hs2_structure["Экспорт Африки в Россию, млрд USD"] = (
    hs2_structure["Africa_to_Russia"] / USD_TO_BILLION
)

hs2_structure["Экспорт России в Африку, млрд USD"] = (
    hs2_structure["Russia_to_Africa"] / USD_TO_BILLION
)

hs2_structure = hs2_structure[
    [
        "Глава HS2",
        "Экспорт Африки в Россию, млрд USD",
        "Экспорт России в Африку, млрд USD",
    ]
].sort_values("Глава HS2")


# ============================================================
# 10. СТРУКТУРА ПО ТОВАРАМ HS6
# ============================================================

hs6_structure = (
    products.groupby(
        ["hs6_normalized", "complexity_block"],
        as_index=False
    )
    .agg({
        "Africa_to_Russia": "sum",
        "Russia_to_Africa": "sum",
        "quantity_tons": "sum",
    })
)

hs6_structure = hs6_structure.rename(columns={
    "hs6_normalized": "Код HS6",
    "complexity_block": "Товарный блок",
    "Africa_to_Russia": "Экспорт Африки в Россию, тыс. USD",
    "Russia_to_Africa": "Экспорт России в Африку, тыс. USD",
    "quantity_tons": "Количество, тонн",
})

hs6_structure["Экспорт Африки в Россию, млрд USD"] = (
    hs6_structure["Экспорт Африки в Россию, тыс. USD"]
    / USD_TO_BILLION
)

hs6_structure["Экспорт России в Африку, млрд USD"] = (
    hs6_structure["Экспорт России в Африку, тыс. USD"]
    / USD_TO_BILLION
)

hs6_structure = hs6_structure.sort_values(
    "Экспорт России в Африку, тыс. USD",
    ascending=False
)


# ============================================================
# 11. PNG: РАСХОДЯЩАЯСЯ ДИАГРАММА
# ============================================================

print("\n" + "=" * 75)
print("3. ПОСТРОЕНИЕ ВИЗУАЛИЗАЦИИ")
print("=" * 75)

plot_data = structure.copy()

plot_data = plot_data[
    (plot_data["Africa_to_Russia"] > 0)
    | (plot_data["Russia_to_Africa"] > 0)
].copy()

plot_data["Africa_bn"] = (
    plot_data["Africa_to_Russia"] / USD_TO_BILLION
)

plot_data["Russia_bn"] = (
    plot_data["Russia_to_Africa"] / USD_TO_BILLION
)

labels = [
    str(x).split(". ", 1)[-1]
    for x in plot_data["complexity_block"]
]

y = np.arange(len(plot_data))

fig, ax = plt.subplots(
    figsize=(15, 8),
    dpi=200
)

left_values = -plot_data["Africa_bn"].to_numpy()
right_values = plot_data["Russia_bn"].to_numpy()

max_value = max(
    abs(left_values).max(),
    abs(right_values).max()
)

if max_value == 0:
    raise ValueError("Нет данных для построения диаграммы.")

# Левая часть — экспорт Африки в Россию
ax.barh(
    y,
    left_values,
    height=0.58,
    label="Экспорт Африки в Россию",
)

# Правая часть — экспорт России в Африку
ax.barh(
    y,
    right_values,
    height=0.58,
    label="Экспорт России в Африку",
)

# Центральная нулевая ось
ax.axvline(
    0,
    color="black",
    linewidth=1.3,
)

# Подписи значений
for i, (left, right) in enumerate(
    zip(left_values, right_values)
):

    if left != 0:
        ax.text(
            left - max_value * 0.025,
            i,
            f"{abs(left):.2f}",
            ha="right",
            va="center",
            fontsize=11,
        )

    if right != 0:
        ax.text(
            right + max_value * 0.025,
            i,
            f"{right:.2f}",
            ha="left",
            va="center",
            fontsize=11,
        )

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=11)

ax.set_xlim(
    -max_value * 1.25,
    max_value * 1.25
)

ax.set_xlabel(
    "Млрд долларов США",
    fontsize=11,
)

ax.legend(
    loc="lower center",
    bbox_to_anchor=(0.5, 1.02),
    ncol=2,
    frameon=False,
    fontsize=10,
)

ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25,
)

ax.set_axisbelow(True)
ax.invert_yaxis()

# Убираем лишние рамки
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Без заголовка, как договорились
plt.tight_layout()

plt.savefig(
    OUTPUT_PNG,
    dpi=300,
    bbox_inches="tight",
    facecolor="white",
)

plt.close()

print("PNG создан:", OUTPUT_PNG)


# ============================================================
# 12. EXCEL: ВЫГРУЗКА ТАБЛИЦ
# ============================================================

print("\n" + "=" * 75)
print("4. ФОРМИРОВАНИЕ EXCEL")
print("=" * 75)

with pd.ExcelWriter(
    OUTPUT_EXCEL,
    engine="openpyxl"
) as writer:

    dynamics.to_excel(
        writer,
        sheet_name="Динамика",
        index=False,
    )

    structure.to_excel(
        writer,
        sheet_name="Структура",
        index=False,
    )

    hs2_structure.to_excel(
        writer,
        sheet_name="Структура_HS2",
        index=False,
    )

    hs6_structure.to_excel(
        writer,
        sheet_name="Структура_HS6",
        index=False,
    )

    # Автоматическая ширина столбцов
    for worksheet in writer.book.worksheets:

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:

            max_length = max(
                len(str(cell.value))
                if cell.value is not None else 0
                for cell in column_cells
            )

            column_letter = column_cells[0].column_letter

            worksheet.column_dimensions[
                column_letter
            ].width = min(max_length + 3, 45)


print("Excel создан:", OUTPUT_EXCEL)


# ============================================================
# 13. ИТОГОВАЯ ПРОВЕРКА
# ============================================================

print("\n" + "=" * 75)
print("РАСЧЕТ ЗАВЕРШЕН")
print("=" * 75)

print(f"Период: {START_YEAR}–{END_YEAR}")

print(
    "Годовых наблюдений:",
    len(dynamics)
)

print(
    "Товарных записей:",
    len(products)
)

print(
    "Товарных позиций HS6:",
    products["hs6_normalized"].nunique()
)

print(
    "Стран:",
    products["country_iso3"].nunique()
)

print(
    "Экспорт Африки в Россию:",
    round(africa_total / USD_TO_BILLION, 2),
    "млрд USD"
)

print(
    "Экспорт России в Африку:",
    round(russia_total / USD_TO_BILLION, 2),
    "млрд USD"
)

print("\nСозданные файлы:")
print(OUTPUT_EXCEL)
print(OUTPUT_PNG)
