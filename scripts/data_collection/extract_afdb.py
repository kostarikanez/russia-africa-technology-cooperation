
import csv
from pathlib import Path
from collections import Counter


# =====================================================
# 1. НАСТРОЙКИ
# =====================================================

AFDB_FILE = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "afdb"
    / "afdb_download"
    / "afdb_all_macro.csv"
)

COUNTRIES_FILE = (
    Path("data")
    / "reference"
    / "baci_africa_country_codes.csv"
)

OUTPUT_DIR = Path("data") / "processed"

OUTPUT_FILE = OUTPUT_DIR / "afdb_africa_long.csv"


# =====================================================
# 2. ЗАГРУЗКА СПРАВОЧНИКА СТРАН
# =====================================================

def load_africa_countries():

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
            name = row["country_name"].strip()

            countries[iso3] = name

    if len(countries) != 54:
        raise ValueError(
            f"Ожидалось 54 страны, найдено: {len(countries)}"
        )

    return countries


# =====================================================
# 3. СОПОСТАВЛЕНИЕ НАЗВАНИЙ AFDB С ISO3
# =====================================================

def create_country_mapping(countries):

    # Названия в исходном AfDB и соответствующие ISO3.
    mapping = {
        "Algeria": "DZA",
        "Angola": "AGO",
        "Benin": "BEN",
        "Botswana": "BWA",
        "Burkina Faso": "BFA",
        "Burundi": "BDI",
        "Cabo Verde": "CPV",
        "Cape Verde": "CPV",
        "Cameroon": "CMR",
        "Central African Republic": "CAF",
        "Chad": "TCD",
        "Comoros": "COM",
        "Congo": "COG",
        "Republic of the Congo": "COG",
        "Congo, Rep.": "COG",
        "Congo, Dem. Rep.": "COD",
        "Democratic Republic of the Congo": "COD",
        "Cote d'Ivoire": "CIV",
        "Côte d'Ivoire": "CIV",
        "Ivory Coast": "CIV",
        "Djibouti": "DJI",
        "Egypt": "EGY",
        "Equatorial Guinea": "GNQ",
        "Eritrea": "ERI",
        "Eswatini": "SWZ",
        "Swaziland": "SWZ",
        "eSwatini": "SWZ",
        "Ethiopia": "ETH",
        "Gabon": "GAB",
        "Gambia": "GMB",
        "The Gambia": "GMB",
        "Ghana": "GHA",
        "Guinea": "GIN",
        "Guinea-Bissau": "GNB",
        "Kenya": "KEN",
        "Lesotho": "LSO",
        "Liberia": "LBR",
        "Libya": "LBY",
        "Madagascar": "MDG",
        "Malawi": "MWI",
        "Mali": "MLI",
        "Mauritania": "MRT",
        "Mauritius": "MUS",
        "Morocco": "MAR",
        "Mozambique": "MOZ",
        "Namibia": "NAM",
        "Niger": "NER",
        "Nigeria": "NGA",
        "Rwanda": "RWA",
        "Sao Tome and Principe": "STP",
        "São Tomé and Príncipe": "STP",
        "Senegal": "SEN",
        "Seychelles": "SYC",
        "Sierra Leone": "SLE",
        "Somalia": "SOM",
        "South Africa": "ZAF",
        "South Sudan": "SSD",
        "Sudan": "SDN",
        "Tanzania": "TZA",
        "United Republic of Tanzania": "TZA",
        "Togo": "TGO",
        "Tunisia": "TUN",
        "Uganda": "UGA",
        "Zambia": "ZMB",
        "Zimbabwe": "ZWE"
    }

    # Проверяем, что все найденные коды есть в нашем справочнике.
    invalid_codes = set(mapping.values()) - set(countries.keys())

    if invalid_codes:
        raise ValueError(
            f"В mapping обнаружены неизвестные ISO3: {invalid_codes}"
        )

    return mapping


# =====================================================
# 4. ОБРАБОТКА AFDB
# =====================================================

def extract_afdb(countries, mapping):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    found_countries = set()
    unknown_countries = Counter()
    indicators = set()
    years = set()

    total_rows = 0
    exported_rows = 0

    output_fields = [
        "country_iso3",
        "country_name",
        "year",
        "indicator_name",
        "unit",
        "value",
        "source"
    ]

    with open(
        AFDB_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as input_file:

        reader = csv.DictReader(input_file)

        required_columns = {
            "country-and-regions",
            "indicators",
            "Unit",
            "Date",
            "Value"
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "Не найдены необходимые колонки AfDB."
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

                total_rows += 1

                source_country = (
                    row["country-and-regions"].strip()
                )

                iso3 = mapping.get(source_country)

                # Исключаем неизвестные географические единицы.
                if iso3 is None:
                    unknown_countries[source_country] += 1
                    continue

                if iso3 not in countries:
                    unknown_countries[source_country] += 1
                    continue

                year = int(row["Date"].strip())
                indicator = row["indicators"].strip()
                unit = row["Unit"].strip()

                raw_value = row["Value"].strip()

                if raw_value == "":
                    continue

                try:
                    value = float(raw_value)
                except ValueError:
                    raise ValueError(
                        f"Некорректное значение: "
                        f"{source_country}, "
                        f"{indicator}, "
                        f"{year}, "
                        f"{raw_value}"
                    )

                writer.writerow({
                    "country_iso3": iso3,
                    "country_name": countries[iso3],
                    "year": year,
                    "indicator_name": indicator,
                    "unit": unit,
                    "value": value,
                    "source": "AfDB"
                })

                found_countries.add(iso3)
                indicators.add(indicator)
                years.add(year)

                exported_rows += 1

    missing_countries = set(countries.keys()) - found_countries

    # =================================================
    # 5. РЕЗУЛЬТАТЫ
    # =================================================

    print("\n" + "=" * 55)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ AFDB")
    print("=" * 55)

    print("Всего исходных строк:", f"{total_rows:,}")
    print("Сохранено наблюдений:", f"{exported_rows:,}")

    print("Найдено стран:", len(found_countries))
    print("Не найдены:", sorted(missing_countries))

    print("Уникальных показателей:", len(indicators))
    print("Годы:", sorted(years))

    print("\nНеизвестные географические единицы:")

    if unknown_countries:
        for name, count in unknown_countries.items():
            print(name, "-", count)
    else:
        print("Отсутствуют")

    print("\nИтоговый файл:")
    print(OUTPUT_FILE.resolve())

    return {
        "total_rows": total_rows,
        "exported_rows": exported_rows,
        "countries_found": len(found_countries),
        "missing_countries": missing_countries,
        "unknown_countries": unknown_countries
    }


# =====================================================
# 6. ЗАПУСК
# =====================================================

def main():

    if not AFDB_FILE.exists():
        raise FileNotFoundError(
            f"Не найден исходный файл: {AFDB_FILE.resolve()}"
        )

    if not COUNTRIES_FILE.exists():
        raise FileNotFoundError(
            f"Не найден справочник: {COUNTRIES_FILE.resolve()}"
        )

    print("Исходный файл AfDB найден.")

    countries = load_africa_countries()

    print("Загружено стран из справочника:", len(countries))

    mapping = create_country_mapping(countries)

    result = extract_afdb(countries, mapping)


if __name__ == "__main__":
    main()
