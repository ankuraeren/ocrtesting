import os
import json
import base64
import requests
import streamlit as st

LOCAL_PARSERS_FILE = os.path.join(os.getcwd(), 'parsers.json')  # Store parsers.json locally

def fetch_parsers_from_github(repo_url, file_path, access_token=None):
    """
    Fetch the parsers.json file from a GitHub repository.
    
    Parameters:
        repo_url (str): The URL of the GitHub repository.
        file_path (str): The path to parsers.json in the repository.
        access_token (str, optional): GitHub access token for private repos.
    
    Returns:
        dict: Parsed JSON content of parsers.json.
    """
    headers = {}
    if access_token:
        headers['Authorization'] = f'token {access_token}'
    
    raw_url = repo_url.replace("github.com", "raw.githubusercontent.com") + f"/main/{file_path}"
    response = requests.get(raw_url, headers=headers)
    
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            st.error("Failed to decode parsers.json from GitHub.")
            return {}
    else:
        st.error(f"Failed to fetch parsers.json from GitHub. Status Code: {response.status_code}")
        return {}

def upload_parsers_to_github(repo_url, file_path, data, access_token):
    """
    Upload the parsers.json file to a GitHub repository.
    
    Parameters:
        repo_url (str): The URL of the GitHub repository.
        file_path (str): The path to parsers.json in the repository.
        data (dict): The parsers data to upload.
        access_token (str): GitHub access token.
    """
    api_url = repo_url.replace("github.com", "api.github.com/repos") + f"/contents/{file_path}"
    headers = {
        'Authorization': f'token {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Check if the file already exists to get its SHA
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        sha = response.json().get('sha')
    else:
        sha = None  # File does not exist
    
    # Encode the content to base64
    encoded_content = base64.b64encode(json.dumps(data, indent=4).encode()).decode('utf-8')
    
    payload = {
        "message": "Update parsers.json",
        "content": encoded_content
    }
    
    if sha:
        payload["sha"] = sha
    
    put_response = requests.put(api_url, headers=headers, json=payload)
    
    if put_response.status_code in [200, 201]:
        st.success("parsers.json uploaded to GitHub successfully!")
    else:
        st.error(f"Failed to upload parsers.json to GitHub. Status Code: {put_response.status_code}")
