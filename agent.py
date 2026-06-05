# -*- coding: utf-8 -*-
from gigachat import GigaChat
import pandas as pd
import os
from dotenv import load_dotenv

# Загружаем ключ из файла .env
load_dotenv()
API_KEY = os.getenv("GIGACHAT_KEY")

# Проверка: если ключ не загрузился
if not API_KEY:
    print("❌ Ошибка: ключ не найден в файле .env")
    print("📝 Создайте файл .env с содержимым: GIGACHAT_KEY=ваш_ключ")
    exit(1)

# Остальной код тот же
DATA_FOLDER = r"C:\giga_agent\excel_files"

giga = GigaChat(
    credentials=API_KEY,
    verify_ssl_certs=False,
    timeout=60
)


def analyze_excel(file_path):
    print(f"📁 Analyzing: {file_path}")

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return f"Error reading file: {e}"

    rows, cols = df.shape
    column_names = list(df.columns)
    missing_values = df.isnull().sum().sum()

    prompt = f"""
    Analyze this Excel file with the following parameters:

    - File name: {os.path.basename(file_path)}
    - Number of rows: {rows}
    - Number of columns: {cols}
    - Column names: {column_names}
    - Total missing values: {missing_values}

    First 3 rows of data:
    {df.head(3).to_string()}

    Give a brief analysis (2-3 sentences) and 2 specific recommendations for this data.
    """

    response = giga.chat(prompt)
    return response.choices[0].message.content


def main():
    print("🤖 AI Excel Analyzer started")
    print(f"📂 Looking for files in: {DATA_FOLDER}")

    if not os.path.exists(DATA_FOLDER):
        print(f"❌ Folder '{DATA_FOLDER}' not found!")
        print(f"📝 Create this folder and put Excel files (.xlsx) in it")
        return

    excel_files = []
    for file in os.listdir(DATA_FOLDER):
        if file.endswith(('.xlsx', '.xls')):
            excel_files.append(os.path.join(DATA_FOLDER, file))

    if not excel_files:
        print("❌ No Excel files found in folder!")
        print("📝 Put at least one .xlsx or .xls file in the folder")
        return

    print(f"✅ Found {len(excel_files)} file(s)")
    print("=" * 50)

    for i, file in enumerate(excel_files, 1):
        print(f"\n📊 File {i}/{len(excel_files)}:")
        analysis = analyze_excel(file)
        print(analysis)
        print("-" * 40)

    print("\n🎉 Analysis complete!")


if __name__ == "__main__":
    main()