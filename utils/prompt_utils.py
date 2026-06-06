# utils/prompt_utils.py
import os


def load_prompt(prompt_name, etalon_info, answers_info, basic_stats=""):
    """
    Загружает промпт из файла и подставляет переменные
    """
    prompt_file = os.path.join("prompts", f"{prompt_name}.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        return f"❌ Ошибка: файл {prompt_file} не найден."
    except Exception as e:
        return f"❌ Ошибка загрузки промпта: {e}"

    # Подставляем переменные
    try:
        prompt = template.format(
            etalon_info=etalon_info,
            answers_info=answers_info,
            basic_stats=basic_stats
        )
        return prompt
    except KeyError as e:
        return f"❌ Ошибка: в промпте отсутствует переменная {e}"
    except Exception as e:
        return f"❌ Ошибка форматирования промпта: {e}"


def get_prompt_content(prompt_name):
    """Возвращает полный текст промпта без подстановки переменных (для просмотра)"""
    prompt_file = os.path.join("prompts", f"{prompt_name}.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"❌ Файл {prompt_file} не найден"
    except Exception as e:
        return f"❌ Ошибка: {e}"