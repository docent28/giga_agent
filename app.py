import streamlit as st
from gigachat import GigaChat
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GIGACHAT_KEY")

st.set_page_config(page_title="AI Excel Analyzer - Чат")
st.title("🤖 AI Агент для анализа Excel (Чат-версия)")


# Инициализация
@st.cache_resource
def init_giga():
    return GigaChat(credentials=API_KEY, verify_ssl_certs=False, timeout=60)


giga = init_giga()

# Загрузка нескольких файлов (как раньше)
uploaded_files = st.file_uploader(
    "📂 Загрузите Excel-файлы",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

# Сохраняем загруженные файлы в session_state
if uploaded_files:
    st.session_state["files"] = uploaded_files
    st.success(f"✅ Загружено {len(uploaded_files)} файлов")

    # Показываем превью каждого файла
    for file in uploaded_files:
        df = pd.read_excel(file)
        with st.expander(f"📊 {file.name} ({df.shape[0]} строк, {df.shape[1]} столбцов)"):
            st.dataframe(df.head(3))
else:
    st.info("📁 Загрузите один или несколько Excel-файлов для начала работы")

# История сообщений
if "messages" not in st.session_state:
    st.session_state.messages = []

# Отображаем историю
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Поле для ввода сообщения
if prompt := st.chat_input("Введите ваш вопрос по загруженным данным..."):
    if not uploaded_files and "files" not in st.session_state:
        st.error("Сначала загрузите Excel-файлы")
    else:
        # Берём файлы из session_state или из текущей загрузки
        files = uploaded_files if uploaded_files else st.session_state.get("files", [])

        # Добавляем вопрос пользователя
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Формируем контекст из ВСЕХ загруженных файлов
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

        # Отправляем в GigaChat
        with st.chat_message("assistant"):
            with st.spinner("Анализирую все файлы..."):
                try:
                    response = giga.chat(full_prompt)
                    answer = response.choices[0].message.content
                    st.write(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Ошибка: {e}")
                    st.info("Попробуйте задать вопрос проще или перезагрузите страницу")