
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 0. НАСТРОЙКИ
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

TRADE_DIR = REPORTS_DIR / "russia_africa_trade"
OUTPUT_DIR = REPORTS_DIR / "russia_africa_trade_technology"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Периоды анализа
MAIN_START = 2002
MAIN_END = 2023

RECENT_START = 2019
RECENT_END = 2023

# Товарные группы HS2.
# Это аналитическая корзина оборудования и технологически
# значимой продукции, а не официальная классификация high-tech.
TECH_HS2 = {
    "84",  # Машины и механическое оборудование
    "85",  # Электрические машины и оборудование
    "86",  # Железнодорожное оборудование
    "87",  # Средства наземного транспорта
    "88",  # Летательные аппараты
    "89",  # Суда и плавучие конструкции
    "90",  # Оптические, измерительные и медицинские приборы
}

# Более широкая промышленная корзина:
# металлы, изделия из металлов, машины и оборудование.
INDUSTRIAL_HS2 = {
    "72", "73", "74", "75", "76",
    "78", "79", "80", "81", "82", "83",
    "84", "85", "86", "87", "88", "89", "90",
}


# ============================================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def read_csv(path, **kwargs):
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл: {path}")

    return pd.read_csv(path, **kwargs)


def normalize_iso3(df):
    df = df.copy()

    if "country_iso3" not in df.columns:
        raise KeyError(
            "В таблице отсутствует обязательное поле country_iso3. "
            f"Доступные поля: {df.columns.tolist()}"
        )

    df["country_iso3"] = (
        df["country_iso3"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def fix_country_name(value, iso3=None):
    """Исправление отдельных проблем отображения названий."""

    if iso3 == "CIV":
        return "Côte d'Ivoire"

    return value


def save_csv(df, filename):
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Сохранён файл: {path.name} ({len(df):,} строк)")


def print_section(title):
    print("\n" + "=" * 85)
    print(title)
    print("=" * 85)


def get_flow_mapping(values):
    """
    Приводит обозначения торговых потоков к двум направлениям:
    exports_to_russia — Африка экспортирует в Россию;
    imports_from_russia — Африка импортирует из России.
    """

    aliases = {
        "exports_to_russia": "exports_to_russia",
        "export_to_russia": "exports_to_russia",
        "africa_to_russia": "exports_to_russia",
        "africa_exports": "exports_to_russia",
        "export": "exports_to_russia",
        "exports": "exports_to_russia",

        "imports_from_russia": "imports_from_russia",
        "import_from_russia": "imports_from_russia",
        "russia_to_africa": "imports_from_russia",
        "africa_imports": "imports_from_russia",
        "import": "imports_from_russia",
        "imports": "imports_from_russia",
    }

    mapping = {}

    for value in values:
        key = str(value).strip().lower()
        if key in aliases:
            mapping[value] = aliases[key]

    return mapping


# ============================================================
# 2. ЗАГРУЗКА И ПРОВЕРКА ИСХОДНЫХ ДАННЫХ
# ============================================================

print_section("ИНТЕГРАЦИЯ ТОРГОВЫХ И ТЕХНОЛОГИЧЕСКИХ ДАННЫХ")

annual_path = DATA_DIR / "baci_russia_africa_annual.csv"
products_path = DATA_DIR / "baci_russia_africa_products.csv"

clusters_path = REPORTS_DIR / "country_clusters.csv"
gaps_path = REPORTS_DIR / "country_technology_gaps.csv"

annual = read_csv(annual_path)
products = read_csv(products_path, dtype={"hs6": str})

clusters = read_csv(clusters_path)
gaps = read_csv(gaps_path)

annual = normalize_iso3(annual)
products = normalize_iso3(products)
clusters = normalize_iso3(clusters)
gaps = normalize_iso3(gaps)

print(f"Годовых записей: {len(annual):,}")
print(f"Товарных записей: {len(products):,}")
print(f"Стран в торговых данных: {annual['country_iso3'].nunique()}")
print(f"Стран в кластеризации: {clusters['country_iso3'].nunique()}")
print(f"Стран в матрице разрывов: {gaps['country_iso3'].nunique()}")

# Проверка необходимых торговых полей
annual_required = {
    "year",
    "country_iso3",
    "country_name",
    "exports_to_russia_thousand_usd",
    "imports_from_russia_thousand_usd",
}

missing = annual_required - set(annual.columns)

if missing:
    raise KeyError(f"В годовой торговой таблице отсутствуют поля: {missing}")

products_required = {
    "year",
    "country_iso3",
    "hs6",
    "trade_flow",
    "value_thousand_usd",
}

missing = products_required - set(products.columns)

if missing:
    raise KeyError(f"В товарной таблице отсутствуют поля: {missing}")

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

annual = annual[
    annual["year"].between(MAIN_START, MAIN_END)
].copy()

products = products[
    products["year"].between(MAIN_START, MAIN_END)
].copy()

if annual.empty or products.empty:
    raise ValueError("После ограничения периода торговые данные оказались пустыми.")

# Проверка дублей
annual_duplicates = annual.duplicated(
    ["year", "country_iso3"]
).sum()

if annual_duplicates:
    raise ValueError(
        f"В годовой торговой таблице обнаружено дублей: {annual_duplicates}"
    )

print(
    f"\nПериод основного анализа: {MAIN_START}–{MAIN_END}"
)
print(
    f"Период анализа последних лет: {RECENT_START}–{RECENT_END}"
)


# ============================================================
# 3. СОВОКУПНЫЕ ТОРГОВЫЕ ПРОФИЛИ
# ============================================================

print_section("1. ФОРМИРОВАНИЕ СОВОКУПНЫХ ТОРГОВЫХ ПРОФИЛЕЙ")


def build_trade_profile(data, start_year, end_year, prefix):
    period = data[
        data["year"].between(start_year, end_year)
    ].copy()

    grouped = (
        period.groupby(
            ["country_iso3", "country_name"],
            as_index=False
        )
        .agg(
            exports_to_russia_thousand_usd=(
                "exports_to_russia_thousand_usd", "sum"
            ),
            imports_from_russia_thousand_usd=(
                "imports_from_russia_thousand_usd", "sum"
            ),
            active_years=("year", "nunique"),
        )
    )

    grouped[f"{prefix}_exports_to_russia_mln_usd"] = (
        grouped["exports_to_russia_thousand_usd"] / 1000
    )

    grouped[f"{prefix}_imports_from_russia_mln_usd"] = (
        grouped["imports_from_russia_thousand_usd"] / 1000
    )

    grouped[f"{prefix}_total_trade_mln_usd"] = (
        grouped[f"{prefix}_exports_to_russia_mln_usd"]
        + grouped[f"{prefix}_imports_from_russia_mln_usd"]
    )

    grouped[f"{prefix}_trade_balance_mln_usd"] = (
        grouped[f"{prefix}_exports_to_russia_mln_usd"]
        - grouped[f"{prefix}_imports_from_russia_mln_usd"]
    )

    grouped[f"{prefix}_average_annual_trade_mln_usd"] = (
        grouped[f"{prefix}_total_trade_mln_usd"]
        / grouped["active_years"].replace(0, np.nan)
    )

    grouped = grouped.drop(
        columns=[
            "exports_to_russia_thousand_usd",
            "imports_from_russia_thousand_usd",
        ]
    )

    return grouped


main_trade = build_trade_profile(
    annual, MAIN_START, MAIN_END, "longterm"
)

recent_trade = build_trade_profile(
    annual, RECENT_START, RECENT_END, "recent"
)

trade_profiles = main_trade.merge(
    recent_trade,
    on=["country_iso3", "country_name"],
    how="left",
    validate="one_to_one"
)

trade_profiles = trade_profiles.rename(
    columns={"country_name": "country_name"}
)

trade_profiles["recent_vs_longterm_ratio"] = (
    trade_profiles["recent_total_trade_mln_usd"]
    / (
        trade_profiles["longterm_total_trade_mln_usd"]
        / (MAIN_END - MAIN_START + 1)
    )
    / (RECENT_END - RECENT_START + 1)
)

trade_profiles["trade_rank"] = (
    trade_profiles["longterm_total_trade_mln_usd"]
    .rank(method="min", ascending=False)
)

trade_profiles["recent_trade_rank"] = (
    trade_profiles["recent_total_trade_mln_usd"]
    .rank(method="min", ascending=False)
)

total_trade = trade_profiles["longterm_total_trade_mln_usd"].sum()

trade_profiles["bilateral_trade_share_pct"] = (
    trade_profiles["longterm_total_trade_mln_usd"]
    / total_trade * 100
    if total_trade else np.nan
)

print(f"Сформировано торговых профилей: {len(trade_profiles)}")
print(
    f"Совокупная торговля за {MAIN_START}–{MAIN_END}: "
    f"{total_trade:,.2f} млн долларов"
)


# ============================================================
# 4. ТЕХНОЛОГИЧЕСКИ И ПРОМЫШЛЕННО ЗНАЧИМЫЕ ТОВАРНЫЕ ГРУППЫ
# ============================================================

print_section("2. ВЫДЕЛЕНИЕ ТОВАРНЫХ ГРУПП")

products["hs6"] = (
    products["hs6"]
    .astype(str)
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(6)
)

products["hs2"] = products["hs6"].str[:2]

flow_mapping = get_flow_mapping(
    products["trade_flow"].dropna().unique()
)

products["trade_direction"] = products["trade_flow"].map(
    flow_mapping
)

print("Исходные обозначения торговых потоков:")
print(products["trade_flow"].value_counts(dropna=False).to_string())

unmapped_flows = products.loc[
    products["trade_direction"].isna(),
    "trade_flow"
].dropna().unique()

if len(unmapped_flows):
    raise ValueError(
        "Не удалось определить направление следующих торговых потоков: "
        f"{list(unmapped_flows)}. "
        "Нужно уточнить их смысл, прежде чем продолжать."
    )

products["is_technology"] = products["hs2"].isin(TECH_HS2)
products["is_industrial"] = products["hs2"].isin(INDUSTRIAL_HS2)


def build_product_profile(data, start_year, end_year, prefix):
    period = data[
        data["year"].between(start_year, end_year)
    ].copy()

    result = (
        period.groupby(
            ["country_iso3", "trade_direction"],
            as_index=False
        )
        .agg(
            total_product_trade_thousand_usd=(
                "value_thousand_usd", "sum"
            ),
            technology_trade_thousand_usd=(
                "value_thousand_usd",
                lambda x: x[
                    period.loc[x.index, "is_technology"]
                ].sum()
            ),
            industrial_trade_thousand_usd=(
                "value_thousand_usd",
                lambda x: x[
                    period.loc[x.index, "is_industrial"]
                ].sum()
            ),
        )
    )

    result["total_product_trade_mln_usd"] = (
        result["total_product_trade_thousand_usd"] / 1000
    )

    result["technology_trade_mln_usd"] = (
        result["technology_trade_thousand_usd"] / 1000
    )

    result["industrial_trade_mln_usd"] = (
        result["industrial_trade_thousand_usd"] / 1000
    )

    result["technology_share_pct"] = (
        result["technology_trade_thousand_usd"]
        / result["total_product_trade_thousand_usd"].replace(0, np.nan)
        * 100
    )

    result["industrial_share_pct"] = (
        result["industrial_trade_thousand_usd"]
        / result["total_product_trade_thousand_usd"].replace(0, np.nan)
        * 100
    )

    result = result.drop(
        columns=[
            "total_product_trade_thousand_usd",
            "technology_trade_thousand_usd",
            "industrial_trade_thousand_usd",
        ]
    )

    result = result.pivot(
        index="country_iso3",
        columns="trade_direction",
        values=[
            "total_product_trade_mln_usd",
            "technology_trade_mln_usd",
            "industrial_trade_mln_usd",
            "technology_share_pct",
            "industrial_share_pct",
        ]
    )

    result.columns = [
        f"{prefix}_{metric}_{direction}"
        for metric, direction in result.columns
    ]

    return result.reset_index()


product_main = build_product_profile(
    products, MAIN_START, MAIN_END, "longterm"
)

product_recent = build_product_profile(
    products, RECENT_START, RECENT_END, "recent"
)

product_profiles = product_main.merge(
    product_recent,
    on="country_iso3",
    how="outer",
    validate="one_to_one"
)

trade_profiles = trade_profiles.merge(
    product_profiles,
    on="country_iso3",
    how="left",
    validate="one_to_one"
)

print(f"Стран с товарными профилями: {product_profiles['country_iso3'].nunique()}")
print(f"Технологическая корзина HS2: {', '.join(sorted(TECH_HS2))}")
print(f"Промышленная корзина HS2: {', '.join(sorted(INDUSTRIAL_HS2))}")


# ============================================================
# 5. ПОДГОТОВКА ТЕХНОЛОГИЧЕСКИХ ПРОФИЛЕЙ И КЛАСТЕРОВ
# ============================================================

print_section("3. ОБЪЕДИНЕНИЕ С ТЕХНОЛОГИЧЕСКИМИ ПРОФИЛЯМИ")

# В country_clusters.csv уже содержатся:
# mean_index, kmeans_cluster, блоки и дополнительные параметры.
# Используем его как основной источник технологических характеристик.

if "kmeans_cluster" not in clusters.columns:
    possible = [
        col for col in clusters.columns
        if col.startswith("kmeans_cluster")
    ]

    if len(possible) == 1:
        clusters = clusters.rename(
            columns={possible[0]: "kmeans_cluster"}
        )
    else:
        raise KeyError(
            "В country_clusters.csv не найден однозначный столбец "
            "kmeans_cluster. Столбцы: "
            f"{clusters.columns.tolist()}"
        )

if "mean_index" not in clusters.columns:
    raise KeyError(
        "В country_clusters.csv отсутствует mean_index. "
        f"Столбцы: {clusters.columns.tolist()}"
    )

if clusters["country_iso3"].duplicated().any():
    raise ValueError("В country_clusters.csv есть дубли стран.")

# Оставляем необходимые технологические поля.
cluster_columns = [
    "country_iso3",
    "mean_index",
    "kmeans_cluster",
    "hierarchical_cluster",
    "individual_silhouette",
    "mean_economic_block",
    "mean_digital_block",
    "mean_science_block",
    "mean_industry_block",
    "mean_institutional_block",
]

cluster_columns = [
    col for col in cluster_columns
    if col in clusters.columns
]

technology_profiles = clusters[cluster_columns].copy()

# Из матрицы разрывов берем только поля, которых нет
# в основном файле кластеризации.
gap_columns = [
    "country_iso3",
    "strongest_block_name",
    "strongest_value",
    "weakest_block_name",
    "weakest_value",
    "structural_gap",
    "mean_block_value",
    "strongest_deviation",
    "weakest_deviation",
    "potential_constraint",
    "interpretation_note",
]

gap_columns = [
    col for col in gap_columns
    if col in gaps.columns
]

gaps_selected = gaps[gap_columns].copy()

if gaps_selected["country_iso3"].duplicated().any():
    raise ValueError("В country_technology_gaps.csv есть дубли стран.")

technology_profiles = technology_profiles.merge(
    gaps_selected,
    on="country_iso3",
    how="left",
    validate="one_to_one"
)

# Присоединяем технологические характеристики к торговым профилям.
result = trade_profiles.merge(
    technology_profiles,
    on="country_iso3",
    how="left",
    validate="one_to_one"
)

# Восстанавливаем единое название страны.
result["country_name"] = result["country_name"].apply(
    lambda x: fix_country_name(x)
)

# Классификация кластеров.
cluster_labels = {
    1: "Сильная экономическая, научная и институциональная база",
    2: "Ресурсно-промышленная специализация",
    3: "Формирующаяся технологическая база",
}

result["technology_cluster"] = (
    result["kmeans_cluster"].map(cluster_labels)
)

# Число стран с технологическими характеристиками.
matched = result["mean_index"].notna().sum()
unmatched = result["mean_index"].isna().sum()

print(f"Всего стран в итоговой матрице: {len(result)}")
print(f"Стран с технологическими профилями: {matched}")
print(f"Стран без технологических профилей: {unmatched}")

print("\nРаспределение по кластерам:")
print(
    result["technology_cluster"]
    .value_counts(dropna=False)
    .to_string()
)


# ============================================================
# 6. ТИПОЛОГИЯ СТРАН ПО ТЕХНОЛОГИЧЕСКОМУ ПОТЕНЦИАЛУ
#    И ТОРГОВЫМ СВЯЗЯМ С РОССИЕЙ
# ============================================================

print_section("4. ТИПОЛОГИЯ СТРАН")

# Используем медианы только среди стран,
# для которых рассчитан технологический индекс.

valid = result["mean_index"].notna()

technology_median = result.loc[
    valid, "mean_index"
].median()

trade_median = result.loc[
    valid, "longterm_total_trade_mln_usd"
].median()

def assign_quadrant(row):
    if pd.isna(row["mean_index"]):
        return "Нет сопоставимого технологического профиля"

    high_technology = row["mean_index"] >= technology_median
    high_trade = row["longterm_total_trade_mln_usd"] >= trade_median

    if high_technology and high_trade:
        return "Высокая технологическая база / высокие торговые связи"

    if high_technology and not high_trade:
        return "Высокая технологическая база / ограниченные торговые связи"

    if not high_technology and high_trade:
        return "Ограниченная технологическая база / высокие торговые связи"

    return "Ограниченная технологическая база / ограниченные торговые связи"


result["cooperation_typology"] = result.apply(
    assign_quadrant, axis=1
)

print(f"Медиана технологического индекса: {technology_median:.2f}")
print(f"Медиана торговли за {MAIN_START}–{MAIN_END}: {trade_median:.2f} млн USD")

print("\nРаспределение стран по типологии:")
print(
    result["cooperation_typology"]
    .value_counts(dropna=False)
    .to_string()
)

for typology, group in result.groupby("cooperation_typology"):
    print(f"\n{typology} ({len(group)} стран):")
    print(", ".join(sorted(group["country_name"].dropna().astype(str).unique())))


# ============================================================
# 7. КОРРЕЛЯЦИОННЫЙ АНАЛИЗ
# ============================================================

print_section("5. СВЯЗЬ ТЕХНОЛОГИЧЕСКОГО ИНДЕКСА И ТОРГОВЛИ")

correlation_data = result[
    [
        "mean_index",
        "longterm_total_trade_mln_usd",
        "recent_total_trade_mln_usd",
    ]
].dropna()

if len(correlation_data) >= 3:
    corr_longterm = correlation_data[
        ["mean_index", "longterm_total_trade_mln_usd"]
    ].corr(method="spearman").iloc[0, 1]

    corr_recent = correlation_data[
        ["mean_index", "recent_total_trade_mln_usd"]
    ].corr(method="spearman").iloc[0, 1]

    print(f"Число наблюдений: {len(correlation_data)}")
    print(f"Спирмен: индекс — торговля {MAIN_START}–{MAIN_END}: {corr_longterm:.3f}")
    print(f"Спирмен: индекс — торговля {RECENT_START}–{RECENT_END}: {corr_recent:.3f}")

    print(
        "\nИнтерпретация: коэффициент показывает силу и направление "
        "ранговой связи, но не доказывает причинно-следственную зависимость."
    )
else:
    corr_longterm = np.nan
    corr_recent = np.nan
    print("Недостаточно наблюдений для корреляционного анализа.")


# ============================================================
# 8. СРАВНЕНИЕ ТОРГОВЫХ И ТЕХНОЛОГИЧЕСКИХ ХАРАКТЕРИСТИК
# ============================================================

print_section("6. ЛИДЕРЫ ПО ОСНОВНЫМ ПОКАЗАТЕЛЯМ")

def print_top(df, column, title, n=15):
    print(f"\n{title}")

    subset = df[
        ["country_iso3", "country_name", column]
    ].dropna()

    subset = subset.sort_values(column, ascending=False).head(n)

    print(subset.to_string(index=False))


print_top(
    result,
    "mean_index",
    "ТОП-15 СТРАН ПО ТЕХНОЛОГИЧЕСКОМУ ИНДЕКСУ"
)

print_top(
    result,
    "longterm_total_trade_mln_usd",
    f"ТОП-15 СТРАН ПО ТОРГОВЛЕ С РОССИЕЙ ({MAIN_START}–{MAIN_END})"
)

print_top(
    result,
    "recent_total_trade_mln_usd",
    f"ТОП-15 СТРАН ПО ТОРГОВЛЕ С РОССИЕЙ ({RECENT_START}–{RECENT_END})"
)

print_top(
    result,
    "longterm_technology_trade_mln_usd_imports_from_russia",
    "ТОП-15 СТРАН ПО ТОРГОВЛЕ ТОВАРАМИ ТЕХНОЛОГИЧЕСКОЙ КОРЗИНЫ: РОССИЯ → АФРИКА"
)

print_top(
    result,
    "longterm_technology_trade_mln_usd_exports_to_russia",
    "ТОП-15 СТРАН ПО ТОРГОВЛЕ ТОВАРАМИ ТЕХНОЛОГИЧЕСКОЙ КОРЗИНЫ: АФРИКА → РОССИЯ"
)


# ============================================================
# 9. СВОДНЫЕ ПОКАЗАТЕЛИ
# ============================================================

print_section("7. СОВОКУПНЫЕ ПОКАЗАТЕЛИ ТОВАРНОЙ КОРЗИНЫ")

for direction, description in [
    ("imports_from_russia", "Россия → Африка"),
    ("exports_to_russia", "Африка → Россия"),
]:
    total_column = (
        f"longterm_total_product_trade_mln_usd_{direction}"
    )

    technology_column = (
        f"longterm_technology_trade_mln_usd_{direction}"
    )

    industrial_column = (
        f"longterm_industrial_trade_mln_usd_{direction}"
    )

    if total_column not in result.columns:
        continue

    total = result[total_column].sum()
    technology = result[technology_column].sum()
    industrial = result[industrial_column].sum()

    technology_share = technology / total * 100 if total else np.nan
    industrial_share = industrial / total * 100 if total else np.nan

    print(f"\nНаправление: {description}")
    print(f"Весь товарный поток: {total:,.2f} млн USD")
    print(f"Технологическая корзина: {technology:,.2f} млн USD")
    print(f"Доля технологической корзины: {technology_share:.2f}%")
    print(f"Промышленная корзина: {industrial:,.2f} млн USD")
    print(f"Доля промышленной корзины: {industrial_share:.2f}%")


# ============================================================
# 10. СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
# ============================================================

print_section("8. СОХРАНЕНИЕ ИТОГОВЫХ ТАБЛИЦ")

# Удобный порядок столбцов: сначала идентификация и основные результаты.
priority_columns = [
    "country_iso3",
    "country_name",
    "mean_index",
    "kmeans_cluster",
    "technology_cluster",
    "cooperation_typology",
    "structural_gap",
    "strongest_block_name",
    "weakest_block_name",
    "potential_constraint",
    "longterm_exports_to_russia_mln_usd",
    "longterm_imports_from_russia_mln_usd",
    "longterm_total_trade_mln_usd",
    "longterm_trade_balance_mln_usd",
    "recent_total_trade_mln_usd",
    "trade_rank",
    "recent_trade_rank",
    "bilateral_trade_share_pct",
]

ordered_columns = [
    col for col in priority_columns
    if col in result.columns
]

other_columns = [
    col for col in result.columns
    if col not in ordered_columns
]

result = result[ordered_columns + other_columns]

result = result.sort_values(
    "longterm_total_trade_mln_usd",
    ascending=False
).reset_index(drop=True)

save_csv(
    result,
    "trade_technology_integrated_matrix.csv"
)

save_csv(
    result[result["mean_index"].notna()].copy(),
    "trade_technology_matrix_46_countries.csv"
)

save_csv(
    result[
        result["mean_index"].isna()
    ].copy(),
    "countries_without_technology_index.csv"
)

# Отдельная таблица для приоритетной типологии.
typology_summary = (
    result.groupby(
        "cooperation_typology",
        dropna=False,
        as_index=False
    )
    .agg(
        countries=("country_iso3", "count"),
        mean_technology_index=("mean_index", "mean"),
        total_bilateral_trade_mln_usd=(
            "longterm_total_trade_mln_usd", "sum"
        ),
        mean_structural_gap=("structural_gap", "mean"),
    )
)

save_csv(
    typology_summary,
    "cooperation_typology_summary.csv"
)

# Сводка по кластерам.
cluster_summary = (
    result[result["kmeans_cluster"].notna()]
    .groupby("kmeans_cluster", as_index=False)
    .agg(
        countries=("country_iso3", "count"),
        mean_index=("mean_index", "mean"),
        mean_trade_mln_usd=(
            "longterm_total_trade_mln_usd", "mean"
        ),
        total_trade_mln_usd=(
            "longterm_total_trade_mln_usd", "sum"
        ),
        mean_structural_gap=("structural_gap", "mean"),
    )
)

save_csv(
    cluster_summary,
    "technology_clusters_trade_summary.csv"
)

# Итоговая проверка.
print_section("9. ФИНАЛЬНАЯ ПРОВЕРКА")

print(f"Итоговая матрица: {len(result)} стран")
print(f"Уникальных ISO3: {result['country_iso3'].nunique()}")
print(f"Дубли ISO3: {result['country_iso3'].duplicated().sum()}")
print(f"Стран с индексом: {result['mean_index'].notna().sum()}")
print(f"Стран без индекса: {result['mean_index'].isna().sum()}")

print("\nПервые 10 строк итоговой матрицы:")
print(
    result[
        [
            "country_iso3",
            "country_name",
            "mean_index",
            "technology_cluster",
            "structural_gap",
            "longterm_total_trade_mln_usd",
            "cooperation_typology",
        ]
    ].head(10).to_string(index=False)
)

print("\n" + "=" * 85)
print("ИНТЕГРАЦИЯ ЗАВЕРШЕНА")
print("=" * 85)

print(f"\nВсе результаты сохранены в:\n{OUTPUT_DIR}")
