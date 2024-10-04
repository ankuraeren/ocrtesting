import os
import json
import streamlit as st
import logging
from github_utils import LOCAL_PARSERS_FILE

def load_parsers():
    if os.path.exists(LOCAL_PARSERS_FILE):
        try:
            with open(LOCAL_PARSERS_FILE, 'r') as f:
                st.session_state['parsers'] = json.load(f)
        except Exception as e:
            st.error(f"Error loading parsers: {e}")
            logging.error(f"Error loading parsers: {e}")

def save_parsers():
    try:
        with open(LOCAL_PARSERS_FILE, 'w') as f:
            json.dump(st.session_state['parsers'], f, indent=4)
        st.success("Parsers saved locally.")
    except Exception as e:
        st.error(f"Error saving parsers: {e}")
        logging.error(f"Error saving parsers: {e}")

def add_new_parser():
    st.subheader("Add a New Parser")
    with st.form("add_parser_form"):
        parser_name = st.text_input("Parser Name").strip()
        api_key = st.text_input("API Key").strip()
        parser_app_id = st.text_input("Parser App ID").strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy")
        expected_response = st.text_area("Expected JSON Response (optional)")
        sample_curl = st.text_area("Sample CURL Request (optional)")

        if st.form_submit_button("Add Parser"):
            if parser_name and api_key and parser_app_id:
                if parser_name not in st.session_state['parsers']:
                    st.session_state['parsers'][parser_name] = {
                        'api_key': api_key,
                        'parser_app_id': parser_app_id,
                        'extra_accuracy': extra_accuracy,
                        'expected_response': expected_response,
                        'sample_curl': sample_curl
                    }
                    save_parsers()
                    st.success("Parser added successfully.")
                else:
                    st.error(f"Parser '{parser_name}' already exists.")
            else:
                st.error("Please fill in all required fields.")

def list_parsers():
    st.subheader("List of Parsers")
    if st.session_state.get('parsers'):
        for parser_name, details in st.session_state['parsers'].items():
            with st.expander(parser_name):
                st.write(f"API Key: {details['api_key']}")
                st.write(f"Parser App ID: {details['parser_app_id']}")
                st.write(f"Extra Accuracy: {'Yes' if details['extra_accuracy'] else 'No'}")
                st.write(f"Expected Response: {details['expected_response'] or 'N/A'}")
                st.write(f"Sample CURL: {details['sample_curl'] or 'N/A'}")
    else:
        st.info("No parsers available.")
