# utils/llm_utils.py
import streamlit as st
from gigachat import GigaChat
from openai import OpenAI
import os


@st.cache_resource
def init_giga():
    """Инициализация GigaChat с кэшированием"""
    GIGACHAT_KEY = os.getenv("GIGACHAT_KEY")
    return GigaChat(credentials=GIGACHAT_KEY, verify_ssl_certs=False, timeout=60)


def call_gigachat(prompt):
    """Вызов GigaChat API"""
    try:
        giga = init_giga()
        response = giga.chat(prompt)
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка GigaChat: {str(e)[:300]}"


def call_deepseek(prompt, api_key):
    """Вызов DeepSeek API"""
    try:
        if not api_key:
            return "❌ Ключ DeepSeek не найден"
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "402" in error_msg or "Insufficient Balance" in error_msg:
            return "❌ Ошибка DeepSeek: Недостаточно средств на балансе API. Пополните баланс."
        elif "401" in error_msg:
            return "❌ Ошибка DeepSeek: Неверный API-ключ."
        else:
            return f"❌ Ошибка DeepSeek: {error_msg[:200]}"


def get_key_status():
    """Возвращает статус всех API ключей"""
    GIGACHAT_KEY = os.getenv("GIGACHAT_KEY")
    DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")

    status = {
        "gigachat": {
            "present": bool(GIGACHAT_KEY),
            "preview": GIGACHAT_KEY[:10] + "..." if GIGACHAT_KEY and len(GIGACHAT_KEY) > 10 else (
                GIGACHAT_KEY if GIGACHAT_KEY else "отсутствует")
        },
        "deepseek": {
            "present": bool(DEEPSEEK_KEY),
            "preview": DEEPSEEK_KEY[:10] + "..." if DEEPSEEK_KEY and len(DEEPSEEK_KEY) > 10 else (
                DEEPSEEK_KEY if DEEPSEEK_KEY else "отсутствует")
        }
    }
    return status