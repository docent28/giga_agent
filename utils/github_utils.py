# utils/github_utils.py
import base64
import requests
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()


def get_github_token():
    """
    Получает GitHub токен.
    Локально: из .env файла (переменная GITHUB_TOKEN)
    Streamlit Cloud: из st.secrets
    """
    # Пробуем получить из st.secrets (для Streamlit Cloud)
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if token:
            return token
    except:
        pass

    # Пробуем получить из .env (для локальной разработки)
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    return None


def get_repo_info():
    """
    Определяет владельца и название репозитория.
    Можно указать в .env переменные GITHUB_OWNER и GITHUB_REPO
    """
    # Пробуем получить из переменных окружения
    owner = os.getenv("GITHUB_OWNER", "")
    repo = os.getenv("GITHUB_REPO", "")

    if owner and repo:
        return owner, repo

    # Если не указаны, пробуем получить из GITHUB_REPOSITORY (для Streamlit Cloud)
    repo_full = os.getenv("GITHUB_REPOSITORY", "")
    if repo_full:
        parts = repo_full.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]

    # ЗНАЧЕНИЯ ПО УМОЛЧАНИЮ - ЗАМЕНИТЕ НА ВАШИ!
    # ВАЖНО: Укажите здесь ваш логин и название репозитория
    return "docent28", "giga_agent"


def get_file_from_github(file_path, branch="main"):
    """
    Получает содержимое файла из GitHub репозитория
    """
    token = get_github_token()
    if not token:
        return None, "❌ GitHub токен не найден. Добавьте GITHUB_TOKEN в .env или Secrets."

    owner, repo = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            sha = data["sha"]
            return {"content": content, "sha": sha}, None
        elif response.status_code == 404:
            return None, f"Файл {file_path} не найден в репозитории"
        else:
            return None, f"Ошибка GitHub API: {response.status_code}"
    except Exception as e:
        return None, f"Ошибка: {e}"


def update_file_on_github(file_path, content, commit_message, branch="main"):
    """
    Обновляет или создаёт файл в GitHub репозитории
    """
    token = get_github_token()
    if not token:
        return False, "❌ GitHub токен не найден. Добавьте GITHUB_TOKEN в .env или Secrets."

    owner, repo = get_repo_info()

    # Проверяем, что owner и repo не содержат значения по умолчанию
    if owner == "ВАШ_ЛОГИН" or repo == "ВАШ_РЕПОЗИТОРИЙ":
        return False, "❌ Не настроены данные репозитория. Укажите GITHUB_OWNER и GITHUB_REPO в .env"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Кодируем содержимое в base64
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    # Пытаемся получить текущий SHA (если файл существует)
    existing_file, _ = get_file_from_github(file_path, branch)
    sha = existing_file["sha"] if existing_file else None

    data = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    try:
        response = requests.put(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            return True, "✅ Файл успешно сохранён в GitHub"
        else:
            return False, f"❌ Ошибка сохранения: {response.status_code}"
    except Exception as e:
        return False, f"❌ Ошибка: {e}"