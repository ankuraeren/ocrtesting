# parser_utils.py

import streamlit as st
from github_utils import download_parsers_from_github, upload_parsers_to_github
from session_state import (
    initialize_session_state,
    reset_session_state,
    add_session_state_key,
    get_session_state_key,
    set_session_state_key,
    initialize_dynamic_keys
)
import json

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
        field_mappings = st.text_area(
            "Field Mappings (JSON format, optional)",
            help="Define how JSON fields map to CSV columns. Example: {\"name\": \"Name\", \"company\": \"Company Name\"}"
        )
        
        submitted = st.form_submit_button("Add Parser")
        if submitted:
            if not parser_name or not api_key or not parser_app_id:
                st.error("Please fill in all required fields: Parser Name, API Key, and Parser App ID.")
            elif parser_name in st.session_state['parsers']:
                st.error(f"Parser '{parser_name}' already exists.")
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
                        return
                
                # Validate parser configuration
                if validate_parser(parser):
                    st.session_state['parsers'][parser_name] = parser
                    set_session_state_key('parser_selected', parser_name)
                    set_session_state_key('parser_info', parser)
                    
                    # Initialize dynamic session state keys based on field mappings
                    if parser['field_mappings']:
                        initialize_dynamic_keys(parser['field_mappings'])
                    
                    # Save parsers locally and to GitHub
                    save_parsers()
                    upload_parsers_to_github()
                    
                    st.success(f"Parser '{parser_name}' has been added successfully.")
                else:
                    st.error("Parser validation failed. Please check the fields.")

def list_parsers():
    """
    UI to list all existing parsers with options to generate parser pages, edit, and delete parsers.
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
                try:
                    expected_response_json = json.loads(details['expected_response'])
                except json.JSONDecodeError:
                    expected_response_json = details['expected_response']
                st.write("**Expected JSON Response:**")
                st.json(expected_response_json)
            
            if details.get('sample_curl'):
                st.write("**Sample CURL Request:**")
                st.code(details['sample_curl'], language='bash')

            app_id_num = app_id_count[details['parser_app_id']]  # Get the number associated with parser_app_id
            parser_page_link = f"https://ocrtesting-csxcl7uybqbmwards96kjo.streamlit.app/?parser={quote(parser_name)}&client=true&id={app_id_num}"

            # Generate and display link button
            if st.button(f"Generate Parser Page for {parser_name}", key=f"generate_{parser_name}"):
                st.write(f"**Parser Page Link:** [Click Here]({parser_page_link})")

            # Add Edit button
            if st.button(f"Edit {parser_name}", key=f"edit_{parser_name}"):
                edit_parser(parser_name)

            # Add Delete button
            if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                del st.session_state['parsers'][parser_name]
                save_parsers()
                upload_parsers_to_github()
                st.success(f"Parser '{parser_name}' has been deleted.")

def edit_parser(parser_name):
    """
    UI form to edit an existing parser.
    
    Parameters:
        parser_name (str): The name of the parser to edit.
    """
    parser = st.session_state['parsers'].get(parser_name, {})
    if not parser:
        st.error(f"Parser '{parser_name}' does not exist.")
        return

    st.subheader(f"Edit Parser: {parser_name}")
    with st.form(f"edit_parser_form_{parser_name}"):
        api_key = st.text_input("API Key", value=parser['api_key']).strip()
        parser_app_id = st.text_input("Parser App ID", value=parser['parser_app_id']).strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy", value=parser['extra_accuracy'])
        parser_type = st.selectbox(
            "Parser Type",
            ["invoice", "ledger", "visiting_card", "business_card", "other"],
            index=["invoice", "ledger", "visiting_card", "business_card", "other"].index(parser['type']) if parser['type'] in ["invoice", "ledger", "visiting_card", "business_card", "other"] else 4
        )
        expected_response = st.text_area("Expected JSON Response (optional)", value=parser.get('expected_response', ''))
        sample_curl = st.text_area("Sample CURL Request (optional)", value=parser.get('sample_curl', ''))
        field_mappings = st.text_area(
            "Field Mappings (JSON format, optional)",
            value=json.dumps(parser.get('field_mappings', {}), indent=4),
            help="Define how JSON fields map to CSV columns. Example: {\"name\": \"Name\", \"company\": \"Company Name\"}"
        )
        
        submitted = st.form_submit_button("Update Parser")
        if submitted:
            if not api_key or not parser_app_id:
                st.error("Please fill in all required fields: API Key and Parser App ID.")
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
                        return
                
                # Validate parser configuration
                if validate_parser(updated_parser):
                    st.session_state['parsers'][parser_name] = updated_parser
                    set_session_state_key('parser_selected', parser_name)
                    set_session_state_key('parser_info', updated_parser)
                    
                    # Initialize dynamic session state keys based on field mappings
                    if updated_parser['field_mappings']:
                        initialize_dynamic_keys(updated_parser['field_mappings'])
                    
                    # Save parsers locally and to GitHub
                    save_parsers()
                    upload_parsers_to_github()
                    
                    st.success(f"Parser '{parser_name}' has been updated successfully.")
                else:
                    st.error("Parser validation failed. Please check the fields.")

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

def get_parser_types():
    """
    Retrieve a list of all unique parser types.
    
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
