
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent

CASEBOOK_DIR = (
    ROOT / "reports" / "mnts_cooperation_priority" / "casebook"
)

INPUT = CASEBOOK_DIR / "mnts_country_sector_casebook.csv"
OUTPUT = CASEBOOK_DIR / "mnts_top15_case_selection.csv"

df = pd.read_csv(INPUT, low_memory=False)

cases = [
    ("EGY", "Transport equipment", "I", "Инженерные и транспортные технологии"),
    ("DZA", "Electrical equipment", "I", "Инженерные и транспортные технологии"),
    ("EGY", "Electrical equipment", "I", "Инженерные и транспортные технологии"),
    ("DZA", "Transport equipment", "I", "Инженерные и транспортные технологии"),
    ("ZAF", "Electrical equipment", "I", "Инженерные и транспортные технологии"),
    ("UGA", "Transport equipment", "I", "Инженерные и транспортные технологии"),
    ("AGO", "Transport equipment", "I", "Инженерные и транспортные технологии"),
    ("MAR", "Other chemicals", "II", "Промышленная переработка"),
    ("ZAF", "Fertilizers", "II", "Промышленная переработка"),
    ("EGY", "Metals and metal products", "II", "Промышленная переработка"),
    ("ZAF", "Metals and metal products", "II", "Промышленная переработка"),
    ("MAR", "Energy goods", "III", "Энергетика"),
    ("NGA", "Energy goods", "III", "Энергетика"),
    ("SEN", "Energy goods", "III", "Энергетика"),
    ("GHA", "Energy goods", "III", "Энергетика"),
]

selection = pd.DataFrame(
    cases,
    columns=[
        "country_iso3",
        "sector",
        "research_group",
        "research_direction"
    ]
)

selection = selection.merge(
    df,
    on=["country_iso3", "sector"],
    how="left",
    indicator=True,
    validate="one_to_one"
)

selection["casebook_match"] = (
    selection["_merge"] == "both"
)

selection = selection.drop(columns="_merge")

if not selection["casebook_match"].all():
    print("\nВНИМАНИЕ: некоторые пары не найдены:")
    print(
        selection.loc[
            ~selection["casebook_match"],
            ["country_iso3", "sector"]
        ].to_string(index=False)
    )

selection["evidence_to_verify"] = (
    "Национальная стратегия; "
    "африканская технологическая потребность; "
    "российские компании и компетенции; "
    "действующие проекты; "
    "локализация и подготовка кадров"
)

selection["methodological_warning"] = (
    "Торговля товарами не доказывает трансфер технологий"
)

selection.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

print("=" * 90)
print("ПРЕДВАРИТЕЛЬНАЯ ВЫБОРКА 15 КЕЙСОВ")
print("=" * 90)

print("Всего:", len(selection))
print("Найдено в casebook:", selection["casebook_match"].sum())
print("Не найдено:", (~selection["casebook_match"]).sum())

print("\nРаспределение по направлениям:")
print(selection["research_direction"].value_counts())

print("\nСписок:")
print(
    selection[
        [
            "country_iso3",
            "country_name",
            "sector",
            "research_group",
            "average_index",
            "weakest_block",
            "total_bilateral_trade_mln_usd_2019_2023",
            "trade_technology_type",
            "casebook_match"
        ]
    ].to_string(index=False)
)

print("\nСохранено:", OUTPUT)
