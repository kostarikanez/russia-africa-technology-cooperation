
import csv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

START_YEAR = 2000
END_YEAR = 2024

# Источники и показатели для первой версии панели.
INDICATORS = {
    "gdp_per_capita_ppp": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "NY.GDP.PCAP.PP.KD"
    },
    "gdp_growth_pct": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "NY.GDP.MKTP.KD.ZG"
    },
    "gdp_constant": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "NY.GDP.MKTP.KD"
    },
    "population": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "SP.POP.TOTL"
    },
    "electricity_access_pct": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "EG.ELC.ACCS.ZS"
    },
    "internet_users_pct": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "IT.NET.USER.ZS"
    },
    "fixed_broadband_per_100": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "IT.NET.BBND.P2"
    },
    "scientific_publications": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "IP.JRN.ARTC.SC"
    },
    "tertiary_enrollment_pct": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "SE.TER.ENRR"
    },
    "manufacturing_value_added_pct": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "NV.IND.MANF.ZS"
    },
    "manufacturing_growth_pct": {
        "file": "wdi_africa_long.csv",
        "column": "indicator_code",
        "code": "NV.IND.MANF.KD.ZG"
    },
    "international_bandwidth_per_inhabitant": {
        "file": "itu_africa_long.csv",
        "column": "indicator_code",
        "code": "i994"
    },
    "wgi_cc": {
        "file": "wgi_africa_long.csv",
        "column": "indicator_code",
        "code": "GOV_WGI_CC.SC"
    },
    "wgi_ge": {
        "file": "wgi_africa_long.csv",
        "column": "indicator_code",
        "code": "GOV_WGI_GE.SC"
    },
    "wgi_pv": {
        "file": "wgi_africa_long.csv",
        "column": "indicator_code",
        "code": "GOV_WGI_PV.SC"
    },
    "wgi_rq": {
        "file": "wgi_africa_long.csv",
        "column": "indicator_code",
        "code": "GOV_WGI_RQ.SC"
    },
    "wgi_rl": {
        "file": "wgi_africa_long.csv",
        "column": "indicator_code",
        "code": "GOV_WGI_RL.SC"
    },
    "wgi_va": {
        "file": "wgi_africa_long.csv",
        "column": "indicator_code",
        "code": "GOV_WGI_VA.SC"
    }
}

# Сначала создаём справочник стран из полного ряда населения WDI.
countries = {}

population_spec = INDICATORS["population"]
population_path = DATA_DIR / population_spec["file"]

with open(
    population_path,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:
    reader = csv.DictReader(file)

    for row in reader:
        if row["indicator_code"] != population_spec["code"]:
            continue

        iso3 = row["country_iso3"].strip()

        if iso3:
            countries[iso3] = row["country_name"].strip()

print("Стран в справочнике:", len(countries))

# Создаём полную сетку страна-год.
panel = {}

for iso3, country_name in countries.items():
    for year in range(START_YEAR, END_YEAR + 1):
        panel[(iso3, year)] = {
            "country_iso3": iso3,
            "country_name": country_name,
            "year": year
        }

# Загружаем показатели.
for column_name, spec in INDICATORS.items():
    path = DATA_DIR / spec["file"]

    if not path.exists():
        print("Файл не найден:", path.name)
        continue

    matched = 0

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row.get(spec["column"], "").strip() != spec["code"]:
                continue

            iso3 = (row.get("country_iso3") or "").strip()

            try:
                year = int(row["year"])
                value = float(row["value"])
            except (ValueError, TypeError, KeyError):
                continue

            key = (iso3, year)

            if key not in panel:
                continue

            panel[key][column_name] = value
            matched += 1

    print(f"{column_name}: загружено значений {matched}")

# Рассчитываем публикации на миллион жителей.
for row in panel.values():
    publications = row.get("scientific_publications")
    population = row.get("population")

    if publications is not None and population:
        row["publications_per_million"] = (
            publications / population * 1_000_000
        )

# Порядок столбцов.
fieldnames = [
    "country_iso3",
    "country_name",
    "year",
    *INDICATORS.keys(),
    "publications_per_million"
]

rows = list(panel.values())
rows.sort(key=lambda x: (x["country_iso3"], x["year"]))

# Сохраняем панель.
panel_path = DATA_DIR / "country_year_panel_raw.csv"

with open(
    panel_path,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
        extrasaction="ignore"
    )
    writer.writeheader()
    writer.writerows(rows)

# Формируем аудит покрытия уже объединённой панели.
coverage = []

for column in fieldnames[3:]:
    available = [
        row[column]
        for row in rows
        if row.get(column) is not None
    ]

    country_count = len({
        row["country_iso3"]
        for row in rows
        if row.get(column) is not None
    })

    year_count = len({
        row["year"]
        for row in rows
        if row.get(column) is not None
    })

    coverage.append({
        "indicator": column,
        "observations": len(available),
        "countries": country_count,
        "years": year_count,
        "coverage_pct": round(
            len(available) / len(rows) * 100, 2
        )
    })

coverage_path = REPORT_DIR / "panel_coverage_report.csv"

with open(
    coverage_path,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "indicator",
            "observations",
            "countries",
            "years",
            "coverage_pct"
        ]
    )
    writer.writeheader()
    writer.writerows(coverage)

# Итог.
print("\n" + "=" * 70)
print("СБОРКА ПАНЕЛИ ЗАВЕРШЕНА")
print("=" * 70)
print("Стран:", len(countries))
print("Лет:", END_YEAR - START_YEAR + 1)
print("Строк:", len(rows))
print("Ожидаемое количество:", len(countries) * (
    END_YEAR - START_YEAR + 1
))
print("Показателей:", len(fieldnames) - 3)

print("\nПокрытие показателей:")
for item in coverage:
    print(
        f'{item["indicator"]}: '
        f'{item["observations"]} наблюдений, '
        f'{item["countries"]} стран, '
        f'{item["coverage_pct"]}%'
    )

print("\nПанель:", panel_path)
print("Аудит:", coverage_path)
