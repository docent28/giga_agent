# utils/github_utils.py
import base64
import requests
import streamlit as st


def get_github_token():
    """Получает GitHub токен из st.secrets"""
    try:
        return st.secrets.get("GITHUB_TOKEN")
    except:
        return None


def get_repo_info():
    """Определяет владельца и название репозитория из переменных окружения"""
    import os
    # Пытаемся получить из переменных окружения (можно установить вручную)
    repo_full = os.getenv("GITHUB_REPOSITORY", "")
    if repo_full:
        parts = repo_full.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]

    # Значения по умолчанию - ЗАМЕНИТЕ НА ВАШИ!
    # ВАЖНО: Укажите здесь ваш логин и название репозитория
    return "docent28", "giga_agent"


def get_file_from_github(file_path, branch="main"):
    """
    Получает содержимое файла из GitHub репозитория
    """
    token = get_github_token()
    if not token:
        return None, "❌ GitHub токен не найден. Добавьте GITHUB_TOKEN в Secrets."

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
        return False, "❌ GitHub токен не найден. Добавьте GITHUB_TOKEN в Secrets."

    owner, repo = get_repo_info()
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
            return False, f"❌ Ошибка сохранения: {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return False, f"❌ Ошибка: {e}"