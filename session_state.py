# session_state.py

import streamlit as st
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    filename='session_state.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def initialize_session_state():
    """
    Initialize all required Streamlit session_state variables with default values.
    This function should be called at the start of the application to ensure
    that all session state variables are properly set up.
    """
    # Parsers Management
    if 'parsers' not in st.session_state:
        st.session_state['parsers'] = {}
        logging.info("Initialized 'parsers' in session_state.")
    
    # Loaded Flag
    if 'loaded' not in st.session_state:
        st.session_state['loaded'] = False
        logging.info("Initialized 'loaded' flag in session_state.")
    
    # File Management
    if 'file_paths' not in st.session_state:
        st.session_state['file_paths'] = []
        logging.info("Initialized 'file_paths' in session_state.")
    
    if 'temp_dirs' not in st.session_state:
        st.session_state['temp_dirs'] = []
        logging.info("Initialized 'temp_dirs' in session_state.")
    
    if 'image_names' not in st.session_state:
        st.session_state['image_names'] = []
        logging.info("Initialized 'image_names' in session_state.")
    
    # OCR Responses
    if 'response_extra' not in st.session_state:
        st.session_state['response_extra'] = None
        logging.info("Initialized 'response_extra' in session_state.")
    
    if 'response_no_extra' not in st.session_state:
        st.session_state['response_no_extra'] = None
        logging.info("Initialized 'response_no_extra' in session_state.")
    
    # Time Taken for OCR
    if 'time_taken_extra' not in st.session_state:
        st.session_state['time_taken_extra'] = None
        logging.info("Initialized 'time_taken_extra' in session_state.")
    
    if 'time_taken_no_extra' not in st.session_state:
        st.session_state['time_taken_no_extra'] = None
        logging.info("Initialized 'time_taken_no_extra' in session_state.")
    
    # Comparison Results
    if 'comparison_results' not in st.session_state:
        st.session_state['comparison_results'] = {}
        logging.info("Initialized 'comparison_results' in session_state.")
    
    if 'comparison_table' not in st.session_state:
        st.session_state['comparison_table'] = pd.DataFrame()
        logging.info("Initialized 'comparison_table' in session_state.")
    
    if 'mismatch_df' not in st.session_state:
        st.session_state['mismatch_df'] = pd.DataFrame()
        logging.info("Initialized 'mismatch_df' in session_state.")
    
    # Parser Selection
    if 'parser_selected' not in st.session_state:
        st.session_state['parser_selected'] = None
        logging.info("Initialized 'parser_selected' in session_state.")
    
    if 'parser_info' not in st.session_state:
        st.session_state['parser_info'] = {}
        logging.info("Initialized 'parser_info' in session_state.")
    
    # JSON Responses
    if 'response_json_extra' not in st.session_state:
        st.session_state['response_json_extra'] = {}
        logging.info("Initialized 'response_json_extra' in session_state.")
    
    if 'response_json_no_extra' not in st.session_state:
        st.session_state['response_json_no_extra'] = {}
        logging.info("Initialized 'response_json_no_extra' in session_state.")
    
    # CSV Data
    if 'csv_data' not in st.session_state:
        st.session_state['csv_data'] = None
        logging.info("Initialized 'csv_data' in session_state.")
    
    if 'csv_filename' not in st.session_state:
        st.session_state['csv_filename'] = "ocr_results.csv"
        logging.info("Initialized 'csv_filename' in session_state.")
    
    # Compiled Results
    if 'compiled_results' not in st.session_state:
        st.session_state['compiled_results'] = pd.DataFrame(columns=[
            'Document Name', 'Record_Type', 'Invoice Number', 'Shipper Name', 'Biller Name',
            'Invoice Date', 'Item Description', 'Unit Price', 'Quantity', 'Total Price',
            'Ledger ID', 'Account Name', 'Date', 'Transaction Description', 'Amount', 'Balance',
            'Name', 'Company', 'Position', 'Phone', 'Email'
        ])
        logging.info("Initialized 'compiled_results' in session_state.")
    
    def reset_session_state():
        """
        Reset all session_state variables to their initial default values.
        This is useful for clearing data or starting a new session.
        """
        st.session_state['parsers'] = {}
        st.session_state['loaded'] = False
        st.session_state['file_paths'] = []
        st.session_state['temp_dirs'] = []
        st.session_state['image_names'] = []
        st.session_state['response_extra'] = None
        st.session_state['response_no_extra'] = None
        st.session_state['time_taken_extra'] = None
        st.session_state['time_taken_no_extra'] = None
        st.session_state['comparison_results'] = {}
        st.session_state['comparison_table'] = pd.DataFrame()
        st.session_state['mismatch_df'] = pd.DataFrame()
        st.session_state['parser_selected'] = None
        st.session_state['parser_info'] = {}
        st.session_state['response_json_extra'] = {}
        st.session_state['response_json_no_extra'] = {}
        st.session_state['csv_data'] = None
        st.session_state['csv_filename'] = "ocr_results.csv"
        st.session_state['compiled_results'] = pd.DataFrame(columns=[
            'Document Name', 'Record_Type', 'Invoice Number', 'Shipper Name', 'Biller Name',
            'Invoice Date', 'Item Description', 'Unit Price', 'Quantity', 'Total Price',
            'Ledger ID', 'Account Name', 'Date', 'Transaction Description', 'Amount', 'Balance',
            'Name', 'Company', 'Position', 'Phone', 'Email'
        ])
        logging.info("Session state has been reset.")
    
    def add_session_state_key(key, default_value):
        """
        Add a new key to the session state with a default value if it doesn't exist.
        
        Parameters:
            key (str): The session state key to add.
            default_value: The default value for the key.
        """
        if key not in st.session_state:
            st.session_state[key] = default_value
            logging.info(f"Added '{key}' to session_state with default value.")
    
    def get_session_state_key(key):
        """
        Retrieve the value of a session state key.
        
        Parameters:
            key (str): The session state key to retrieve.
        
        Returns:
            The value associated with the key, or None if it doesn't exist.
        """
        return st.session_state.get(key, None)
    
    def set_session_state_key(key, value):
        """
        Set the value of a session state key.
        
        Parameters:
            key (str): The session state key to set.
            value: The value to assign to the key.
        """
        st.session_state[key] = value
        logging.info(f"Set '{key}' in session_state to '{value}'.")
    
    def initialize_dynamic_keys(field_mappings):
        """
        Dynamically add session state keys based on field mappings.
        This allows for flexible handling of various parser types.
        
        Parameters:
            field_mappings (dict): A dictionary mapping JSON fields to CSV columns.
        """
        for json_field, csv_column in field_mappings.items():
            add_session_state_key(csv_column, "")
            logging.info(f"Dynamically initialized session_state key '{csv_column}'.")
    
    # Example usage:
    # from session_state import initialize_session_state, reset_session_state, add_session_state_key
    ```

---

## **3. Explanation of `session_state.py` Components**

### **a. Logging Configuration**

```python
import logging

logging.basicConfig(
    filename='session_state.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
