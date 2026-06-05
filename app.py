import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Импорты из наших модулей
from utils.file_utils import detect_file_type, detect_files_pairs, format_file_info, get_basic_stats_from_df
from utils.prompt_utils import load_prompt, get_prompt_preview, get_full_prompt_text
from utils.llm_utils import call_gigachat, call_deepseek, get_key_status

load_dotenv()

st.set_page_config(page_title="AI Excel Analyzer - Чат", page_icon="🤖")
st.title("🤖 AI Агент для анализа результатов тестов")

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant",
                                  "content": "👋 Добро пожаловать!\n\nЗагрузите Excel-файлы, затем нажмите одну из кнопок в боковой панели."}]

if "processing" not in st.session_state:
    st.session_state.processing = False

if "action" not in st.session_state:
    st.session_state.action = None

if "show_prompt" not in st.session_state:
    st.session_state.show_prompt = None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")

    # Получаем статус ключей
    key_status = get_key_status()

    # Выбор модели (только GigaChat, если нет ключа)
    if not key_status["gigachat"]["present"]:
        model_choice = "GigaChat (нет ключа)"
        model_disabled = True
    else:
        model_choice = st.selectbox(
            "Выберите нейросеть:",
            ["GigaChat", "DeepSeek"],
            index=0,
            disabled=st.session_state.processing
        )
        model_disabled = False

    st.divider()

    # --- СТАТУС ВСЕХ КЛЮЧЕЙ ---
    st.subheader("🔑 Статус API ключей")

    # GigaChat статус
    if key_status["gigachat"]["present"]:
        st.success("✅ **GigaChat:** ключ загружен")
    else:
        st.error("❌ **GigaChat:** ключ не найден")
        st.caption("Добавьте GIGACHAT_KEY в файл .env")

    # DeepSeek статус
    if key_status["deepseek"]["present"]:
        st.success("✅ **DeepSeek:** ключ загружен")
        st.caption("💡 Для работы нужен пополненный баланс")
    else:
        st.warning("⚠️ **DeepSeek:** ключ не найден")
        st.caption("Добавьте DEEPSEEK_KEY в файл .env")

    st.divider()

    # --- БЫСТРЫЙ АНАЛИЗ ---
    st.subheader("🎯 Быстрый анализ")

    if st.session_state.processing:
        st.warning("⏳ Анализ выполняется... Пожалуйста, подождите.")


    # Функция для создания кнопок с возможностью просмотра промпта
    def create_action_button(label, action_name, key):
        col1, col2 = st.columns([3, 1])
        with col1:
            btn = st.button(label, use_container_width=True, disabled=st.session_state.processing, key=f"btn_{key}")
        with col2:
            show_btn = st.button("📄", key=f"show_{key}", help="Показать промпт", disabled=st.session_state.processing)

        if show_btn:
            st.session_state.show_prompt = action_name
            st.rerun()

        return btn


    btn_compare = create_action_button("📊 Сравнить ответы с эталоном", "compare", "compare")
    btn_time = create_action_button("⏱️ Анализ времени выполнения", "time", "time")
    btn_critical = create_action_button("⚠️ Выявить критические изменения", "critical", "critical")
    btn_report = create_action_button("📄 Сформировать полный отчёт", "report", "report")

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

    # --- ИНФОРМАЦИЯ ---
    with st.expander("ℹ️ О программе"):
        st.markdown("""
        **AI Агент для анализа результатов тестов**

        - Анализирует ответы пользователей
        - Сравнивает с эталоном
        - Выявляет аномалии времени
        - Формирует отчёты

        **Промпты** хранятся в папке `prompts/`
        - compare.txt - сравнение ответов
        - time.txt - анализ времени
        - critical.txt - критические изменения
        - report.txt - полный отчёт
        """)

# --- ОСНОВНАЯ ОБЛАСТЬ ---

# --- ПРОСМОТР ПРОМПТА (если открыт) ---
if st.session_state.show_prompt:
    prompt_names = {
        "compare": "compare.txt - Сравнение ответов",
        "time": "time.txt - Анализ времени",
        "critical": "critical.txt - Критические изменения",
        "report": "report.txt - Полный отчёт"
    }

    with st.expander(f"📄 Промпт: {prompt_names.get(st.session_state.show_prompt, st.session_state.show_prompt)}",
                     expanded=True):
        prompt_text = get_full_prompt_text(st.session_state.show_prompt)
        st.code(prompt_text, language="text")

        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Закрыть"):
                st.session_state.show_prompt = None
                st.rerun()

    st.divider()

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

# --- ОБРАБОТКА ДЕЙСТВИЙ ---
if st.session_state.action is not None and st.session_state.processing:

    action = st.session_state.action
    files = st.session_state.get("files", [])

    # Проверка наличия файлов
    if not files:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "❌ Ошибка: Сначала загрузите Excel-файлы.\n\n💡 Используйте кнопку «Browse files» в верхней части страницы."})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    etalon, answers = detect_files_pairs(files)

    if etalon is None:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "❌ Не найден файл с эталоном.\n\n💡 Добавьте в название слова: эталон, etalon, ключ, правильные ответы"})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    if answers is None:
        st.session_state.messages.append({"role": "assistant",
                                          "content": "❌ Не найден файл с ответами пользователей.\n\n💡 Добавьте в название слова: ответы, answers, пользователь, результаты"})
        st.session_state.action = None
        st.session_state.processing = False
        st.rerun()

    # Форматируем информацию
    etalon_info = format_file_info(etalon, "📖 Файл с эталонными ответами")
    answers_info = format_file_info(answers, "📝 Файл с ответами пользователей")

    try:
        answers_df = pd.read_excel(answers)
        basic_stats = get_basic_stats_from_df(answers_df)
    except Exception as e:
        basic_stats = f"Не удалось вычислить статистику: {e}"

    # Загружаем промпт
    prompt = load_prompt(action, etalon_info, answers_info, basic_stats)

    action_names = {
        "compare": "Сравнение ответов с эталоном",
        "time": "Анализ времени выполнения",
        "critical": "Выявление критических изменений",
        "report": "Формирование полного отчёта"
    }
    action_name = action_names.get(action, action)

    # Добавляем сообщение о начале
    st.session_state.messages.append({"role": "user", "content": f"🔍 {action_name}"})
    st.session_state.messages.append({"role": "assistant",
                                      "content": f"**Анализируемые файлы:**\n- 📖 Эталон: {etalon.name}\n- 📝 Ответы: {answers.name}"})

    # Вызываем нейросеть
    with st.spinner(f"Выполняется {action_name} через {model_choice}..."):
        if model_choice == "GigaChat" or (not key_status["gigachat"]["present"]):
            if not key_status["gigachat"]["present"]:
                answer = "❌ Ключ GigaChat не найден. Добавьте GIGACHAT_KEY в файл .env"
            else:
                answer = call_gigachat(prompt)
        else:
            answer = call_deepseek(prompt, os.getenv("DEEPSEEK_KEY"))

        st.session_state.messages.append({"role": "assistant", "content": answer})

    # Сбрасываем флаги
    st.session_state.action = None
    st.session_state.processing = False
    st.rerun()

# --- ПОЛЕ ДЛЯ РУЧНОГО ВВОДА ---
if prompt := st.chat_input("Или задайте свой вопрос по загруженным данным...", disabled=st.session_state.processing):
    files = st.session_state.get("files", [])

    if not files:
        st.error("❌ Сначала загрузите Excel-файлы")
    else:
        etalon, answers = detect_files_pairs(files)

        context = ""
        for f in files:
            df = pd.read_excel(f)
            file_type = "📖 Эталон" if detect_file_type(f.name) == "etalon" else "📝 Ответы" if detect_file_type(
                f.name) == "answers" else "📄 Другой"
            context += f"\n\n=== {file_type}: {f.name} ===\n"
            context += f"Строк: {df.shape[0]}, Столбцов: {df.shape[1]}\n"
            context += f"Колонки: {list(df.columns)}\n"
            context += f"Первые 5 строк:\n{df.head(5).to_string()}\n"

        full_prompt = f"У меня есть данные:\n{context}\n\nМой вопрос: {prompt}\n\nОтветь, анализируя все предоставленные данные."

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner(f"Анализирую через {model_choice}..."):
            if model_choice == "GigaChat" or (not key_status["gigachat"]["present"]):
                if not key_status["gigachat"]["present"]:
                    answer = "❌ Ключ GigaChat не найден. Добавьте GIGACHAT_KEY в файл .env"
                else:
                    answer = call_gigachat(full_prompt)
            else:
                answer = call_deepseek(full_prompt, os.getenv("DEEPSEEK_KEY"))

            st.session_state.messages.append({"role": "assistant", "content": answer})

        st.rerun()