# parsers/github_manager.py

import os
import json
import requests
import base64
import logging
import streamlit as st
from .parser_manager import load_parsers

# GitHub Configuration using Streamlit Secrets
GITHUB_REPO = 'ankuraeren/ocr'
GITHUB_BRANCH = 'main'  # Define the branch
GITHUB_FILE_PATH = 'parsers.json'
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}'

# Access GitHub Access Token securely from secrets
GITHUB_ACCESS_TOKEN = st.secrets["github"]["access_token"]

# Define local parsers file path using a temporary directory
LOCAL_PARSERS_FILE = os.path.join(st.session_state.get('temp_dir', ''), 'parsers.json')


def download_parsers_from_github():
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses

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
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred while downloading `parsers.json`: {http_err}")
        logging.error(f"HTTP error occurred while downloading `parsers.json`: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Connection error occurred while downloading `parsers.json`: {conn_err}")
        logging.error(f"Connection error occurred while downloading `parsers.json`: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        st.error(f"Timeout error occurred while downloading `parsers.json`: {timeout_err}")
        logging.error(f"Timeout error occurred while downloading `parsers.json`: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"An error occurred while downloading `parsers.json`: {req_err}")
        logging.error(f"An error occurred while downloading `parsers.json`: {req_err}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}")


def upload_parsers_to_github():
    try:
        if not os.path.exists(LOCAL_PARSERS_FILE):
            st.error("`parsers.json` file not found locally. Please download it first.")
            logging.error("`parsers.json` file not found locally.")
            return
        with open(LOCAL_PARSERS_FILE, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')

        current_sha = get_current_sha()
        if not current_sha:
            return

        headers = {
            'Authorization': f'token {GITHUB_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }
        payload = {
            'message': 'Update parsers.json file',
            'content': content,
            'sha': current_sha,
            'branch': GITHUB_BRANCH  # Corrected: Removed duplicate 'branch' key
        }

        response = requests.put(GITHUB_API_URL, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            st.success("`parsers.json` uploaded successfully to GitHub.")
            logging.info("`parsers.json` uploaded successfully to GitHub.")
        else:
            error_message = response.json().get('message', 'Unknown error')
            st.error(f"Failed to upload `parsers.json` to GitHub: {error_message}")
            logging.error(f"Failed to upload `parsers.json` to GitHub: {error_message}")
    except FileNotFoundError:
        st.error("`parsers.json` file not found locally. Please download it first.")
        logging.error("`parsers.json` file not found locally.")
    except Exception as e:
        st.error(f"An unexpected error occurred during upload: {e}")
        logging.error(f"An unexpected error occurred during upload: {e}")


def get_current_sha():
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        sha = response.json().get('sha')
        if sha:
            return sha
        else:
            st.error("SHA not found for `parsers.json` in GitHub.")
            logging.error("SHA not found for `parsers.json` in GitHub.")
            return None
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred while fetching SHA: {http_err}")
        logging.error(f"HTTP error occurred while fetching SHA: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Connection error occurred while fetching SHA: {conn_err}")
        logging.error(f"Connection error occurred while fetching SHA: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        st.error(f"Timeout error occurred while fetching SHA: {timeout_err}")
        logging.error(f"Timeout error occurred while fetching SHA: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"An error occurred while fetching SHA: {req_err}")
        logging.error(f"An error occurred while fetching SHA: {req_err}")
    except Exception as e:
        st.error(f"Unexpected error while fetching SHA: {e}")
        logging.error(f"Unexpected error while fetching SHA: {e}")
    return None
  
