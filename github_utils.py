import tempfile
import requests
import os
import base64
import logging
import streamlit as st

GITHUB_REPO = 'ankuraeren/ocr'
GITHUB_BRANCH = 'main'
GITHUB_FILE_PATH = 'parsers.json'
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}'

GITHUB_ACCESS_TOKEN = st.secrets["github"]["access_token"]

LOCAL_PARSERS_FILE = os.path.join(tempfile.gettempdir(), 'parsers.json')

def download_parsers_from_github():
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()

        content = response.json().get('content')
        if content:
            with open(LOCAL_PARSERS_FILE, 'wb') as f:
                f.write(base64.b64decode(content))
            load_parsers()
            st.success("`parsers.json` downloaded successfully from GitHub.")
            logging.info("`parsers.json` downloaded successfully from GitHub.")
        else:
            st.error("`parsers.json` content is empty.")
            logging.error("`parsers.json` content is empty.")
    except Exception as e:
        st.error(f"Error: {e}")
        logging.error(f"Error: {e}")

def upload_parsers_to_github():
    try:
        if not os.path.exists(LOCAL_PARSERS_FILE):
            st.error("`parsers.json` file not found locally. Please download it first.")
            return
        with open(LOCAL_PARSERS_FILE, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')

        current_sha = get_current_sha()
        if not current_sha:
            return

        headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}', 'Content-Type': 'application/json'}
        payload = {'message': 'Update parsers.json file', 'content': content, 'sha': current_sha}

        response = requests.put(GITHUB_API_URL, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            st.success("`parsers.json` uploaded successfully to GitHub.")
        else:
            st.error(f"Failed to upload: {response.json().get('message', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error: {e}")
