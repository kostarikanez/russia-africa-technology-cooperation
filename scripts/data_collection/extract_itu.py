
import csv
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# 1. ПУТИ К ФАЙЛАМ
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

MACRO_DIR = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
)

REFERENCE_FILE = (
    PROJECT_DIR
    / "data"
    / "reference"
    / "baci_africa_country_codes.csv"
)

OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "itu_africa_long.csv"
LOG_FILE = OUTPUT_DIR / "itu_processing_log.csv"


# ============================================================
# 2. ПОИСК ИСХОДНОГО ФАЙЛА
# ============================================================

itu_files = list(MACRO_DIR.rglob("itu_data.csv"))

if not itu_files:
    raise FileNotFoundError(
        f"Файл itu_data.csv не найден: {MACRO_DIR}"
    )

ITU_FILE = itu_files[0]

if not REFERENCE_FILE.exists():
    raise FileNotFoundError(
        f"Справочник стран не найден: {REFERENCE_FILE}"
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 3. ЗАГРУЗКА СПРАВОЧНИКА АФРИКАНСКИХ СТРАН
# ============================================================

africa_countries = {}

with open(
    REFERENCE_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)

    for row in reader:

        iso3 = row["country_iso3"].strip()
        name = row["country_name"].strip()

        africa_countries[iso3] = name

print("=" * 60)
print("СПРАВОЧНИК АФРИКАНСКИХ СТРАН")
print("=" * 60)

print("Уникальных стран:", len(africa_countries))


# ============================================================
# 4. ЧТЕНИЕ ИСХОДНЫХ ДАННЫХ ITU
# ============================================================

source_rows = 0
africa_rows = 0

outside_africa = 0
technical_rows = 0
invalid_years = 0
outside_period = 0
empty_values = 0
invalid_values = 0

# Храним наблюдения по ключу
observations = defaultdict(list)

# Статистика
countries_found = set()
indicators_found = set()
years_found = set()
units_found = set()

# Лог обработки
processing_log = []


with open(
    ITU_FILE,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)

    for row in reader:

        source_rows += 1

        iso3 = (row["AreaCode"] or "").strip()
        year_raw = (row["Year"] or "").strip()
        code = (row["SeriesCode"] or "").strip()
        value_raw = (row["Value"] or "").strip()

        # ----------------------------------------------------
        # Исключаем технические строки
        # ----------------------------------------------------

        if not iso3 or not year_raw or not code:
            technical_rows += 1
            continue

        # ----------------------------------------------------
        # Оставляем только 54 африканские страны
        # ----------------------------------------------------

        if iso3 not in africa_countries:
            outside_africa += 1
            continue

        africa_rows += 1

        # ----------------------------------------------------
        # Проверяем год
        # ----------------------------------------------------

        try:
            year = int(year_raw)
        except ValueError:
            invalid_years += 1
            continue

        if year < 2000 or year > 2025:
            outside_period += 1
            continue

        # ----------------------------------------------------
        # Проверяем числовое значение
        # ----------------------------------------------------

        if value_raw == "":
            empty_values += 1
            continue

        try:
            numeric_value = float(value_raw)

            if not (
                numeric_value == numeric_value
                and abs(numeric_value) != float("inf")
            ):
                raise ValueError

        except ValueError:
            invalid_values += 1
            continue

        # ----------------------------------------------------
        # Формируем наблюдение
        # ----------------------------------------------------

        record = {
            "country_iso3": iso3,
            "country_name": africa_countries[iso3],
            "year": year,
            "indicator_code": code,
            "indicator_name": (row["Series"] or "").strip(),
            "unit": (row["Unit"] or "").strip(),
            "value": value_raw,
            "source": (row["Source"] or "").strip()
        }

        key = (
            iso3,
            year,
            code
        )

        observations[key].append(record)

        countries_found.add(iso3)
        indicators_found.add(code)
        years_found.add(year)
        units_found.add(record["unit"])


# ============================================================
# 5. ОБРАБОТКА ДУБЛИКАТОВ
# ============================================================

clean_records = []
duplicate_keys = 0
identical_duplicates = 0
conflicting_duplicates = 0

for key, records in observations.items():

    if len(records) == 1:
        clean_records.append(records[0])
        continue

    duplicate_keys += 1

    # Группируем записи по значениям
    values = {}

    for record in records:

        value = record["value"]

        if value not in values:
            values[value] = record

        else:
            # При одинаковом значении предпочитаем запись
            # с заполненным источником
            current = values[value]

            if not current["source"] and record["source"]:
                values[value] = record

    if len(values) == 1:

        identical_duplicates += 1

        clean_records.append(
            next(iter(values.values()))
        )

    else:

        # Если значения различаются, не удаляем их автоматически
        conflicting_duplicates += 1

        for record in values.values():
            clean_records.append(record)

        processing_log.append({
            "event": "conflicting_duplicate",
            "country_iso3": key[0],
            "year": key[1],
            "indicator_code": key[2],
            "details": "Различающиеся непустые значения сохранены"
        })


# ============================================================
# 6. СОХРАНЕНИЕ ОБРАБОТАННЫХ ДАННЫХ
# ============================================================

fieldnames = [
    "country_iso3",
    "country_name",
    "year",
    "indicator_code",
    "indicator_name",
    "unit",
    "value",
    "source"
]

clean_records.sort(
    key=lambda x: (
        x["country_iso3"],
        x["year"],
        x["indicator_code"]
    )
)

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
    writer.writerows(clean_records)


# ============================================================
# 7. СОХРАНЕНИЕ ЖУРНАЛА ОБРАБОТКИ
# ============================================================

log_summary = [
    {
        "event": "source_rows",
        "country_iso3": "",
        "year": "",
        "indicator_code": "",
        "details": str(source_rows)
    },
    {
        "event": "technical_rows_excluded",
        "country_iso3": "",
        "year": "",
        "indicator_code": "",
        "details": str(technical_rows)
    },
    {
        "event": "outside_africa_excluded",
        "country_iso3": "",
        "year": "",
        "indicator_code": "",
        "details": str(outside_africa)
    },
    {
        "event": "empty_values_excluded",
        "country_iso3": "",
        "year": "",
        "indicator_code": "",
        "details": str(empty_values)
    },
    {
        "event": "identical_duplicates_removed",
        "country_iso3": "",
        "year": "",
        "indicator_code": "",
        "details": str(identical_duplicates)
    },
    {
        "event": "conflicting_duplicates",
        "country_iso3": "",
        "year": "",
        "indicator_code": "",
        "details": str(conflicting_duplicates)
    }
]

log_records = log_summary + processing_log

with open(
    LOG_FILE,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    log_fields = [
        "event",
        "country_iso3",
        "year",
        "indicator_code",
        "details"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=log_fields
    )

    writer.writeheader()
    writer.writerows(log_records)


# ============================================================
# 8. ИТОГОВАЯ СТАТИСТИКА
# ============================================================

print("\n" + "=" * 60)
print("РЕЗУЛЬТАТЫ ОБРАБОТКИ ITU")
print("=" * 60)

print("Исходных строк:", f"{source_rows:,}")
print("Африканских строк:", f"{africa_rows:,}")

print("Исключено технических строк:", technical_rows)
print("Исключено строк вне Африки:", f"{outside_africa:,}")
print("Исключено пустых значений:", empty_values)
print("Некорректных значений:", invalid_values)
print("Некорректных годов:", invalid_years)

print("\nДубликаты:")
print("Комбинаций с дубликатами:", duplicate_keys)
print("Идентичных дубликатов устранено:", identical_duplicates)
print("Конфликтных комбинаций:", conflicting_duplicates)

print("\nИтоговые данные:")
print("Наблюдений:", f"{len(clean_records):,}")
print("Стран:", len(countries_found))
print("Показателей:", len(indicators_found))
print("Лет:", len(years_found))

if years_found:
    print("Период:", min(years_found), "-", max(years_found))

print("\nСтраны:")
print(sorted(countries_found))

print("\nПоказатели:")
for code in sorted(indicators_found):
    print(code)

print("\nЕдиницы измерения:")
for unit in sorted(units_found):
    print(unit)

print("\nФайл данных сохранён:")
print(OUTPUT_FILE)

print("\nЖурнал обработки сохранён:")
print(LOG_FILE)

print("\n" + "=" * 60)
print("ОБРАБОТКА ITU ЗАВЕРШЕНА")
print("=" * 60)
