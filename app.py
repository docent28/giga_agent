import streamlit as st
from gigachat import GigaChat
from openai import OpenAI
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
GIGACHAT_KEY = os.getenv("GIGACHAT_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")

st.set_page_config(page_title="AI Excel Analyzer - Чат", page_icon="🤖")
st.title("🤖 AI Агент для анализа результатов тестов")


# --- ФУНКЦИЯ ЗАГРУЗКИ ПРОМПТА ИЗ ФАЙЛА ---
def load_prompt(prompt_name, etalon_info, answers_info, basic_stats=""):
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


# --- ФУНКЦИИ ОПРЕДЕЛЕНИЯ ТИПОВ ФАЙЛОВ ---
def detect_file_type(filename):
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


# --- ИНИЦИАЛИЗАЦИЯ GigaChat ---
@st.cache_resource
def init_giga():
    return GigaChat(credentials=GIGACHAT_KEY, verify_ssl_certs=False, timeout=60)


def call_gigachat(prompt):
    try:
        giga = init_giga()
        response = giga.chat(prompt)
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка GigaChat: {str(e)[:300]}"


# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant",
                                  "content": "👋 Добро пожаловать!\n\nЗагрузите Excel-файлы, затем нажмите одну из кнопок в боковой панели."}]

if "processing" not in st.session_state:
    st.session_state.processing = False

if "action" not in st.session_state:
    st.session_state.action = None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    model_choice = st.selectbox("Выберите нейросеть:", ["GigaChat", "DeepSeek"], index=0,
                                disabled=st.session_state.processing)

    st.divider()
    st.subheader("🔑 Статус ключей")
    if GIGACHAT_KEY:
        st.success("✅ GigaChat: ключ есть")
    else:
        st.error("❌ GigaChat: нет ключа")

    st.divider()
    st.subheader("🎯 Быстрый анализ")

    if st.session_state.processing:
        st.warning("⏳ Анализ выполняется... Пожалуйста, подождите.")

    # Кнопки с блокировкой
    btn_compare = st.button("📊 Сравнить ответы с эталоном", use_container_width=True,
                            disabled=st.session_state.processing)
    btn_time = st.button("⏱️ Анализ времени выполнения", use_container_width=True, disabled=st.session_state.processing)
    btn_critical = st.button("⚠️ Выявить критические изменения", use_container_width=True,
                             disabled=st.session_state.processing)
    btn_report = st.button("📄 Сформировать полный отчёт", use_container_width=True,
                           disabled=st.session_state.processing)

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

# --- ОСНОВНАЯ ОБЛАСТЬ ---

# Загрузка файлов (СОХРАНЯЕМ В session_state)
uploaded_files = st.file_uploader(
    "📂 Загрузите Excel-файлы (эталоны и ответы пользователей)",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    disabled=st.session_state.processing
)

# ВАЖНО: Сохраняем файлы в session_state при каждой загрузке
if uploaded_files:
    st.session_state.files = uploaded_files

# Проверяем, есть ли файлы в session_state
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
        if model_choice == "GigaChat":
            answer = call_gigachat(prompt)
        else:
            answer = "⚠️ DeepSeek временно отключён. Используйте GigaChat."

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
            if model_choice == "GigaChat":
                answer = call_gigachat(full_prompt)
            else:
                answer = "⚠️ DeepSeek временно отключён. Используйте GigaChat."

            st.session_state.messages.append({"role": "assistant", "content": answer})

        st.rerun()