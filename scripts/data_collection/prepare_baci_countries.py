
import csv
from pathlib import Path


# 1. Путь к исходному справочнику BACI
base_path = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "baci"
    / "baci_download"
)

input_file = base_path / "country_codes.csv"


# 2. ISO3-коды 54 суверенных государств Африки
africa_iso3 = {
    "DZA", "AGO", "BEN", "BWA", "BFA", "BDI",
    "CPV", "CMR", "CAF", "TCD", "COM", "COG",
    "COD", "CIV", "DJI", "EGY", "GNQ", "ERI",
    "SWZ", "ETH", "GAB", "GMB", "GHA", "GIN",
    "GNB", "KEN", "LSO", "LBR", "LBY", "MDG",
    "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ",
    "NAM", "NER", "NGA", "RWA", "STP", "SEN",
    "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN",
    "TZA", "TGO", "TUN", "UGA", "ZMB", "ZWE"
}


# 3. Проверяем наличие исходного файла
if not input_file.exists():
    raise FileNotFoundError(
        f"Исходный справочник не найден: {input_file}"
    )


# 4. Читаем справочник BACI и отбираем африканские страны
africa_countries = []

with open(
    input_file,
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    reader = csv.DictReader(file)

    required_columns = {
        "country_code",
        "country_name",
        "country_iso2",
        "country_iso3"
    }

    if not required_columns.issubset(reader.fieldnames):
        raise ValueError(
            f"В справочнике отсутствуют необходимые колонки: "
            f"{required_columns - set(reader.fieldnames)}"
        )

    for row in reader:

        iso3 = row["country_iso3"].strip()

        if iso3 in africa_iso3:

            country = row.copy()

            # Нормализуем название Судана.
            # Исторический код 736 и современный 729
            # сохраняются как отдельные BACI ID.
            if iso3 == "SDN":
                country["country_name"] = "Sudan"

            africa_countries.append(country)


# 5. Проверяем полноту справочника
found_iso3 = {
    country["country_iso3"]
    for country in africa_countries
}

missing_iso3 = africa_iso3 - found_iso3

print("РЕЗУЛЬТАТ ПРОВЕРКИ")
print("-" * 40)

print("Уникальных африканских стран:", len(found_iso3))
print("Всего кодов BACI:", len(africa_countries))
print("Не найдены:", missing_iso3)


# 6. Проверяем дублирующиеся коды ISO3
print("\nПРОВЕРКА ДУБЛИРУЮЩИХСЯ ISO3")
print("-" * 40)

iso3_counts = {}

for country in africa_countries:
    iso3 = country["country_iso3"]
    iso3_counts[iso3] = iso3_counts.get(iso3, 0) + 1

for iso3, count in iso3_counts.items():
    if count > 1:
        print(f"{iso3}: {count} записи")


# 7. Отдельно проверяем коды Судана
print("\nКОДЫ СУДАНА")
print("-" * 40)

for country in africa_countries:
    if country["country_iso3"] == "SDN":
        print(
            country["country_code"],
            country["country_name"],
            country["country_iso3"]
        )


# 8. Проверяем наличие всех 54 стран и сохраняем справочник
if len(found_iso3) != 54 or missing_iso3:
    raise ValueError(
        "Проверка не пройдена: количество стран "
        "не соответствует ожидаемым 54."
    )

output_dir = Path("data") / "reference"
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "baci_africa_country_codes.csv"

fieldnames = [
    "country_code",
    "country_name",
    "country_iso2",
    "country_iso3"
]

with open(
    output_file,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(africa_countries)


# 9. Итог
print("\n" + "-" * 40)
print("СПРАВОЧНИК УСПЕШНО СОХРАНЁН")
print(output_file.resolve())
