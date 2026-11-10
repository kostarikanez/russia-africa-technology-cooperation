
import csv
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# ПУТИ
# ============================================================

BASE_DIR = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "unesco"
    / "unesco_download"
)

DATA_FILE = BASE_DIR / "unesco_data.csv"
INDICATORS_FILE = BASE_DIR / "indicators.csv"

PROJECT_DIR = Path(__file__).resolve().parent

REFERENCE_FILE = (
    PROJECT_DIR
    / "data"
    / "reference"
    / "baci_africa_country_codes.csv"
)

OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "unesco_africa_long.csv"
LOG_FILE = OUTPUT_DIR / "unesco_processing_log.csv"

START_YEAR = 2000
END_YEAR = 2024


# ============================================================
# ЗАГРУЗКА СПРАВОЧНИКА АФРИКАНСКИХ СТРАН
# ============================================================

def load_countries():

    countries = {}

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

            if iso3:
                countries[iso3] = name

    return countries


# ============================================================
# ЗАГРУЗКА СПРАВОЧНИКА ПОКАЗАТЕЛЕЙ UNESCO
# ============================================================

def load_indicators():

    indicators = {}

    with open(
        INDICATORS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            code = row["indicatorId"].strip()

            indicators[code] = {
                "indicator_name": row.get("name", "").strip(),
                "theme": row.get("theme", "").strip(),
                "last_data_update": row.get(
                    "lastDataUpdate", ""
                ).strip()
            }

    return indicators


# ============================================================
# ОСНОВНАЯ ОБРАБОТКА
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    for path in [
        DATA_FILE,
        INDICATORS_FILE,
        REFERENCE_FILE
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Файл не найден: {path}"
            )

    countries = load_countries()
    indicators = load_indicators()

    print("=" * 60)
    print("СПРАВОЧНИК АФРИКАНСКИХ СТРАН")
    print("=" * 60)
    print("Уникальных стран:", len(countries))

    print("\nПоказателей в справочнике UNESCO:", len(indicators))

    # Счётчики обработки
    total_rows = 0
    african_rows = 0
    excluded_non_africa = 0
    excluded_invalid_year = 0
    excluded_outside_period = 0
    excluded_empty_values = 0
    invalid_values = 0
    unknown_indicators = 0

    years = Counter()
    country_counts = Counter()
    indicator_counts = Counter()
    themes = Counter()
    units = Counter()

    records = []
    processing_log = []

    # Проверка ключей для выявления дубликатов
    seen = {}
    duplicate_keys = Counter()

    # ========================================================
    # ЧТЕНИЕ ИСХОДНОГО ФАЙЛА
    # ========================================================

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "indicatorId",
            "geoUnit",
            "year",
            "value",
            "qualifier",
            "magnitude"
        }

        missing_columns = (
            required_columns - set(reader.fieldnames or [])
        )

        if missing_columns:
            raise ValueError(
                f"В UNESCO отсутствуют колонки: {missing_columns}"
            )

        for row in reader:

            total_rows += 1

            iso3 = row["geoUnit"].strip()
            indicator_code = row["indicatorId"].strip()
            year_raw = row["year"].strip()
            value_raw = row["value"].strip()

            # ------------------------------------------------
            # ФИЛЬТР ПО АФРИКАНСКИМ СТРАНАМ
            # ------------------------------------------------

            if iso3 not in countries:
                excluded_non_africa += 1
                continue

            african_rows += 1

            # ------------------------------------------------
            # ПРОВЕРКА ГОДА
            # ------------------------------------------------

            try:
                year = int(year_raw)
            except (ValueError, TypeError):
                excluded_invalid_year += 1
                continue

            if year < START_YEAR or year > END_YEAR:
                excluded_outside_period += 1
                continue

            # ------------------------------------------------
            # ПРОВЕРКА ЗНАЧЕНИЯ
            # ------------------------------------------------

            if value_raw == "":
                excluded_empty_values += 1
                continue

            try:
                value = float(value_raw)
            except ValueError:
                invalid_values += 1
                continue

            # ------------------------------------------------
            # МЕТАДАННЫЕ ПОКАЗАТЕЛЯ
            # ------------------------------------------------

            metadata = indicators.get(
                indicator_code,
                {}
            )

            if not metadata:
                unknown_indicators += 1

            indicator_name = metadata.get(
                "indicator_name",
                ""
            )

            theme = metadata.get(
                "theme",
                ""
            )

            last_data_update = metadata.get(
                "last_data_update",
                ""
            )

            # ------------------------------------------------
            # ФОРМИРОВАНИЕ ЗАПИСИ
            # ------------------------------------------------

            record = {
                "country_iso3": iso3,
                "country_name": countries[iso3],
                "year": year,
                "indicator_code": indicator_code,
                "indicator_name": indicator_name,
                "theme": theme,
                "value": value,
                "qualifier": row["qualifier"].strip(),
                "magnitude": row["magnitude"].strip(),
                "last_data_update": last_data_update,
                "source": "UNESCO UIS"
            }

            # ------------------------------------------------
            # ПРОВЕРКА ДУБЛИКАТОВ
            # ------------------------------------------------

            key = (
                iso3,
                year,
                indicator_code
            )

            if key in seen:

                duplicate_keys[key] += 1

                if seen[key] == record:
                    processing_log.append({
                        "country_iso3": iso3,
                        "year": year,
                        "indicator_code": indicator_code,
                        "status": "duplicate_identical",
                        "details": "Идентичная запись"
                    })
                else:
                    processing_log.append({
                        "country_iso3": iso3,
                        "year": year,
                        "indicator_code": indicator_code,
                        "status": "duplicate_conflict",
                        "details": "Различающиеся записи"
                    })

                continue

            seen[key] = record
            records.append(record)

            years[year] += 1
            country_counts[iso3] += 1
            indicator_counts[indicator_code] += 1
            themes[theme] += 1

    # ========================================================
    # СОХРАНЕНИЕ ИТОГОВОГО ФАЙЛА
    # ========================================================

    fieldnames = [
        "country_iso3",
        "country_name",
        "year",
        "indicator_code",
        "indicator_name",
        "theme",
        "value",
        "qualifier",
        "magnitude",
        "last_data_update",
        "source"
    ]

    records.sort(
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
        writer.writerows(records)

    # ========================================================
    # СОХРАНЕНИЕ ЖУРНАЛА
    # ========================================================

    with open(
        LOG_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        log_fields = [
            "country_iso3",
            "year",
            "indicator_code",
            "status",
            "details"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=log_fields
        )

        writer.writeheader()
        writer.writerows(processing_log)

    # ========================================================
    # ИТОГОВАЯ СТАТИСТИКА
    # ========================================================

    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ UNESCO")
    print("=" * 60)

    print("Исходных строк:", f"{total_rows:,}")
    print("Строк по африканским странам:", f"{african_rows:,}")
    print("Исключено строк вне Африки:", f"{excluded_non_africa:,}")
    print("Исключено некорректных годов:", excluded_invalid_year)
    print("Исключено строк вне периода:", excluded_outside_period)
    print("Исключено пустых значений:", excluded_empty_values)
    print("Некорректных значений:", invalid_values)
    print("Неизвестных кодов показателей:", unknown_indicators)

    print("\nДубликаты:")

    print(
        "Комбинаций с дубликатами:",
        len(duplicate_keys)
    )

    identical = sum(
        1 for row in processing_log
        if row["status"] == "duplicate_identical"
    )

    conflicts = sum(
        1 for row in processing_log
        if row["status"] == "duplicate_conflict"
    )

    print("Идентичных дубликатов:", identical)
    print("Конфликтных записей:", conflicts)

    print("\nИТОГОВЫЕ ДАННЫЕ")
    print("Наблюдений:", f"{len(records):,}")
    print("Стран:", len(set(r["country_iso3"] for r in records)))
    print("Показателей:", len(indicator_counts))
    print("Тематических категорий:", len(themes))

    if years:
        print("Лет:", len(years))
        print("Период:", min(years), "-", max(years))

    print("\nСТРАНЫ:")
    print(sorted(set(r["country_iso3"] for r in records)))

    print("\nПОКАЗАТЕЛИ:")

    for code, count in sorted(indicator_counts.items()):
        name = indicators.get(code, {}).get(
            "indicator_name",
            ""
        )

        print(
            code,
            "|",
            name,
            "|",
            f"{count:,}"
        )

    print("\nТЕМАТИЧЕСКИЕ КАТЕГОРИИ:")

    for theme, count in themes.most_common():
        print(theme, "-", f"{count:,}")

    print("\nПОКРЫТИЕ ПО ГОДАМ:")

    for year in sorted(years):
        print(year, "-", f"{years[year]:,}")

    print("\nПОКРЫТИЕ ПО ПОКАЗАТЕЛЯМ И ГОДАМ:")

    coverage = defaultdict(Counter)

    for record in records:
        coverage[record["indicator_code"]][record["year"]] += 1

    for code in sorted(coverage):

        print("\n", code)

        for year in sorted(coverage[code]):
            print(
                year,
                "-",
                coverage[code][year]
            )

    print("\nФАЙЛ ДАННЫХ:")
    print(OUTPUT_FILE)

    print("\nЖУРНАЛ ОБРАБОТКИ:")
    print(LOG_FILE)

    print("\n" + "=" * 60)
    print("ОБРАБОТКА UNESCO ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    main()
