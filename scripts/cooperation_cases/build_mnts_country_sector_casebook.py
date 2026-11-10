
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent

PRIORITY_DIR = ROOT / "reports" / "mnts_cooperation_priority"
AUDIT_DIR = PRIORITY_DIR / "audit"
TECH_AUDIT_DIR = AUDIT_DIR / "technology_classification"
OUTPUT_DIR = PRIORITY_DIR / "casebook"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PERIODS = ["2002_2023", "2019_2023"]

FLOW_NAMES = {
    "imports_from_russia": "russia_to_africa",
    "exports_to_russia": "africa_to_russia",
}


# ============================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================

def section(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def normalize_keys(df):
    df = df.copy()

    if "country_iso3" in df.columns:
        df["country_iso3"] = (
            df["country_iso3"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

    if "sector" in df.columns:
        df["sector"] = (
            df["sector"]
            .astype("string")
            .str.strip()
        )

    return df


def load_csv(path, **kwargs):
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл: {path}")

    df = pd.read_csv(path, low_memory=False, **kwargs)
    return normalize_keys(df)


def safe_divide(a, b):
    if pd.isna(b) or b == 0:
        return np.nan
    return a / b


def normalize_text_column(df, source_col, target_col):
    """
    Создает нормализованный столбец из исходного.
    Не перезаписывает существующие непустые значения.
    """
    if source_col not in df.columns:
        return df

    source = (
        df[source_col]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    if target_col not in df.columns:
        df[target_col] = source
    else:
        current = (
            df[target_col]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )
        df[target_col] = current.fillna(source)

    return df


# ============================================================
# 1. ЗАГРУЗКА SHORTLIST
# ============================================================

section("1. ЗАГРУЗКА ОСНОВНОГО SHORTLIST")

shortlist_candidates = [
    AUDIT_DIR / "mnts_priority_shortlist_enriched.csv",
    PRIORITY_DIR / "mnts_priority_shortlist_enriched.csv",
    PRIORITY_DIR / "mnts_priority_shortlist.csv",
]

shortlist_path = next(
    (path for path in shortlist_candidates if path.exists()),
    None
)

if shortlist_path is None:
    raise FileNotFoundError(
        "Не найден ни один файл shortlist"
    )

shortlist = load_csv(shortlist_path)

required = {"country_iso3", "sector"}

if not required.issubset(shortlist.columns):
    raise ValueError(
        f"В shortlist отсутствуют обязательные поля: "
        f"{required - set(shortlist.columns)}"
    )

if shortlist[["country_iso3", "sector"]].isna().any().any():
    raise ValueError(
        "В shortlist обнаружены пустые country_iso3 или sector"
    )

if shortlist.duplicated(["country_iso3", "sector"]).any():
    raise ValueError(
        "В shortlist обнаружены дубликаты страна–отрасль"
    )

print("Файл:", shortlist_path.name)
print("Путь:", shortlist_path)
print("Кандидатов:", len(shortlist))
print("Стран:", shortlist["country_iso3"].nunique())
print("Отраслей:", shortlist["sector"].nunique())


# ============================================================
# 1.1. НОРМАЛИЗАЦИЯ СТРУКТУРНЫХ ПРОФИЛЕЙ
# ============================================================

section("1.1. НОРМАЛИЗАЦИЯ СТРУКТУРНЫХ ПРОФИЛЕЙ")

# В обогащенном shortlist фактические значения находятся
# в weakest_block_name, а weakest_block может быть пустым.

shortlist = normalize_text_column(
    shortlist,
    "weakest_block_name",
    "weakest_block"
)

shortlist = normalize_text_column(
    shortlist,
    "strongest_block_name",
    "strongest_block"
)

print(
    "Заполнено weakest_block:",
    shortlist["weakest_block"].notna().sum()
    if "weakest_block" in shortlist.columns else 0,
    "из",
    len(shortlist)
)

if "weakest_block" in shortlist.columns:
    print("\nРаспределение слабейших блоков:")
    print(shortlist["weakest_block"].value_counts(dropna=False))

print(
    "\nКандидатов без структурного профиля:",
    shortlist["weakest_block"].isna().sum()
    if "weakest_block" in shortlist.columns else len(shortlist)
)


# ============================================================
# 2. ЗАГРУЗКА ТОВАРНЫХ ДАННЫХ
# ============================================================

section("2. ЗАГРУЗКА HS6 ПО ДВУМ ПЕРИОДАМ")

evidence_frames = []

for period in PERIODS:

    path = AUDIT_DIR / (
        f"candidate_product_evidence_{period}.csv"
    )

    df = load_csv(path, dtype={"hs6": str})

    df["period"] = period

    if "hs6" not in df.columns:
        raise ValueError(
            f"В {path.name} отсутствует столбец hs6"
        )

    df["hs6"] = (
        df["hs6"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .str.zfill(6)
    )

    if "value_mln_usd" not in df.columns:
        raise ValueError(
            f"Нет value_mln_usd в {path.name}"
        )

    df["value_mln_usd"] = pd.to_numeric(
        df["value_mln_usd"],
        errors="coerce"
    ).fillna(0)

    required_evidence = {
        "country_iso3",
        "sector",
        "trade_flow",
        "hs6",
        "value_mln_usd"
    }

    missing = required_evidence - set(df.columns)

    if missing:
        raise ValueError(
            f"В {path.name} отсутствуют поля: {missing}"
        )

    evidence_frames.append(df)

    print(
        period,
        "| строк:", len(df),
        "| стран:", df["country_iso3"].nunique(),
        "| отраслей:", df["sector"].nunique()
    )

evidence = pd.concat(
    evidence_frames,
    ignore_index=True
)

if "product_description" not in evidence.columns:
    evidence["product_description"] = (
        "HS6 " + evidence["hs6"].astype(str)
    )
else:
    evidence["product_description"] = (
        evidence["product_description"]
        .fillna("HS6 " + evidence["hs6"].astype(str))
    )


# ============================================================
# 3. СВОДНЫЕ ТОРГОВЫЕ ПОКАЗАТЕЛИ
# ============================================================

section("3. РАСЧЁТ СТРАНОВО-ОТРАСЛЕВЫХ ПОКАЗАТЕЛЕЙ")

group_keys = [
    "country_iso3",
    "sector",
    "period",
    "trade_flow"
]

trade_summary = (
    evidence.groupby(group_keys, as_index=False)
    .agg(
        trade_value_mln_usd=("value_mln_usd", "sum"),
        products_count=("hs6", "nunique"),
        product_records=("hs6", "size")
    )
)

trade_summary["direction"] = (
    trade_summary["trade_flow"].map(FLOW_NAMES)
)

if trade_summary["direction"].isna().any():
    unknown_flows = (
        trade_summary.loc[
            trade_summary["direction"].isna(),
            "trade_flow"
        ].unique()
    )

    raise ValueError(
        f"Неизвестные направления торговли: {unknown_flows}"
    )

trade_wide = trade_summary.pivot_table(
    index=["country_iso3", "sector", "period"],
    columns="direction",
    values="trade_value_mln_usd",
    aggfunc="sum",
    fill_value=0
).reset_index()

trade_wide.columns.name = None

for direction in [
    "russia_to_africa",
    "africa_to_russia"
]:
    if direction not in trade_wide.columns:
        trade_wide[direction] = 0

products_wide = trade_summary.pivot_table(
    index=["country_iso3", "sector", "period"],
    columns="direction",
    values="products_count",
    aggfunc="sum",
    fill_value=0
).reset_index()

products_wide.columns.name = None

for direction in [
    "russia_to_africa",
    "africa_to_russia"
]:
    if direction not in products_wide.columns:
        products_wide[direction] = 0

products_wide = products_wide.rename(
    columns={
        "russia_to_africa": "products_russia_to_africa",
        "africa_to_russia": "products_africa_to_russia"
    }
)

trade_wide = trade_wide.merge(
    products_wide,
    on=["country_iso3", "sector", "period"],
    how="left",
    validate="one_to_one"
)

trade_wide["total_bilateral_trade_mln_usd"] = (
    trade_wide["russia_to_africa"]
    + trade_wide["africa_to_russia"]
)

trade_wide["directional_asymmetry"] = (
    trade_wide["russia_to_africa"]
    / trade_wide["africa_to_russia"].replace(0, np.nan)
)

trade_wide["russia_share_pct"] = (
    trade_wide["russia_to_africa"]
    / trade_wide["total_bilateral_trade_mln_usd"].replace(
        0, np.nan
    )
    * 100
)

metrics = [
    "russia_to_africa",
    "africa_to_russia",
    "total_bilateral_trade_mln_usd",
    "products_russia_to_africa",
    "products_africa_to_russia",
    "directional_asymmetry",
    "russia_share_pct"
]

trade_pivot = trade_wide.pivot_table(
    index=["country_iso3", "sector"],
    columns="period",
    values=metrics,
    aggfunc="first"
)

trade_pivot.columns = [
    f"{metric}_{period}"
    for metric, period in trade_pivot.columns
]

trade_pivot = trade_pivot.reset_index()

print(
    "Страново-отраслевых торговых профилей:",
    len(trade_wide)
)


# ============================================================
# 4. ТОП-5 ТОВАРОВ ПО КАЖДОМУ КАНДИДАТУ
# ============================================================

section("4. ВЫДЕЛЕНИЕ КОНКРЕТНЫХ ТОВАРОВ HS6")

product_keys = [
    "country_iso3",
    "sector",
    "period",
    "trade_flow",
    "hs6",
    "product_description"
]

top_products = (
    evidence.groupby(product_keys, as_index=False)
    .agg(
        value_mln_usd=("value_mln_usd", "sum")
    )
)

top_products = top_products.sort_values(
    [
        "country_iso3",
        "sector",
        "period",
        "trade_flow",
        "value_mln_usd"
    ],
    ascending=[
        True,
        True,
        True,
        True,
        False
    ]
)

top_products["total_flow_value"] = (
    top_products.groupby(
        [
            "country_iso3",
            "sector",
            "period",
            "trade_flow"
        ]
    )["value_mln_usd"].transform("sum")
)

top_products["share_pct"] = (
    top_products["value_mln_usd"]
    / top_products["total_flow_value"].replace(
        0, np.nan
    )
    * 100
)

top_products["rank"] = (
    top_products.groupby(
        [
            "country_iso3",
            "sector",
            "period",
            "trade_flow"
        ]
    ).cumcount() + 1
)

top5 = top_products[
    top_products["rank"] <= 5
].copy()

top5["trade_direction"] = top5["trade_flow"].map({
    "imports_from_russia": "Россия → Африка",
    "exports_to_russia": "Африка → Россия"
})

top5.to_csv(
    OUTPUT_DIR / "casebook_top5_products_hs6.csv",
    index=False,
    encoding="utf-8-sig"
)

top3 = top_products[
    top_products["rank"] <= 3
].copy()

top3["product_label"] = (
    top3["hs6"].astype(str)
    + " — "
    + top3["product_description"].astype(str)
)

top3["product_label"] += (
    " ($"
    + top3["value_mln_usd"].round(2).astype(str)
    + " млн; "
    + top3["share_pct"].round(1).astype(str)
    + "%)"
)

top3_text = (
    top3.groupby(
        [
            "country_iso3",
            "sector",
            "period",
            "trade_flow"
        ]
    )["product_label"]
    .agg(" | ".join)
    .reset_index()
)

top3_text["direction"] = (
    top3_text["trade_flow"].map(FLOW_NAMES)
)

top3_wide = top3_text.pivot_table(
    index=[
        "country_iso3",
        "sector",
        "period"
    ],
    columns="direction",
    values="product_label",
    aggfunc="first"
).reset_index()

top3_wide.columns.name = None

top3_wide = top3_wide.rename(
    columns={
        "russia_to_africa":
            "top3_products_russia_to_africa",
        "africa_to_russia":
            "top3_products_africa_to_russia"
    }
)

top3_pivot = top3_wide.pivot_table(
    index=["country_iso3", "sector"],
    columns="period",
    values=[
        "top3_products_russia_to_africa",
        "top3_products_africa_to_russia"
    ],
    aggfunc="first"
)

top3_pivot.columns = [
    f"{metric}_{period}"
    for metric, period in top3_pivot.columns
]

top3_pivot = top3_pivot.reset_index()

print("Товарных строк в топ-5:", len(top5))


# ============================================================
# 5. ТЕХНОЛОГИЧЕСКАЯ КЛАССИФИКАЦИЯ
# ============================================================

section("5. ТЕХНОЛОГИЧЕСКАЯ КЛАССИФИКАЦИЯ")

classification_path = (
    TECH_AUDIT_DIR
    / "mnts_candidates_technology_classified.csv"
)

classification = None

if classification_path.exists():

    classification = load_csv(
        classification_path
    )

    if classification.duplicated(
        ["country_iso3", "sector"]
    ).any():
        raise ValueError(
            "Дубликаты в технологической классификации"
        )

    if "trade_technology_type" not in classification.columns:
        raise ValueError(
            "В классификации отсутствует "
            "trade_technology_type"
        )

    classification = classification[
        [
            "country_iso3",
            "sector",
            "trade_technology_type"
        ]
    ]

    print(
        "Классификация загружена:",
        len(classification)
    )

else:
    print(
        "Файл классификации не найден — "
        "этот блок будет пропущен."
    )


# ============================================================
# 6. СБОРКА ЕДИНОГО CASEBOOK
# ============================================================

section("6. СБОРКА ЕДИНОГО РЕЕСТРА")

casebook = shortlist.copy()

initial_count = len(casebook)

casebook = casebook.merge(
    trade_pivot,
    on=["country_iso3", "sector"],
    how="left",
    validate="one_to_one"
)

casebook = casebook.merge(
    top3_pivot,
    on=["country_iso3", "sector"],
    how="left",
    validate="one_to_one"
)

if classification is not None:

    casebook = casebook.merge(
        classification,
        on=["country_iso3", "sector"],
        how="left",
        validate="one_to_one"
    )

# Контроль количества строк после объединений.
if len(casebook) != initial_count:
    raise ValueError(
        "После объединения изменилось количество строк: "
        f"{initial_count} -> {len(casebook)}"
    )

if casebook.duplicated(
    ["country_iso3", "sector"]
).any():
    raise ValueError(
        "После объединения появились дубликаты страна–отрасль"
    )


# ============================================================
# 6.1. НАЛИЧИЕ ТОРГОВЫХ ДАННЫХ
# ============================================================

for period in PERIODS:

    col = (
        f"total_bilateral_trade_mln_usd_{period}"
    )

    if col in casebook.columns:

        casebook[f"has_trade_{period}"] = (
            casebook[col].notna()
            & (casebook[col] > 0)
        )


# ============================================================
# 6.2. СРЕДНЕГОДОВЫЕ ЗНАЧЕНИЯ
# ============================================================

for period, years in {
    "2002_2023": 22,
    "2019_2023": 5
}.items():

    col = (
        f"total_bilateral_trade_mln_usd_{period}"
    )

    if col in casebook.columns:

        casebook[
            f"annual_average_trade_mln_usd_{period}"
        ] = casebook[col] / years


# ============================================================
# 6.3. СОПОСТАВЛЕНИЕ ПЕРИОДОВ
# ============================================================

full_avg = (
    "annual_average_trade_mln_usd_2002_2023"
)

recent_avg = (
    "annual_average_trade_mln_usd_2019_2023"
)

if (
    full_avg in casebook.columns
    and recent_avg in casebook.columns
):

    casebook["recent_vs_full_average_pct"] = (
        casebook[recent_avg]
        / casebook[full_avg].replace(0, np.nan)
        * 100
    )


# ============================================================
# 6.4. НАЛИЧИЕ КОНКРЕТНЫХ ТОВАРОВ
# ============================================================

for period in PERIODS:

    col = (
        f"top3_products_russia_to_africa_{period}"
    )

    if col in casebook.columns:

        casebook[
            f"has_identified_russian_products_{period}"
        ] = casebook[col].notna()


# ============================================================
# 6.5. ФЛАГИ СТРУКТУРНЫХ ПРОФИЛЕЙ
# ============================================================

if "weakest_block" in casebook.columns:

    casebook["has_structural_profile"] = (
        casebook["weakest_block"].notna()
    )

if "strongest_block" in casebook.columns:

    casebook["has_strongest_block_data"] = (
        casebook["strongest_block"].notna()
    )


# ============================================================
# 6.6. СОРТИРОВКА
# ============================================================

sort_cols = [
    c for c in [
        "preliminary_candidate",
        "evidence_count",
        "total_bilateral_trade_mln_usd_2019_2023"
    ]
    if c in casebook.columns
]

if sort_cols:

    casebook = casebook.sort_values(
        sort_cols,
        ascending=[False] * len(sort_cols),
        na_position="last"
    )


# ============================================================
# 6.7. СОХРАНЕНИЕ CASEBOOK
# ============================================================

casebook.to_csv(
    OUTPUT_DIR / "mnts_country_sector_casebook.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 7. ДИАГНОСТИКА ПОЛНОТЫ ДАННЫХ
# ============================================================

section("7. ДИАГНОСТИКА ПОЛНОТЫ ДАННЫХ")

diagnostics = []

diagnostic_columns = [
    "average_index",
    "weakest_block",
    "strongest_block",
    "structural_gap",
    "trade_technology_type",
    "total_bilateral_trade_mln_usd_2002_2023",
    "total_bilateral_trade_mln_usd_2019_2023",
    "top3_products_russia_to_africa_2002_2023",
    "top3_products_russia_to_africa_2019_2023"
]

for col in diagnostic_columns:

    if col in casebook.columns:

        diagnostics.append({
            "indicator": col,
            "filled": int(casebook[col].notna().sum()),
            "missing": int(casebook[col].isna().sum()),
            "coverage_pct": round(
                casebook[col].notna().mean() * 100,
                2
            )
        })

diagnostics_df = pd.DataFrame(diagnostics)

diagnostics_df.to_csv(
    OUTPUT_DIR / "casebook_data_coverage.csv",
    index=False,
    encoding="utf-8-sig"
)

print(diagnostics_df.to_string(index=False))


# ============================================================
# 8. КОНТРОЛЬ КАЧЕСТВА
# ============================================================

section("8. КОНТРОЛЬ КАЧЕСТВА")

print(
    "Строк в исходном shortlist:",
    len(shortlist)
)

print(
    "Строк в итоговом casebook:",
    len(casebook)
)

print(
    "Уникальных страна–отрасль:",
    casebook[
        ["country_iso3", "sector"]
    ].drop_duplicates().shape[0]
)

print(
    "Дубликатов:",
    casebook.duplicated(
        ["country_iso3", "sector"]
    ).sum()
)

print(
    "Стран:",
    casebook["country_iso3"].nunique()
)

print(
    "Отраслей:",
    casebook["sector"].nunique()
)


# ============================================================
# 8.1. СТРУКТУРНЫЕ ПРОФИЛИ
# ============================================================

if "weakest_block" in casebook.columns:

    print("\nСТРУКТУРНЫЕ ОГРАНИЧЕНИЯ:")

    print(
        "Заполнено:",
        casebook["weakest_block"].notna().sum(),
        "из",
        len(casebook)
    )

    print(
        casebook["weakest_block"]
        .value_counts(dropna=False)
        .to_string()
    )


# ============================================================
# 8.2. ТЕХНОЛОГИЧЕСКАЯ КЛАССИФИКАЦИЯ
# ============================================================

if "trade_technology_type" in casebook.columns:

    print("\nТИПЫ ТОВАРНОЙ СТРУКТУРЫ:")

    print(
        casebook["trade_technology_type"]
        .value_counts(dropna=False)
        .to_string()
    )


# ============================================================
# 8.3. ТОП-15 ПО ТОРГОВЛЕ
# ============================================================

trade_col = (
    "total_bilateral_trade_mln_usd_2019_2023"
)

if trade_col in casebook.columns:

    print("\nТОП-15 ПО ТОРГОВЛЕ 2019–2023:")

    cols = [
        c for c in [
            "country_iso3",
            "country_name",
            "sector",
            trade_col,
            "average_index",
            "weakest_block",
            "trade_technology_type"
        ]
        if c in casebook.columns
    ]

    print(
        casebook[cols]
        .sort_values(
            trade_col,
            ascending=False
        )
        .head(15)
        .to_string(index=False)
    )


# ============================================================
# 8.4. ИТОГОВЫЕ ПРОВЕРКИ
# ============================================================

if len(casebook) != len(shortlist):
    raise AssertionError(
        "Количество строк casebook не совпадает с shortlist"
    )

if casebook.duplicated(
    ["country_iso3", "sector"]
).any():
    raise AssertionError(
        "Обнаружены дубликаты в итоговом casebook"
    )

if (
    "weakest_block" in casebook.columns
    and "weakest_block_name" in shortlist.columns
):

    expected_profiles = (
        shortlist["weakest_block_name"].notna().sum()
    )

    actual_profiles = (
        casebook["weakest_block"].notna().sum()
    )

    if actual_profiles < expected_profiles:
        raise AssertionError(
            "Потеряны структурные профили при сборке: "
            f"ожидалось не менее {expected_profiles}, "
            f"получено {actual_profiles}"
        )


# ============================================================
# 9. ЗАВЕРШЕНИЕ
# ============================================================

section("9. ЗАВЕРШЕНИЕ")

print("ФАЙЛЫ СОХРАНЕНЫ В:")
print(OUTPUT_DIR)

print("\nСозданы файлы:")
print("- mnts_country_sector_casebook.csv")
print("- casebook_top5_products_hs6.csv")
print("- casebook_data_coverage.csv")

print("\nСБОРКА CASEBOOK ЗАВЕРШЕНА УСПЕШНО")
