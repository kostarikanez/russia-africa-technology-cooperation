
import csv
import re
from pathlib import Path
from collections import defaultdict


# ============================================================
# 1. НАСТРОЙКИ
# ============================================================

# Папка с исходными файлами BACI
BACI_DIR = (
    Path.home()
    / "Desktop"
    / "masters"
    / "practice"
    / "macro"
    / "baci"
    / "baci_download"
)

# Справочник африканских стран, созданный ранее
COUNTRIES_FILE = (
    Path("data")
    / "reference"
    / "baci_africa_country_codes.csv"
)

# Папка для результатов
OUTPUT_DIR = Path("data") / "processed"

# Код России в BACI
RUSSIA_CODE = 643

# Период исследования
START_YEAR = 2000
END_YEAR = 2024


# ============================================================
# 2. ЗАГРУЗКА СПРАВОЧНИКА СТРАН
# ============================================================

def load_countries():
    """
    Создаёт соответствие:
    числовой код BACI -> ISO3 и название страны.
    """

    if not COUNTRIES_FILE.exists():
        raise FileNotFoundError(
            f"Не найден справочник: {COUNTRIES_FILE.resolve()}"
        )

    baci_to_country = {}
    iso3_to_name = {}

    with open(
        COUNTRIES_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            baci_code = int(row["country_code"])
            iso3 = row["country_iso3"]
            name = row["country_name"]

            baci_to_country[baci_code] = {
                "iso3": iso3,
                "name": name
            }

            iso3_to_name[iso3] = name

    if RUSSIA_CODE in baci_to_country:
        raise ValueError(
            "Код России ошибочно присутствует "
            "в африканском справочнике."
        )

    if len(iso3_to_name) != 54:
        raise ValueError(
            f"Ожидалось 54 страны, найдено: {len(iso3_to_name)}"
        )

    print("Справочник загружен.")
    print("Уникальных стран:", len(iso3_to_name))
    print("Числовых кодов BACI:", len(baci_to_country))

    return baci_to_country, iso3_to_name


# ============================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def parse_number(value):
    """
    Преобразует значение в число.
    Пустые значения трактуются как 0.
    """

    if value is None or value.strip() == "":
        return 0.0

    return float(value)


def get_input_files():
    """
    Находит годовые файлы BACI за 2000–2024 годы.
    """

    pattern = re.compile(
        r"BACI_HS92_Y(\d{4})_V202601\.csv"
    )

    files_by_year = {}

    for file_path in BACI_DIR.glob("BACI_HS92_Y*_V202601.csv"):

        match = pattern.fullmatch(file_path.name)

        if match:
            year = int(match.group(1))
            files_by_year[year] = file_path

    expected_years = set(range(START_YEAR, END_YEAR + 1))
    found_years = set(files_by_year.keys())

    missing_years = expected_years - found_years
    unexpected_years = found_years - expected_years

    if missing_years:
        raise FileNotFoundError(
            f"Не найдены файлы за годы: {sorted(missing_years)}"
        )

    if unexpected_years:
        print(
            "Обнаружены дополнительные годы:",
            sorted(unexpected_years)
        )

    return files_by_year


# ============================================================
# 4. ОБРАБОТКА ОДНОГО ГОДОВОГО ФАЙЛА
# ============================================================

def process_year(year, file_path, baci_to_country, iso3_to_name):
    """
    Извлекает двустороннюю торговлю России
    с африканскими странами за один год.
    """

    print("\n" + "=" * 55)
    print(f"Обрабатываем {year} год")
    print("Файл:", file_path.name)

    # Агрегированные показатели по странам
    annual = {
        iso3: {
            "exports_to_russia": 0.0,
            "imports_from_russia": 0.0
        }
        for iso3 in iso3_to_name
    }

    # Товарная детализация:
    # (ISO3, HS6, направление) -> стоимость и количество
    products = defaultdict(
        lambda: {
            "value": 0.0,
            "quantity": 0.0
        }
    )

    total_rows = 0
    selected_rows = 0

    required_columns = {"t", "i", "j", "k", "v", "q"}

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                f"Неверная структура файла {file_path.name}. "
                f"Колонки: {reader.fieldnames}"
            )

        for row in reader:

            total_rows += 1

            exporter = int(row["i"])
            importer = int(row["j"])

            # Проверяем направления торговли

            if importer == RUSSIA_CODE and exporter in baci_to_country:

                # Африканская страна -> Россия
                country = baci_to_country[exporter]
                direction = "exports_to_russia"

            elif exporter == RUSSIA_CODE and importer in baci_to_country:

                # Россия -> африканская страна
                country = baci_to_country[importer]
                direction = "imports_from_russia"

            else:
                continue

            # Проверяем год
            row_year = int(row["t"])

            if row_year != year:
                raise ValueError(
                    f"В файле за {year} год обнаружена "
                    f"строка за {row_year} год."
                )

            iso3 = country["iso3"]

            # Стоимость в тысячах долларов США
            value = parse_number(row["v"])

            # Количество в метрических тоннах
            quantity = parse_number(row["q"])

            # Код товара HS6 сохраняем строкой
            hs6 = row["k"].strip()

            if not hs6:
                raise ValueError(
                    f"Обнаружен пустой HS6-код в файле {file_path.name}"
                )

            selected_rows += 1

            # Агрегация по стране и направлению
            annual[iso3][direction] += value

            # Агрегация по стране, товару и направлению
            key = (iso3, hs6, direction)

            products[key]["value"] += value
            products[key]["quantity"] += quantity

    print("Всего строк:", f"{total_rows:,}")
    print("Отобрано торговых строк:", f"{selected_rows:,}")
    print("Уникальных товарных групп:", f"{len(products):,}")

    # --------------------------------------------------------
    # 5. СОХРАНЕНИЕ ГОДОВЫХ РЕЗУЛЬТАТОВ
    # --------------------------------------------------------

    annual_rows = []

    for iso3 in sorted(iso3_to_name):

        annual_rows.append({
            "year": year,
            "country_iso3": iso3,
            "country_name": iso3_to_name[iso3],
            "exports_to_russia_thousand_usd":
                annual[iso3]["exports_to_russia"],
            "imports_from_russia_thousand_usd":
                annual[iso3]["imports_from_russia"]
        })

    annual_file = OUTPUT_DIR / "baci_russia_africa_annual.csv"

    annual_fields = [
        "year",
        "country_iso3",
        "country_name",
        "exports_to_russia_thousand_usd",
        "imports_from_russia_thousand_usd"
    ]

    write_header = not annual_file.exists()

    with open(
        annual_file,
        "a",
        encoding="utf-8-sig" if write_header else "utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=annual_fields
        )

        if write_header:
            writer.writeheader()

        writer.writerows(annual_rows)

    # --------------------------------------------------------
    # 6. СОХРАНЕНИЕ ТОВАРНОЙ ДЕТАЛИЗАЦИИ
    # --------------------------------------------------------

    products_file = OUTPUT_DIR / "baci_russia_africa_products.csv"

    product_fields = [
        "year",
        "country_iso3",
        "country_name",
        "hs6",
        "trade_flow",
        "value_thousand_usd",
        "quantity_tons"
    ]

    product_write_header = not products_file.exists()

    with open(
        products_file,
        "a",
        encoding="utf-8-sig" if product_write_header else "utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=product_fields
        )

        if product_write_header:
            writer.writeheader()

        for (iso3, hs6, direction), metrics in sorted(products.items()):

            writer.writerow({
                "year": year,
                "country_iso3": iso3,
                "country_name": iso3_to_name[iso3],
                "hs6": hs6,
                "trade_flow": direction,
                "value_thousand_usd": metrics["value"],
                "quantity_tons": metrics["quantity"]
            })

    # Возвращаем показатели для журнала обработки
    return {
        "year": year,
        "source_file": file_path.name,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "product_groups": len(products)
    }


# ============================================================
# 7. ОСНОВНОЙ ЗАПУСК
# ============================================================

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Удаляем старые результаты, чтобы не дублировать данные
    annual_file = OUTPUT_DIR / "baci_russia_africa_annual.csv"
    products_file = OUTPUT_DIR / "baci_russia_africa_products.csv"
    log_file = OUTPUT_DIR / "baci_processing_log.csv"

    for output_file in [annual_file, products_file, log_file]:
        if output_file.exists():
            output_file.unlink()

    # Загружаем справочник
    baci_to_country, iso3_to_name = load_countries()

    # Находим 25 исходных файлов
    files_by_year = get_input_files()

    print("\nНайдено годовых файлов:", len(files_by_year))

    # Последовательно обрабатываем каждый год
    processing_log = []

    for year in range(START_YEAR, END_YEAR + 1):

        result = process_year(
            year,
            files_by_year[year],
            baci_to_country,
            iso3_to_name
        )

        processing_log.append(result)

    # Сохраняем журнал обработки
    log_fields = [
        "year",
        "source_file",
        "total_rows",
        "selected_rows",
        "product_groups"
    ]

    with open(
        log_file,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=log_fields
        )

        writer.writeheader()
        writer.writerows(processing_log)

    # Итоговая статистика
    print("\n" + "=" * 55)
    print("ОБРАБОТКА BACI ЗАВЕРШЕНА")
    print("=" * 55)

    print("Обработано лет:", len(processing_log))
    print(
        "Всего исходных строк:",
        f"{sum(x['total_rows'] for x in processing_log):,}"
    )
    print(
        "Отобрано торговых строк:",
        f"{sum(x['selected_rows'] for x in processing_log):,}"
    )
    print(
        "Товарных групп по годам:",
        f"{sum(x['product_groups'] for x in processing_log):,}"
    )

    print("\nРезультаты сохранены в:", OUTPUT_DIR.resolve())

    print("\nСозданные файлы:")
    print(annual_file.resolve())
    print(products_file.resolve())
    print(log_file.resolve())


if __name__ == "__main__":
    main()
