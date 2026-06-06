import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from utils.file_utils import detect_file_type, detect_files_pairs, format_file_info, get_basic_stats_from_df
from utils.prompt_utils import load_prompt, get_prompt_content
from utils.llm_utils import call_gigachat, call_deepseek, get_key_status

load_dotenv()

st.set_page_config(page_title="AI Excel Analyzer - Чат", page_icon="🤖")
st.title("🤖 AI Агент для анализа результатов тестов")

# --- CSS ДЛЯ КАСТОМИЗАЦИИ st.dialog ---
st.markdown("""
<style>
    /* Кастомизация модального окна */
    div[role="dialog"] {
        width: 50% !important;
        max-width: 800px !important;
        min-width: 300px !important;
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        margin: 0 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
    }

    /* Затемнённый фон */
    div[data-testid="stDialogOverlay"] {
        background-color: rgba(0, 0, 0, 0.5) !important;
    }

    /* Внутренний контент модального окна */
    div[role="dialog"] > div {
        max-height: 80vh !important;
        overflow-y: auto !important;
    }

    /* Код внутри диалога */
    div[role="dialog"] pre {
        font-size: 12px;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)


# --- ФУНКЦИЯ ДЛЯ МОДАЛЬНОГО ОКНА (st.dialog) ---
@st.dialog("📄 Просмотр промпта")
def show_prompt_dialog(prompt_name, display_name):
    """Отображает промпт в модальном окне (центр экрана, ширина 50%)"""
    content = get_prompt_content(prompt_name)

    st.code(content, language="text", line_numbers=False)
    st.caption(f"📁 Файл: {display_name}")
    st.caption("💡 Совет: Вы можете скопировать текст (Ctrl+C) для удобного просмотра")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Закрыть", use_container_width=True):
            st.rerun()


# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant",
                                  "content": "👋 Добро пожаловать!\n\nЗагрузите Excel-файлы, затем нажмите одну из кнопок в боковой панели."}]

if "processing" not in st.session_state:
    st.session_state.processing = False

if "action" not in st.session_state:
    st.session_state.action = None

if "files" not in st.session_state:
    st.session_state.files = []

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")

    key_status = get_key_status()

    if not key_status["gigachat"]["present"]:
        st.error("❌ GigaChat: ключ не найден. Добавьте GIGACHAT_KEY в файл .env")
        model_choice = "GigaChat"
    else:
        model_choice = st.selectbox(
            "Выберите нейросеть:",
            ["GigaChat", "DeepSeek"],
            index=0,
            disabled=st.session_state.processing
        )

    st.divider()

    st.subheader("🔑 Статус API ключей")

    if key_status["gigachat"]["present"]:
        st.success("✅ **GigaChat:** ключ загружен")
    else:
        st.error("❌ **GigaChat:** ключ не найден")
        st.caption("Добавьте GIGACHAT_KEY в файл .env")

    if key_status["deepseek"]["present"]:
        st.success("✅ **DeepSeek:** ключ загружен")
        st.caption("💡 Для работы нужен пополненный баланс")
    else:
        st.warning("⚠️ **DeepSeek:** ключ не найден")
        st.caption("Добавьте DEEPSEEK_KEY в файл .env")

    st.divider()

    st.subheader("🎯 Быстрый анализ")

    if st.session_state.processing:
        st.warning("⏳ Анализ выполняется... Пожалуйста, подождите.")

    # Кнопка 1: Сравнение
    col1, col2 = st.columns([3, 1])
    with col1:
        btn_compare = st.button("📊 Сравнить ответы с эталоном", use_container_width=True,
                                disabled=st.session_state.processing, key="btn_compare")
    with col2:
        if st.button("👁️", key="view_compare", help="Просмотреть промпт"):
            show_prompt_dialog("compare", "compare.txt - Сравнение ответов с эталоном")

    # Кнопка 2: Время
    col1, col2 = st.columns([3, 1])
    with col1:
        btn_time = st.button("⏱️ Анализ времени выполнения", use_container_width=True,
                             disabled=st.session_state.processing, key="btn_time")
    with col2:
        if st.button("👁️", key="view_time", help="Просмотреть промпт"):
            show_prompt_dialog("time", "time.txt - Анализ времени выполнения")

    # Кнопка 3: Критические изменения
    col1, col2 = st.columns([3, 1])
    with col1:
        btn_critical = st.button("⚠️ Выявить критические изменения", use_container_width=True,
                                 disabled=st.session_state.processing, key="btn_critical")
    with col2:
        if st.button("👁️", key="view_critical", help="Просмотреть промпт"):
            show_prompt_dialog("critical", "critical.txt - Выявление критических изменений")

    # Кнопка 4: Полный отчёт
    col1, col2 = st.columns([3, 1])
    with col1:
        btn_report = st.button("📄 Сформировать полный отчёт", use_container_width=True,
                               disabled=st.session_state.processing, key="btn_report")
    with col2:
        if st.button("👁️", key="view_report", help="Просмотреть промпт"):
            show_prompt_dialog("report", "report.txt - Формирование полного отчёта")

    # Обработка нажатий кнопок анализа
    if btn_compare:
        st.session_state.action = "compare"
        st.session_state.processing = True
        st.rerun()

    if btn_time:
        st.session_state.action = "time"
        st.session_state.processing = True
        st.rerun()

    if btn_critical:
        st.session_state.action = "critical"
        st.session_state.processing = True
        st.rerun()

    if btn_report:
        st.session_state.action = "report"
        st.session_state.processing = True
        st.rerun()

    st.divider()

    with st.expander("ℹ️ О программе"):
        st.markdown("""
        **AI Агент для анализа результатов тестов**

        - Анализирует ответы пользователей
        - Сравнивает с эталоном
        - Выявляет аномалии времени
        - Формирует отчёты

        **Просмотр промптов:** нажмите 👁️ рядом с кнопкой анализа
        """)

# --- ОСНОВНАЯ ОБЛАСТЬ ---

# --- ЗАГРУЗКА ФАЙЛОВ ---
uploaded_files = st.file_uploader(
    "📂 Загрузите Excel-файлы (эталоны и ответы пользователей)",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    disabled=st.session_state.processing
)

if uploaded_files:
    st.session_state.files = uploaded_files

files = st.session_state.get("files", [])

if files:
    st.success(f"✅ Загружено {len(files)} файлов")

    etalon, answers = detect_files_pairs(files)

    col1, col2 = st.columns(2)
    with col1:
        if etalon:
            st.info(f"📖 **Эталон:** {etalon.name}")
        else:
            st.warning("📖 **Эталон не определён**")
    with col2:
        if answers:
            st.info(f"📝 **Ответы:** {answers.name}")
        else:
            st.warning("📝 **Ответы не определены**")

    for f in files:
        df = pd.read_excel(f)
        emoji = "📖" if detect_file_type(f.name) == "etalon" else "📝" if detect_file_type(f.name) == "answers" else "📄"
        with st.expander(f"{emoji} {f.name} ({df.shape[0]} строк, {df.shape[1]} столбцов)"):
            st.dataframe(df.head(3))
else:
    st.info("📁 Ожидание загрузки файлов...")

# --- ИСТОРИЯ ЧАТА ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- ОБРАБОТКА ДЕЙСТВИЙ (АНАЛИЗ) ---
if st.session_state.action is not None and st.session_state.processing:

    action = st.session_state.action
    files = st.session_state.get("files", [])

    if not files:
        st.session_state.messages.append({"role": "assistant", "content": "❌ Ошибка: Сначала загрузите Excel-файлы."})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    etalon, answers = detect_files_pairs(files)

    if etalon is None:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "❌ Не найден файл с эталоном.\n\n💡 Добавьте в название слова: эталон, etalon, ключ"})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    if answers is None:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "❌ Не найден файл с ответами пользователей.\n\n💡 Добавьте в название слова: ответы, answers"})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    etalon_info = format_file_info(etalon, "📖 Файл с эталонными ответами")
    answers_info = format_file_info(answers, "📝 Файл с ответами пользователей")

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

    with st.spinner(f"Выполняется {action_name} через {model_choice}..."):
        if model_choice == "GigaChat":
            if not key_status["gigachat"]["present"]:
                answer = "❌ Ключ GigaChat не найден."
            else:
                answer = call_gigachat(prompt)
        else:
            answer = call_deepseek(prompt, os.getenv("DEEPSEEK_KEY"))

        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.session_state.action = None
    st.session_state.processing = False
    st.rerun()

# --- ПОЛЕ ДЛЯ РУЧНОГО ВВОДА ---
if prompt := st.chat_input("Или задайте свой вопрос по загруженным данным...", disabled=st.session_state.processing):
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
                if not key_status["gigachat"]["present"]:
                    answer = "❌ Ключ GigaChat не найден."
                else:
                    answer = call_gigachat(full_prompt)
            else:
                answer = call_deepseek(full_prompt, os.getenv("DEEPSEEK_KEY"))

            st.session_state.messages.append({"role": "assistant", "content": answer})

        st.rerun()