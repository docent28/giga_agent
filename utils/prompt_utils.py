# utils/prompt_utils.py
import os

def load_prompt(prompt_name, etalon_info, answers_info, basic_stats=""):
    """Загружает промпт из файла prompts/{prompt_name}.txt и подставляет переменные"""
    prompt_file = os.path.join("prompts", f"{prompt_name}.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()
        prompt = template.format(
            etalon_info=etalon_info,
            answers_info=answers_info,
            basic_stats=basic_stats
        )
        return prompt
    except FileNotFoundError:
        return f"❌ Ошибка: файл {prompt_file} не найден."
    except Exception as e:
        return f"❌ Ошибка загрузки промпта: {e}"

def get_prompt_preview(prompt_name):
    """Возвращает первые 500 символов промпта для предпросмотра"""
    prompt_file = os.path.join("prompts", f"{prompt_name}.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        preview = content[:500]
        if len(content) > 500:
            preview += "\n\n... (промпт обрезан, полный текст в файле)"
        return preview
    except FileNotFoundError:
        return f"❌ Файл {prompt_file} не найден"
    except Exception as e:
        return f"❌ Ошибка: {e}"

def get_full_prompt_text(prompt_name):
    """Возвращает полный текст промпта"""
    prompt_file = os.path.join("prompts", f"{prompt_name}.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"❌ Файл {prompt_file} не найден"