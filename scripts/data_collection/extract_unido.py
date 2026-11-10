
import csv
import re
import unicodedata
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# 1. ПУТИ
# ============================================================

BASE_DIR = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
)

UNIDO_DIR = BASE_DIR / "unido" / "unido_download"

SOURCE_FILE = UNIDO_DIR / "unido_data.csv"

REFERENCE_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "reference"
    / "baci_africa_country_codes.csv"
)

OUTPUT_DIR = (
    Path(__file__).resolve().parent
    / "data"
    / "processed"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "unido_africa_long.csv"
LOG_FILE = OUTPUT_DIR / "unido_processing_log.csv"

START_YEAR = 2000
END_YEAR = 2023


# ============================================================
# 2. СПРАВОЧНИКИ
# ============================================================

UNIT_TYPES = {
    "N": "numeric",
    "M": "monetary (local currency)",
    "USD": "$ (USD)",
    "I": "index"
}

VARIABLE_NAMES = {
    "05": "Wages and salaries",
    "14": "Output",
    "20": "Value added",
    "21": "Gross fixed capital formation"
}

ACTIVITY_NAMES = {
    "C": "Total mining and quarrying",
    "D": "Total manufacturing",
    "E": "Total electricity, gas and water supply"
}

# Историческая сущность не приравнивается к современному Судану.
HISTORICAL_ENTITIES = {
    "former sudan": "Former Sudan"
}

# Дополнительные варианты написания стран.
ALIASES = {
    "congo": "COG",
    "cote d ivoire": "CIV",
    "ivory coast": "CIV",
    "cape verde": "CPV",
    "cabo verde": "CPV",
    "eswatini": "SWZ",
    "swaziland": "SWZ",
    "united republic of tanzania": "TZA",
    "tanzania": "TZA",
    "democratic republic of the congo": "COD",
    "democratic republic of congo": "COD",
    "dr congo": "COD",
    "drc": "COD"
}

CANONICAL_NAMES = {
    "CIV": "Côte d'Ivoire",
    "COG": "Congo",
    "CPV": "Cabo Verde",
    "SWZ": "Eswatini",
    "TZA": "United Republic of Tanzania"
}


# ============================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def read_csv(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


def normalize_name(value):
    """Нормализует название страны для сопоставления."""

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def add_log(log_rows, key, value, details=""):
    log_rows.append({
        "category": key,
        "value": value,
        "details": details
    })


# ============================================================
# 4. ЗАГРУЗКА ИСТОЧНИКОВ
# ============================================================

print("=" * 75)
print("ИЗВЛЕЧЕНИЕ ДАННЫХ UNIDO ПО АФРИКЕ")
print("=" * 75)

source_rows = read_csv(SOURCE_FILE)
reference_rows = read_csv(REFERENCE_FILE)

print("Исходных строк UNIDO:", len(source_rows))
print("Стран в справочнике BACI:", len(reference_rows))


# ============================================================
# 5. СОПОСТАВЛЕНИЕ СТРАН
# ============================================================

name_to_iso3 = {}

for row in reference_rows:

    iso3 = row["country_iso3"]
    name = row["country_name"]

    name_to_iso3[normalize_name(name)] = iso3


# Добавляем явные алиасы.
for alias, iso3 in ALIASES.items():
    name_to_iso3[normalize_name(alias)] = iso3


iso3_to_name = {
    row["country_iso3"]: row["country_name"]
    for row in reference_rows
}

iso3_to_name.update(CANONICAL_NAMES)

africa_iso3 = set(iso3_to_name.keys())

country_mapping = {}
historical_mapping = {}

for row in source_rows:

    source_name = row["Country"]
    normalized = normalize_name(source_name)

    if normalized in HISTORICAL_ENTITIES:
        historical_mapping[row["CountryCode"]] = (
            HISTORICAL_ENTITIES[normalized]
        )
        continue

    iso3 = name_to_iso3.get(normalized)

    if iso3:
        country_mapping[row["CountryCode"]] = iso3


# ============================================================
# 6. ФИЛЬТРАЦИЯ ПО СТРАНАМ И ПЕРИОДУ
# ============================================================

selected_rows = []
excluded_period = 0

for row in source_rows:

    try:
        year = int(row["Year"])
    except (ValueError, TypeError):
        continue

    if not START_YEAR <= year <= END_YEAR:
        excluded_period += 1
        continue

    code = row["CountryCode"]

    if code in country_mapping or code in historical_mapping:
        selected_rows.append(row)


# ============================================================
# 7. ИНДЕКСИРУЕМ OUTPUT ДЛЯ РАСЧЁТА GFCF
# ============================================================

output_index = defaultdict(list)

for row in selected_rows:

    if row["VariableCode"] != "14":
        continue

    value = to_float(row["ValueUSD"])

    if value is None or value <= 0:
        continue

    key = (
        row["CountryCode"],
        row["Year"],
        row["ActivityCode"]
    )

    output_index[key].append(value)


# ============================================================
# 8. ОПРЕДЕЛЯЕМ ДУБЛИКАТЫ
# ============================================================

duplicate_groups = defaultdict(list)

for row in selected_rows:

    key = (
        row["CountryCode"],
        row["Year"],
        row["VariableCode"],
        row["UnconsolidatedVariableCode"],
        row["ActivityCode"]
    )

    duplicate_groups[key].append(row)


duplicate_group_counts = {
    key: len(group)
    for key, group in duplicate_groups.items()
    if len(group) > 1
}


# ============================================================
# 9. ПОДГОТОВКА ИТОГОВОЙ ТАБЛИЦЫ
# ============================================================

processed_rows = []

negative_rows = []
gfcf_anomalies = []
gfcf_extremes = []

for row in selected_rows:

    code = row["CountryCode"]

    if code in historical_mapping:

        country_iso3 = ""
        country_name = historical_mapping[code]
        country_status = "historical_entity"

    else:

        country_iso3 = country_mapping[code]
        country_name = iso3_to_name[country_iso3]
        country_status = "matched"

    value = to_float(row["Value"])
    value_usd = to_float(row["ValueUSD"])

    negative_flag = (
        (value is not None and value < 0)
        or
        (value_usd is not None and value_usd < 0)
    )

    if negative_flag:
        negative_rows.append(row)

    duplicate_key = (
        row["CountryCode"],
        row["Year"],
        row["VariableCode"],
        row["UnconsolidatedVariableCode"],
        row["ActivityCode"]
    )

    duplicate_count = duplicate_group_counts.get(
        duplicate_key, 1
    )

    # Отношение GFCF к максимальному положительному Output.
    gfcf_ratio = None

    if row["VariableCode"] == "21" and value_usd is not None:

        key = (
            row["CountryCode"],
            row["Year"],
            row["ActivityCode"]
        )

        available_outputs = output_index.get(key, [])

        if value_usd > 0 and available_outputs:

            max_output = max(available_outputs)
            gfcf_ratio = value_usd / max_output

            if gfcf_ratio > 1:
                gfcf_anomalies.append(row)

            if gfcf_ratio > 2:
                gfcf_extremes.append(row)

    anomaly_flag = (
        row["VariableCode"] == "21"
        and gfcf_ratio is not None
        and gfcf_ratio > 1
    )

    extreme_flag = (
        row["VariableCode"] == "21"
        and gfcf_ratio is not None
        and gfcf_ratio > 2
    )

    processed = {
        "country_iso3": country_iso3,
        "country_name": country_name,
        "source_country_name": row["Country"],
        "source_country_code": code,
        "country_match_status": country_status,

        "year": row["Year"],

        "variable": row["Variable"],
        "variable_code": row["VariableCode"],

        "unconsolidated_variable_code":
            row["UnconsolidatedVariableCode"],

        "unconsolidated_variable_name":
            row["UnconsolidatedVariableName"],

        "activity_code": row["ActivityCode"],
        "activity": row["Activity"],
        "activity_combination": row["ActivityCombination"],

        "value": row["Value"],
        "value_usd": row["ValueUSD"],
        "unit_type": row["UnitType"],

        "unit_description": UNIT_TYPES.get(
            row["UnitType"], "unknown"
        ),

        "metadata": row["Metadata"],

        "negative_value_flag": int(negative_flag),

        "duplicate_flag": int(duplicate_count > 1),
        "duplicate_group_count": duplicate_count,

        "gfcf_to_output_ratio": (
            round(gfcf_ratio, 6)
            if gfcf_ratio is not None
            else ""
        ),

        "gfcf_anomaly_flag": int(anomaly_flag),
        "gfcf_extreme_flag": int(extreme_flag)
    }

    processed_rows.append(processed)


# ============================================================
# 10. СОХРАНЕНИЕ ОСНОВНОГО ФАЙЛА
# ============================================================

fieldnames = list(processed_rows[0].keys())

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
    writer.writerows(processed_rows)


# ============================================================
# 11. ФОРМИРОВАНИЕ ЖУРНАЛА ОБРАБОТКИ
# ============================================================

log_rows = []

matched_iso3 = {
    row["country_iso3"]
    for row in processed_rows
    if row["country_iso3"]
}

historical_countries = {
    row["source_country_name"]
    for row in processed_rows
    if row["country_match_status"] == "historical_entity"
}

missing_countries = sorted(africa_iso3 - matched_iso3)

add_log(log_rows, "source_rows", len(source_rows))
add_log(log_rows, "selected_rows", len(processed_rows))
add_log(log_rows, "excluded_outside_period", excluded_period)

add_log(log_rows, "reference_countries", len(africa_iso3))
add_log(log_rows, "matched_african_countries", len(matched_iso3))
add_log(log_rows, "missing_african_countries", len(missing_countries),
        "; ".join(missing_countries))

add_log(log_rows, "historical_entities", len(historical_countries),
        "; ".join(sorted(historical_countries)))

add_log(log_rows, "years", len({
    row["year"] for row in processed_rows
}))

add_log(log_rows, "minimum_year", min(
    int(row["year"]) for row in processed_rows
))

add_log(log_rows, "maximum_year", max(
    int(row["year"]) for row in processed_rows
))

add_log(log_rows, "negative_observations", len(negative_rows))

add_log(log_rows, "duplicate_groups", len(duplicate_group_counts))

add_log(log_rows, "rows_in_duplicate_groups", sum(
    duplicate_group_counts.values()
))

add_log(log_rows, "gfcf_observations", sum(
    1 for row in processed_rows
    if row["variable_code"] == "21"
))

add_log(log_rows, "gfcf_anomalies_ratio_over_1",
        len(gfcf_anomalies))

add_log(log_rows, "gfcf_extremes_ratio_over_2",
        len(gfcf_extremes))

add_log(log_rows, "metadata_filled", sum(
    1 for row in processed_rows
    if row["metadata"].strip()
))


# Распределения по годам, переменным, секторам и единицам.
distributions = {
    "observations_by_year": Counter(
        row["year"] for row in processed_rows
    ),
    "observations_by_variable": Counter(
        row["variable"] for row in processed_rows
    ),
    "observations_by_activity": Counter(
        row["activity"] for row in processed_rows
    ),
    "observations_by_unit": Counter(
        row["unit_type"] for row in processed_rows
    ),
    "observations_by_country": Counter(
        row["country_iso3"] or "HISTORICAL"
        for row in processed_rows
    )
}

for category, distribution in distributions.items():

    for key, count in sorted(distribution.items()):

        add_log(
            log_rows,
            category,
            count,
            str(key)
        )


# Детализация отрицательных значений.
for row in negative_rows:

    add_log(
        log_rows,
        "negative_observation",
        row["ValueUSD"],
        (
            f'{row["Country"]}; {row["Year"]}; '
            f'{row["Variable"]}; {row["Activity"]}'
        )
    )


# Детализация GFCF-анomalий.
for row in gfcf_anomalies:

    key = (
        row["CountryCode"],
        row["Year"],
        row["ActivityCode"]
    )

    outputs = output_index.get(key, [])
    max_output = max(outputs) if outputs else None
    gfcf_value = to_float(row["ValueUSD"])

    ratio = (
        gfcf_value / max_output
        if max_output and gfcf_value is not None
        else None
    )

    add_log(
        log_rows,
        "gfcf_anomaly",
        round(ratio, 6) if ratio is not None else "",
        f'{row["Country"]}; {row["Year"]}; '
        f'GFCF={gfcf_value}; Output={max_output}'
    )


# Дубликаты: сохраняем, не удаляем.
for key, count in duplicate_group_counts.items():

    add_log(
        log_rows,
        "duplicate_group",
        count,
        str(key)
    )


# ============================================================
# 12. СОХРАНЕНИЕ ЖУРНАЛА
# ============================================================

with open(
    LOG_FILE,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=["category", "value", "details"]
    )

    writer.writeheader()
    writer.writerows(log_rows)


# ============================================================
# 13. ИТОГОВЫЙ ОТЧЁТ В КОНСОЛИ
# ============================================================

print("\n" + "=" * 75)
print("РЕЗУЛЬТАТЫ ОБРАБОТКИ UNIDO")
print("=" * 75)

print("Сохранено наблюдений:", len(processed_rows))
print("Стран с ISO3:", len(matched_iso3))
print("Исторических сущностей:", len(historical_countries))
print("Отсутствуют страны:", missing_countries)

print("\nПЕРЕМЕННЫЕ:")
for key, value in distributions["observations_by_variable"].items():
    print(f"{key}: {value}")

print("\nСЕКТОРА:")
for key, value in distributions["observations_by_activity"].items():
    print(f"{key}: {value}")

print("\nЕДИНИЦЫ ИЗМЕРЕНИЯ:")
for key, value in distributions["observations_by_unit"].items():
    print(f"{key}: {value}")

print("\nКАЧЕСТВО ДАННЫХ:")
print("Отрицательных наблюдений:", len(negative_rows))
print("Групп с дубликатами:", len(duplicate_group_counts))
print("GFCF / Output > 1:", len(gfcf_anomalies))
print("GFCF / Output > 2:", len(gfcf_extremes))

print("\nСОХРАНЁННЫЕ ФАЙЛЫ:")
print(OUTPUT_FILE)
print(LOG_FILE)

print("\n" + "=" * 75)
print("ОБРАБОТКА UNIDO ЗАВЕРШЕНА")
print("=" * 75)
