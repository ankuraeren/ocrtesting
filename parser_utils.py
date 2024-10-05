import os
import base64
import requests
import tempfile
import logging
import streamlit as st
from urllib.parse import urlencode

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

    for parser_name, details in st.session_state['parsers'].items():
        with st.expander(parser_name):
            st.write(f"**API Key:** {details['api_key']}")
            st.write(f"**Parser App ID:** {details['parser_app_id']}")
            st.write(f"**Extra Accuracy:** {'Yes' if details['extra_accuracy'] else 'No'}")

            # Direct link to run the parser
            run_parser_link = f"/?parser={parser_name}&client=False"
            st.markdown(f"[Run Parser]({run_parser_link})")

            # Generate dynamic parser page link button
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"Generate Parser Page for {parser_name}", key=f"generate_{parser_name}"):
                    query_params = urlencode({'parser': parser_name, 'client': 'True'})
                    parser_page_url = f"/?{query_params}"
                    st.write(f"**Generated Link:** [{parser_page_url}]({parser_page_url})")

            with col2:
                # Delete parser button
                if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                    del st.session_state['parsers'][parser_name]
                    save_parsers()
                    st.success(f"Parser '{parser_name}' has been deleted.")
