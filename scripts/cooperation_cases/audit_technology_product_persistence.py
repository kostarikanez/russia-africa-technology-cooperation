
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent

CASEBOOK_DIR = (
    ROOT / "reports" / "mnts_cooperation_priority" / "casebook"
)

BACI_FILE = ROOT / "data" / "processed" / "baci_russia_africa_products.csv"
CANDIDATES_FILE = CASEBOOK_DIR / "technology_case_candidate_products.csv"

YEARS = list(range(2019, 2024))

print("=" * 110)
print("АУДИТ УСТОЙЧИВОСТИ ОТДЕЛЬНЫХ ТЕХНОЛОГИЧЕСКИХ ТОВАРОВ")
print("=" * 110)

# ------------------------------------------------------------
# 1. ЗАГРУЗКА
# ------------------------------------------------------------

baci = pd.read_csv(BACI_FILE, low_memory=False)
candidates = pd.read_csv(CANDIDATES_FILE, low_memory=False)

baci["year"] = pd.to_numeric(baci["year"], errors="coerce")
baci["hs6"] = pd.to_numeric(baci["hs6"], errors="coerce")
baci["value_thousand_usd"] = pd.to_numeric(
    baci["value_thousand_usd"], errors="coerce"
)

candidates["hs6"] = pd.to_numeric(
    candidates["hs6"], errors="coerce"
)

required = ["country_iso3", "sector", "hs6"]

for col in required:
    if col not in candidates.columns:
        raise ValueError(f"В файле кандидатов нет колонки {col}")

# ------------------------------------------------------------
# 2. ПОДГОТОВКА ТОВАРНЫХ КАНДИДАТОВ
# ------------------------------------------------------------

candidate_columns = [
    "country_iso3", "sector", "hs6"
]

if "trade_flow" in candidates.columns:
    candidate_columns.append("trade_flow")

if "product_description" in candidates.columns:
    candidate_columns.append("product_description")

products = (
    candidates[candidate_columns]
    .dropna(subset=["country_iso3", "sector", "hs6"])
    .drop_duplicates()
    .copy()
)

products["hs6"] = products["hs6"].astype(int)

# Если направление не указано, проверяем оба потока.
if "trade_flow" not in products.columns:
    products["key"] = 1

    flow_table = pd.DataFrame({
        "trade_flow": [
            "imports_from_russia",
            "exports_to_russia"
        ],
        "key": [1, 1]
    })

    products = (
        products.merge(flow_table, on="key")
        .drop(columns="key")
    )

products = products.drop_duplicates(
    ["country_iso3", "sector", "hs6", "trade_flow"]
)

# ------------------------------------------------------------
# 3. СОПОСТАВЛЕНИЕ С BACI
# ------------------------------------------------------------

baci_period = baci[
    baci["year"].isin(YEARS)
].copy()

baci_period["value_mln_usd"] = (
    baci_period["value_thousand_usd"] / 1000
)

merged = baci_period.merge(
    products,
    on=["country_iso3", "hs6", "trade_flow"],
    how="inner"
)

print("\n1. ОБЪЁМ СОПОСТАВЛЕНИЯ")
print("Товарных кандидатов:", len(products))
print("Строк BACI после объединения:", len(merged))
print("Стран:", merged["country_iso3"].nunique())
print("Товарных кодов:", merged["hs6"].nunique())

# ------------------------------------------------------------
# 4. АГРЕГАЦИЯ ПО ТОВАРАМ И ГОДАМ
# ------------------------------------------------------------

keys = [
    "country_iso3", "sector", "hs6", "trade_flow"
]

annual = (
    merged.groupby(keys + ["year"], as_index=False)
    .agg(
        value_mln_usd=("value_mln_usd", "sum")
    )
)

# Формируем полную сетку, включая годы без поставок.
base = products[keys].drop_duplicates()

grid = []

for _, row in base.iterrows():
    for year in YEARS:
        item = row.to_dict()
        item["year"] = year
        grid.append(item)

grid = pd.DataFrame(grid)

annual = grid.merge(
    annual,
    on=keys + ["year"],
    how="left"
)

annual["value_mln_usd"] = (
    annual["value_mln_usd"].fillna(0)
)

annual["active"] = annual["value_mln_usd"] > 0

annual = annual.merge(
    products.drop_duplicates(keys),
    on=keys,
    how="left"
)

annual["trade_direction"] = annual["trade_flow"].map({
    "imports_from_russia": "Россия → Африка",
    "exports_to_russia": "Африка → Россия"
})

# ------------------------------------------------------------
# 5. СВОДКА ПО КАЖДОМУ HS6
# ------------------------------------------------------------

summary_rows = []

for key, group in annual.groupby(keys):

    country, sector, hs6, flow = key

    group = group.sort_values("year")

    total = group["value_mln_usd"].sum()
    active_years = int(group["active"].sum())

    max_year_value = group["value_mln_usd"].max()

    max_year = int(
        group.loc[
            group["value_mln_usd"].idxmax(), "year"
        ]
    ) if total > 0 else None

    max_year_share = (
        max_year_value / total * 100 if total > 0 else 0
    )

    active_year_list = group.loc[
        group["active"], "year"
    ].astype(int).tolist()

    if active_years == 5:
        persistence = "Все 5 лет"
    elif active_years == 4:
        persistence = "4 из 5 лет"
    elif active_years >= 2:
        persistence = "2–3 года"
    elif active_years == 1:
        persistence = "Один год"
    else:
        persistence = "Нет поставок"

    description = None
    if "product_description" in group.columns:
        values = group["product_description"].dropna()
        if len(values):
            description = values.iloc[0]

    summary_rows.append({
        "country_iso3": country,
        "sector": sector,
        "hs6": hs6,
        "product_description": description,
        "trade_flow": flow,
        "trade_direction": (
            "Россия → Африка"
            if flow == "imports_from_russia"
            else "Африка → Россия"
        ),
        "total_value_mln_usd_2019_2023": total,
        "active_years": active_years,
        "active_years_list": ", ".join(
            map(str, active_year_list)
        ),
        "largest_year": max_year,
        "largest_year_share_pct": max_year_share,
        "persistence_category": persistence
    })

summary = pd.DataFrame(summary_rows)

summary = summary.sort_values(
    [
        "active_years",
        "total_value_mln_usd_2019_2023"
    ],
    ascending=[False, False]
)

# ------------------------------------------------------------
# 6. СОХРАНЕНИЕ
# ------------------------------------------------------------

annual_file = CASEBOOK_DIR / "technology_product_annual_dynamics.csv"
summary_file = CASEBOOK_DIR / "technology_product_persistence.csv"

annual.to_csv(
    annual_file,
    index=False,
    encoding="utf-8-sig"
)

summary.to_csv(
    summary_file,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 7. ВЫВОД РЕЗУЛЬТАТОВ
# ------------------------------------------------------------

print("\n2. УСТОЙЧИВЫЕ ТОВАРЫ — ВСЕ 5 ЛЕТ")
print("-" * 110)

print(
    summary[
        summary["active_years"] == 5
    ][
        [
            "country_iso3",
            "sector",
            "hs6",
            "product_description",
            "trade_direction",
            "total_value_mln_usd_2019_2023",
            "largest_year_share_pct"
        ]
    ].round(2).head(40).to_string(index=False)
)

print("\n3. ТОВАРЫ С АКТИВНОСТЬЮ 4 ИЗ 5 ЛЕТ")
print("-" * 110)

print(
    summary[
        summary["active_years"] == 4
    ][
        [
            "country_iso3",
            "sector",
            "hs6",
            "product_description",
            "trade_direction",
            "total_value_mln_usd_2019_2023"
        ]
    ].round(2).head(30).to_string(index=False)
)

print("\n4. РАСПРЕДЕЛЕНИЕ ПО УСТОЙЧИВОСТИ")
print("-" * 110)

print(
    summary.groupby(
        ["trade_direction", "persistence_category"]
    )
    .size()
    .unstack(fill_value=0)
    .to_string()
)

print("\n5. ГОДОВАЯ ДИНАМИКА: ТОП-20 ТОВАРОВ")
print("-" * 110)

top = summary.head(20)[keys].drop_duplicates()

top_annual = annual.merge(
    top,
    on=keys,
    how="inner"
)

print(
    top_annual.pivot_table(
        index=[
            "country_iso3", "sector", "hs6",
            "trade_direction"
        ],
        columns="year",
        values="value_mln_usd",
        aggfunc="sum",
        fill_value=0
    ).round(3).to_string()
)

print("\n6. СОХРАНЁННЫЕ ФАЙЛЫ")
print("Годовая динамика:", annual_file)
print("Устойчивость товаров:", summary_file)

print("\n" + "=" * 110)
print("АУДИТ ЗАВЕРШЁН")
print("=" * 110)
