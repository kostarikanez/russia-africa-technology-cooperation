from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
CASEBOOK = REPORTS / "mnts_cooperation_priority" / "casebook"

RANKING_FILE = CASEBOOK / "technology_case_final_ranking.csv"
PROFILE_FILE = REPORTS / "country_block_profiles.csv"
PRODUCT_FILE = CASEBOOK / "technology_case_product_evidence_shortlist.csv"

OUT_MATRIX = CASEBOOK / "technology_final_case_matrix.csv"
OUT_PRODUCTS = CASEBOOK / "technology_final_case_products.csv"

# ---------------------------------------------------------
# 1. ЗАГРУЗКА
# ---------------------------------------------------------

ranking = pd.read_csv(RANKING_FILE)
profiles = pd.read_csv(PROFILE_FILE)
products = pd.read_csv(PRODUCT_FILE)

# ---------------------------------------------------------
# 2. ПРОФИЛИ ТЕХНОЛОГИЧЕСКОЙ ГОТОВНОСТИ
# ---------------------------------------------------------

blocks = {
    "economic": "mean_economic_block",
    "digital": "mean_digital_block",
    "science": "mean_science_block",
    "industry": "mean_industry_block",
    "institutions": "mean_institutional_block",
}

block_names = {
    "economic": "Экономический потенциал",
    "digital": "Цифровая инфраструктура",
    "science": "Научно-технологическая база",
    "industry": "Промышленная база",
    "institutions": "Институциональная среда",
}

profiles["weakest_block"] = profiles[
    list(blocks.values())
].idxmin(axis=1)

profiles["strongest_block"] = profiles[
    list(blocks.values())
].idxmax(axis=1)

profiles["weakest_block_name"] = profiles["weakest_block"].map(
    {v: block_names[k] for k, v in blocks.items()}
)

profiles["strongest_block_name"] = profiles["strongest_block"].map(
    {v: block_names[k] for k, v in blocks.items()}
)

profiles["structural_gap"] = (
    profiles[list(blocks.values())].max(axis=1)
    - profiles[list(blocks.values())].min(axis=1)
)

profile_columns = [
    "country_iso3",
    "country_name",
    "rank_overall",
    "observations",
    "coverage_pct",
    "mean_index",
    *blocks.values(),
    "weakest_block_name",
    "strongest_block_name",
    "structural_gap",
]

profiles_selected = profiles[profile_columns].copy()

# ---------------------------------------------------------
# 3. ОБЪЕДИНЕНИЕ РЕЙТИНГА И ПРОФИЛЕЙ
# ---------------------------------------------------------

matrix = ranking.merge(
    profiles_selected,
    on="country_iso3",
    how="left",
    validate="many_to_one",
)

# ---------------------------------------------------------
# 4. ПРЕДВАРИТЕЛЬНЫЙ ОТБОР КЕЙСОВ
# ---------------------------------------------------------

primary_cases = {
    ("ZAF", "Machinery and equipment"):
        "ЮАР: промышленное оборудование и взаимные промышленные потоки",

    ("ZAF", "Measuring and medical equipment"):
        "ЮАР: измерительная, рентгеновская и медицинская техника",

    ("EGY", "Machinery and equipment"):
        "Египет: инженерное оборудование и инфраструктура",

    ("DZA", "Machinery and equipment"):
        "Алжир: крупные поставки авиационной и инженерной техники",

    ("MAR", "Machinery and equipment"):
        "Марокко: обратные потоки промышленных компонентов",

    ("GAB", "Electrical equipment"):
        "Габон: электротехническое оборудование",

    ("AGO", "Machinery and equipment"):
        "Ангола: оборудование для добывающей промышленности",
}

reserve_cases = {
    ("TUN", "Machinery and equipment"):
        "Тунис: экспорт промышленных компонентов в Россию",

    ("CMR", "Electrical equipment"):
        "Камерун: электротехническое оборудование",

    ("GAB", "Machinery and equipment"):
        "Габон: насосное и промышленное оборудование",
}

def classify_case(row):
    key = (row["country_iso3"], row["sector"])

    if key in primary_cases:
        return "Основное ядро"

    if key in reserve_cases:
        return "Резерв"

    return "Дополнительный кандидат"

def describe_case(row):
    key = (row["country_iso3"], row["sector"])

    if key in primary_cases:
        return primary_cases[key]

    if key in reserve_cases:
        return reserve_cases[key]

    return ""

matrix["selection_status"] = matrix.apply(classify_case, axis=1)
matrix["case_description"] = matrix.apply(describe_case, axis=1)

# ---------------------------------------------------------
# 5. АНАЛИТИЧЕСКИЕ ПОЛЯ
# ---------------------------------------------------------

matrix["trade_balance_direction"] = np.select(
    [
        matrix["russia_to_africa_mln_usd"]
        > matrix["africa_to_russia_mln_usd"],

        matrix["africa_to_russia_mln_usd"]
        > matrix["russia_to_africa_mln_usd"],
    ],
    [
        "Преобладают поставки России",
        "Преобладают поставки Африки",
    ],
    default="Сопоставимые потоки",
)

matrix["stable_product_share"] = (
    matrix["stable_5y"] / matrix["product_positions"] * 100
).round(1)

matrix["average_year_concentration"] = (
    matrix["average_year_concentration"].round(1)
)

# Сортировка: основное ядро, резерв, остальные
order = {
    "Основное ядро": 0,
    "Резерв": 1,
    "Дополнительный кандидат": 2,
}

matrix["selection_order"] = matrix["selection_status"].map(order)

matrix = matrix.sort_values(
    ["selection_order", "final_score"],
    ascending=[True, False],
)

# ---------------------------------------------------------
# 6. ТОВАРНЫЕ ДОКАЗАТЕЛЬСТВА
# ---------------------------------------------------------

products["selection_status"] = products.apply(
    lambda row: (
        "Основное ядро"
        if (row["country_iso3"], row["sector"]) in primary_cases
        else (
            "Резерв"
            if (row["country_iso3"], row["sector"]) in reserve_cases
            else "Дополнительный кандидат"
        )
    ),
    axis=1,
)

products = products.merge(
    profiles_selected[
        [
            "country_iso3",
            "country_name",
            "mean_index",
            "weakest_block_name",
            "structural_gap",
        ]
    ],
    on="country_iso3",
    how="left",
    validate="many_to_one",
)

products = products.sort_values(
    [
        "selection_status",
        "country_iso3",
        "product_evidence_score",
        "total_value_mln_usd_2019_2023",
    ],
    ascending=[True, True, False, False],
)

# ---------------------------------------------------------
# 7. СОХРАНЕНИЕ
# ---------------------------------------------------------

matrix.to_csv(OUT_MATRIX, index=False, encoding="utf-8-sig")
products.to_csv(OUT_PRODUCTS, index=False, encoding="utf-8-sig")

# ---------------------------------------------------------
# 8. КОНСОЛЬНЫЙ ОТЧЁТ
# ---------------------------------------------------------

print("=" * 110)
print("ФИНАЛЬНАЯ МАТРИЦА ТЕХНОЛОГИЧЕСКИХ КЕЙСОВ")
print("=" * 110)

print("\n1. СТРУКТУРА ОТБОРА")
print(matrix["selection_status"].value_counts().to_string())

print("\n2. ОСНОВНОЕ ЯДРО")
print("-" * 110)

main = matrix[matrix["selection_status"] == "Основное ядро"]

print(
    main[
        [
            "country_iso3",
            "country_name",
            "sector",
            "final_score",
            "mean_index",
            "weakest_block_name",
            "strongest_block_name",
            "structural_gap",
            "russia_to_africa_mln_usd",
            "africa_to_russia_mln_usd",
            "stable_5y",
            "stable_4y",
        ]
    ].to_string(index=False)
)

print("\n3. РЕЗЕРВНЫЕ КЕЙСЫ")
print("-" * 110)

reserve = matrix[matrix["selection_status"] == "Резерв"]

print(
    reserve[
        [
            "country_iso3",
            "country_name",
            "sector",
            "final_score",
            "mean_index",
            "weakest_block_name",
            "russia_to_africa_mln_usd",
            "africa_to_russia_mln_usd",
        ]
    ].to_string(index=False)
)

print("\n4. ТОВАРНЫЕ ДОКАЗАТЕЛЬСТВА ОСНОВНОГО ЯДРА")
print("-" * 110)

print(
    products[products["selection_status"] == "Основное ядро"][
        [
            "country_iso3",
            "sector",
            "trade_direction",
            "hs6",
            "product_description",
            "total_value_mln_usd_2019_2023",
            "persistence_category",
            "largest_year_share_pct",
        ]
    ].head(40).to_string(index=False)
)

print("\n5. ПРОВЕРКА ПОКРЫТИЯ ИНДЕКСОМ")
print("-" * 110)

print(
    "Кейсов основного ядра:",
    len(main),
)

print(
    "Кейсов с профилем индекса:",
    main["mean_index"].notna().sum(),
)

print(
    "Товарных позиций основного ядра:",
    (products["selection_status"] == "Основное ядро").sum(),
)

print("\n6. СОХРАНЁННЫЕ ФАЙЛЫ")
print(OUT_MATRIX)
print(OUT_PRODUCTS)

print("\n" + "=" * 110)
print("ФИНАЛЬНАЯ МАТРИЦА СФОРМИРОВАНА")
print("=" * 110)