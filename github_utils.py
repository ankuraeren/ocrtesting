import os
import requests
import base64
import tempfile
import streamlit as st
import logging

# GitHub Configuration
GITHUB_REPO = 'ankuraeren/ocr'
GITHUB_BRANCH = 'main'
GITHUB_FILE_PATH = 'parsers.json'
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}'

# Local path for storing parsers.json
LOCAL_PARSERS_FILE = os.path.join(tempfile.gettempdir(), 'parsers.json')

# GitHub Access Token from secrets
GITHUB_ACCESS_TOKEN = st.secrets["github"]["access_token"]

def download_parsers_from_github():
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        content = response.json().get('content')
        if content:
            with open(LOCAL_PARSERS_FILE, 'wb') as f:
                f.write(base64.b64decode(content))
            logging.info("`parsers.json` downloaded successfully.")
            st.success("`parsers.json` downloaded successfully.")
        else:
            st.error("`parsers.json` content is empty.")
            logging.error("`parsers.json` content is empty.")
    except Exception as e:
        st.error(f"Error downloading parsers from GitHub: {e}")
        logging.error(f"Error downloading parsers from GitHub: {e}")

def upload_parsers_to_github():
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}', 'Content-Type': 'application/json'}
    if not os.path.exists(LOCAL_PARSERS_FILE):
        st.error("`parsers.json` file not found locally.")
        return

    try:
        with open(LOCAL_PARSERS_FILE, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')

        sha = get_current_sha()
        if sha is None:
            return

        payload = {
            'message': 'Update parsers.json',
            'content': content,
            'sha': sha,
            'branch': GITHUB_BRANCH
        }

        response = requests.put(GITHUB_API_URL, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            st.success("`parsers.json` uploaded successfully.")
        else:
            st.error(f"Failed to upload parsers: {response.json().get('message', 'Unknown error')}")

    except Exception as e:
        st.error(f"Error uploading parsers to GitHub: {e}")

def get_current_sha():
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get('sha')
    except Exception as e:
        st.error(f"Error fetching SHA: {e}")
        return None
