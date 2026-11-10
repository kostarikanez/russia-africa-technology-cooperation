
from pathlib import Path
import pandas as pd


# ============================================================
# ПУТИ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "reports" / "country_clusters.csv"
OUTPUT_DIR = BASE_DIR / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# БЛОКИ ТЕХНОЛОГИЧЕСКОГО РАЗВИТИЯ
# ============================================================

BLOCKS = {
    "Экономические возможности": "mean_economic_block",
    "Цифровая инфраструктура": "mean_digital_block",
    "Научно-технологическая база": "mean_science_block",
    "Промышленная база": "mean_industry_block",
    "Институциональная среда": "mean_institutional_block"
}

BLOCK_COLUMNS = list(BLOCKS.values())

BLOCK_ACTIONS = {
    "Экономические возможности": (
        "Ограниченность экономических ресурсов и возможностей "
        "финансирования технологического развития"
    ),
    "Цифровая инфраструктура": (
        "Недостаточность цифровой и телекоммуникационной инфраструктуры"
    ),
    "Научно-технологическая база": (
        "Недостаточность научно-исследовательского потенциала "
        "и технологических компетенций"
    ),
    "Промышленная база": (
        "Ограниченность промышленной базы и возможностей "
        "производственного освоения технологий"
    ),
    "Институциональная среда": (
        "Институциональные ограничения технологического развития"
    )
}


# ============================================================
# ЗАГРУЗКА
# ============================================================

print("=" * 80)
print("МАТРИЦА ТЕХНОЛОГИЧЕСКИХ ПРОФИЛЕЙ И СТРУКТУРНЫХ РАЗРЫВОВ")
print("=" * 80)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Не найден входной файл: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

required_columns = [
    "country_iso3",
    "country_name",
    "mean_index",
    "observations",
    "kmeans_cluster"
] + BLOCK_COLUMNS

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"В исходном файле отсутствуют колонки: {missing_columns}"
    )

df[BLOCK_COLUMNS] = df[BLOCK_COLUMNS].apply(
    pd.to_numeric,
    errors="coerce"
)

if df[BLOCK_COLUMNS].isna().any().any():
    raise ValueError(
        "Обнаружены пропуски в значениях пяти блоков."
    )

print(f"Стран: {len(df)}")
print(f"Блоков: {len(BLOCKS)}")


# ============================================================
# ОПРЕДЕЛЕНИЕ СИЛЬНЕЙШЕГО И СЛАБЕЙШЕГО БЛОКОВ
# ============================================================

df["strongest_block"] = df[BLOCK_COLUMNS].idxmax(axis=1)
df["weakest_block"] = df[BLOCK_COLUMNS].idxmin(axis=1)

# Перевод технических названий колонок в названия блоков

COLUMN_TO_NAME = {
    column: name
    for name, column in BLOCKS.items()
}

df["strongest_block_name"] = (
    df["strongest_block"].map(COLUMN_TO_NAME)
)

df["weakest_block_name"] = (
    df["weakest_block"].map(COLUMN_TO_NAME)
)

df["strongest_value"] = df[BLOCK_COLUMNS].max(axis=1)
df["weakest_value"] = df[BLOCK_COLUMNS].min(axis=1)

# Среднее значение пяти блоков

df["mean_block_value"] = df[BLOCK_COLUMNS].mean(axis=1)

# Структурный разрыв

df["structural_gap"] = (
    df["strongest_value"] - df["weakest_value"]
)

# Отклонение сильнейшего и слабейшего блоков от среднего

df["strongest_deviation"] = (
    df["strongest_value"] - df["mean_block_value"]
)

df["weakest_deviation"] = (
    df["weakest_value"] - df["mean_block_value"]
)


# ============================================================
# ОТКЛОНЕНИЯ КАЖДОГО БЛОКА ОТ СРЕДНЕГО ПРОФИЛЯ СТРАНЫ
# ============================================================

for block_name, column in BLOCKS.items():

    deviation_column = (
        "deviation_"
        + column.replace("mean_", "")
    )

    df[deviation_column] = (
        df[column] - df["mean_block_value"]
    )


# ============================================================
# ПРЕДВАРИТЕЛЬНАЯ ИНТЕРПРЕТАЦИЯ ОГРАНИЧЕНИЙ
# ============================================================

df["potential_constraint"] = (
    df["weakest_block_name"].map(BLOCK_ACTIONS)
)

df["interpretation_note"] = (
    "Предварительная оценка по относительной слабости блока; "
    "требуется проверка дополнительными показателями"
)


# Исправление некорректного отображения названия страны

df.loc[
    df["country_iso3"] == "CIV",
    "country_name"
] = "Côte d'Ivoire"


# ============================================================
# ФОРМИРОВАНИЕ ИТОГОВОЙ МАТРИЦЫ
# ============================================================

output_columns = [
    "country_iso3",
    "country_name",
    "kmeans_cluster",
    "mean_index",
    "observations",
    "strongest_block_name",
    "strongest_value",
    "weakest_block_name",
    "weakest_value",
    "structural_gap",
    "mean_block_value",
    "strongest_deviation",
    "weakest_deviation"
]

deviation_columns = [
    "deviation_" + column.replace("mean_", "")
    for column in BLOCK_COLUMNS
]

output_columns += deviation_columns
output_columns += [
    "potential_constraint",
    "interpretation_note"
]

gap_matrix = df[output_columns].copy()

gap_matrix = gap_matrix.sort_values(
    ["kmeans_cluster", "structural_gap"],
    ascending=[True, False]
)

gap_matrix.to_csv(
    OUTPUT_DIR / "country_technology_gaps.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# СВОДКА ПО СЛАБЕЙШИМ БЛОКАМ
# ============================================================

weakest_summary = (
    df.groupby("weakest_block_name")
    .agg(
        countries_count=("country_iso3", "count"),
        average_block_value=("weakest_value", "mean"),
        average_structural_gap=("structural_gap", "mean")
    )
    .reset_index()
    .sort_values("countries_count", ascending=False)
)

weakest_summary.to_csv(
    OUTPUT_DIR / "weakest_blocks_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# СВОДКА ПО КЛАСТЕРАМ
# ============================================================

cluster_summary = (
    df.groupby("kmeans_cluster")
    .agg(
        countries_count=("country_iso3", "count"),
        average_index=("mean_index", "mean"),
        average_structural_gap=("structural_gap", "mean"),
        median_structural_gap=("structural_gap", "median"),
        average_economic_block=("mean_economic_block", "mean"),
        average_digital_block=("mean_digital_block", "mean"),
        average_science_block=("mean_science_block", "mean"),
        average_industry_block=("mean_industry_block", "mean"),
        average_institutional_block=(
            "mean_institutional_block", "mean"
        )
    )
    .reset_index()
)

cluster_summary.to_csv(
    OUTPUT_DIR / "cluster_gap_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# ВЫВОД РЕЗУЛЬТАТОВ
# ============================================================

print("\n" + "=" * 80)
print("ОБЩИЕ РЕЗУЛЬТАТЫ")
print("=" * 80)

print(
    f"Средний структурный разрыв: "
    f"{df['structural_gap'].mean():.2f}"
)

print(
    f"Медианный структурный разрыв: "
    f"{df['structural_gap'].median():.2f}"
)

print(
    f"Минимальный разрыв: "
    f"{df['structural_gap'].min():.2f}"
)

print(
    f"Максимальный разрыв: "
    f"{df['structural_gap'].max():.2f}"
)


print("\n" + "=" * 80)
print("РАСПРЕДЕЛЕНИЕ СЛАБЕЙШИХ БЛОКОВ")
print("=" * 80)

print(
    weakest_summary.to_string(index=False)
)


print("\n" + "=" * 80)
print("СТРАНЫ С НАИБОЛЬШИМИ СТРУКТУРНЫМИ РАЗРЫВАМИ")
print("=" * 80)

print(
    gap_matrix[
        [
            "country_name",
            "country_iso3",
            "strongest_block_name",
            "weakest_block_name",
            "structural_gap"
        ]
    ]
    .sort_values("structural_gap", ascending=False)
    .head(10)
    .to_string(index=False)
)


print("\n" + "=" * 80)
print("СТРУКТУРНЫЕ РАЗРЫВЫ ПО КЛАСТЕРАМ")
print("=" * 80)

print(cluster_summary.to_string(index=False))


print("\n" + "=" * 80)
print("ФАЙЛЫ СОХРАНЕНЫ")
print("=" * 80)

print(OUTPUT_DIR / "country_technology_gaps.csv")
print(OUTPUT_DIR / "weakest_blocks_summary.csv")
print(OUTPUT_DIR / "cluster_gap_summary.csv")

print("\nАНАЛИЗ ЗАВЕРШЁН")
