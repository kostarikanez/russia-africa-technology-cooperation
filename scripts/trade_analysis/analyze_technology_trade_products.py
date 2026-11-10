
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 0. НАСТРОЙКИ
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data" / "processed"
REFERENCE_DIR = ROOT / "data" / "reference"
REPORTS_DIR = ROOT / "reports"

OUTPUT_DIR = REPORTS_DIR / "technology_trade_products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAIN_START = 2002
MAIN_END = 2023

RECENT_START = 2019
RECENT_END = 2023

# HS2: машины, электрическое оборудование, транспорт,
# летательные аппараты, суда, приборы.
TECH_HS2 = {
    "84", "85", "86", "87", "88", "89", "90"
}

# Более широкая промышленная корзина.
INDUSTRIAL_HS2 = {
    "72", "73", "74", "75", "76",
    "78", "79", "80", "81", "82", "83",
    "84", "85", "86", "87", "88", "89", "90"
}

FOCUS_COUNTRIES = {
    "LBR": "Liberia",
    "DZA": "Algeria",
    "EGY": "Egypt",
    "AGO": "Angola",
    "ZAF": "South Africa",
    "UGA": "Uganda",
}

TOP_N = 10


# ============================================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def section(title):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def read_csv(path, **kwargs):
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл: {path}")

    return pd.read_csv(path, **kwargs)


def save_csv(df, filename):
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Сохранён: {filename} ({len(df):,} строк)")


def normalize_country(df):
    df = df.copy()

    df["country_iso3"] = (
        df["country_iso3"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def normalize_hs6(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(6)
    )


def find_product_dictionary():
    """
    Ищет справочник кодов BACI.
    Если справочник отсутствует, анализ всё равно выполняется
    по кодам HS6.
    """

    candidates = [
        REFERENCE_DIR / "product_codes.csv",
        DATA_DIR / "product_codes.csv",
        ROOT / "product_codes.csv",
        ROOT / "data" / "reference" / "baci_product_codes.csv",
    ]

    for path in candidates:
        if path.exists():
            return path

    # Дополнительный поиск в папках проекта.
    matches = list(ROOT.glob("**/product_codes.csv"))

    if matches:
        return matches[0]

    return None


def load_product_dictionary():
    path = find_product_dictionary()

    if path is None:
        print(
            "\nСправочник product_codes.csv не найден. "
            "Анализ будет выполнен по кодам HS6."
        )
        return None

    print(f"\nНайден справочник товаров: {path}")

    try:
        dictionary = pd.read_csv(
            path,
            dtype=str,
            encoding="utf-8-sig"
        )
    except UnicodeDecodeError:
        dictionary = pd.read_csv(
            path,
            dtype=str,
            encoding="latin1"
        )

    dictionary.columns = [
        str(col).strip().lower()
        for col in dictionary.columns
    ]

    code_candidates = [
        "code", "hs6", "product_code", "productcode"
    ]

    description_candidates = [
        "description", "product", "name", "product_description"
    ]

    code_col = next(
        (col for col in code_candidates if col in dictionary.columns),
        None
    )

    description_col = next(
        (
            col for col in description_candidates
            if col in dictionary.columns
        ),
        None
    )

    if code_col is None or description_col is None:
        print("Не удалось определить столбцы справочника.")
        print("Столбцы:", dictionary.columns.tolist())
        return None

    dictionary = dictionary[[code_col, description_col]].copy()

    dictionary.columns = ["hs6", "product_description"]

    dictionary["hs6"] = normalize_hs6(dictionary["hs6"])

    dictionary["product_description"] = (
        dictionary["product_description"].astype(str).str.strip()
    )

    dictionary = dictionary.drop_duplicates("hs6")

    print(f"Загружено описаний товаров: {len(dictionary):,}")

    return dictionary


def add_description(df, dictionary):
    df = df.copy()

    if dictionary is not None:
        df = df.merge(
            dictionary,
            on="hs6",
            how="left",
            validate="many_to_one"
        )

    if "product_description" not in df.columns:
        df["product_description"] = np.nan

    df["product_description"] = (
        df["product_description"]
        .fillna("HS6 " + df["hs6"].astype(str))
    )

    return df


# ============================================================
# 2. ЗАГРУЗКА ДАННЫХ
# ============================================================

section("АНАЛИЗ ТОВАРНОЙ СТРУКТУРЫ ТОРГОВЛИ РОССИИ И АФРИКИ")

products_path = DATA_DIR / "baci_russia_africa_products.csv"

products = read_csv(
    products_path,
    dtype={"hs6": str}
)

products = normalize_country(products)

required_columns = {
    "year",
    "country_iso3",
    "country_name",
    "hs6",
    "trade_flow",
    "value_thousand_usd",
}

missing = required_columns - set(products.columns)

if missing:
    raise KeyError(f"Не хватает полей: {missing}")

products["year"] = pd.to_numeric(
    products["year"], errors="coerce"
)

products["value_thousand_usd"] = pd.to_numeric(
    products["value_thousand_usd"], errors="coerce"
)

products["hs6"] = normalize_hs6(products["hs6"])

products["hs2"] = products["hs6"].str[:2]

products = products.dropna(
    subset=[
        "year",
        "country_iso3",
        "hs6",
        "value_thousand_usd"
    ]
).copy()

products["year"] = products["year"].astype(int)

products = products[
    products["year"].between(MAIN_START, MAIN_END)
].copy()

products = products[
    products["trade_flow"].isin([
        "imports_from_russia",
        "exports_to_russia"
    ])
].copy()

products["is_technology"] = products["hs2"].isin(TECH_HS2)
products["is_industrial"] = products["hs2"].isin(INDUSTRIAL_HS2)

print(f"Товарных записей: {len(products):,}")
print(f"Стран: {products['country_iso3'].nunique()}")
print(f"Уникальных HS6: {products['hs6'].nunique()}")
print(f"Период: {products['year'].min()}–{products['year'].max()}")

print("\nНаправления торговли:")
print(products["trade_flow"].value_counts().to_string())

dictionary = load_product_dictionary()


# ============================================================
# 3. ФОРМИРОВАНИЕ ВЫБОРКИ ТЕХНОЛОГИЧЕСКОЙ КОРЗИНЫ
# ============================================================

section("1. ФОРМИРОВАНИЕ ТЕХНОЛОГИЧЕСКОЙ И ПРОМЫШЛЕННОЙ ВЫБОРОК")

tech = products[products["is_technology"]].copy()

industrial = products[products["is_industrial"]].copy()

print(f"Технологическая корзина: {len(tech):,} записей")
print(f"Промышленная корзина: {len(industrial):,} записей")

print(
    f"Уникальных HS6 в технологической корзине: "
    f"{tech['hs6'].nunique()}"
)

print(
    f"Уникальных HS6 в промышленной корзине: "
    f"{industrial['hs6'].nunique()}"
)

tech = add_description(tech, dictionary)
industrial = add_description(industrial, dictionary)


# ============================================================
# 4. ГЛОБАЛЬНАЯ СТРУКТУРА ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ
# ============================================================

section("2. ГЛОБАЛЬНАЯ СТРУКТУРА ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ")

def build_global_product_structure(data, start, end, label):
    subset = data[
        data["year"].between(start, end)
    ].copy()

    result = (
        subset.groupby(
            ["trade_flow", "hs6", "product_description"],
            as_index=False
        )
        .agg(
            value_thousand_usd=("value_thousand_usd", "sum"),
            active_years=("year", "nunique"),
            countries=("country_iso3", "nunique"),
        )
    )

    result["value_mln_usd"] = (
        result["value_thousand_usd"] / 1000
    )

    result["period"] = label

    result["share_pct"] = (
        result.groupby("trade_flow")["value_thousand_usd"]
        .transform(
            lambda x: x / x.sum() * 100 if x.sum() else 0
        )
    )

    result = result.sort_values(
        ["trade_flow", "value_thousand_usd"],
        ascending=[True, False]
    )

    result["rank"] = (
        result.groupby("trade_flow")["value_thousand_usd"]
        .rank(method="min", ascending=False)
    )

    return result


global_tech_main = build_global_product_structure(
    tech, MAIN_START, MAIN_END, "2002-2023"
)

global_tech_recent = build_global_product_structure(
    tech, RECENT_START, RECENT_END, "2019-2023"
)

global_industrial_main = build_global_product_structure(
    industrial, MAIN_START, MAIN_END, "2002-2023"
)

global_industrial_recent = build_global_product_structure(
    industrial, RECENT_START, RECENT_END, "2019-2023"
)

save_csv(
    global_tech_main,
    "global_technology_products_2002_2023.csv"
)

save_csv(
    global_tech_recent,
    "global_technology_products_2019_2023.csv"
)

save_csv(
    global_industrial_main,
    "global_industrial_products_2002_2023.csv"
)

save_csv(
    global_industrial_recent,
    "global_industrial_products_2019_2023.csv"
)


# ============================================================
# 5. ТОП ТОВАРОВ ПО НАПРАВЛЕНИЯМ
# ============================================================

section("3. КРУПНЕЙШИЕ ТОВАРЫ В ТЕХНОЛОГИЧЕСКОЙ КОРЗИНЕ")

for flow, title in [
    ("imports_from_russia", "РОССИЯ → АФРИКА"),
    ("exports_to_russia", "АФРИКА → РОССИЯ"),
]:
    for period_name, table in [
        ("2002–2023", global_tech_main),
        ("2019–2023", global_tech_recent),
    ]:
        subset = table[
            table["trade_flow"] == flow
        ].head(15)

        print(f"\n{title} | {period_name}")

        if subset.empty:
            print("Нет данных.")
            continue

        print(
            subset[
                [
                    "hs6",
                    "product_description",
                    "value_mln_usd",
                    "share_pct",
                    "countries",
                ]
            ].to_string(index=False)
        )


# ============================================================
# 6. ТОВАРНЫЕ ПРОФИЛИ КАЖДОЙ СТРАНЫ
# ============================================================

section("4. ТОВАРНЫЕ ПРОФИЛИ ПО СТРАНАМ")

def build_country_product_details(data, start, end, basket, period_label):
    subset = data[
        data["year"].between(start, end)
    ].copy()

    result = (
        subset.groupby(
            [
                "country_iso3",
                "country_name",
                "trade_flow",
                "hs6",
                "product_description",
            ],
            as_index=False
        )
        .agg(
            value_thousand_usd=("value_thousand_usd", "sum"),
            active_years=("year", "nunique"),
        )
    )

    result["value_mln_usd"] = (
        result["value_thousand_usd"] / 1000
    )

    result["country_flow_total_thousand_usd"] = (
        result.groupby(
            ["country_iso3", "trade_flow"]
        )["value_thousand_usd"].transform("sum")
    )

    result["share_in_country_flow_pct"] = (
        result["value_thousand_usd"]
        / result["country_flow_total_thousand_usd"].replace(0, np.nan)
        * 100
    )

    result["period"] = period_label
    result["basket"] = basket

    result["product_rank"] = (
        result.groupby(
            ["country_iso3", "trade_flow"]
        )["value_thousand_usd"]
        .rank(method="min", ascending=False)
    )

    return result


tech_details_main = build_country_product_details(
    tech, MAIN_START, MAIN_END,
    "technology_HS84_90", "2002-2023"
)

tech_details_recent = build_country_product_details(
    tech, RECENT_START, RECENT_END,
    "technology_HS84_90", "2019-2023"
)

industrial_details_main = build_country_product_details(
    industrial, MAIN_START, MAIN_END,
    "industrial_HS72_90", "2002-2023"
)

industrial_details_recent = build_country_product_details(
    industrial, RECENT_START, RECENT_END,
    "industrial_HS72_90", "2019-2023"
)

save_csv(
    tech_details_main,
    "country_technology_products_2002_2023.csv"
)

save_csv(
    tech_details_recent,
    "country_technology_products_2019_2023.csv"
)

save_csv(
    industrial_details_main,
    "country_industrial_products_2002_2023.csv"
)

save_csv(
    industrial_details_recent,
    "country_industrial_products_2019_2023.csv"
)


# ============================================================
# 7. ДИВЕРСИФИКАЦИЯ ТОВАРНОЙ СТРУКТУРЫ
# ============================================================

section("5. ДИВЕРСИФИКАЦИЯ ТОВАРНОЙ ТОРГОВЛИ")

def calculate_diversification(data, start, end, period_label, basket_name):
    subset = data[
        data["year"].between(start, end)
    ].copy()

    grouped = (
        subset.groupby(
            ["country_iso3", "country_name", "trade_flow", "hs6"],
            as_index=False
        )
        .agg(
            value_thousand_usd=("value_thousand_usd", "sum")
        )
    )

    output = []

    for (iso3, country, flow), group in grouped.groupby(
        ["country_iso3", "country_name", "trade_flow"]
    ):
        total = group["value_thousand_usd"].sum()

        if total <= 0:
            continue

        shares = group["value_thousand_usd"] / total

        hhi = (shares.pow(2).sum()) * 10000

        sorted_values = group.sort_values(
            "value_thousand_usd",
            ascending=False
        )

        top1_share = (
            sorted_values["value_thousand_usd"].iloc[0]
            / total * 100
        )

        top5_share = (
            sorted_values.head(5)["value_thousand_usd"].sum()
            / total * 100
        )

        top10_share = (
            sorted_values.head(10)["value_thousand_usd"].sum()
            / total * 100
        )

        effective_products = (
            10000 / hhi if hhi > 0 else np.nan
        )

        output.append({
            "country_iso3": iso3,
            "country_name": country,
            "trade_flow": flow,
            "period": period_label,
            "basket": basket_name,
            "total_value_mln_usd": total / 1000,
            "number_of_hs6_products": group["hs6"].nunique(),
            "hhi_hs6": hhi,
            "effective_number_of_products": effective_products,
            "top1_share_pct": top1_share,
            "top5_share_pct": top5_share,
            "top10_share_pct": top10_share,
        })

    return pd.DataFrame(output)


diversification_main = calculate_diversification(
    tech, MAIN_START, MAIN_END,
    "2002-2023", "technology_HS84_90"
)

diversification_recent = calculate_diversification(
    tech, RECENT_START, RECENT_END,
    "2019-2023", "technology_HS84_90"
)

industrial_diversification_main = calculate_diversification(
    industrial, MAIN_START, MAIN_END,
    "2002-2023", "industrial_HS72_90"
)

industrial_diversification_recent = calculate_diversification(
    industrial, RECENT_START, RECENT_END,
    "2019-2023", "industrial_HS72_90"
)

diversification = pd.concat(
    [
        diversification_main,
        diversification_recent,
        industrial_diversification_main,
        industrial_diversification_recent,
    ],
    ignore_index=True
)

save_csv(
    diversification,
    "country_product_diversification.csv"
)


# ============================================================
# 8. ДИНАМИКА ТОВАРНОЙ СТРУКТУРЫ
# ============================================================

section("6. ИЗМЕНЕНИЕ ТОВАРНОЙ СТРУКТУРЫ")

def build_product_dynamics(main, recent, basket_name):
    keys = [
        "country_iso3",
        "trade_flow",
        "hs6",
    ]

    a = (
        main.groupby(keys, as_index=False)
        .agg(value_2002_2023=("value_thousand_usd", "sum"))
    )

    b = (
        recent.groupby(keys, as_index=False)
        .agg(value_2019_2023=("value_thousand_usd", "sum"))
    )

    result = a.merge(
        b,
        on=keys,
        how="outer",
        validate="one_to_one"
    ).fillna({
        "value_2002_2023": 0,
        "value_2019_2023": 0,
    })

    result["basket"] = basket_name

    result["value_2002_2023_mln_usd"] = (
        result["value_2002_2023"] / 1000
    )

    result["value_2019_2023_mln_usd"] = (
        result["value_2019_2023"] / 1000
    )

    result["recent_annual_average_mln_usd"] = (
        result["value_2019_2023_mln_usd"] / 5
    )

    result["longterm_annual_average_mln_usd"] = (
        result["value_2002_2023_mln_usd"] / 22
    )

    result["recent_vs_longterm_annual_average"] = (
        result["recent_annual_average_mln_usd"]
        / result["longterm_annual_average_mln_usd"].replace(0, np.nan)
    )

    return result


tech_dynamics = build_product_dynamics(
    tech[tech["year"].between(MAIN_START, MAIN_END)],
    tech[tech["year"].between(RECENT_START, RECENT_END)],
    "technology_HS84_90"
)

industrial_dynamics = build_product_dynamics(
    industrial[industrial["year"].between(MAIN_START, MAIN_END)],
    industrial[industrial["year"].between(RECENT_START, RECENT_END)],
    "industrial_HS72_90"
)

save_csv(
    tech_dynamics,
    "technology_product_dynamics.csv"
)

save_csv(
    industrial_dynamics,
    "industrial_product_dynamics.csv"
)


# ============================================================
# 9. АНАЛИЗ ОТДЕЛЬНЫХ СТРАН
# ============================================================

section("7. УГЛУБЛЁННЫЙ АНАЛИЗ ШЕСТИ СТРАН")

focus_details = tech_details_main[
    tech_details_main["country_iso3"].isin(FOCUS_COUNTRIES)
].copy()

focus_details_recent = tech_details_recent[
    tech_details_recent["country_iso3"].isin(FOCUS_COUNTRIES)
].copy()

focus_diversification = diversification[
    diversification["country_iso3"].isin(FOCUS_COUNTRIES)
].copy()

save_csv(
    focus_details,
    "focus_countries_technology_products_2002_2023.csv"
)

save_csv(
    focus_details_recent,
    "focus_countries_technology_products_2019_2023.csv"
)

save_csv(
    focus_diversification,
    "focus_countries_diversification.csv"
)

for iso3, country in FOCUS_COUNTRIES.items():
    print(f"\n{'-' * 80}")
    print(f"{country} ({iso3})")

    for flow, flow_name in [
        ("imports_from_russia", "Россия → страна"),
        ("exports_to_russia", "Страна → Россия"),
    ]:
        group = focus_details[
            (focus_details["country_iso3"] == iso3)
            & (focus_details["trade_flow"] == flow)
        ]

        print(f"\n{flow_name}")

        if group.empty:
            print("Нет торговли в технологической корзине.")
            continue

        print(
            group.sort_values(
                "value_thousand_usd",
                ascending=False
            )[
                [
                    "hs6",
                    "product_description",
                    "value_mln_usd",
                    "share_in_country_flow_pct",
                ]
            ].head(TOP_N).to_string(index=False)
        )


# ============================================================
# 10. СТРУКТУРА ПО HS2
# ============================================================

section("8. СТРУКТУРА ТЕХНОЛОГИЧЕСКОЙ ТОРГОВЛИ ПО HS2")

def build_hs2_structure(data, start, end, period_label):
    subset = data[
        data["year"].between(start, end)
    ].copy()

    result = (
        subset.groupby(
            ["trade_flow", "hs2"],
            as_index=False
        )
        .agg(
            value_thousand_usd=("value_thousand_usd", "sum"),
            countries=("country_iso3", "nunique"),
            products=("hs6", "nunique"),
        )
    )

    result["value_mln_usd"] = (
        result["value_thousand_usd"] / 1000
    )

    result["share_pct"] = (
        result.groupby("trade_flow")["value_thousand_usd"]
        .transform(
            lambda x: x / x.sum() * 100 if x.sum() else 0
        )
    )

    result["period"] = period_label

    return result.sort_values(
        ["trade_flow", "value_thousand_usd"],
        ascending=[True, False]
    )


hs2_main = build_hs2_structure(
    tech, MAIN_START, MAIN_END, "2002-2023"
)

hs2_recent = build_hs2_structure(
    tech, RECENT_START, RECENT_END, "2019-2023"
)

save_csv(hs2_main, "technology_trade_hs2_2002_2023.csv")
save_csv(hs2_recent, "technology_trade_hs2_2019_2023.csv")

print("\nHS2: 2002–2023")
print(
    hs2_main[
        [
            "trade_flow",
            "hs2",
            "value_mln_usd",
            "share_pct",
            "countries",
            "products",
        ]
    ].to_string(index=False)
)


# ============================================================
# 11. КОНТРОЛЬ КАЧЕСТВА И ИТОГОВЫЕ ПОКАЗАТЕЛИ
# ============================================================

section("9. КОНТРОЛЬ КАЧЕСТВА")

print("Проверка исходной товарной базы:")

print(f"Всего записей: {len(products):,}")
print(f"Стран: {products['country_iso3'].nunique()}")
print(f"HS6: {products['hs6'].nunique()}")

print(
    "Пропуски в кодах HS6:",
    products["hs6"].isna().sum()
)

print(
    "Пропуски в стоимости:",
    products["value_thousand_usd"].isna().sum()
)

print(
    "Отрицательные стоимости:",
    (products["value_thousand_usd"] < 0).sum()
)

print(
    "Записей вне технологической корзины в tech:",
    (~tech["hs2"].isin(TECH_HS2)).sum()
)

print(
    "Записей вне промышленной корзины в industrial:",
    (~industrial["hs2"].isin(INDUSTRIAL_HS2)).sum()
)

print("\nСовокупные результаты технологической корзины:")

for flow, name in [
    ("imports_from_russia", "Россия → Африка"),
    ("exports_to_russia", "Африка → Россия"),
]:
    for label, data in [
        ("2002–2023", tech),
        ("2019–2023", tech),
    ]:
        if label == "2002–2023":
            subset = data[
                data["year"].between(MAIN_START, MAIN_END)
            ]
        else:
            subset = data[
                data["year"].between(RECENT_START, RECENT_END)
            ]

        subset = subset[subset["trade_flow"] == flow]

        total = subset["value_thousand_usd"].sum() / 1000

        print(
            f"{name} | {label}: "
            f"{total:,.2f} млн USD"
        )

print("\nРаспределение числа HS6 по странам и направлениям:")

print(
    diversification_main.groupby("trade_flow")[
        "number_of_hs6_products"
    ].describe().round(2).to_string()
)

print("\n" + "=" * 90)
print("АНАЛИЗ ТОВАРНОЙ СТРУКТУРЫ ЗАВЕРШЁН")
print("=" * 90)

print(f"\nРезультаты сохранены в:\n{OUTPUT_DIR}")
