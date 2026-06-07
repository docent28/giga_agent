# utils/prompt_utils.py
import os
from utils.github_utils import get_file_content, get_prompt_files


def load_prompt(prompt_name, etalon_info, answers_info, basic_stats=""):
    """
    Загружает промпт из GitHub и подставляет переменные
    """
    content, error = get_file_content(f"prompts/{prompt_name}.txt")
    if error:
        return f"Ошибка загрузки промпта: {error}"

    try:
        prompt = content.format(
            etalon_info=etalon_info,
            answers_info=answers_info,
            basic_stats=basic_stats
        )
        return prompt
    except KeyError as e:
        return f"Ошибка: в промпте отсутствует переменная {e}"
    except Exception as e:
        return f"Ошибка форматирования промпта: {e}"


def get_prompt_content(prompt_name):
    """
    Возвращает полный текст промпта без подстановки переменных
    """
    content, error = get_file_content(f"prompts/{prompt_name}.txt")
    if error:
        return f"Ошибка: {error}"
    return content


def get_all_prompts():
    """
    Возвращает список всех промптов (имён файлов без расширения)
    """
    return get_prompt_files()