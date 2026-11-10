
import csv
import re
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# 1. ПУТИ И ПАРАМЕТРЫ
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

BASE_DIR = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "wgi"
    / "wgi"
)

SOURCE_FILE = BASE_DIR / "wgi_data_1.csv"

REFERENCE_FILE = (
    PROJECT_DIR
    / "data"
    / "reference"
    / "baci_africa_country_codes.csv"
)

OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "wgi_africa_long.csv"
LOG_FILE = OUTPUT_DIR / "wgi_processing_log.csv"

START_YEAR = 2000
END_YEAR = 2024


# ============================================================
# 2. СПРАВОЧНИК СТРАН
# ============================================================

with open(
    REFERENCE_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)
    reference_rows = list(reader)

country_reference = {}

for row in reference_rows:

    iso3 = row["country_iso3"].strip()
    name = row["country_name"].strip()

    country_reference[iso3] = name

african_iso3 = set(country_reference)

print("=" * 70)
print("ИЗВЛЕЧЕНИЕ ДАННЫХ WGI ПО АФРИКЕ")
print("=" * 70)

print("Стран в справочнике:", len(african_iso3))


# ============================================================
# 3. ЗАГРУЗКА ИСХОДНОГО ФАЙЛА
# ============================================================

with open(
    SOURCE_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)
    source_rows = list(reader)
    headers = reader.fieldnames


# ============================================================
# 4. ОПРЕДЕЛЕНИЕ ГОДОВЫХ КОЛОНОК
# ============================================================

year_columns = {}

for column in headers:

    match = re.match(
        r"^(\d{4}) \[YR\d{4}\]$",
        column.strip()
    )

    if match:

        year = int(match.group(1))

        if START_YEAR <= year <= END_YEAR:
            year_columns[year] = column

years = sorted(year_columns)

print("Годы:", years)
print("Количество доступных лет:", len(years))


# ============================================================
# 5. СПРАВОЧНИК ПОКАЗАТЕЛЕЙ
# ============================================================

indicator_names = {
    "GOV_WGI_CC.SC": "Control of Corruption",
    "GOV_WGI_GE.SC": "Government Effectiveness",
    "GOV_WGI_PV.SC": "Political Stability",
    "GOV_WGI_RQ.SC": "Regulatory Quality",
    "GOV_WGI_RL.SC": "Rule of Law",
    "GOV_WGI_VA.SC": "Voice and Accountability"
}


# ============================================================
# 6. ФИЛЬТРАЦИЯ И ПРЕОБРАЗОВАНИЕ
# ============================================================

result = []

excluded_non_african = 0
excluded_service = 0
excluded_empty = 0
invalid_values = 0

country_counts = Counter()
indicator_counts = Counter()
year_counts = Counter()

for row in source_rows:

    country_iso3 = (row["Country Code"] or "").strip()
    indicator_code = (row["Series Code"] or "").strip()

    # Исключаем служебные строки и неизвестные показатели.
    if indicator_code not in indicator_names:
        excluded_service += 1
        continue

    # Оставляем только африканские страны.
    if country_iso3 not in african_iso3:
        excluded_non_african += 1
        continue

    country_name = country_reference[country_iso3]

    for year, column in year_columns.items():

        raw_value = (row.get(column) or "").strip()

        # Пропуски не заменяем нулями.
        if raw_value in ("", ".."):
            excluded_empty += 1
            continue

        try:
            value = float(raw_value)

        except ValueError:
            invalid_values += 1
            continue

        observation = {
            "country_iso3": country_iso3,
            "country_name": country_name,
            "year": year,
            "indicator_code": indicator_code,
            "indicator_name": indicator_names[indicator_code],
            "value": value
        }

        result.append(observation)

        country_counts[country_iso3] += 1
        indicator_counts[indicator_code] += 1
        year_counts[year] += 1


# ============================================================
# 7. ПРОВЕРКА ДУБЛИКАТОВ
# ============================================================

key_counts = Counter(
    (
        row["country_iso3"],
        row["year"],
        row["indicator_code"]
    )
    for row in result
)

duplicate_groups = {
    key: count
    for key, count in key_counts.items()
    if count > 1
}


# ============================================================
# 8. СОХРАНЕНИЕ ОСНОВНОГО ФАЙЛА
# ============================================================

fieldnames = [
    "country_iso3",
    "country_name",
    "year",
    "indicator_code",
    "indicator_name",
    "value"
]

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(result)


# ============================================================
# 9. ЖУРНАЛ ОБРАБОТКИ
# ============================================================

log = [
    ("source_file", SOURCE_FILE.name),
    ("source_rows", len(source_rows)),
    ("selected_observations", len(result)),
    ("matched_countries", len(country_counts)),
    ("reference_countries", len(african_iso3)),
    ("excluded_non_african", excluded_non_african),
    ("excluded_service_rows", excluded_service),
    ("excluded_empty_values", excluded_empty),
    ("invalid_values", invalid_values),
    ("duplicate_groups", len(duplicate_groups)),
    ("start_year", START_YEAR),
    ("end_year", END_YEAR),
    ("available_years", len(years)),
    ("indicators", len(indicator_counts))
]

with open(
    LOG_FILE,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.writer(file)
    writer.writerow(["category", "value"])

    for category, value in log:
        writer.writerow([category, value])


# ============================================================
# 10. ИТОГОВЫЙ ОТЧЁТ
# ============================================================

print("\n" + "=" * 70)
print("РЕЗУЛЬТАТЫ ОБРАБОТКИ")
print("=" * 70)

print("Исходных строк:", len(source_rows))
print("Итоговых наблюдений:", len(result))
print("Африканских стран:", len(country_counts))
print("Показателей:", len(indicator_counts))
print("Период:", START_YEAR, "-", END_YEAR)

print("\nИСКЛЮЧЕНО:")
print("Неафриканские строки:", excluded_non_african)
print("Служебные строки:", excluded_service)
print("Пустые значения:", excluded_empty)
print("Некорректные значения:", invalid_values)

print("\nНАБЛЮДЕНИЯ ПО ПОКАЗАТЕЛЯМ:")

for code, count in sorted(indicator_counts.items()):
    print(code, "|", indicator_names[code], "|", count)

print("\nНАБЛЮДЕНИЯ ПО ГОДАМ:")

for year in years:
    print(year, "|", year_counts[year])

print("\nГрупп дубликатов:", len(duplicate_groups))

missing_countries = african_iso3 - set(country_counts)

print("\nСтраны без единого наблюдения:", sorted(missing_countries))

print("\nСОХРАНЕНО:")
print(OUTPUT_FILE)
print(LOG_FILE)

print("\nИЗВЛЕЧЕНИЕ WGI ЗАВЕРШЕНО")
print("=" * 70)
