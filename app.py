import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from utils.file_utils import detect_file_type, detect_files_pairs, format_file_info, get_basic_stats_from_df
from utils.prompt_utils import (
    load_prompt, get_edited_prompt_content, save_edited_prompt,
    clear_edited_prompt, get_local_prompt_content
)
from utils.llm_utils import call_gigachat, call_deepseek, get_key_status
from utils.github_utils import update_file_on_github, get_file_from_github

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

if "edit_prompt" not in st.session_state:
    st.session_state.edit_prompt = None

if "test_mode" not in st.session_state:
    st.session_state.test_mode = None


# --- ФУНКЦИЯ ДЛЯ СОЗДАНИЯ КНОПОК С РЕДАКТИРОВАНИЕМ ---
def create_action_with_edit(label, action_name, key):
    """Создаёт кнопку анализа и кнопку редактирования промпта рядом"""
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        btn = st.button(label, use_container_width=True, disabled=st.session_state.processing, key=f"btn_{key}")
    with col2:
        edit_btn = st.button("✏️", key=f"edit_{key}", help="Редактировать промпт", disabled=st.session_state.processing)
    with col3:
        if st.session_state.edit_prompt == action_name:
            clear_btn = st.button("✖️", key=f"clear_{key}", help="Отменить редактирование")
            if clear_btn:
                clear_edited_prompt(action_name)
                st.session_state.edit_prompt = None
                st.rerun()

    if edit_btn:
        st.session_state.edit_prompt = action_name
        st.rerun()

    return btn


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

    btn_compare = create_action_with_edit("📊 Сравнить ответы с эталоном", "compare", "compare")
    btn_time = create_action_with_edit("⏱️ Анализ времени выполнения", "time", "time")
    btn_critical = create_action_with_edit("⚠️ Выявить критические изменения", "critical", "critical")
    btn_report = create_action_with_edit("📄 Сформировать полный отчёт", "report", "report")

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

        **Редактирование промптов:**
        - Нажмите ✏️ для редактирования
        - Измените текст
        - Нажмите 🧪 Тестировать
        - Если нравится → 💾 Сохранить в GitHub
        """)

# --- ОСНОВНАЯ ОБЛАСТЬ ---

# --- РЕДАКТОР ПРОМПТА ---
if st.session_state.edit_prompt:
    prompt_name = st.session_state.edit_prompt
    prompt_names_display = {
        "compare": "compare.txt - Сравнение ответов с эталоном",
        "time": "time.txt - Анализ времени выполнения",
        "critical": "critical.txt - Выявление критических изменений",
        "report": "report.txt - Формирование полного отчёта"
    }

    st.subheader(f"✏️ Редактирование промпта: {prompt_names_display.get(prompt_name, prompt_name)}")

    # Получаем текущее содержимое
    current_content = get_edited_prompt_content(prompt_name)

    # Поле для редактирования
    new_content = st.text_area(
        "Редактируйте промпт. Используйте переменные: {etalon_info}, {answers_info}, {basic_stats}",
        value=current_content,
        height=400,
        key="prompt_editor"
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if st.button("💾 Сохранить временно", use_container_width=True):
            save_edited_prompt(prompt_name, new_content)
            st.success("✅ Промпт временно сохранён! Теперь можно тестировать.")
            st.rerun()

    with col2:
        if st.button("🧪 Тестировать", use_container_width=True):
            save_edited_prompt(prompt_name, new_content)
            st.session_state.test_mode = prompt_name
            st.session_state.edit_prompt = None
            st.rerun()

    with col3:
        # Кнопка сохранения в GitHub (требует токен)
        github_token = None
        try:
            github_token = st.secrets.get("GITHUB_TOKEN")
        except:
            pass

        if github_token:
            if st.button("💾 Сохранить в GitHub", use_container_width=True):
                save_edited_prompt(prompt_name, new_content)
                # Сохраняем в GitHub
                file_path = f"prompts/{prompt_name}.txt"
                success, message = update_file_on_github(
                    file_path,
                    new_content,
                    f"Обновлён промпт {prompt_name} через Streamlit агента"
                )
                if success:
                    st.success(message)
                    # Очищаем временную версию после успешного сохранения
                    clear_edited_prompt(prompt_name)
                else:
                    st.error(message)
                st.rerun()
        else:
            st.button("💾 Сохранить в GitHub", use_container_width=True, disabled=True,
                      help="GitHub токен не настроен. Добавьте GITHUB_TOKEN в Secrets.")

    with col4:
        if st.button("✖️ Отмена", use_container_width=True):
            st.session_state.edit_prompt = None
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

# --- ТЕСТОВЫЙ РЕЖИМ (запуск с отредактированным промптом) ---
if st.session_state.test_mode:
    action = st.session_state.test_mode
    files = st.session_state.get("files", [])

    if not files:
        st.error("❌ Сначала загрузите Excel-файлы")
        st.session_state.test_mode = None
        st.rerun()

    etalon, answers = detect_files_pairs(files)

    if etalon is None or answers is None:
        st.error("❌ Не найдены эталон или ответы")
        st.session_state.test_mode = None
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
        "compare": "Сравнение ответов с эталоном (ТЕСТОВЫЙ РЕЖИМ)",
        "time": "Анализ времени выполнения (ТЕСТОВЫЙ РЕЖИМ)",
        "critical": "Выявление критических изменений (ТЕСТОВЫЙ РЕЖИМ)",
        "report": "Формирование полного отчёта (ТЕСТОВЫЙ РЕЖИМ)"
    }
    action_name = action_names.get(action, f"{action} (ТЕСТОВЫЙ РЕЖИМ)")

    st.session_state.messages.append({"role": "user", "content": f"🧪 {action_name}"})
    st.session_state.messages.append({"role": "assistant",
                                      "content": f"**Используется ОТРЕДАКТИРОВАННАЯ версия промпта**\n\n**Анализируемые файлы:**\n- 📖 Эталон: {etalon.name}\n- 📝 Ответы: {answers.name}"})

    with st.spinner(f"Выполняется {action_name} через {model_choice}..."):
        if model_choice == "GigaChat":
            if not key_status["gigachat"]["present"]:
                answer = "❌ Ключ GigaChat не найден."
            else:
                answer = call_gigachat(prompt)
        else:
            answer = call_deepseek(prompt, os.getenv("DEEPSEEK_KEY"))

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.messages.append({"role": "assistant",
                                          "content": "💡 **Результат получен с использованием ОТРЕДАКТИРОВАННОГО промпта.**\n\nЕсли результат устраивает, нажмите ✏️ → 💾 Сохранить в GitHub, чтобы сохранить изменения навсегда."})

    st.session_state.test_mode = None
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