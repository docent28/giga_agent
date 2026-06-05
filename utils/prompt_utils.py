# utils/prompt_utils.py
import os
import streamlit as st


# --- ИНИЦИАЛИЗАЦИЯ edited_prompts (ДОБАВЛЕНО) ---
def _init_edited_prompts():
    """Инициализирует edited_prompts в session_state, если его нет"""
    if "edited_prompts" not in st.session_state:
        st.session_state.edited_prompts = {}


# Вызываем инициализацию при загрузке модуля
_init_edited_prompts()


def load_prompt(prompt_name, etalon_info, answers_info, basic_stats=""):
    """
    Загружает промпт из файла или из временного хранилища (есть правки)
    """
    # Убеждаемся, что edited_prompts существует
    _init_edited_prompts()

    # Сначала проверяем, есть ли отредактированная версия в session_state
    if prompt_name in st.session_state.edited_prompts:
        template = st.session_state.edited_prompts[prompt_name]
    else:
        # Иначе загружаем из файла
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


def get_local_prompt_content(prompt_name):
    """Загружает промпт из локального файла (без подстановки переменных)"""
    prompt_file = os.path.join("prompts", f"{prompt_name}.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"❌ Файл {prompt_file} не найден"
    except Exception as e:
        return f"❌ Ошибка: {e}"


def get_edited_prompt_content(prompt_name):
    """Возвращает отредактированную версию промпта (если есть) или локальную"""
    _init_edited_prompts()

    if prompt_name in st.session_state.edited_prompts:
        return st.session_state.edited_prompts[prompt_name]
    else:
        return get_local_prompt_content(prompt_name)


def save_edited_prompt(prompt_name, content):
    """Сохраняет отредактированную версию промпта в session_state (временно)"""
    _init_edited_prompts()
    st.session_state.edited_prompts[prompt_name] = content
    return True


def clear_edited_prompt(prompt_name):
    """Удаляет отредактированную версию промпта"""
    _init_edited_prompts()
    if prompt_name in st.session_state.edited_prompts:
        del st.session_state.edited_prompts[prompt_name]
        return True
    return False


def get_full_prompt_text(prompt_name):
    """Возвращает полный текст промпта для предпросмотра"""
    return get_edited_prompt_content(prompt_name)


def get_prompt_preview(prompt_name, length=500):
    """Возвращает preview промпта"""
    content = get_edited_prompt_content(prompt_name)
    preview = content[:length]
    if len(content) > length:
        preview += "\n\n... (промпт обрезан)"
    return preview