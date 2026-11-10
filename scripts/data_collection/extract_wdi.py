
import csv
from pathlib import Path


# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

# Исходный файл WDI
WDI_FILE = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "wdi"
    / "wdi_download"
    / "wdi_data.csv"
)

# Справочник 54 африканских стран
COUNTRIES_FILE = (
    Path("data")
    / "reference"
    / "baci_africa_country_codes.csv"
)

# Итоговый файл
OUTPUT_DIR = Path("data") / "processed"
OUTPUT_FILE = OUTPUT_DIR / "wdi_africa_long.csv"

# Период исследования
START_YEAR = 2000
END_YEAR = 2024

YEARS = [
    str(year)
    for year in range(START_YEAR, END_YEAR + 1)
]


# ============================================================
# 2. ЗАГРУЗКА СПРАВОЧНИКА СТРАН
# ============================================================

def load_africa_countries():

    if not COUNTRIES_FILE.exists():
        raise FileNotFoundError(
            f"Не найден справочник: {COUNTRIES_FILE.resolve()}"
        )

    countries = {}

    with open(
        COUNTRIES_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            iso3 = row["country_iso3"].strip()

            countries[iso3] = row["country_name"]

    if len(countries) != 54:
        raise ValueError(
            f"Ожидалось 54 страны, найдено: {len(countries)}"
        )

    print("Справочник стран загружен.")
    print("Уникальных стран:", len(countries))

    return countries


# ============================================================
# 3. ПРОВЕРКА ИСХОДНОГО ФАЙЛА
# ============================================================

def check_input_file():

    if not WDI_FILE.exists():
        raise FileNotFoundError(
            f"Не найден файл WDI: {WDI_FILE.resolve()}"
        )

    print("\nИсходный файл найден:", WDI_FILE)


# ============================================================
# 4. ОСНОВНАЯ ОБРАБОТКА WDI
# ============================================================

def extract_wdi(countries):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    found_countries = set()

    total_source_rows = 0
    africa_source_rows = 0
    exported_observations = 0
    skipped_missing_values = 0

    output_fields = [
        "country_iso3",
        "country_name",
        "year",
        "indicator_code",
        "indicator_name",
        "value"
    ]

    # Значения, которые считаются пропусками
    missing_values = {
        "",
        ".."
    }

    print("\nНачинаем обработку WDI...")
    print("Период:", START_YEAR, "-", END_YEAR)

    with open(
        WDI_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as input_file:

        reader = csv.DictReader(input_file)

        required_columns = {
            "Country Name",
            "Country Code",
            "Indicator Name",
            "Indicator Code"
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "Не найдены необходимые колонки WDI."
            )

        missing_year_columns = set(YEARS) - set(reader.fieldnames)

        if missing_year_columns:
            raise ValueError(
                f"Отсутствуют годовые колонки: "
                f"{sorted(missing_year_columns)}"
            )

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as output_file:

            writer = csv.DictWriter(
                output_file,
                fieldnames=output_fields
            )

            writer.writeheader()

            for row in reader:

                total_source_rows += 1

                iso3 = row["Country Code"].strip()

                # Оставляем только 54 страны Африки
                # Региональные агрегаты автоматически исключаются
                if iso3 not in countries:
                    continue

                africa_source_rows += 1
                found_countries.add(iso3)

                # Перебираем годы 2000–2024
                for year in YEARS:

                    raw_value = row[year].strip()

                    # Не превращаем пропуски в нули
                    if raw_value in missing_values:
                        skipped_missing_values += 1
                        continue

                    try:
                        value = float(raw_value)
                    except ValueError:
                        raise ValueError(
                            f"Некорректное значение WDI: "
                            f"страна={iso3}, "
                            f"показатель={row['Indicator Code']}, "
                            f"год={year}, "
                            f"значение={raw_value}"
                        )

                    writer.writerow({
                        "country_iso3": iso3,
                        "country_name": countries[iso3],
                        "year": int(year),
                        "indicator_code": row["Indicator Code"],
                        "indicator_name": row["Indicator Name"],
                        "value": value
                    })

                    exported_observations += 1

                # Периодически выводим прогресс
                if total_source_rows % 100000 == 0:
                    print(
                        f"Обработано исходных строк: "
                        f"{total_source_rows:,}"
                    )

    # ========================================================
    # 5. ПРОВЕРКА ПОЛНОТЫ
    # ========================================================

    missing_countries = set(countries.keys()) - found_countries

    print("\n" + "=" * 55)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ WDI")
    print("=" * 55)

    print("Всего строк исходного файла:", f"{total_source_rows:,}")

    print(
        "Строк по африканским странам:",
        f"{africa_source_rows:,}"
    )

    print("Найдено стран:", len(found_countries))

    print("Не найдены:", sorted(missing_countries))

    print(
        "Сохранено наблюдений:",
        f"{exported_observations:,}"
    )

    print(
        "Пропущено пустых значений:",
        f"{skipped_missing_values:,}"
    )

    print("\nИтоговый файл:")
    print(OUTPUT_FILE.resolve())

    if len(found_countries) != 54:
        print(
            "\nВНИМАНИЕ: не все 54 страны обнаружены в WDI."
        )

    return {
        "source_rows": total_source_rows,
        "africa_rows": africa_source_rows,
        "countries_found": len(found_countries),
        "missing_countries": missing_countries,
        "observations": exported_observations,
        "missing_values": skipped_missing_values
    }


# ============================================================
# 6. ЗАПУСК
# ============================================================

def main():

    check_input_file()

    countries = load_africa_countries()

    extract_wdi(countries)


if __name__ == "__main__":
    main()
