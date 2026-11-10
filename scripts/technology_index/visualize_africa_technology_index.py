
import pandas as pd
import plotly.express as px
import os

# ============================================================
# 1. ЗАГРУЗКА ДАННЫХ
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(
    BASE_DIR,
    "reports",
    "country_clusters.csv"
)

OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "visualizations")
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(INPUT_FILE)

# Оставляем необходимые столбцы
df = df[
    ["country_iso3", "country_name", "mean_index"]
].copy()

# Приводим индекс к числовому формату
df["mean_index"] = pd.to_numeric(
    df["mean_index"],
    errors="coerce"
)

# Убираем строки без ISO-кода
df = df.dropna(subset=["country_iso3"])

print("Количество стран в таблице:", len(df))
print("Стран с рассчитанным индексом:", df["mean_index"].notna().sum())


# ============================================================
# 2. ПОСТРОЕНИЕ КАРТЫ
# ============================================================

fig = px.choropleth(
    df,
    locations="country_iso3",
    locationmode="ISO-3",
    color="mean_index",

    hover_name="country_name",

    hover_data={
        "country_iso3": True,
        "mean_index": ":.2f"
    },

    color_continuous_scale=[
        [0.0, "#EAF2F8"],
        [0.2, "#C6DBEF"],
        [0.4, "#6BAED6"],
        [0.6, "#3182BD"],
        [0.8, "#08519C"],
        [1.0, "#08306B"]
    ],

    range_color=[
        df["mean_index"].min(),
        df["mean_index"].max()
    ],

    labels={
        "mean_index": "Индекс технологического развития"
    },

    title="Условия технологического развития стран Африки"
)


# ============================================================
# 3. НАСТРОЙКА ВНЕШНЕГО ВИДА
# ============================================================

fig.update_geos(
    scope="africa",

    showland=True,
    landcolor="#D9DDE3",

    showcountries=True,
    countrycolor="white",
    countrywidth=0.8,

    showcoastlines=False,
    showframe=False
)

fig.update_layout(
    title={
        "text": (
            "Условия технологического развития стран Африки"
            "<br><sup>Чем темнее оттенок синего, тем выше значение индекса</sup>"
        ),
        "x": 0.5,
        "xanchor": "center"
    },

    width=1200,
    height=850,

    font=dict(
        family="Arial",
        size=13
    ),

    coloraxis_colorbar=dict(
        title="Значение индекса",
        thickness=18,
        len=0.65
    ),

    margin=dict(
        l=20,
        r=20,
        t=100,
        b=20
    )
)


# ============================================================
# 4. СОХРАНЕНИЕ
# ============================================================

html_path = os.path.join(
    OUTPUT_DIR,
    "africa_technology_index.html"
)

fig.write_html(html_path)

print("\nКарта сохранена:")
print(html_path)

fig.show()

# Сохранение карты в PNG для PowerPoint
png_path = os.path.join(
    OUTPUT_DIR,
    "africa_technology_index.png"
)

fig.write_image(
    png_path,
    width=1800,
    height=1200,
    scale=2
)

print("PNG сохранён:", png_path)
