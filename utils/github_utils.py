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


def update_file_on_github(file_path, content, commit_message, branch="master"):
    token = get_github_token()
    if not token:
        return False, "❌ GitHub токен не найден"

    owner, repo = get_repo_info()
    if not owner or not repo:
        return False, "❌ Не настроены данные репозитория"

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

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
            return True, "✅ Файл сохранён в GitHub"
        else:
            return False, f"❌ Ошибка {response.status_code}"
    except Exception as e:
        return False, f"❌ Ошибка: {e}"