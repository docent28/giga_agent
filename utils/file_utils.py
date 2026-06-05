# utils/file_utils.py
import pandas as pd


def detect_file_type(filename):
    """Определяет тип файла по ключевым словам в названии"""
    name_lower = filename.lower()

    etalon_keywords = ['эталон', 'etalon', 'correct', 'ключ', 'правильный', 'правильные ответы', 'эталонный',
                       'reference']
    answers_keywords = ['ответ', 'ответы', 'answers', 'user', 'пользователь', 'результат', 'results', 'массив ответов']

    for kw in etalon_keywords:
        if kw in name_lower:
            return 'etalon'
    for kw in answers_keywords:
        if kw in name_lower:
            return 'answers'
    return 'unknown'


def detect_files_pairs(files_list):
    """Определяет пары файлов (эталон + ответы)"""
    etalon_file = None
    answers_file = None
    for file in files_list:
        ft = detect_file_type(file.name)
        if ft == 'etalon':
            etalon_file = file
        elif ft == 'answers':
            answers_file = file
    return etalon_file, answers_file


def format_file_info(file, label):
    """Форматирует информацию о файле для отправки в промпт"""
    if file is None:
        return f"**{label}:** Не найден\n"
    df = pd.read_excel(file)
    return f"""
**{label}:** {file.name}
- Строк: {df.shape[0]}, Столбцов: {df.shape[1]}
- Названия столбцов: {list(df.columns)}
- Первые 5 строк данных:
{df.head(5).to_string()}
"""


def get_basic_stats_from_df(df):
    """Извлекает базовую статистику из DataFrame"""
    stats = []
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        stats.append("**Числовые колонки:**")
        for col in numeric_cols[:5]:
            stats.append(
                f"  - {col}: среднее={df[col].mean():.2f}, медиана={df[col].median():.2f}, мин={df[col].min():.2f}, макс={df[col].max():.2f}")
    text_cols = df.select_dtypes(include=['object']).columns
    if len(text_cols) > 0:
        stats.append("\n**Текстовые колонки:**")
        for col in text_cols[:3]:
            stats.append(f"  - {col}: {df[col].nunique()} уникальных значений")
    return "\n".join(stats) if stats else "Нет данных для анализа."