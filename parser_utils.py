import os
import base64
import requests
import tempfile
import logging
import streamlit as st
from urllib.parse import quote

LOCAL_PARSERS_FILE = os.path.join(tempfile.gettempdir(), 'parsers.json')

def download_parsers_from_github():
    headers = {'Authorization': f'token {st.secrets["github"]["access_token"]}'}
    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=10)
        response.raise_for_status()

        content = response.json().get('content')
        if content:
            with open(LOCAL_PARSERS_FILE, 'wb') as f:
                f.write(base64.b64decode(content))
            load_parsers()  # Call the function after downloading
            st.success("`parsers.json` downloaded successfully from GitHub.")
        else:
            st.error("`parsers.json` content is empty.")
    except Exception as e:
        st.error(f"Error: {e}")

def save_parsers():
    try:
        with open(LOCAL_PARSERS_FILE, 'w') as f:
            json.dump(st.session_state['parsers'], f, indent=4)
    except Exception as e:
        st.error(f"Error: {e}")

def add_new_parser():
    st.subheader("Add a New Parser")
    with st.form("add_parser_form"):
        parser_name = st.text_input("Parser Name").strip()
        api_key = st.text_input("API Key").strip()
        parser_app_id = st.text_input("Parser App ID").strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy")
        expected_response = st.text_area("Expected JSON Response (optional)")
        sample_curl = st.text_area("Sample CURL Request (optional)")

        submitted = st.form_submit_button("Add Parser")
        if submitted:
            if not parser_name or not api_key or not parser_app_id:
                st.error("Please fill in all required fields.")
            elif parser_name in st.session_state['parsers']:
                st.error(f"Parser '{parser_name}' already exists.")
            else:
                st.session_state['parsers'][parser_name] = {
                    'api_key': api_key,
                    'parser_app_id': parser_app_id,
                    'extra_accuracy': extra_accuracy,
                    'expected_response': expected_response,
                    'sample_curl': sample_curl
                }
                save_parsers()
                st.success("The parser has been added successfully.")

def list_parsers():
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

            app_id_num = app_id_count[details['parser_app_id']]  # Get the number associated with parser_app_id
            parser_page_link = f"https://ocrtesting-csxcl7uybqbmwards96kjo.streamlit.app/?parser={quote(parser_name)}&client=true&id={app_id_num}"

            # Generate and display link button
            if st.button(f"Generate Parser Page for {parser_name}", key=f"generate_{parser_name}"):
                st.write(f"**Parser Page Link:** [Click Here]({parser_page_link})")
                
            # Add Delete button
            if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                del st.session_state['parsers'][parser_name]
                save_parsers()
                st.success(f"Parser '{parser_name}' has been deleted.")
