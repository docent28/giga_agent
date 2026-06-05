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
st.title("🤖 AI Агент для анализа Excel (Чат-версия)")

# --- БОКОВАЯ ПАНЕЛЬ ДЛЯ ВЫБОРА МОДЕЛИ ---
with st.sidebar:
    st.header("⚙️ Настройки")

    # Выбор нейросети
    model_choice = st.selectbox(
        "Выберите нейросеть:",
        ["GigaChat", "DeepSeek"],
        help="GigaChat — от Сбера, DeepSeek — китайская модель"
    )

    # Показываем, какая модель активна
    if model_choice == "GigaChat":
        st.success("🔵 Активна: GigaChat")
    else:
        st.success("🟢 Активна: DeepSeek")

    st.divider()


# --- ИНИЦИАЛИЗАЦИЯ GigaChat (кэшируем) ---
@st.cache_resource
def init_giga():
    return GigaChat(credentials=GIGACHAT_KEY, verify_ssl_certs=False, timeout=60)


# --- УНИВЕРСАЛЬНАЯ ФУНКЦИЯ ДЛЯ ВЫЗОВА ЛЮБОЙ МОДЕЛИ ---
def call_llm(model, full_prompt):
    """
    Вызывает выбранную модель (GigaChat или DeepSeek) с одним промптом
    """
    try:
        if model == "GigaChat":
            giga = init_giga()
            response = giga.chat(full_prompt)
            return response.choices[0].message.content

        elif model == "DeepSeek":
            client = OpenAI(
                api_key=DEEPSEEK_KEY,
                base_url="https://api.deepseek.com",
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content

        else:
            return "Модель не выбрана"

    except Exception as e:
        return f"❌ Ошибка при обращении к {model}: {str(e)}"


# --- ЗАГРУЗКА ФАЙЛОВ ---
uploaded_files = st.file_uploader(
    "📂 Загрузите Excel-файлы",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state["files"] = uploaded_files
    st.success(f"✅ Загружено {len(uploaded_files)} файлов")

    for file in uploaded_files:
        df = pd.read_excel(file)
        with st.expander(f"📊 {file.name} ({df.shape[0]} строк, {df.shape[1]} столбцов)"):
            st.dataframe(df.head(3))
else:
    st.info("📁 Загрузите один или несколько Excel-файлов для начала работы")

# --- ИСТОРИЯ ЧАТА ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- ПОЛЕ ДЛЯ ВВОДА СООБЩЕНИЯ ---
if prompt := st.chat_input("Введите ваш вопрос по загруженным данным..."):
    if not uploaded_files and "files" not in st.session_state:
        st.error("Сначала загрузите Excel-файлы")
    else:
        files = uploaded_files if uploaded_files else st.session_state.get("files", [])

        # Добавляем вопрос пользователя в историю
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Формируем контекст из всех файлов
        context = ""
        for file in files:
            df = pd.read_excel(file)
            context += f"""

=== Файл: {file.name} ===
- Строк: {df.shape[0]}
- Столбцов: {df.shape[1]}
- Названия столбцов: {list(df.columns)}
- Первые 5 строк данных:
{df.head(5).to_string()}

"""

        full_prompt = f"""
У меня есть несколько Excel-файлов с данными.

{context}

Мой вопрос: {prompt}

Ответь на вопрос, анализируя все предоставленные файлы. Если нужно сравнить файлы между собой — сравнивай.
"""

        # Отправляем в ВЫБРАННУЮ модель
        with st.chat_message("assistant"):
            with st.spinner(f"Анализирую все файлы через {model_choice}..."):
                answer = call_llm(model_choice, full_prompt)
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})