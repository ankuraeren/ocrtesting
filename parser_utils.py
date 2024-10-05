import os
import json
import base64
import requests
import tempfile
import logging
import streamlit as st
from urllib.parse import quote

# Configure logging
logging.basicConfig(
    filename='parser_utils.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
LOCAL_PARSERS_FILE = os.path.join(tempfile.gettempdir(), 'parsers.json')
GITHUB_API_URL = "https://api.github.com/repos/yourusername/yourrepo/contents/parsers.json"  # Replace with your actual GitHub API URL

def load_parsers():
    """
    Load parsers from the local parsers.json file into session_state.
    """
    if not os.path.exists(LOCAL_PARSERS_FILE):
        st.warning("`parsers.json` not found locally. Please download it from GitHub.")
        return
    
    try:
        with open(LOCAL_PARSERS_FILE, 'r') as f:
            parsers = json.load(f)
        st.session_state['parsers'] = parsers
        logging.info("Parsers loaded successfully from local file.")
    except Exception as e:
        st.error(f"Failed to load parsers: {e}")
        logging.error(f"Failed to load parsers: {e}")

def download_parsers_from_github():
    """
    Download the parsers.json file from GitHub and load it into session_state.
    """
    headers = {'Authorization': f'token {st.secrets["github"]["access_token"]}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()

        content = response.json().get('content')
        if content:
            with open(LOCAL_PARSERS_FILE, 'wb') as f:
                f.write(base64.b64decode(content))
            load_parsers()  # Load parsers after downloading
            st.success("`parsers.json` downloaded successfully from GitHub.")
            logging.info("Parsers downloaded successfully from GitHub.")
        else:
            st.error("`parsers.json` content is empty.")
            logging.error("`parsers.json` content is empty on GitHub.")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to download `parsers.json` from GitHub: {e}")
        logging.error(f"Failed to download `parsers.json` from GitHub: {e}")

def upload_parsers_to_github():
    """
    Upload the local parsers.json file to GitHub.
    """
    headers = {'Authorization': f'token {st.secrets["github"]["access_token"]}',
               'Content-Type': 'application/json'}
    
    try:
        with open(LOCAL_PARSERS_FILE, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
        
        # Get the SHA of the existing file to update it
        get_response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        if get_response.status_code == 200:
            sha = get_response.json().get('sha')
        else:
            sha = None  # File does not exist, create a new one
        
        payload = {
            "message": "Update parsers.json",
            "content": content
        }
        if sha:
            payload["sha"] = sha
        
        put_response = requests.put(GITHUB_API_URL, headers=headers, data=json.dumps(payload), timeout=10)
        put_response.raise_for_status()
        
        st.success("`parsers.json` uploaded successfully to GitHub.")
        logging.info("Parsers uploaded successfully to GitHub.")
    except FileNotFoundError:
        st.error("Local `parsers.json` file not found.")
        logging.error("Local `parsers.json` file not found.")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to upload `parsers.json` to GitHub: {e}")
        logging.error(f"Failed to upload `parsers.json` to GitHub: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        logging.error(f"An unexpected error occurred while uploading parsers: {e}")

def save_parsers():
    """
    Save the current parsers in session_state to the local parsers.json file.
    """
    try:
        with open(LOCAL_PARSERS_FILE, 'w') as f:
            json.dump(st.session_state['parsers'], f, indent=4)
        st.success("Parsers saved locally.")
        logging.info("Parsers saved successfully to local file.")
    except Exception as e:
        st.error(f"Failed to save parsers: {e}")
        logging.error(f"Failed to save parsers: {e}")

def validate_parser(parser):
    """
    Validate the parser configuration.
    
    Parameters:
        parser (dict): The parser configuration to validate.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    required_fields = ['api_key', 'parser_app_id', 'extra_accuracy', 'type']
    for field in required_fields:
        if field not in parser:
            st.error(f"Missing required field: {field}")
            logging.error(f"Parser validation failed: Missing field {field}")
            return False
    return True

def add_new_parser():
    """
    UI form to add a new parser.
    """
    st.subheader("Add a New Parser")
    with st.form("add_parser_form"):
        parser_name = st.text_input("Parser Name").strip()
        api_key = st.text_input("API Key").strip()
        parser_app_id = st.text_input("Parser App ID").strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy")
        parser_type = st.selectbox("Parser Type", ["invoice", "ledger", "visiting_card", "business_card", "other"])
        expected_response = st.text_area("Expected JSON Response (optional)")
        sample_curl = st.text_area("Sample CURL Request (optional)")
        field_mappings = st.text_area("Field Mappings (JSON format, optional)", help="Define how JSON fields map to CSV columns. Example: {\"name\": \"Name\", \"company\": \"Company Name\"}")
        
        submitted = st.form_submit_button("Add Parser")
        if submitted:
            if not parser_name or not api_key or not parser_app_id:
                st.error("Please fill in all required fields: Parser Name, API Key, and Parser App ID.")
                logging.error("Parser addition failed: Missing required fields.")
            elif parser_name in st.session_state['parsers']:
                st.error(f"Parser '{parser_name}' already exists.")
                logging.error(f"Parser addition failed: Parser '{parser_name}' already exists.")
            else:
                parser = {
                    'api_key': api_key,
                    'parser_app_id': parser_app_id,
                    'extra_accuracy': extra_accuracy,
                    'type': parser_type,
                    'expected_response': expected_response,
                    'sample_curl': sample_curl,
                    'field_mappings': {}
                }
                if field_mappings:
                    try:
                        parser['field_mappings'] = json.loads(field_mappings)
                    except json.JSONDecodeError:
                        st.error("Field Mappings must be a valid JSON.")
                        logging.error("Parser addition failed: Invalid JSON in Field Mappings.")
                        return
                
                if validate_parser(parser):
                    st.session_state['parsers'][parser_name] = parser
                    save_parsers()
                    st.success(f"Parser '{parser_name}' has been added successfully.")
                    logging.info(f"Parser '{parser_name}' added successfully.")
                else:
                    st.error("Parser validation failed. Please check the fields.")
                    logging.error("Parser addition failed: Validation failed.")

def list_parsers():
    """
    UI to list all existing parsers with options to generate parser pages and delete parsers.
    """
    st.subheader("List of All Parsers")
    if not st.session_state['parsers']:
        st.info("No parsers available. Please add a parser first.")
        return

    # Count parser_app_id occurrences for dynamic numbering
    app_id_count = {}
    for parser_name, details in st.session_state['parsers'].items():
        app_id = details['parser_app_id']
        if app_id in app_id_count:
            app_id_count[app_id] += 1
        else:
            app_id_count[app_id] = 1

    # Iterate over the parsers and display details
    for parser_name, details in st.session_state['parsers'].items():
        with st.expander(parser_name):
            st.write(f"**API Key:** {details['api_key']}")
            st.write(f"**Parser App ID:** {details['parser_app_id']}")
            st.write(f"**Extra Accuracy:** {'Yes' if details['extra_accuracy'] else 'No'}")
            st.write(f"**Parser Type:** {details['type']}")
            if details.get('field_mappings'):
                st.write("**Field Mappings:**")
                st.json(details['field_mappings'])
            if details.get('expected_response'):
                st.write("**Expected JSON Response:**")
                st.json(json.loads(details['expected_response']) if isinstance(details['expected_response'], str) else details['expected_response'])
            if details.get('sample_curl'):
                st.write("**Sample CURL Request:**")
                st.code(details['sample_curl'], language='bash')

            app_id_num = app_id_count[details['parser_app_id']]  # Get the number associated with parser_app_id
            parser_page_link = f"https://ocrtesting-csxcl7uybqbmwards96kjo.streamlit.app/?parser={quote(parser_name)}&client=true&id={app_id_num}"

            # Generate and display link button
            if st.button(f"Generate Parser Page for {parser_name}", key=f"generate_{parser_name}"):
                st.write(f"**Parser Page Link:** [Click Here]({parser_page_link})")
                logging.info(f"Parser page link generated for '{parser_name}'.")

            # Add Delete button
            if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                del st.session_state['parsers'][parser_name]
                save_parsers()
                st.success(f"Parser '{parser_name}' has been deleted.")
                logging.info(f"Parser '{parser_name}' deleted successfully.")

def edit_parser(parser_name):
    """
    UI form to edit an existing parser.
    
    Parameters:
        parser_name (str): The name of the parser to edit.
    """
    st.subheader(f"Edit Parser: {parser_name}")
    parser = st.session_state['parsers'][parser_name]
    with st.form(f"edit_parser_form_{parser_name}"):
        api_key = st.text_input("API Key", value=parser['api_key']).strip()
        parser_app_id = st.text_input("Parser App ID", value=parser['parser_app_id']).strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy", value=parser['extra_accuracy'])
        parser_type = st.selectbox("Parser Type", ["invoice", "ledger", "visiting_card", "business_card", "other"], index=["invoice", "ledger", "visiting_card", "business_card", "other"].index(parser['type']) if parser['type'] in ["invoice", "ledger", "visiting_card", "business_card", "other"] else 4)
        expected_response = st.text_area("Expected JSON Response (optional)", value=parser.get('expected_response', ''))
        sample_curl = st.text_area("Sample CURL Request (optional)", value=parser.get('sample_curl', ''))
        field_mappings = st.text_area("Field Mappings (JSON format, optional)", value=json.dumps(parser.get('field_mappings', {}), indent=4))
        
        submitted = st.form_submit_button("Update Parser")
        if submitted:
            if not api_key or not parser_app_id:
                st.error("Please fill in all required fields: API Key and Parser App ID.")
                logging.error(f"Parser '{parser_name}' update failed: Missing required fields.")
            else:
                updated_parser = {
                    'api_key': api_key,
                    'parser_app_id': parser_app_id,
                    'extra_accuracy': extra_accuracy,
                    'type': parser_type,
                    'expected_response': expected_response,
                    'sample_curl': sample_curl,
                    'field_mappings': {}
                }
                if field_mappings:
                    try:
                        updated_parser['field_mappings'] = json.loads(field_mappings)
                    except json.JSONDecodeError:
                        st.error("Field Mappings must be a valid JSON.")
                        logging.error(f"Parser '{parser_name}' update failed: Invalid JSON in Field Mappings.")
                        return
                
                if validate_parser(updated_parser):
                    st.session_state['parsers'][parser_name] = updated_parser
                    save_parsers()
                    st.success(f"Parser '{parser_name}' has been updated successfully.")
                    logging.info(f"Parser '{parser_name}' updated successfully.")
                else:
                    st.error("Parser validation failed. Please check the fields.")
                    logging.error(f"Parser '{parser_name}' update failed: Validation failed.")

def get_parser_types():
    """
    Retrieve a list of all parser types.
    
    Returns:
        list: A list of unique parser types.
    """
    types = set()
    for parser in st.session_state['parsers'].values():
        types.add(parser.get('type', 'other'))
    return list(types)

def get_field_mappings(parser_name):
    """
    Retrieve field mappings for a given parser.
    
    Parameters:
        parser_name (str): The name of the parser.
    
    Returns:
        dict: Field mappings.
    """
    parser = st.session_state['parsers'].get(parser_name, {})
    return parser.get('field_mappings', {})

def get_parser_type(parser_name):
    """
    Retrieve the type of a given parser.
    
    Parameters:
        parser_name (str): The name of the parser.
    
    Returns:
        str: The type of the parser.
    """
    parser = st.session_state['parsers'].get(parser_name, {})
    return parser.get('type', 'other')

def get_parser_field_mappings(parser_name):
    """
    Retrieve the field mappings of a given parser.
    
    Parameters:
        parser_name (str): The name of the parser.
    
    Returns:
        dict: Field mappings.
    """
    return st.session_state['parsers'][parser_name].get('field_mappings', {})
