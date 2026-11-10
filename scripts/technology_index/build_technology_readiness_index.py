
import csv
import math
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

INPUT = DATA_DIR / "country_year_panel_raw.csv"
OUTPUT = DATA_DIR / "country_year_panel_normalized.csv"
PARAMETERS_OUTPUT = REPORT_DIR / "normalization_parameters.csv"
COVERAGE_OUTPUT = REPORT_DIR / "technology_index_coverage.csv"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Показатели для нормализации.
# Для логарифмируемых показателей используем ln(1 + x).
INDICATORS = {
    "gdp_per_capita_ppp": "log1p",
    "electricity_access_pct": "linear",
    "internet_users_pct": "linear",
    "international_bandwidth_per_inhabitant": "log1p",
    "publications_per_million": "log1p",
    "manufacturing_value_added_pct": "linear",
    "wgi_cc": "linear",
    "wgi_ge": "linear",
    "wgi_pv": "linear",
    "wgi_rq": "linear",
    "wgi_rl": "linear",
    "wgi_va": "linear",
}

DIGITAL_COLUMNS = [
    "electricity_access_pct",
    "internet_users_pct",
    "international_bandwidth_per_inhabitant"
]

WGI_COLUMNS = [
    "wgi_cc", "wgi_ge", "wgi_pv",
    "wgi_rq", "wgi_rl", "wgi_va"
]

# Веса блоков.
WEIGHTS = {
    "economic_block": 0.20,
    "digital_block": 0.25,
    "science_block": 0.20,
    "industry_block": 0.20,
    "institutional_block": 0.15
}


def transform(value, method):
    if method == "log1p":
        if value < 0:
            raise ValueError(
                f"Отрицательное значение для log1p: {value}"
            )
        return math.log1p(value)

    return value


def parse_value(raw):
    if raw is None or raw.strip() == "":
        return None

    try:
        value = float(raw)
    except ValueError:
        return None

    if not math.isfinite(value):
        return None

    return value


# ---------------------------------------------------------
# 1. Читаем исходную панель и собираем значения индикаторов
# ---------------------------------------------------------

with open(INPUT, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    rows = list(reader)
    original_fields = reader.fieldnames

transformed_values = {
    column: []
    for column in INDICATORS
}

for row in rows:
    for column, method in INDICATORS.items():
        value = parse_value(row.get(column))

        if value is not None:
            transformed_values[column].append(
                transform(value, method)
            )


# ---------------------------------------------------------
# 2. Определяем общие границы нормализации за весь период
# ---------------------------------------------------------

parameters = {}

for column, values in transformed_values.items():
    if not values:
        raise ValueError(
            f"Нет данных для нормализации: {column}"
        )

    parameters[column] = {
        "method": INDICATORS[column],
        "minimum": min(values),
        "maximum": max(values)
    }


def normalize(value, column):
    if value is None:
        return None

    method = parameters[column]["method"]
    transformed = transform(value, method)

    minimum = parameters[column]["minimum"]
    maximum = parameters[column]["maximum"]

    if maximum == minimum:
        return 50.0

    score = (
        (transformed - minimum)
        / (maximum - minimum)
        * 100
    )

    return max(0.0, min(100.0, score))


# ---------------------------------------------------------
# 3. Добавляем нормализованные показатели
# ---------------------------------------------------------

normalized_columns = [
    f"{column}_norm"
    for column in INDICATORS
]

for row in rows:
    for column in INDICATORS:
        value = parse_value(row.get(column))
        score = normalize(value, column)

        row[f"{column}_norm"] = (
            round(score, 6)
            if score is not None
            else ""
        )


# ---------------------------------------------------------
# 4. Рассчитываем пять тематических блоков
# ---------------------------------------------------------

def average_available(row, columns, minimum_count):
    values = []

    for column in columns:
        raw = row.get(f"{column}_norm", "")

        if raw == "":
            continue

        values.append(float(raw))

    if len(values) < minimum_count:
        return None

    return sum(values) / len(values)


for row in rows:

    # Экономические возможности
    economic = row["gdp_per_capita_ppp_norm"]

    row["economic_block"] = economic

    # Цифровая инфраструктура:
    # минимум 2 из 3 показателей
    digital = average_available(
        row,
        DIGITAL_COLUMNS,
        minimum_count=2
    )

    row["digital_block"] = (
        round(digital, 6)
        if digital is not None
        else ""
    )

    # Научно-технологическая база
    science = row["publications_per_million_norm"]

    row["science_block"] = science

    # Промышленная база
    industry = row["manufacturing_value_added_pct_norm"]

    row["industry_block"] = industry

    # Институциональная среда:
    # минимум 4 из 6 компонентов WGI
    institutional = average_available(
        row,
        WGI_COLUMNS,
        minimum_count=4
    )

    row["institutional_block"] = (
        round(institutional, 6)
        if institutional is not None
        else ""
    )

    # -----------------------------------------------------
    # 5. Итоговый индекс — только при наличии всех блоков
    # -----------------------------------------------------

    blocks = [
        row["economic_block"],
        row["digital_block"],
        row["science_block"],
        row["industry_block"],
        row["institutional_block"]
    ]

    if all(value != "" for value in blocks):

        index = (
            float(row["economic_block"])
            * WEIGHTS["economic_block"]
            +
            float(row["digital_block"])
            * WEIGHTS["digital_block"]
            +
            float(row["science_block"])
            * WEIGHTS["science_block"]
            +
            float(row["industry_block"])
            * WEIGHTS["industry_block"]
            +
            float(row["institutional_block"])
            * WEIGHTS["institutional_block"]
        )

        row["technology_readiness_index"] = round(
            index, 6
        )

    else:
        row["technology_readiness_index"] = ""


# ---------------------------------------------------------
# 6. Сохраняем нормализованную панель
# ---------------------------------------------------------

new_columns = (
    normalized_columns
    + [
        "economic_block",
        "digital_block",
        "science_block",
        "industry_block",
        "institutional_block",
        "technology_readiness_index"
    ]
)

output_fields = original_fields + new_columns

with open(
    OUTPUT, "w", encoding="utf-8-sig", newline=""
) as file:
    writer = csv.DictWriter(file, fieldnames=output_fields)
    writer.writeheader()
    writer.writerows(rows)


# ---------------------------------------------------------
# 7. Сохраняем параметры нормализации
# ---------------------------------------------------------

with open(
    PARAMETERS_OUTPUT,
    "w", encoding="utf-8-sig", newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "indicator",
            "transformation",
            "transformed_min",
            "transformed_max"
        ]
    )

    writer.writeheader()

    for column, params in parameters.items():
        writer.writerow({
            "indicator": column,
            "transformation": params["method"],
            "transformed_min": params["minimum"],
            "transformed_max": params["maximum"]
        })


# ---------------------------------------------------------
# 8. Отчёт о покрытии индекса
# ---------------------------------------------------------

total_rows = len(rows)

coverage_columns = [
    "economic_block",
    "digital_block",
    "science_block",
    "industry_block",
    "institutional_block",
    "technology_readiness_index"
]

coverage = []

for column in coverage_columns:

    available = sum(
        1 for row in rows
        if row.get(column, "") != ""
    )

    coverage.append({
        "indicator": column,
        "available_country_years": available,
        "missing_country_years": total_rows - available,
        "coverage_pct": round(
            available / total_rows * 100, 2
        )
    })

with open(
    COVERAGE_OUTPUT,
    "w", encoding="utf-8-sig", newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "indicator",
            "available_country_years",
            "missing_country_years",
            "coverage_pct"
        ]
    )

    writer.writeheader()
    writer.writerows(coverage)


# ---------------------------------------------------------
# 9. Вывод результатов
# ---------------------------------------------------------

print("=" * 70)
print("ПОСТРОЕНИЕ ИНДЕКСА УСЛОВИЙ ТЕХНОЛОГИЧЕСКОГО РАЗВИТИЯ")
print("=" * 70)

print(f"Всего строк: {total_rows}")
print(f"Стран: {len(set(row['country_iso3'] for row in rows))}")

print("\nВЕСА БЛОКОВ")

for block, weight in WEIGHTS.items():
    print(f"{block}: {weight * 100:.0f}%")

print("\nПОКРЫТИЕ")

for item in coverage:
    print(
        f"{item['indicator']}: "
        f"{item['available_country_years']} / {total_rows} "
        f"({item['coverage_pct']}%)"
    )

index_values = [
    float(row["technology_readiness_index"])
    for row in rows
    if row["technology_readiness_index"] != ""
]

print("\nИТОГОВЫЙ ИНДЕКС")

if index_values:
    print(f"Наблюдений: {len(index_values)}")
    print(f"Минимум: {min(index_values):.2f}")
    print(f"Максимум: {max(index_values):.2f}")
    print(f"Среднее: {sum(index_values) / len(index_values):.2f}")
else:
    print("Нет наблюдений с полным набором блоков.")

print("\nСОЗДАННЫЕ ФАЙЛЫ")
print(OUTPUT)
print(PARAMETERS_OUTPUT)
print(COVERAGE_OUTPUT)

print("\nРАСЧЁТ ЗАВЕРШЁН")
