import os
import base64
import requests
import tempfile
import logging
import json
import streamlit as st

GITHUB_REPO = 'ankuraeren/ocr'
GITHUB_BRANCH = 'main'
GITHUB_FILE_PATH = 'parsers.json'
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}'

LOCAL_PARSERS_FILE = os.path.join(tempfile.gettempdir(), 'parsers.json')
GITHUB_ACCESS_TOKEN = st.secrets["github"]["access_token"]

def load_parsers():
    """Load parsers from the local file and store them in session state."""
    if os.path.exists(LOCAL_PARSERS_FILE):
        try:
            with open(LOCAL_PARSERS_FILE, 'r') as f:
                st.session_state['parsers'] = json.load(f)
            st.success("`parsers.json` loaded into session state.")
        except json.JSONDecodeError:
            st.error("`parsers.json` is corrupted or not in valid JSON format.")
        except Exception as e:
            st.error(f"Unexpected error while loading `parsers.json`: {e}")
    else:
        st.error("`parsers.json` does not exist locally. Please download it from GitHub.")

def download_parsers_from_github():
    """Download the `parsers.json` from GitHub and save it locally."""
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()

        content = response.json().get('content')
        if content:
            with open(LOCAL_PARSERS_FILE, 'wb') as f:
                f.write(base64.b64decode(content))
            load_parsers()  # After downloading, load it into session state
            st.success("`parsers.json` downloaded successfully from GitHub.")
        else:
            st.error("`parsers.json` content is empty.")
    except requests.exceptions.RequestException as req_err:
        st.error(f"An error occurred while downloading `parsers.json`: {req_err}")
        logging.error(f"An error occurred while downloading `parsers.json`: {req_err}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        logging.error(f"Unexpected error: {e}")

def upload_parsers_to_github():
    """Upload the updated `parsers.json` to GitHub."""
    if not os.path.exists(LOCAL_PARSERS_FILE):
        st.error("`parsers.json` file not found locally. Please download it first.")
        return

    try:
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
            'sha': current_sha
        }

        response = requests.put(GITHUB_API_URL, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            st.success("`parsers.json` uploaded successfully to GitHub.")
        else:
            st.error(f"Failed to upload `parsers.json`: {response.json().get('message', 'Unknown error')}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

def get_current_sha():
    """Retrieve the current SHA for the `parsers.json` file on GitHub."""
    headers = {'Authorization': f'token {GITHUB_ACCESS_TOKEN}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        sha = response.json().get('sha')
        return sha
    except Exception as e:
        st.error(f"Error fetching SHA: {e}")
        return None

def are_fields_equal(field1, field2):
    """Custom logic to determine if two fields are equal, treating 'N/A', 'null', and empty fields as equal."""
    normalized_field1 = str(field1).strip().lower() if field1 is not None else ""
    normalized_field2 = str(field2).strip().lower() if field2 is not None else ""
    return normalized_field1 in ["", "n/a", "null"] and normalized_field2 in ["", "n/a", "null"] or normalized_field1 == normalized_field2

# Example usage in comparison logic
# Assume we are comparing two OCR outputs (response1, response2) for mismatches
def compare_ocr_outputs(response1, response2):
    mismatches = []
    for key in response1.keys() | response2.keys():
        value1 = response1.get(key, "")
        value2 = response2.get(key, "")
        if not are_fields_equal(value1, value2):
            mismatches.append({"field": key, "value1": value1, "value2": value2})
    return mismatches
