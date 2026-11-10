
from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 1. ПУТИ И НАСТРОЙКИ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ANNUAL_FILE = BASE_DIR / "data" / "processed" / "baci_russia_africa_annual.csv"
PRODUCT_FILE = BASE_DIR / "data" / "processed" / "baci_russia_africa_products.csv"

OUTPUT_DIR = BASE_DIR / "reports" / "russia_africa_trade"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_YEAR = 2000
END_YEAR = 2024

TOP_N_COUNTRIES = 20
TOP_N_PRODUCTS = 50


# ============================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def safe_cagr(first_value, last_value, periods):
    """Среднегодовой темп роста. Возвращает NaN при некорректных значениях."""
    if (
        pd.isna(first_value)
        or pd.isna(last_value)
        or first_value <= 0
        or last_value <= 0
        or periods <= 0
    ):
        return np.nan

    return ((last_value / first_value) ** (1 / periods) - 1) * 100


def normalize_trade_flow(value):
    """Приведение названий товарных потоков к единому формату."""
    value = str(value).strip().lower()

    if "exports_to_russia" in value:
        return "exports_to_russia"

    if "imports_from_russia" in value:
        return "imports_from_russia"

    raise ValueError(
        f"Неизвестное значение trade_flow: {value}. "
        "Проверь названия товарных потоков в исходном файле."
    )


def calculate_hhi(data, group_columns, value_column):
    """
    Индекс Херфиндаля — Хиршмана.
    Рассчитывается по долям положительных торговых потоков.
    Диапазон: от 0 до 10 000.
    """
    result = data.copy()

    totals = result.groupby(group_columns)[value_column].transform("sum")

    result = result[totals > 0].copy()
    totals = result.groupby(group_columns)[value_column].transform("sum")

    result["share"] = result[value_column] / totals
    result["share_squared"] = result["share"] ** 2

    hhi = (
        result.groupby(group_columns)["share_squared"]
        .sum()
        .mul(10000)
        .reset_index(name="hhi")
    )

    return hhi


# ============================================================
# 3. ЗАГРУЗКА ДАННЫХ
# ============================================================

print_section("АНАЛИЗ РОССИЙСКО-АФРИКАНСКОЙ ТОРГОВЛИ")

print("Загрузка файлов...")

if not ANNUAL_FILE.exists():
    raise FileNotFoundError(f"Не найден файл: {ANNUAL_FILE}")

if not PRODUCT_FILE.exists():
    raise FileNotFoundError(f"Не найден файл: {PRODUCT_FILE}")

annual = pd.read_csv(ANNUAL_FILE)
products = pd.read_csv(
    PRODUCT_FILE,
    dtype={"hs6": str}
)

print(f"Годовых записей: {len(annual):,}")
print(f"Товарных записей: {len(products):,}")

annual["year"] = pd.to_numeric(annual["year"], errors="coerce")
products["year"] = pd.to_numeric(products["year"], errors="coerce")

annual["exports_to_russia_thousand_usd"] = pd.to_numeric(
    annual["exports_to_russia_thousand_usd"], errors="coerce"
)

annual["imports_from_russia_thousand_usd"] = pd.to_numeric(
    annual["imports_from_russia_thousand_usd"], errors="coerce"
)

products["value_thousand_usd"] = pd.to_numeric(
    products["value_thousand_usd"], errors="coerce"
)

products["quantity_tons"] = pd.to_numeric(
    products["quantity_tons"], errors="coerce"
)

annual = annual[
    annual["year"].between(START_YEAR, END_YEAR)
].copy()

products = products[
    products["year"].between(START_YEAR, END_YEAR)
].copy()

products["trade_flow"] = products["trade_flow"].apply(
    normalize_trade_flow
)

# Сохраняем HS6 как шестизначный строковый код.
products["hs6"] = (
    products["hs6"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(6)
)

products["hs2"] = products["hs6"].str[:2]
products["hs4"] = products["hs6"].str[:4]

# Значения BACI представлены в тысячах долларов США.
# Переводим их в миллионы долларов для удобства представления.
annual["africa_exports_to_russia_mln_usd"] = (
    annual["exports_to_russia_thousand_usd"] / 1000
)

annual["africa_imports_from_russia_mln_usd"] = (
    annual["imports_from_russia_thousand_usd"] / 1000
)

annual["africa_trade_balance_mln_usd"] = (
    annual["africa_exports_to_russia_mln_usd"]
    - annual["africa_imports_from_russia_mln_usd"]
)

products["value_mln_usd"] = (
    products["value_thousand_usd"] / 1000
)


# ============================================================
# 4. ПРОВЕРКА КАЧЕСТВА ДАННЫХ
# ============================================================

print_section("1. ПРОВЕРКА КАЧЕСТВА ДАННЫХ")

annual_duplicates = annual.duplicated(
    subset=["year", "country_iso3"]
).sum()

product_duplicates = products.duplicated(
    subset=["year", "country_iso3", "hs6", "trade_flow"]
).sum()

quality = pd.DataFrame([
    {
        "dataset": "annual",
        "rows": len(annual),
        "countries": annual["country_iso3"].nunique(),
        "years": annual["year"].nunique(),
        "duplicates": annual_duplicates,
        "missing_values": annual[
            [
                "year",
                "country_iso3",
                "exports_to_russia_thousand_usd",
                "imports_from_russia_thousand_usd"
            ]
        ].isna().sum().sum()
    },
    {
        "dataset": "products",
        "rows": len(products),
        "countries": products["country_iso3"].nunique(),
        "years": products["year"].nunique(),
        "duplicates": product_duplicates,
        "missing_values": products[
            [
                "year",
                "country_iso3",
                "hs6",
                "trade_flow",
                "value_thousand_usd"
            ]
        ].isna().sum().sum()
    }
])

print(quality.to_string(index=False))

quality.to_csv(
    OUTPUT_DIR / "trade_data_quality.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nЗначения trade_flow:")
print(products["trade_flow"].value_counts().to_string())


# ============================================================
# 5. ГОДОВАЯ ДИНАМИКА ТОРГОВЛИ
# ============================================================

print_section("2. ГОДОВАЯ ДИНАМИКА ТОРГОВЛИ")

annual_summary = (
    annual.groupby("year", as_index=False)
    .agg(
        africa_exports_to_russia_mln_usd=(
            "africa_exports_to_russia_mln_usd", "sum"
        ),
        africa_imports_from_russia_mln_usd=(
            "africa_imports_from_russia_mln_usd", "sum"
        ),
        countries_count=("country_iso3", "nunique")
    )
)

annual_summary["africa_trade_balance_mln_usd"] = (
    annual_summary["africa_exports_to_russia_mln_usd"]
    - annual_summary["africa_imports_from_russia_mln_usd"]
)

annual_summary["total_trade_mln_usd"] = (
    annual_summary["africa_exports_to_russia_mln_usd"]
    + annual_summary["africa_imports_from_russia_mln_usd"]
)

annual_summary["russia_share_in_africa_trade"] = np.where(
    annual_summary["total_trade_mln_usd"] > 0,
    annual_summary["africa_imports_from_russia_mln_usd"]
    / annual_summary["total_trade_mln_usd"],
    np.nan
)

annual_summary.to_csv(
    OUTPUT_DIR / "trade_annual_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

print(annual_summary.to_string(index=False))

first_year = annual_summary.iloc[0]
last_year = annual_summary.iloc[-1]

print("\nДИНАМИКА ЗА ВЕСЬ ПЕРИОД")

print(
    "CAGR экспорта Африки в Россию:",
    round(
        safe_cagr(
            first_year["africa_exports_to_russia_mln_usd"],
            last_year["africa_exports_to_russia_mln_usd"],
            int(last_year["year"] - first_year["year"])
        ),
        2
    ),
    "%"
)

print(
    "CAGR импорта Африки из России:",
    round(
        safe_cagr(
            first_year["africa_imports_from_russia_mln_usd"],
            last_year["africa_imports_from_russia_mln_usd"],
            int(last_year["year"] - first_year["year"])
        ),
        2
    ),
    "%"
)


# ============================================================
# 6. ГЕОГРАФИЧЕСКАЯ СТРУКТУРА
# ============================================================

print_section("3. ГЕОГРАФИЧЕСКАЯ СТРУКТУРА ТОРГОВЛИ")

country_summary = (
    annual.groupby(
        ["country_iso3", "country_name"],
        as_index=False
    )
    .agg(
        exports_to_russia_mln_usd=(
            "africa_exports_to_russia_mln_usd", "sum"
        ),
        imports_from_russia_mln_usd=(
            "africa_imports_from_russia_mln_usd", "sum"
        ),
        active_years=("year", "nunique")
    )
)

country_summary["total_trade_mln_usd"] = (
    country_summary["exports_to_russia_mln_usd"]
    + country_summary["imports_from_russia_mln_usd"]
)

country_summary["trade_balance_mln_usd"] = (
    country_summary["exports_to_russia_mln_usd"]
    - country_summary["imports_from_russia_mln_usd"]
)

total_africa_trade = country_summary["total_trade_mln_usd"].sum()

country_summary["share_in_total_trade_pct"] = (
    country_summary["total_trade_mln_usd"]
    / total_africa_trade * 100
    if total_africa_trade > 0 else np.nan
)

country_summary = country_summary.sort_values(
    "total_trade_mln_usd",
    ascending=False
)

country_summary.to_csv(
    OUTPUT_DIR / "country_trade_profiles.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nТОП-20 ТОРГОВЫХ ПАРТНЁРОВ ЗА 2000–2024 ГГ.")

print(
    country_summary.head(TOP_N_COUNTRIES).to_string(index=False)
)

print("\nДОЛЯ ПЕРВЫХ 5 СТРАН В ОБЩЕЙ ТОРГОВЛЕ:")

print(
    round(
        country_summary.head(5)["share_in_total_trade_pct"].sum(),
        2
    ),
    "%"
)


# ============================================================
# 7. ГОДОВАЯ КОНЦЕНТРАЦИЯ ТОРГОВЛИ ПО СТРАНАМ
# ============================================================

print_section("4. КОНЦЕНТРАЦИЯ ТОРГОВЛИ ПО СТРАНАМ")

country_year_long = annual.melt(
    id_vars=["year", "country_iso3", "country_name"],
    value_vars=[
        "africa_exports_to_russia_mln_usd",
        "africa_imports_from_russia_mln_usd"
    ],
    var_name="trade_direction",
    value_name="trade_value_mln_usd"
)

country_hhi = calculate_hhi(
    country_year_long,
    ["year", "trade_direction"],
    "trade_value_mln_usd"
)

country_hhi.to_csv(
    OUTPUT_DIR / "country_trade_concentration.csv",
    index=False,
    encoding="utf-8-sig"
)

print(country_hhi.to_string(index=False))


# ============================================================
# 8. ТОВАРНАЯ СТРУКТУРА HS6
# ============================================================

print_section("5. ТОВАРНАЯ СТРУКТУРА")

product_summary = (
    products.groupby(
        ["trade_flow", "hs6", "hs4", "hs2"],
        as_index=False
    )
    .agg(
        value_mln_usd=("value_mln_usd", "sum"),
        quantity_tons=("quantity_tons", "sum"),
        countries_count=("country_iso3", "nunique"),
        active_years=("year", "nunique")
    )
)

product_summary["share_in_flow_pct"] = (
    product_summary["value_mln_usd"]
    / product_summary.groupby("trade_flow")["value_mln_usd"]
    .transform("sum") * 100
)

product_summary = product_summary.sort_values(
    ["trade_flow", "value_mln_usd"],
    ascending=[True, False]
)

product_summary.to_csv(
    OUTPUT_DIR / "product_trade_profiles_hs6.csv",
    index=False,
    encoding="utf-8-sig"
)

for flow in ["imports_from_russia", "exports_to_russia"]:

    print(f"\nТОП-{TOP_N_PRODUCTS} ТОВАРОВ: {flow}")

    top_products = product_summary[
        product_summary["trade_flow"] == flow
    ].head(TOP_N_PRODUCTS)

    print(top_products.to_string(index=False))


# ============================================================
# 9. ТОВАРНАЯ СТРУКТУРА HS2
# ============================================================

hs2_summary = (
    products.groupby(
        ["trade_flow", "hs2"],
        as_index=False
    )
    .agg(
        value_mln_usd=("value_mln_usd", "sum"),
        quantity_tons=("quantity_tons", "sum"),
        countries_count=("country_iso3", "nunique"),
        active_years=("year", "nunique"),
        hs6_products_count=("hs6", "nunique")
    )
)

hs2_summary["share_in_flow_pct"] = (
    hs2_summary["value_mln_usd"]
    / hs2_summary.groupby("trade_flow")["value_mln_usd"]
    .transform("sum") * 100
)

hs2_summary = hs2_summary.sort_values(
    ["trade_flow", "value_mln_usd"],
    ascending=[True, False]
)

hs2_summary.to_csv(
    OUTPUT_DIR / "product_trade_profiles_hs2.csv",
    index=False,
    encoding="utf-8-sig"
)

print_section("6. КРУПНЫЕ ТОВАРНЫЕ ГРУППЫ HS2")

for flow in ["imports_from_russia", "exports_to_russia"]:

    print(f"\n{flow}")

    print(
        hs2_summary[
            hs2_summary["trade_flow"] == flow
        ].head(20).to_string(index=False)
    )


# ============================================================
# 10. КОНЦЕНТРАЦИЯ ТОВАРНОЙ СТРУКТУРЫ
# ============================================================

print_section("7. КОНЦЕНТРАЦИЯ ТОВАРНОЙ СТРУКТУРЫ")

product_hhi = calculate_hhi(
    products,
    ["year", "trade_flow"],
    "value_thousand_usd"
)

product_hhi.to_csv(
    OUTPUT_DIR / "product_trade_concentration.csv",
    index=False,
    encoding="utf-8-sig"
)

print(product_hhi.to_string(index=False))


# ============================================================
# 11. СОГЛАСОВАНИЕ ТОВАРНЫХ И ГОДОВЫХ АГРЕГАТОВ
# ============================================================

print_section("8. ПРОВЕРКА СОГЛАСОВАНИЯ BACI")

product_annual = (
    products.groupby(
        ["year", "country_iso3", "trade_flow"],
        as_index=False
    )
    .agg(
        product_value_thousand_usd=("value_thousand_usd", "sum")
    )
)

product_annual_wide = product_annual.pivot_table(
    index=["year", "country_iso3"],
    columns="trade_flow",
    values="product_value_thousand_usd",
    aggfunc="sum",
    fill_value=0
).reset_index()

for col in ["exports_to_russia", "imports_from_russia"]:
    if col not in product_annual_wide.columns:
        product_annual_wide[col] = 0

comparison = annual.merge(
    product_annual_wide,
    on=["year", "country_iso3"],
    how="left"
)

comparison["exports_to_russia"] = (
    comparison["exports_to_russia"].fillna(0)
)

comparison["imports_from_russia"] = (
    comparison["imports_from_russia"].fillna(0)
)

comparison["exports_difference_thousand_usd"] = (
    comparison["exports_to_russia_thousand_usd"]
    - comparison["exports_to_russia"]
)

comparison["imports_difference_thousand_usd"] = (
    comparison["imports_from_russia_thousand_usd"]
    - comparison["imports_from_russia"]
)

max_exports_difference = comparison[
    "exports_difference_thousand_usd"
].abs().max()

max_imports_difference = comparison[
    "imports_difference_thousand_usd"
].abs().max()

print(
    "Максимальное расхождение экспорта, тыс. USD:",
    max_exports_difference
)

print(
    "Максимальное расхождение импорта, тыс. USD:",
    max_imports_difference
)

comparison.to_csv(
    OUTPUT_DIR / "trade_annual_reconciliation.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 12. ИТОГОВЫЙ СВОДНЫЙ ОТЧЁТ
# ============================================================

print_section("9. ИТОГОВЫЕ РЕЗУЛЬТАТЫ")

print("Период:", START_YEAR, "–", END_YEAR)
print("Стран:", annual["country_iso3"].nunique())
print("Годовых наблюдений:", len(annual))
print("Товарных наблюдений:", len(products))

print(
    "Экспорт Африки в Россию за весь период, млн USD:",
    round(annual_summary["africa_exports_to_russia_mln_usd"].sum(), 2)
)

print(
    "Импорт Африки из России за весь период, млн USD:",
    round(annual_summary["africa_imports_from_russia_mln_usd"].sum(), 2)
)

print(
    "Общий товарооборот за весь период, млн USD:",
    round(annual_summary["total_trade_mln_usd"].sum(), 2)
)

print(
    "Средний годовой товарооборот, млн USD:",
    round(annual_summary["total_trade_mln_usd"].mean(), 2)
)

print("\nФАЙЛЫ СОХРАНЕНЫ В:", OUTPUT_DIR)

for file in sorted(OUTPUT_DIR.glob("*.csv")):
    print(" -", file.name)

print("\nАНАЛИЗ РОССИЙСКО-АФРИКАНСКОЙ ТОРГОВЛИ ЗАВЕРШЁН")
