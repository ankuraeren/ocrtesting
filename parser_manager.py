# parsers/parser_manager.py

import os
import json
import streamlit as st
import logging
from .github_manager import LOCAL_PARSERS_FILE


def load_parsers():
    if os.path.exists(LOCAL_PARSERS_FILE):
        try:
            with open(LOCAL_PARSERS_FILE, 'r') as f:
                st.session_state['parsers'] = json.load(f)
            logging.info("`parsers.json` loaded into session state.")
        except json.JSONDecodeError:
            st.error("`parsers.json` is corrupted or not in valid JSON format.")
            logging.error("`parsers.json` is corrupted or not in valid JSON format.")
        except Exception as e:
            st.error(f"Unexpected error while loading `parsers.json`: {e}")
            logging.error(f"Unexpected error while loading `parsers.json`: {e}")
    else:
        st.error("`parsers.json` does not exist locally. Please download it from GitHub.")
        logging.error("`parsers.json` does not exist locally.")


def save_parsers():
    try:
        with open(LOCAL_PARSERS_FILE, 'w') as f:
            json.dump(st.session_state['parsers'], f, indent=4)
        st.success("`parsers.json` has been updated locally. Please upload it back to GitHub.")
        logging.info("`parsers.json` has been updated locally.")
    except Exception as e:
        st.error(f"Failed to save `parsers.json` locally: {e}")
        logging.error(f"Failed to save `parsers.json` locally: {e}")


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
                if expected_response:
                    try:
                        json.loads(expected_response)
                    except json.JSONDecodeError:
                        st.error("Expected JSON Response is not valid JSON.")
                        return

                st.session_state['parsers'][parser_name] = {
                    'api_key': api_key,
                    'parser_app_id': parser_app_id,
                    'extra_accuracy': extra_accuracy,
                    'expected_response': expected_response,
                    'sample_curl': sample_curl
                }
                save_parsers()
                st.success("The parser has been added successfully.")
                st.experimental_rerun()  # Changed to rerun for immediate update


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
            st.write(f"**Expected Response:**")
            if details['expected_response']:
                try:
                    expected_json = json.loads(details['expected_response'])
                    st.json(expected_json)
                except json.JSONDecodeError:
                    st.text(details['expected_response'])
            else:
                st.write("N/A")
            st.write(f"**Sample CURL Request:**")
            if details['sample_curl']:
                st.code(details['sample_curl'], language='bash')
            else:
                st.write("N/A")

            # Use a unique key for each delete button to prevent conflicts
            if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                del st.session_state['parsers'][parser_name]
                save_parsers()
                st.success(f"Parser '{parser_name}' has been deleted.")
                st.experimental_rerun()  # Changed to rerun for immediate update
