# utils/github_utils.py
import base64
import requests
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()


def get_github_token():
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        if token:
            return token
    except:
        pass
    return os.getenv("GITHUB_TOKEN")


def get_repo_info():
    owner = os.getenv("GITHUB_OWNER", "")
    repo = os.getenv("GITHUB_REPO", "")

    if owner and repo:
        return owner, repo

    try:
        owner = st.secrets.get("GITHUB_OWNER", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        if owner and repo:
            return owner, repo
    except:
        pass

    return "", ""


def get_prompt_files():
    """
    Получает список всех .txt файлов из папки prompts/ на GitHub
    Возвращает список имён файлов (без расширения)
    """
    token = get_github_token()
    if not token:
        return []

    owner, repo = get_repo_info()
    if not owner or not repo:
        return []

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/prompts"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            files = response.json()
            txt_files = []
            for file in files:
                if file["name"].endswith(".txt"):
                    name = file["name"][:-4]  # убираем .txt
                    txt_files.append(name)
            return sorted(txt_files)  # сортируем по алфавиту
        else:
            return []
    except Exception as e:
        return []


def get_file_content(file_path):
    """
    Получает содержимое файла из GitHub репозитория
    """
    token = get_github_token()
    if not token:
        return None, "GitHub токен не найден"

    owner, repo = get_repo_info()
    if not owner or not repo:
        return None, "Репозиторий не настроен"

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
            return content, None
        elif response.status_code == 404:
            return None, "Файл не найден"
        else:
            return None, f"Ошибка {response.status_code}"
    except Exception as e:
        return None, str(e)


def update_file_on_github(file_path, content, commit_message, branch="master"):
    token = get_github_token()
    if not token:
        return False, "GitHub токен не найден"

    owner, repo = get_repo_info()
    if not owner or not repo:
        return False, "Репозиторий не настроен"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    # Пытаемся получить текущий SHA
    response_get = requests.get(url, headers=headers)
    sha = None
    if response_get.status_code == 200:
        sha = response_get.json().get("sha")

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
            return True, "Файл сохранён на GitHub"
        else:
            return False, f"Ошибка {response.status_code}"
    except Exception as e:
        return False, str(e)


def delete_file_on_github(file_path, commit_message, branch="master"):
    """
    Удаляет файл из GitHub репозитория
    """
    token = get_github_token()
    if not token:
        return False, "GitHub токен не найден"

    owner, repo = get_repo_info()
    if not owner or not repo:
        return False, "Репозиторий не настроен"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Получаем SHA файла
    response_get = requests.get(url, headers=headers)
    if response_get.status_code != 200:
        return False, "Файл не найден"

    sha = response_get.json().get("sha")

    data = {
        "message": commit_message,
        "sha": sha,
        "branch": branch
    }

    try:
        response = requests.delete(url, headers=headers, json=data)
        if response.status_code == 200:
            return True, "Файл удалён"
        else:
            return False, f"Ошибка {response.status_code}"
    except Exception as e:
        return False, str(e)


def create_prompt_file(filename, content, branch="master"):
    """
    Создаёт новый файл с промптом в папке prompts/
    """
    file_path = f"prompts/{filename}.txt"
    return update_file_on_github(
        file_path,
        content,
        f"Создан промпт {filename}",
        branch
    )


def delete_prompt_file(filename, branch="master"):
    """
    Удаляет файл с промптом из папки prompts/
    """
    file_path = f"prompts/{filename}.txt"
    return delete_file_on_github(
        file_path,
        f"Удалён промпт {filename}",
        branch
    )


def validate_filename(name):
    """
    Валидация имени файла:
    - максимум 2 слова
    - разрешены: буквы (лат/кир), цифры, дефис, подчёркивание
    - обрезаем до 2 слов
    - удаляем недопустимые символы
    """
    import re

    # Удаляем всё, кроме букв, цифр, пробелов, дефиса, подчёркивания
    cleaned = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s\-_]', '', name)

    # Убираем лишние пробелы
    cleaned = ' '.join(cleaned.split())

    # Берём первые 2 слова
    words = cleaned.split()[:2]
    result = ' '.join(words)

    return result.strip()


def check_file_exists(filename, branch="master"):
    """
    Проверяет, существует ли файл в папке prompts/
    """
    token = get_github_token()
    if not token:
        return False

    owner, repo = get_repo_info()
    if not owner or not repo:
        return False

    file_path = f"prompts/{filename}.txt"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(url, headers=headers)
        return response.status_code == 200
    except:
        return False