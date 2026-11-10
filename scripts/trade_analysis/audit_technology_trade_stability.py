
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent

CASEBOOK_DIR = (
    ROOT / "reports" / "mnts_cooperation_priority" / "casebook"
)

BACi_FILE = ROOT / "data" / "processed" / "baci_russia_africa_products.csv"
CANDIDATES_FILE = CASEBOOK_DIR / "technology_case_candidate_products.csv"

START_YEAR = 2019
END_YEAR = 2023
YEARS = list(range(START_YEAR, END_YEAR + 1))

print("=" * 110)
print("АУДИТ УСТОЙЧИВОСТИ ТЕХНОЛОГИЧЕСКИХ ТОРГОВЫХ КЕЙСОВ")
print("=" * 110)

# ------------------------------------------------------------
# 1. ЗАГРУЗКА
# ------------------------------------------------------------

baci = pd.read_csv(BACi_FILE, low_memory=False)
candidates = pd.read_csv(CANDIDATES_FILE, low_memory=False)

required_baci = {
    "year", "country_iso3", "hs6",
    "trade_flow", "value_thousand_usd"
}

required_candidates = {
    "country_iso3", "sector", "hs6"
}

missing_baci = required_baci - set(baci.columns)
missing_candidates = required_candidates - set(candidates.columns)

if missing_baci:
    raise ValueError(f"В BACI отсутствуют колонки: {missing_baci}")

if missing_candidates:
    raise ValueError(
        f"В файле кандидатов отсутствуют колонки: {missing_candidates}"
    )

baci["year"] = pd.to_numeric(baci["year"], errors="coerce")
baci["hs6"] = pd.to_numeric(baci["hs6"], errors="coerce")
baci["value_thousand_usd"] = pd.to_numeric(
    baci["value_thousand_usd"], errors="coerce"
)

candidates["hs6"] = pd.to_numeric(
    candidates["hs6"], errors="coerce"
)

baci = baci[
    baci["year"].between(START_YEAR, END_YEAR)
].copy()

# ------------------------------------------------------------
# 2. ФОРМИРОВАНИЕ СПИСКА ТОВАРОВ ДЛЯ ПРОВЕРКИ
# ------------------------------------------------------------

candidate_products = (
    candidates[
        ["country_iso3", "sector", "hs6"]
    ]
    .dropna()
    .drop_duplicates()
)

candidate_products["hs6"] = (
    candidate_products["hs6"].astype(int)
)

# Если в файле кандидатов есть направление торговли,
# сохраняем его. Если нет — проверяем оба направления.
if "trade_flow" in candidates.columns:
    flows = (
        candidates[
            ["country_iso3", "sector", "hs6", "trade_flow"]
        ]
        .dropna(subset=["country_iso3", "sector", "hs6", "trade_flow"])
        .drop_duplicates()
    )
else:
    flows = candidate_products.copy()
    flows["key"] = 1

    flow_table = pd.DataFrame({
        "trade_flow": [
            "imports_from_russia",
            "exports_to_russia"
        ],
        "key": [1, 1]
    })

    flows = flows.merge(flow_table, on="key").drop(columns="key")

flows["hs6"] = flows["hs6"].astype(int)

print("\n1. ИСХОДНЫЙ МАССИВ")
print("Кандидатных товарных сочетаний:", len(flows))
print("Стран:", flows["country_iso3"].nunique())
print("Отраслей:", flows["sector"].nunique())
print("Товарных кодов HS6:", flows["hs6"].nunique())
print("Период:", START_YEAR, "—", END_YEAR)

# ------------------------------------------------------------
# 3. СОПОСТАВЛЕНИЕ С BACI
# ------------------------------------------------------------

merged = baci.merge(
    flows,
    on=["country_iso3", "hs6", "trade_flow"],
    how="inner"
)

merged["value_mln_usd"] = (
    merged["value_thousand_usd"] / 1000
)

print("\n2. РЕЗУЛЬТАТ СОПОСТАВЛЕНИЯ")
print("Строк после объединения:", len(merged))
print("Уникальных страново-отраслевых сочетаний:",
      merged[["country_iso3", "sector"]].drop_duplicates().shape[0])

# ------------------------------------------------------------
# 4. ДИНАМИКА ПО ГОДАМ
# ------------------------------------------------------------

annual = (
    merged.groupby(
        ["country_iso3", "sector", "trade_flow", "year"],
        as_index=False
    )
    .agg(
        trade_value_mln_usd=("value_mln_usd", "sum"),
        product_count=("hs6", "nunique")
    )
)

# Добавляем нулевые годы для корректной оценки регулярности.
case_flow_keys = flows[
    ["country_iso3", "sector", "trade_flow"]
].drop_duplicates()

full_index = []

for _, row in case_flow_keys.iterrows():
    for year in YEARS:
        full_index.append({
            "country_iso3": row["country_iso3"],
            "sector": row["sector"],
            "trade_flow": row["trade_flow"],
            "year": year
        })

full_index = pd.DataFrame(full_index)

annual = full_index.merge(
    annual,
    on=["country_iso3", "sector", "trade_flow", "year"],
    how="left"
)

annual["trade_value_mln_usd"] = (
    annual["trade_value_mln_usd"].fillna(0)
)

annual["product_count"] = (
    annual["product_count"].fillna(0).astype(int)
)

annual["active_year"] = (
    annual["trade_value_mln_usd"] > 0
)

annual["trade_direction"] = annual["trade_flow"].map({
    "imports_from_russia": "Россия → Африка",
    "exports_to_russia": "Африка → Россия"
})

annual = annual.sort_values(
    ["country_iso3", "sector", "trade_flow", "year"]
)

annual_file = (
    CASEBOOK_DIR / "technology_case_annual_dynamics.csv"
)

annual.to_csv(
    annual_file,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 5. СВОДНЫЕ ПОКАЗАТЕЛИ УСТОЙЧИВОСТИ
# ------------------------------------------------------------

summary_rows = []

for (country, sector, flow), group in annual.groupby(
    ["country_iso3", "sector", "trade_flow"]
):

    group = group.sort_values("year")

    total_value = group["trade_value_mln_usd"].sum()

    active_years = int(group["active_year"].sum())

    largest_year_value = group["trade_value_mln_usd"].max()

    largest_year = int(
        group.loc[
            group["trade_value_mln_usd"].idxmax(), "year"
        ]
    )

    largest_year_share = (
        largest_year_value / total_value * 100
        if total_value > 0 else 0
    )

    product_group = merged[
        (merged["country_iso3"] == country) &
        (merged["sector"] == sector) &
        (merged["trade_flow"] == flow)
    ]

    product_totals = (
        product_group.groupby("hs6")["value_mln_usd"]
        .sum()
    )

    largest_product_value = (
        product_totals.max() if len(product_totals) else 0
    )

    largest_product_hs6 = (
        int(product_totals.idxmax())
        if len(product_totals) else None
    )

    largest_product_share = (
        largest_product_value / total_value * 100
        if total_value > 0 else 0
    )

    if active_years >= 4:
        stability = "Устойчивая торговля"
    elif active_years >= 2:
        stability = "Повторяющаяся торговля"
    elif active_years == 1:
        stability = "Единичная поставка"
    else:
        stability = "Поставки не обнаружены"

    summary_rows.append({
        "country_iso3": country,
        "sector": sector,
        "trade_flow": flow,
        "trade_direction": (
            "Россия → Африка"
            if flow == "imports_from_russia"
            else "Африка → Россия"
        ),
        "total_trade_2019_2023_mln_usd": total_value,
        "active_years": active_years,
        "active_year_share_pct": active_years / len(YEARS) * 100,
        "largest_year": largest_year if total_value > 0 else None,
        "largest_year_value_mln_usd": largest_year_value,
        "largest_year_share_pct": largest_year_share,
        "largest_product_hs6": largest_product_hs6,
        "largest_product_value_mln_usd": largest_product_value,
        "largest_product_share_pct": largest_product_share,
        "stability_category": stability
    })

summary = pd.DataFrame(summary_rows)

summary = summary.sort_values(
    ["country_iso3", "sector", "trade_flow"]
)

summary_file = (
    CASEBOOK_DIR / "technology_case_stability_summary.csv"
)

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 6. ПЕЧАТЬ РЕЗУЛЬТАТОВ
# ------------------------------------------------------------

print("\n3. УСТОЙЧИВОСТЬ ТОРГОВЛИ ПО КАНДИДАТАМ")
print("-" * 110)

display_columns = [
    "country_iso3",
    "sector",
    "trade_direction",
    "total_trade_2019_2023_mln_usd",
    "active_years",
    "largest_year",
    "largest_year_share_pct",
    "largest_product_hs6",
    "largest_product_share_pct",
    "stability_category"
]

print(
    summary[display_columns]
    .round(2)
    .to_string(index=False)
)

print("\n4. СВОДКА ПО КАТЕГОРИЯМ УСТОЙЧИВОСТИ")
print("-" * 110)

print(
    summary.groupby(
        ["trade_direction", "stability_category"]
    )
    .size()
    .unstack(fill_value=0)
    .to_string()
)

print("\n5. ГОДОВАЯ ДИНАМИКА")
print("-" * 110)

print(
    annual.pivot_table(
        index=["country_iso3", "sector", "trade_direction"],
        columns="year",
        values="trade_value_mln_usd",
        aggfunc="sum",
        fill_value=0
    )
    .round(2)
    .to_string()
)

print("\n6. СОХРАНЁННЫЕ ФАЙЛЫ")
print("Годовая динамика:", annual_file)
print("Сводка устойчивости:", summary_file)

print("\n" + "=" * 110)
print("АУДИТ ЗАВЕРШЁН")
print("=" * 110)
