import streamlit as st
import pandas as pd
import os
import time
from dotenv import load_dotenv

from utils.file_utils import detect_file_type, detect_files_pairs, format_file_info, get_basic_stats_from_df
from utils.prompt_utils import load_prompt, get_prompt_content, get_all_prompts
from utils.llm_utils import call_gigachat, call_deepseek, get_key_status
from utils.github_utils import (
    get_github_token, get_repo_info,
    create_prompt_file, delete_prompt_file,
    validate_filename, check_file_exists
)

load_dotenv()

st.set_page_config(page_title="AI Excel Analyzer - Чат", page_icon="", layout="wide")
st.title("AI Агент для анализа результатов тестов")

# --- CSS ДЛЯ СТИЛИЗАЦИИ ---
st.markdown("""
<style>
    div[role="dialog"] {
        width: 60% !important;
        max-width: 900px !important;
        min-width: 400px !important;
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        margin: 0 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
        background-color: #ffffff !important;
    }
    div[data-testid="stDialogOverlay"] {
        background-color: rgba(0, 0, 0, 0.5) !important;
    }
    div[role="dialog"] > div {
        max-height: 85vh !important;
        overflow-y: auto !important;
    }

    .stApp {
        background-color: #f0f2f6 !important;
    }

    .user-message {
        background-color: #0a2a4a !important;
        color: white !important;
        border-radius: 15px 15px 5px 15px !important;
        padding: 12px 16px !important;
        margin: 8px 0 !important;
        max-width: 80% !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        word-wrap: break-word !important;
    }

    .assistant-message {
        background-color: #e9ecef !important;
        color: #212529 !important;
        border-radius: 15px 15px 15px 5px !important;
        padding: 12px 16px !important;
        margin: 8px 0 !important;
        max-width: 80% !important;
        margin-left: 0 !important;
        margin-right: auto !important;
        border: 1px solid #dee2e6 !important;
        word-wrap: break-word !important;
    }

    .chat-container-custom {
        height: 500px;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 12px;
        margin-bottom: 10px;
        scroll-behavior: smooth;
    }

    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #e9ecef;
    }
    ::-webkit-scrollbar-thumb {
        background: #adb5bd;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)


@st.dialog("Просмотр промпта")
def view_prompt_dialog(prompt_name):
    content = get_prompt_content(prompt_name)
    st.code(content, language="text", line_numbers=False)
    st.caption(f"Файл: {prompt_name}.txt")
    if st.button("Закрыть", use_container_width=True):
        st.rerun()


@st.dialog("Редактирование промпта")
def edit_prompt_dialog(prompt_name):
    content_key = f"edit_content_{prompt_name}"
    if content_key not in st.session_state:
        st.session_state[content_key] = get_prompt_content(prompt_name)

    st.caption(f"Файл: {prompt_name}.txt")

    new_content = st.text_area(
        "Редактируйте промпт:",
        value=st.session_state[content_key],
        height=400,
        key=f"textarea_{prompt_name}",
        help="Используйте переменные: {etalon_info}, {answers_info}, {basic_stats}"
    )
    st.session_state[content_key] = new_content
    st.caption("Переменные: {etalon_info}, {answers_info}, {basic_stats}")
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Копировать", use_container_width=True):
            st.toast("Промпт скопирован", icon="")

    with col2:
        token = get_github_token()
        if token:
            if st.button("Сохранить в GitHub", use_container_width=True):
                from utils.github_utils import update_file_on_github
                file_path = f"prompts/{prompt_name}.txt"
                success, message = update_file_on_github(
                    file_path,
                    st.session_state[content_key],
                    f"Обновлён промпт {prompt_name}"
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.button("Сохранить в GitHub", use_container_width=True, disabled=True)

    with col3:
        if st.button("Закрыть", use_container_width=True):
            st.session_state.pop(content_key, None)
            st.rerun()


@st.dialog("Создание нового промпта")
def create_prompt_dialog():
    st.markdown("### Создание нового промпта")

    raw_name = st.text_input("Название промпта (максимум 2 слова, латиница/кириллица/цифры/-/_)")
    prompt_text = st.text_area("Текст промпта", height=300,
                               help="Используйте переменные: {etalon_info}, {answers_info}, {basic_stats}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Создать", use_container_width=True):
            if not raw_name.strip():
                st.error("Введите название промпта")
            elif not prompt_text.strip():
                st.error("Введите текст промпта")
            else:
                # Валидируем имя
                valid_name = validate_filename(raw_name)
                if not valid_name:
                    st.error("Некорректное имя. Используйте буквы, цифры, дефис, подчёркивание. Максимум 2 слова.")
                elif check_file_exists(valid_name):
                    st.error(f"Файл {valid_name}.txt уже существует. Введите другое имя.")
                else:
                    success, message = create_prompt_file(valid_name, prompt_text)
                    if success:
                        st.success(f"Промпт '{valid_name}' создан!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Ошибка: {message}")

    with col2:
        if st.button("Отмена", use_container_width=True):
            st.rerun()


@st.dialog("Подтверждение удаления")
def delete_prompt_dialog(prompt_name):
    st.markdown(f"### Удалить промпт '{prompt_name}'?")
    st.caption("Это действие необратимо.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Да, удалить", use_container_width=True):
            success, message = delete_prompt_file(prompt_name)
            if success:
                st.success(f"Промпт '{prompt_name}' удалён")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Ошибка: {message}")

    with col2:
        if st.button("Отмена", use_container_width=True):
            st.rerun()


def render_chat():
    chat_html = '<div id="chatContainer" class="chat-container-custom">'
    for msg in st.session_state.messages:
        content = msg["content"].replace("\n", "<br>")
        if msg["role"] == "user":
            chat_html += f'<div class="user-message">{content}</div>'
        else:
            chat_html += f'<div class="assistant-message">{content}</div>'
    chat_html += '<div id="chat-bottom-anchor"></div>'
    chat_html += '</div>'
    return chat_html


def scroll_bottom():
    st.components.v1.html("""
    <script>
        function scrollToAnchor() {
            var anchor = document.getElementById('chat-bottom-anchor');
            if (anchor) {
                anchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
        }
        setTimeout(scrollToAnchor, 100);
        setTimeout(scrollToAnchor, 300);
        setTimeout(scrollToAnchor, 500);
    </script>
    """, height=0)


# --- ИНИЦИАЛИЗАЦИЯ ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant",
                                  "content": "Добро пожаловать!\n\nЗагрузите Excel-файлы, затем нажмите кнопку с названием промпта."}]

if "processing" not in st.session_state:
    st.session_state.processing = False

if "action" not in st.session_state:
    st.session_state.action = None

if "action_prompt_name" not in st.session_state:
    st.session_state.action_prompt_name = None

if "files" not in st.session_state:
    st.session_state.files = []

left_col, center_col, right_col = st.columns([1.2, 3, 1.2])

# ==================== ЛЕВАЯ КОЛОНКА ====================
with left_col:
    st.markdown("### Настройки")

    key_status = get_key_status()

    if not key_status["gigachat"]["present"]:
        st.error("GigaChat: ключ не найден")
        model_choice = "GigaChat"
    else:
        model_choice = st.selectbox(
            "Выберите нейросеть:",
            ["GigaChat", "DeepSeek"],
            index=0,
            disabled=st.session_state.processing
        )

    st.divider()

    st.markdown("### Статус API")

    if key_status["gigachat"]["present"]:
        st.success("GigaChat: ключ есть")
    else:
        st.error("GigaChat: нет ключа")

    if key_status["deepseek"]["present"]:
        st.success("DeepSeek: ключ есть")
        st.caption("Нужен пополненный баланс")
    else:
        st.warning("DeepSeek: нет ключа")

    st.divider()

    token = get_github_token()
    if token:
        st.success("GitHub: токен настроен")
        owner, repo = get_repo_info()
        st.caption(f"{owner}/{repo}")
    else:
        st.error("GitHub: токен не настроен")

    st.divider()

    uploaded_files = st.file_uploader(
        "Загрузите Excel-файлы",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        disabled=st.session_state.processing
    )

    if uploaded_files:
        st.session_state.files = uploaded_files

    files = st.session_state.get("files", [])

    if files:
        st.success(f"Загружено {len(files)} файлов")
        etalon, answers = detect_files_pairs(files)
        if etalon:
            st.caption(f"Эталон: {etalon.name[:30]}")
        if answers:
            st.caption(f"Ответы: {answers.name[:30]}")
    else:
        st.info("Ожидание файлов...")

# ==================== ЦЕНТРАЛЬНАЯ КОЛОНКА ====================
with center_col:
    st.markdown("### Результаты анализа")

    chat_placeholder = st.empty()
    chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
    scroll_bottom()

    if prompt := st.chat_input("Или задайте свой вопрос по данным...", disabled=st.session_state.processing):
        files = st.session_state.get("files", [])

        if not files:
            st.error("Сначала загрузите Excel-файлы")
        else:
            context = ""
            for f in files:
                df = pd.read_excel(f)
                file_type = "Эталон" if detect_file_type(f.name) == "etalon" else "Ответы" if detect_file_type(
                    f.name) == "answers" else "Другой"
                context += f"\n\n=== {file_type}: {f.name} ===\n"
                context += f"Строк: {df.shape[0]}, Столбцов: {df.shape[1]}\n"
                context += f"Первые 5 строк:\n{df.head(5).to_string()}\n"

            full_prompt = f"У меня есть данные:\n{context}\n\nМой вопрос: {prompt}\n\nОтветь, анализируя все предоставленные данные."

            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.spinner(f"Анализирую через {model_choice}..."):
                if model_choice == "GigaChat":
                    answer = call_gigachat(full_prompt)
                else:
                    answer = call_deepseek(full_prompt, os.getenv("DEEPSEEK_KEY"))

                st.session_state.messages.append({"role": "assistant", "content": answer})

            chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
            scroll_bottom()

# ==================== ПРАВАЯ КОЛОНКА ====================
with right_col:
    st.markdown("### Промпты")

    if st.session_state.processing:
        st.warning("Анализ...")

    # Кнопка создания промпта
    token = get_github_token()
    if token:
        if st.button("+ Создать промпт", use_container_width=True, key="create_prompt_btn"):
            create_prompt_dialog()
    else:
        st.info("Для создания промптов настройте GitHub токен")

    st.divider()

    # Получаем список всех промптов
    prompts = get_all_prompts()

    if not prompts:
        st.info("Нет промптов. Нажмите 'Создать промпт' для добавления.")
    else:
        for prompt_name in prompts:
            col_a, col_b, col_c, col_d = st.columns([4, 1, 1, 1])
            with col_a:
                if st.button(prompt_name, use_container_width=True, key=f"btn_{prompt_name}",
                             disabled=st.session_state.processing):
                    st.session_state.action = "run_prompt"
                    st.session_state.action_prompt_name = prompt_name
                    st.session_state.processing = True
                    st.rerun()
            with col_b:
                if st.button("👁️", key=f"view_{prompt_name}", help="Просмотреть промпт"):
                    view_prompt_dialog(prompt_name)
            with col_c:
                if st.button("✏️", key=f"edit_{prompt_name}", help="Редактировать промпт"):
                    edit_prompt_dialog(prompt_name)
            with col_d:
                if st.button("🗑️", key=f"delete_{prompt_name}", help="Удалить промпт"):
                    delete_prompt_dialog(prompt_name)

    st.divider()

    with st.expander("О программе"):
        st.markdown("""
        AI Агент для анализа тестов

        1. Загрузите Excel-файлы
        2. Нажмите на кнопку промпта
        3. Получите анализ
        """)

# --- ОБРАБОТКА ДЕЙСТВИЙ (ЗАПУСК ПРОМПТА) ---
if st.session_state.action == "run_prompt" and st.session_state.processing:
    prompt_name = st.session_state.action_prompt_name
    files = st.session_state.get("files", [])

    if not files:
        st.session_state.messages.append({"role": "assistant", "content": "Сначала загрузите файлы."})
        st.session_state.action = None
        st.session_state.action_prompt_name = None
        st.session_state.processing = False
        st.rerun()

    etalon, answers = detect_files_pairs(files)

    if etalon is None:
        st.session_state.messages.append(
            {"role": "assistant", "content": "Не найден эталон. Добавьте в название файла: эталон, etalon, ключ"})
        st.session_state.action = None
        st.session_state.action_prompt_name = None
        st.session_state.processing = False
        st.rerun()

    if answers is None:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "Не найдены ответы. Добавьте в название файла: ответы, answers, пользователь"})
        st.session_state.action = None
        st.session_state.action_prompt_name = None
        st.session_state.processing = False
        st.rerun()

    etalon_info = format_file_info(etalon, "Эталон")
    answers_info = format_file_info(answers, "Ответы")

    try:
        answers_df = pd.read_excel(answers)
        basic_stats = get_basic_stats_from_df(answers_df)
    except Exception as e:
        basic_stats = f"Не удалось вычислить статистику: {e}"

    prompt = load_prompt(prompt_name, etalon_info, answers_info, basic_stats)

    st.session_state.messages.append({"role": "user", "content": f"Запрос: {prompt_name}"})
    st.session_state.messages.append(
        {"role": "assistant", "content": f"Анализируемые файлы:\n- Эталон: {etalon.name}\n- Ответы: {answers.name}"})

    with st.spinner(f"Выполняется {prompt_name}..."):
        if model_choice == "GigaChat":
            answer = call_gigachat(prompt)
        else:
            answer = call_deepseek(prompt, os.getenv("DEEPSEEK_KEY"))

        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.action = None
    st.session_state.action_prompt_name = None
    st.session_state.processing = False
    st.rerun()