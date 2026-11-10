
import csv
from pathlib import Path
from collections import defaultdict

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import (
    silhouette_score,
    silhouette_samples,
    adjusted_rand_score
)


# =========================================================
# НАСТРОЙКИ
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parent

INPUT = (
    PROJECT_DIR
    / "reports"
    / "country_block_profiles.csv"
)

REPORT_DIR = PROJECT_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BLOCKS = {
    "mean_economic_block": "Экономические возможности",
    "mean_digital_block": "Цифровая инфраструктура",
    "mean_science_block": "Научно-технологическая база",
    "mean_industry_block": "Промышленная база",
    "mean_institutional_block": "Институциональная среда"
}

K_VALUES = range(2, 7)

RANDOM_STATE = 42
N_INIT = 50


# =========================================================
# 1. ЗАГРУЗКА ДАННЫХ
# =========================================================

countries = []

with open(INPUT, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        country = {
            "country_iso3": row["country_iso3"],
            "country_name": row["country_name"],
            "mean_index": float(row["mean_index"]),
            "observations": int(row["observations"])
        }

        for column in BLOCKS:
            country[column] = float(row[column])

        countries.append(country)


feature_columns = list(BLOCKS.keys())

X = np.array([
    [country[column] for column in feature_columns]
    for country in countries
])

country_codes = [
    country["country_iso3"]
    for country in countries
]

country_names = [
    country["country_name"]
    for country in countries
]

print("=" * 80)
print("КЛАСТЕРИЗАЦИЯ АФРИКАНСКИХ СТРАН")
print("=" * 80)

print("Стран:", len(countries))
print("Признаков:", len(feature_columns))
print("Алгоритм основной модели: K-Means")
print("Метод стандартизации: StandardScaler")


# =========================================================
# 2. СТАНДАРТИЗАЦИЯ
# =========================================================

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print("\nСтандартизация завершена.")

print("Средние стандартизированных признаков:")
print(np.round(X_scaled.mean(axis=0), 4))

print("Стандартные отклонения:")
print(np.round(X_scaled.std(axis=0), 4))


# =========================================================
# 3. ПРОВЕРКА ЧИСЛА КЛАСТЕРОВ
# =========================================================

models = {}
metrics = []

print("\n" + "=" * 80)
print("ОЦЕНКА ЧИСЛА КЛАСТЕРОВ")
print("=" * 80)

for k in K_VALUES:

    model = KMeans(
        n_clusters=k,
        random_state=RANDOM_STATE,
        n_init=N_INIT
    )

    labels = model.fit_predict(X_scaled)

    score = silhouette_score(X_scaled, labels)

    cluster_sizes = defaultdict(int)

    for label in labels:
        cluster_sizes[int(label)] += 1

    models[k] = {
        "model": model,
        "labels": labels,
        "silhouette": score,
        "sizes": dict(cluster_sizes)
    }

    metrics.append({
        "k": k,
        "silhouette": round(score, 5),
        "inertia": round(model.inertia_, 5),
        "cluster_sizes": ";".join(
            str(cluster_sizes[i])
            for i in sorted(cluster_sizes)
        )
    })

    print(f"\nКластеров: {k}")
    print(f"Коэффициент силуэта: {score:.4f}")
    print(
        "Размеры кластеров:",
        dict(sorted(cluster_sizes.items()))
    )


# =========================================================
# 4. ВЫБОР ЛУЧШЕГО K
# =========================================================

best_k = max(
    models,
    key=lambda k: models[k]["silhouette"]
)

best_model = models[best_k]["model"]
best_labels = models[best_k]["labels"]

print("\n" + "=" * 80)
print("ЛУЧШЕЕ РЕШЕНИЕ ПО КОЭФФИЦИЕНТУ СИЛУЭТА")
print("=" * 80)

print("Число кластеров:", best_k)
print(
    "Коэффициент силуэта:",
    round(models[best_k]["silhouette"], 4)
)


# =========================================================
# 5. ИЕРАРХИЧЕСКАЯ КЛАСТЕРИЗАЦИЯ
# =========================================================

hierarchical = AgglomerativeClustering(
    n_clusters=best_k,
    linkage="ward"
)

hierarchical_labels = hierarchical.fit_predict(X_scaled)

ari = adjusted_rand_score(
    best_labels,
    hierarchical_labels
)

hierarchical_silhouette = silhouette_score(
    X_scaled,
    hierarchical_labels
)

print("\n" + "=" * 80)
print("СРАВНЕНИЕ С ИЕРАРХИЧЕСКОЙ КЛАСТЕРИЗАЦИЕЙ")
print("=" * 80)

print("Метод: Ward")
print("Число кластеров:", best_k)
print("Коэффициент силуэта:", round(
    hierarchical_silhouette, 4
))
print("Adjusted Rand Index:", round(ari, 4))


# =========================================================
# 6. УПОРЯДОЧИВАЕМ КЛАСТЕРЫ ПО СРЕДНЕМУ ИНДЕКСУ
# =========================================================

cluster_mean_indices = {}

for cluster_id in range(best_k):

    indices = [
        countries[i]["mean_index"]
        for i in range(len(countries))
        if best_labels[i] == cluster_id
    ]

    cluster_mean_indices[cluster_id] = np.mean(indices)


ordered_cluster_ids = sorted(
    cluster_mean_indices,
    key=lambda cluster_id: cluster_mean_indices[cluster_id],
    reverse=True
)

cluster_number = {
    old_id: new_id + 1
    for new_id, old_id in enumerate(ordered_cluster_ids)
}


# =========================================================
# 7. СТРАНОВЫЕ РЕЗУЛЬТАТЫ
# =========================================================

individual_silhouettes = silhouette_samples(
    X_scaled,
    best_labels
)

country_output = []

for i, country in enumerate(countries):

    old_cluster = int(best_labels[i])

    row = {
        "country_iso3": country["country_iso3"],
        "country_name": country["country_name"],
        "mean_index": round(country["mean_index"], 4),
        "observations": country["observations"],
        "kmeans_cluster": cluster_number[old_cluster],
        "hierarchical_cluster": int(hierarchical_labels[i]) + 1,
        "individual_silhouette": round(
            individual_silhouettes[i], 5
        )
    }

    for column in feature_columns:
        row[column] = round(country[column], 4)

    country_output.append(row)


country_output.sort(
    key=lambda item: (
        item["kmeans_cluster"],
        -item["mean_index"]
    )
)

country_fields = [
    "country_iso3",
    "country_name",
    "mean_index",
    "observations",
    "kmeans_cluster",
    "hierarchical_cluster",
    "individual_silhouette"
] + feature_columns

country_file = REPORT_DIR / "country_clusters.csv"

with open(
    country_file,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=country_fields
    )

    writer.writeheader()
    writer.writerows(country_output)


# =========================================================
# 8. ПРОФИЛИ КЛАСТЕРОВ
# =========================================================

cluster_profiles = []

for new_cluster in range(1, best_k + 1):

    members = [
        country
        for country in country_output
        if country["kmeans_cluster"] == new_cluster
    ]

    profile = {
        "cluster": new_cluster,
        "countries_count": len(members),
        "mean_index": round(
            np.mean([item["mean_index"] for item in members]),
            4
        ),
        "countries": "; ".join(
            item["country_name"] for item in members
        )
    }

    for column in feature_columns:
        profile[column] = round(
            np.mean([item[column] for item in members]),
            4
        )

    cluster_profiles.append(profile)


profile_fields = [
    "cluster",
    "countries_count",
    "mean_index",
    "countries"
] + feature_columns

profile_file = REPORT_DIR / "cluster_profiles.csv"

with open(
    profile_file,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=profile_fields
    )

    writer.writeheader()
    writer.writerows(cluster_profiles)


# =========================================================
# 9. СОХРАНЯЕМ МЕТРИКИ
# =========================================================

metrics_file = REPORT_DIR / "clustering_metrics.csv"

with open(
    metrics_file,
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "k",
            "silhouette",
            "inertia",
            "cluster_sizes"
        ]
    )

    writer.writeheader()
    writer.writerows(metrics)


# =========================================================
# 10. ВЫВОДИМ ИТОГИ
# =========================================================

print("\n" + "=" * 80)
print("ИТОГОВЫЕ КЛАСТЕРЫ")
print("=" * 80)

for profile in cluster_profiles:

    print("\nКЛАСТЕР", profile["cluster"])
    print("Количество стран:", profile["countries_count"])
    print("Средний индекс:", profile["mean_index"])

    print("Страны:")
    for item in country_output:
        if item["kmeans_cluster"] == profile["cluster"]:
            print(
                f"  - {item['country_name']} "
                f"({item['country_iso3']})"
            )

    print("Средние значения блоков:")

    for column, name in BLOCKS.items():
        print(
            f"  {name}: {profile[column]:.2f}"
        )


print("\n" + "=" * 80)
print("ФАЙЛЫ СОХРАНЕНЫ")
print("=" * 80)

print(country_file)
print(profile_file)
print(metrics_file)

print("\nКЛАСТЕРИЗАЦИЯ ЗАВЕРШЕНА")
