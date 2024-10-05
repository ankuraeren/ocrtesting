import os
import base64
import requests
import tempfile
import logging
import json
import streamlit as st

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
        # Generate a unique URL for each parser for the client
        client_url = f"{st.get_url()}?parser={parser_name}&client=true"

        with st.expander(parser_name):
            # Show only the "Run Parser" option for clients
            is_client = st.experimental_get_query_params().get("client", ["false"])[0].lower() == "true"

            if is_client:
                st.write(f"**Parser App ID:** {details['parser_app_id']}")
                st.write(f"**Extra Accuracy Required:** {'Yes' if details['extra_accuracy'] else 'No'}")
                if st.button("Run Parser"):
                    run_parser(details)  # This should be the function to run the parser for clients
            else:
                # Internal Team View (with more options)
                st.write(f"**API Key:** {details['api_key']}")
                st.write(f"**Parser App ID:** {details['parser_app_id']}")
                st.write(f"**Extra Accuracy:** {'Yes' if details['extra_accuracy'] else 'No'}")
                st.write(f"**Expected Response:**")
                if details['expected_response']:
                    try:
                        st.json(json.loads(details['expected_response']))
                    except Exception:
                        st.text(details['expected_response'])
                st.write(f"**Sample CURL Request:**")
                if details['sample_curl']:
                    st.code(details['sample_curl'], language='bash')

                # Show delete button for internal users
                if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                    del st.session_state['parsers'][parser_name]
                    save_parsers()
                    st.success(f"Parser '{parser_name}' has been deleted.")
            
            # Display the unique URL to share with clients
            st.write(f"[Shareable Client Link]({client_url})")


def run_parser(details):
    # Add your logic to run the parser here
    st.write("Running parser...")
    # For the sake of this example, let's just display the details:
    st.write(details)
