
import csv
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# 1. ПУТИ
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

BASE_DIR = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "wipo"
)

REFERENCE_FILE = (
    PROJECT_DIR
    / "data"
    / "reference"
    / "baci_africa_country_codes.csv"
)

OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "wipo_africa_long.csv"
LOG_FILE = OUTPUT_DIR / "wipo_processing_log.csv"

FILES = {
    "PATENT": "wipo_patent.csv",
    "PCT": "wipo_pct.csv",
    "TRADEMARK": "wipo_trademark.csv"
}

INDICATORS = {
    "PATENT": "Patent applications by office",
    "PCT": "PCT applications received by receiving office",
    "TRADEMARK": "Trademark applications by office"
}


# ============================================================
# 2. ЧТЕНИЕ CSV
# ============================================================

def parse_wipo_file(path):

    parsed_rows = []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        for line_number, raw_line in enumerate(file, start=1):

            line = raw_line.strip()

            if not line:
                continue

            # Некоторые строки целиком обёрнуты в кавычки.
            if line.startswith('"') and line.endswith('"'):

                line = line[1:-1]
                line = line.replace('""', '"')

            values = next(csv.reader([line]))

            parsed_rows.append({
                "line_number": line_number,
                "values": values
            })

    if not parsed_rows:
        return [], []

    headers = parsed_rows[0]["values"]

    # Убираем пустые завершающие колонки.
    while headers and headers[-1] == "":
        headers.pop()

    data = []

    for item in parsed_rows[1:]:

        values = item["values"]

        while len(values) > len(headers) and values[-1] == "":
            values.pop()

        if len(values) != len(headers):

            raise ValueError(
                f"Ошибка структуры {path.name}, "
                f"строка {item['line_number']}: "
                f"{len(values)} значений вместо {len(headers)}"
            )

        data.append(dict(zip(headers, values)))

    return headers, data


# ============================================================
# 3. СПРАВОЧНИК СТРАН
# ============================================================

def load_country_reference(path):

    iso2_to_country = {}

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            iso2 = row["country_iso2"].strip().upper()
            iso3 = row["country_iso3"].strip().upper()
            name = row["country_name"].strip()

            if iso2 and iso3:
                iso2_to_country[iso2] = {
                    "country_iso3": iso3,
                    "country_name": name
                }

    return iso2_to_country


# ============================================================
# 4. ЧИСЛОВЫЕ ЗНАЧЕНИЯ
# ============================================================

def parse_value(raw_value):

    value = raw_value.strip()

    if value == "":
        return None

    number = float(value.replace(",", ""))

    if number.is_integer():
        return int(number)

    return number


# ============================================================
# 5. ЗАГРУЗКА СПРАВОЧНИКА
# ============================================================

print("=" * 70)
print("ИЗВЛЕЧЕНИЕ ДАННЫХ WIPO ПО АФРИКЕ")
print("=" * 70)

country_reference = load_country_reference(REFERENCE_FILE)

print("Стран в справочнике:", len(country_reference))


# ============================================================
# 6. ОБРАБОТКА ТРЁХ ИСТОЧНИКОВ
# ============================================================

all_observations = []
log_records = []

source_country_sets = {}

total_source_rows = 0
total_empty = 0
total_invalid = 0
total_unmatched_countries = 0

for category, filename in FILES.items():

    path = BASE_DIR / filename

    print("\n" + "-" * 70)
    print("ОБРАБОТКА:", category)
    print("-" * 70)

    headers, rows = parse_wipo_file(path)

    total_source_rows += len(rows)

    if category == "PCT":

        office_column = "Receiving Office (RO)"
        code_column = "Receiving Office (RO)(Code)"
        origin_column = "Origin"
        origin_code_column = "Origin(Code)"

    else:

        office_column = "Office"
        code_column = "Office (Code)"
        origin_column = "Origin"
        origin_code_column = None

    year_columns = [
        column
        for column in headers
        if column.isdigit()
    ]

    source_countries = set()
    matched_countries = set()

    source_observations = 0
    empty_values = 0
    invalid_values = 0

    for row in rows:

        office_name = row[office_column].strip()
        office_iso2 = row[code_column].strip().upper()

        if office_iso2:
            source_countries.add(office_iso2)

        country = country_reference.get(office_iso2)

        if country is None:

            total_unmatched_countries += 1

            print(
                "НЕ НАЙДЕНА СТРАНА:",
                office_name,
                office_iso2
            )

            continue

        matched_countries.add(office_iso2)

        origin = row.get(origin_column, "").strip()
        origin_code = (
            row.get(origin_code_column, "").strip()
            if origin_code_column
            else ""
        )

        # В Patent и Trademark есть Type.
        # В PCT этого измерения нет.
        application_type = row.get("Type", "").strip()

        for year_column in year_columns:

            raw_value = row[year_column].strip()

            if raw_value == "":

                empty_values += 1
                continue

            try:

                value = parse_value(raw_value)

            except ValueError:

                invalid_values += 1

                print(
                    "НЕКОРРЕКТНОЕ ЗНАЧЕНИЕ:",
                    category,
                    office_iso2,
                    year_column,
                    raw_value
                )

                continue

            observation = {
                "country_iso3": country["country_iso3"],
                "country_name": country["country_name"],
                "office_name": office_name,
                "office_iso2": office_iso2,
                "year": int(year_column),
                "ip_category": category,
                "indicator": INDICATORS[category],
                "origin": origin,
                "origin_code": origin_code,
                "application_type": application_type,
                "value": value,
                "unit": "applications",
                "source_file": filename
            }

            all_observations.append(observation)
            source_observations += 1

    source_country_sets[category] = matched_countries

    total_empty += empty_values
    total_invalid += invalid_values

    log_records.extend([
        {
            "category": category,
            "metric": "source_rows",
            "value": len(rows)
        },
        {
            "category": category,
            "metric": "source_countries",
            "value": len(source_countries)
        },
        {
            "category": category,
            "metric": "matched_countries",
            "value": len(matched_countries)
        },
        {
            "category": category,
            "metric": "observations",
            "value": source_observations
        },
        {
            "category": category,
            "metric": "empty_values",
            "value": empty_values
        },
        {
            "category": category,
            "metric": "invalid_values",
            "value": invalid_values
        },
        {
            "category": category,
            "metric": "first_year",
            "value": min(map(int, year_columns))
        },
        {
            "category": category,
            "metric": "last_year",
            "value": max(map(int, year_columns))
        }
    ])

    print("Строк источника:", len(rows))
    print("Стран:", len(source_countries))
    print("Сопоставлено стран:", len(matched_countries))
    print("Непустых наблюдений:", source_observations)
    print("Пустых значений:", empty_values)
    print("Некорректных значений:", invalid_values)


# ============================================================
# 7. ПРОВЕРКА ДУБЛИКАТОВ
# ============================================================

print("\n" + "=" * 70)
print("ПРОВЕРКА ДУБЛИКАТОВ")
print("=" * 70)

keys = Counter(
    (
        row["country_iso3"],
        row["year"],
        row["ip_category"],
        row["origin"],
        row["origin_code"],
        row["application_type"]
    )
    for row in all_observations
)

duplicates = {
    key: count
    for key, count in keys.items()
    if count > 1
}

print("Групп дубликатов:", len(duplicates))

for key, count in list(duplicates.items())[:20]:
    print(key, count)


# ============================================================
# 8. СОХРАНЕНИЕ ЕДИНОГО ФАЙЛА
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

fieldnames = [
    "country_iso3",
    "country_name",
    "office_name",
    "office_iso2",
    "year",
    "ip_category",
    "indicator",
    "origin",
    "origin_code",
    "application_type",
    "value",
    "unit",
    "source_file"
]

all_observations.sort(
    key=lambda row: (
        row["country_iso3"],
        row["year"],
        row["ip_category"],
        row["application_type"]
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
    writer.writerows(all_observations)


# ============================================================
# 9. СОХРАНЕНИЕ ЖУРНАЛА
# ============================================================

log_records.extend([
    {
        "category": "ALL",
        "metric": "source_rows",
        "value": total_source_rows
    },
    {
        "category": "ALL",
        "metric": "observations",
        "value": len(all_observations)
    },
    {
        "category": "ALL",
        "metric": "empty_values",
        "value": total_empty
    },
    {
        "category": "ALL",
        "metric": "invalid_values",
        "value": total_invalid
    },
    {
        "category": "ALL",
        "metric": "duplicate_groups",
        "value": len(duplicates)
    },
    {
        "category": "ALL",
        "metric": "unmatched_country_rows",
        "value": total_unmatched_countries
    }
])

with open(
    LOG_FILE,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=["category", "metric", "value"]
    )

    writer.writeheader()
    writer.writerows(log_records)


# ============================================================
# 10. ИТОГОВАЯ СТАТИСТИКА
# ============================================================

print("\n" + "=" * 70)
print("ИТОГИ ОБРАБОТКИ WIPO")
print("=" * 70)

print("Всего исходных строк:", total_source_rows)
print("Итоговых наблюдений:", len(all_observations))

print(
    "Уникальных стран:",
    len({
        row["country_iso3"]
        for row in all_observations
    })
)

print(
    "Групп дубликатов:",
    len(duplicates)
)

print("\nНАБЛЮДЕНИЯ ПО КАТЕГОРИЯМ:")

category_counts = Counter(
    row["ip_category"]
    for row in all_observations
)

for category, count in sorted(category_counts.items()):
    print(category, "|", count)

print("\nНАБЛЮДЕНИЯ ПО ГОДАМ:")

year_counts = Counter(
    row["year"]
    for row in all_observations
)

for year, count in sorted(year_counts.items()):
    print(year, "|", count)

print("\nСТРАНЫ ПО КАТЕГОРИЯМ:")

for category, countries in source_country_sets.items():

    print(
        category,
        "|",
        len(countries),
        "|",
        sorted(countries)
    )

print("\nСОХРАНЕНО:")
print(OUTPUT_FILE)
print(LOG_FILE)

print("\nПУСТЫХ ЗНАЧЕНИЙ:", total_empty)
print("НЕКОРРЕКТНЫХ ЗНАЧЕНИЙ:", total_invalid)

print("\nИЗВЛЕЧЕНИЕ WIPO ЗАВЕРШЕНО")
print("=" * 70)
