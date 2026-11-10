from pathlib import Path
import pandas as pd

# Путь к проекту
PROJECT_DIR = Path(__file__).resolve().parents[2]

# Папка для справочников
REFERENCE_DIR = PROJECT_DIR / "data" / "reference"
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

# 54 государства Африки
african_countries = [
    ("DZA", "Algeria", "Алжир", "Northern Africa"),
    ("AGO", "Angola", "Ангола", "Middle Africa"),
    ("BEN", "Benin", "Бенин", "Western Africa"),
    ("BWA", "Botswana", "Ботсвана", "Southern Africa"),
    ("BFA", "Burkina Faso", "Буркина-Фасо", "Western Africa"),
    ("BDI", "Burundi", "Бурунди", "Eastern Africa"),
    ("CPV", "Cabo Verde", "Кабо-Верде", "Western Africa"),
    ("CMR", "Cameroon", "Камерун", "Middle Africa"),
    ("CAF", "Central African Republic", "ЦАР", "Middle Africa"),
    ("TCD", "Chad", "Чад", "Middle Africa"),
    ("COM", "Comoros", "Коморы", "Eastern Africa"),
    ("COG", "Congo", "Республика Конго", "Middle Africa"),
    ("CIV", "Côte d'Ivoire", "Кот-д'Ивуар", "Western Africa"),
    ("COD", "Democratic Republic of the Congo", "ДР Конго", "Middle Africa"),
    ("DJI", "Djibouti", "Джибути", "Eastern Africa"),
    ("EGY", "Egypt", "Египет", "Northern Africa"),
    ("GNQ", "Equatorial Guinea", "Экваториальная Гвинея", "Middle Africa"),
    ("ERI", "Eritrea", "Эритрея", "Eastern Africa"),
    ("SWZ", "Eswatini", "Эсватини", "Southern Africa"),
    ("ETH", "Ethiopia", "Эфиопия", "Eastern Africa"),
    ("GAB", "Gabon", "Габон", "Middle Africa"),
    ("GMB", "Gambia", "Гамбия", "Western Africa"),
    ("GHA", "Ghana", "Гана", "Western Africa"),
    ("GIN", "Guinea", "Гвинея", "Western Africa"),
    ("GNB", "Guinea-Bissau", "Гвинея-Бисау", "Western Africa"),
    ("KEN", "Kenya", "Кения", "Eastern Africa"),
    ("LSO", "Lesotho", "Лесото", "Southern Africa"),
    ("LBR", "Liberia", "Либерия", "Western Africa"),
    ("LBY", "Libya", "Ливия", "Northern Africa"),
    ("MDG", "Madagascar", "Мадагаскар", "Eastern Africa"),
    ("MWI", "Malawi", "Малави", "Eastern Africa"),
    ("MLI", "Mali", "Мали", "Western Africa"),
    ("MRT", "Mauritania", "Мавритания", "Western Africa"),
    ("MUS", "Mauritius", "Маврикий", "Eastern Africa"),
    ("MAR", "Morocco", "Марокко", "Northern Africa"),
    ("MOZ", "Mozambique", "Мозамбик", "Eastern Africa"),
    ("NAM", "Namibia", "Намибия", "Southern Africa"),
    ("NER", "Niger", "Нигер", "Western Africa"),
    ("NGA", "Nigeria", "Нигерия", "Western Africa"),
    ("RWA", "Rwanda", "Руанда", "Eastern Africa"),
    ("STP", "Sao Tome and Principe", "Сан-Томе и Принсипи", "Middle Africa"),
    ("SEN", "Senegal", "Сенегал", "Western Africa"),
    ("SYC", "Seychelles", "Сейшелы", "Eastern Africa"),
    ("SLE", "Sierra Leone", "Сьерра-Леоне", "Western Africa"),
    ("SOM", "Somalia", "Сомали", "Eastern Africa"),
    ("ZAF", "South Africa", "ЮАР", "Southern Africa"),
    ("SSD", "South Sudan", "Южный Судан", "Eastern Africa"),
    ("SDN", "Sudan", "Судан", "Northern Africa"),
    ("TZA", "Tanzania", "Танзания", "Eastern Africa"),
    ("TGO", "Togo", "Того", "Western Africa"),
    ("TUN", "Tunisia", "Тунис", "Northern Africa"),
    ("UGA", "Uganda", "Уганда", "Eastern Africa"),
    ("ZMB", "Zambia", "Замбия", "Eastern Africa"),
    ("ZWE", "Zimbabwe", "Зимбабве", "Eastern Africa"),
]

columns = [
    "country_code",
    "country_name",
    "country_name_ru",
    "subregion"
]

df = pd.DataFrame(african_countries, columns=columns)

df["is_africa"] = True

# Проверяем уникальность кодов и количество стран
assert len(df) == 54, f"Ожидалось 54 страны, получено {len(df)}"
assert df["country_code"].nunique() == 54, "Обнаружены повторяющиеся ISO-коды"

# Сохраняем справочник
output_path = REFERENCE_DIR / "africa_countries.csv"

df.to_csv(output_path, index=False, encoding="utf-8-sig")

print("Справочник успешно создан!")
print(f"Количество стран: {len(df)}")
print(f"Уникальных ISO-кодов: {df['country_code'].nunique()}")
print(f"Файл: {output_path}")

print("\nПервые 10 стран:")
print(df.head(10).to_string(index=False))
