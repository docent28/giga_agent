import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from utils.file_utils import detect_file_type, detect_files_pairs, format_file_info, get_basic_stats_from_df
from utils.prompt_utils import load_prompt, get_prompt_content, save_prompt_to_local
from utils.llm_utils import call_gigachat, call_deepseek, get_key_status
from utils.github_utils import update_file_on_github, get_github_token, get_repo_info

load_dotenv()

st.set_page_config(page_title="AI Excel Analyzer - Чат", page_icon="🤖", layout="wide")
st.title("🤖 AI Агент для анализа результатов тестов")

# --- CSS ДЛЯ КАСТОМИЗАЦИИ ---
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
    }
    div[data-testid="stDialogOverlay"] {
        background-color: rgba(0, 0, 0, 0.5) !important;
    }
    div[role="dialog"] > div {
        max-height: 85vh !important;
        overflow-y: auto !important;
    }
    div[role="dialog"] pre, div[role="dialog"] textarea {
        font-size: 12px;
        font-family: monospace;
    }
    .stChatMessage {
        max-width: 100% !important;
    }
    .fixed-chat-container {
        height: calc(100vh - 280px);
        overflow-y: auto;
        padding-right: 10px;
    }
    @media (max-width: 768px) {
        .stColumn {
            min-width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# --- ФУНКЦИЯ ДЛЯ ПРОСМОТРА ПРОМПТА ---
@st.dialog("📄 Просмотр промпта")
def view_prompt_dialog(prompt_name, display_name):
    content = get_prompt_content(prompt_name)
    st.code(content, language="text", line_numbers=False)
    st.caption(f"📁 Файл: {display_name}")
    if st.button("Закрыть", use_container_width=True):
        st.rerun()


# --- ФУНКЦИЯ ДЛЯ РЕДАКТИРОВАНИЯ ПРОМПТА ---
@st.dialog("✏️ Редактирование промпта")
def edit_prompt_dialog(prompt_name, display_name):
    content_key = f"edit_content_{prompt_name}"
    if content_key not in st.session_state:
        st.session_state[content_key] = get_prompt_content(prompt_name)

    st.caption("📁 " + display_name)

    new_content = st.text_area(
        "Редактируйте промпт:",
        value=st.session_state[content_key],
        height=400,
        key=f"textarea_{prompt_name}",
        help="Используйте переменные: {etalon_info}, {answers_info}, {basic_stats}"
    )
    st.session_state[content_key] = new_content
    st.caption("💡 Переменные: {etalon_info}, {answers_info}, {basic_stats}")
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 Копировать", use_container_width=True):
            st.toast("Промпт скопирован!", icon="📋")

    with col2:
        token = get_github_token()
        if token:
            if st.button("💾 Сохранить в GitHub", use_container_width=True):
                file_path = f"prompts/{prompt_name}.txt"
                success, message = update_file_on_github(
                    file_path,
                    st.session_state[content_key],
                    f"Обновлён промпт {prompt_name} через Streamlit"
                )
                if success:
                    st.success(message)
                    save_prompt_to_local(prompt_name, st.session_state[content_key])
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.button("💾 Сохранить в GitHub", use_container_width=True, disabled=True)

    with col3:
        if st.button("✖️ Закрыть", use_container_width=True):
            st.session_state.pop(content_key, None)
            st.rerun()


# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant",
                                  "content": "👋 Добро пожаловать!\n\nЗагрузите Excel-файлы, затем нажмите кнопку с названием промпта."}]

if "processing" not in st.session_state:
    st.session_state.processing = False

if "action" not in st.session_state:
    st.session_state.action = None

if "files" not in st.session_state:
    st.session_state.files = []

# --- СОЗДАЁМ ТРИ КОЛОНКИ ---
left_col, center_col, right_col = st.columns([1.2, 3, 1.2])

# ==================== ЛЕВАЯ КОЛОНКА ====================
with left_col:
    st.markdown("### ⚙️ Настройки")

    key_status = get_key_status()

    if not key_status["gigachat"]["present"]:
        st.error("❌ GigaChat: ключ не найден")
        model_choice = "GigaChat"
    else:
        model_choice = st.selectbox(
            "Выберите нейросеть:",
            ["GigaChat", "DeepSeek"],
            index=0,
            disabled=st.session_state.processing
        )

    st.divider()

    st.markdown("### 🔑 Статус API")

    if key_status["gigachat"]["present"]:
        st.success("✅ GigaChat: ключ есть")
    else:
        st.error("❌ GigaChat: нет ключа")

    if key_status["deepseek"]["present"]:
        st.success("✅ DeepSeek: ключ есть")
        st.caption("💡 Нужен пополненный баланс")
    else:
        st.warning("⚠️ DeepSeek: нет ключа")

    st.divider()

    token = get_github_token()
    if token:
        st.success("✅ GitHub: токен настроен")
        owner, repo = get_repo_info()
        st.caption(f"📁 {owner}/{repo}")
    else:
        st.error("❌ GitHub: токен не настроен")

    st.divider()

    # Загрузка файлов
    uploaded_files = st.file_uploader(
        "📂 Загрузите Excel-файлы",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        disabled=st.session_state.processing
    )

    if uploaded_files:
        st.session_state.files = uploaded_files

    files = st.session_state.get("files", [])

    if files:
        st.success(f"✅ {len(files)} файлов")
        etalon, answers = detect_files_pairs(files)
        if etalon:
            st.caption(f"📖 Эталон: {etalon.name[:30]}")
        if answers:
            st.caption(f"📝 Ответы: {answers.name[:30]}")
    else:
        st.info("Ожидание файлов...")

# ==================== ЦЕНТРАЛЬНАЯ КОЛОНКА ====================
with center_col:
    st.markdown("### 💬 Результаты анализа")

    # Контейнер для сообщений с фиксированной высотой
    with st.container():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Пустое пространство для прижатия поля ввода вниз (работает через CSS)
    st.markdown('<div style="flex: 1;"></div>', unsafe_allow_html=True)

    # Поле для ручного ввода (вне контейнера, будет внизу)
    if prompt := st.chat_input("Или задайте свой вопрос по данным...", disabled=st.session_state.processing):
        files = st.session_state.get("files", [])

        if not files:
            st.error("❌ Сначала загрузите Excel-файлы")
        else:
            context = ""
            for f in files:
                df = pd.read_excel(f)
                file_type = "📖 Эталон" if detect_file_type(f.name) == "etalon" else "📝 Ответы" if detect_file_type(
                    f.name) == "answers" else "📄 Другой"
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

            st.rerun()

# ==================== ПРАВАЯ КОЛОНКА ====================
with right_col:
    st.markdown("### 🎯 Промпты")

    if st.session_state.processing:
        st.warning("⏳ Анализ...")

    # Строка 1: Сравнение ответов
    col_a, col_b, col_c = st.columns([4, 1, 1])
    with col_a:
        btn_compare = st.button("📊 Сравнить ответы", use_container_width=True, disabled=st.session_state.processing,
                                key="btn_compare")
    with col_b:
        if st.button("👁️", key="view_compare", help="Просмотреть промпт"):
            view_prompt_dialog("compare", "compare.txt")
    with col_c:
        if st.button("✏️", key="edit_compare", help="Редактировать промпт"):
            edit_prompt_dialog("compare", "compare.txt")

    if btn_compare:
        st.session_state.action = "compare"
        st.session_state.processing = True
        st.rerun()

    # Строка 2: Анализ времени
    col_a, col_b, col_c = st.columns([4, 1, 1])
    with col_a:
        btn_time = st.button("⏱️ Анализ времени", use_container_width=True, disabled=st.session_state.processing,
                             key="btn_time")
    with col_b:
        if st.button("👁️", key="view_time", help="Просмотреть промпт"):
            view_prompt_dialog("time", "time.txt")
    with col_c:
        if st.button("✏️", key="edit_time", help="Редактировать промпт"):
            edit_prompt_dialog("time", "time.txt")

    if btn_time:
        st.session_state.action = "time"
        st.session_state.processing = True
        st.rerun()

    # Строка 3: Критические изменения
    col_a, col_b, col_c = st.columns([4, 1, 1])
    with col_a:
        btn_critical = st.button("⚠️ Критические изменения", use_container_width=True,
                                 disabled=st.session_state.processing, key="btn_critical")
    with col_b:
        if st.button("👁️", key="view_critical", help="Просмотреть промпт"):
            view_prompt_dialog("critical", "critical.txt")
    with col_c:
        if st.button("✏️", key="edit_critical", help="Редактировать промпт"):
            edit_prompt_dialog("critical", "critical.txt")

    if btn_critical:
        st.session_state.action = "critical"
        st.session_state.processing = True
        st.rerun()

    # Строка 4: Полный отчёт
    col_a, col_b, col_c = st.columns([4, 1, 1])
    with col_a:
        btn_report = st.button("📄 Полный отчёт", use_container_width=True, disabled=st.session_state.processing,
                               key="btn_report")
    with col_b:
        if st.button("👁️", key="view_report", help="Просмотреть промпт"):
            view_prompt_dialog("report", "report.txt")
    with col_c:
        if st.button("✏️", key="edit_report", help="Редактировать промпт"):
            edit_prompt_dialog("report", "report.txt")

    if btn_report:
        st.session_state.action = "report"
        st.session_state.processing = True
        st.rerun()

    st.divider()

    with st.expander("ℹ️ О программе"):
        st.markdown("""
        **AI Агент**

        1. Загрузите Excel-файлы
        2. Нажмите на кнопку промпта
        3. Получите анализ
        """)

# --- ОБРАБОТКА ДЕЙСТВИЙ (АНАЛИЗ) ---
if st.session_state.action is not None and st.session_state.processing:
    action = st.session_state.action
    files = st.session_state.get("files", [])

    if not files:
        st.session_state.messages.append({"role": "assistant", "content": "❌ Сначала загрузите файлы."})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    etalon, answers = detect_files_pairs(files)

    if etalon is None:
        st.session_state.messages.append(
            {"role": "assistant", "content": "❌ Не найден эталон. Добавьте в название файла: эталон, etalon, ключ"})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    if answers is None:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "❌ Не найдены ответы. Добавьте в название файла: ответы, answers, пользователь"})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    etalon_info = format_file_info(etalon, "📖 Эталон")
    answers_info = format_file_info(answers, "📝 Ответы")

    try:
        answers_df = pd.read_excel(answers)
        basic_stats = get_basic_stats_from_df(answers_df)
    except Exception as e:
        basic_stats = f"Не удалось вычислить статистику: {e}"

    prompt = load_prompt(action, etalon_info, answers_info, basic_stats)

    action_names = {
        "compare": "Сравнение ответов с эталоном",
        "time": "Анализ времени выполнения",
        "critical": "Выявление критических изменений",
        "report": "Формирование полного отчёта"
    }
    action_name = action_names.get(action, action)

    st.session_state.messages.append({"role": "user", "content": f"🔍 {action_name}"})
    st.session_state.messages.append({"role": "assistant",
                                      "content": f"**Анализируемые файлы:**\n- 📖 Эталон: {etalon.name}\n- 📝 Ответы: {answers.name}"})

    with st.spinner(f"Выполняется {action_name}..."):
        if model_choice == "GigaChat":
            answer = call_gigachat(prompt)
        else:
            answer = call_deepseek(prompt, os.getenv("DEEPSEEK_KEY"))

        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.action = None
    st.session_state.processing = False
    st.rerun()