# ocr_utils.py

import os
import json
import requests
import time
import pandas as pd
import streamlit as st
import logging
import tempfile
from typing import List, Tuple, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    filename='ocr_utils.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
DEFAULT_TIMEOUT = 120  # seconds
RETRY_COUNT = 3
RETRY_DELAY = 5  # seconds between retries
SUPPORTED_FILE_TYPES = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.pdf'}
MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.bmp': 'image/bmp',
    '.gif': 'image/gif',
    '.tiff': 'image/tiff',
    '.pdf': 'application/pdf'
}

def flatten_json(y: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Flatten a nested JSON object into a single level.

    Args:
        y (dict): The JSON object to flatten.

    Returns:
        Tuple containing the flattened JSON and the order of keys.
    """
    out = {}
    order = []

    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, name + str(i) + '.')
        else:
            out[name[:-1]] = x
            order.append(name[:-1])

    flatten(y)
    return out, order

def generate_comparison_results(json1: Dict[str, Any], json2: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate comparison results between two JSON responses, ignoring case differences for strings.

    Args:
        json1 (dict): First JSON response.
        json2 (dict): Second JSON response.

    Returns:
        dict: A dictionary with keys as attributes and values as "✔" or "✘" indicating match or mismatch.
    """
    flat_json1, order1 = flatten_json(json1)
    flat_json2, _ = flatten_json(json2)

    comparison_results = {}
    for key in order1:
        val1 = flat_json1.get(key, "N/A")
        val2 = flat_json2.get(key, "N/A")

        # Perform case-insensitive comparison if both values are strings
        if isinstance(val1, str) and isinstance(val2, str):
            match = (val1.lower() == val2.lower())
        else:
            match = (val1 == val2)

        comparison_results[key] = "✔" if match else "✘"
    return comparison_results

def generate_comparison_df(json1: Dict[str, Any], json2: Dict[str, Any], comparison_results: Dict[str, str]) -> pd.DataFrame:
    """
    Generate a DataFrame for the comparison results.

    Args:
        json1 (dict): First JSON response.
        json2 (dict): Second JSON response.
        comparison_results (dict): Comparison results from generate_comparison_results.

    Returns:
        pd.DataFrame: DataFrame containing the comparison.
    """
    flat_json1, order1 = flatten_json(json1)
    flat_json2, _ = flatten_json(json2)

    data = []
    for key in order1:
        val1 = flat_json1.get(key, "N/A")
        val2 = flat_json2.get(key, "N/A")
        match = comparison_results[key]
        data.append([key, val1, val2, match])

    df = pd.DataFrame(data, columns=['Attribute', 'Result with Extra Accuracy', 'Result without Extra Accuracy', 'Comparison'])
    return df

def generate_mismatch_df(json1: Dict[str, Any], json2: Dict[str, Any], comparison_results: Dict[str, str]) -> pd.DataFrame:
    """
    Generate a DataFrame containing only the mismatched fields.

    Args:
        json1 (dict): First JSON response.
        json2 (dict): Second JSON response.
        comparison_results (dict): Comparison results from generate_comparison_results.

    Returns:
        pd.DataFrame: DataFrame containing mismatched fields.
    """
    flat_json1, order1 = flatten_json(json1)
    flat_json2, _ = flatten_json(json2)

    data = []
    for key in order1:
        if comparison_results[key] == "✘":  # Only include mismatched fields
            val1 = flat_json1.get(key, "N/A")
            val2 = flat_json2.get(key, "N/A")
            data.append([key, val1, val2])

    df = pd.DataFrame(data, columns=['Field', 'Result with Extra Accuracy', 'Result without Extra Accuracy'])
    return df

def send_request(image_paths: List[str], headers: Dict[str, str], form_data: Dict[str, Any],
                extra_accuracy: bool, API_ENDPOINT: str) -> Tuple[Optional[requests.Response], float]:
    """
    Send OCR request to the API endpoint with retry mechanism.

    Args:
        image_paths (List[str]): List of file paths to upload.
        headers (Dict[str, str]): HTTP headers.
        form_data (Dict[str, Any]): Form data for the request.
        extra_accuracy (bool): Whether to request extra accuracy.
        API_ENDPOINT (str): OCR API endpoint.

    Returns:
        Tuple containing the response object (or None if failed) and the time taken.
    """
    local_headers = headers.copy()
    local_form_data = form_data.copy()

    if extra_accuracy:
        local_form_data['extra_accuracy'] = 'true'
    else:
        local_form_data['extra_accuracy'] = 'false'

    # Prepare files to upload
    files = []
    for image_path in image_paths:
        _, file_ext = os.path.splitext(image_path.lower())
        mime_type = MIME_TYPES.get(file_ext, 'application/octet-stream')
        try:
            file = open(image_path, 'rb')
            files.append(('file', (os.path.basename(image_path), file, mime_type)))
        except Exception as e:
            st.error(f"Error opening file {image_path}: {e}")
            logging.error(f"Error opening file {image_path}: {e}")
            return None, 0

    # Retry mechanism
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            start_time = time.time()
            response = requests.post(API_ENDPOINT, headers=local_headers, data=local_form_data,
                                     files=files if files else None, timeout=DEFAULT_TIMEOUT)
            time_taken = time.time() - start_time

            # Check for successful response
            if response.status_code == 200:
                logging.info(f"OCR request successful on attempt {attempt}.")
                return response, time_taken
            else:
                logging.warning(f"OCR request failed on attempt {attempt}. Status code: {response.status_code}")
                st.warning(f"OCR request failed (Attempt {attempt}/{RETRY_COUNT}). Status code: {response.status_code}")
        except requests.exceptions.Timeout:
            logging.warning(f"OCR request timed out on attempt {attempt}.")
            st.warning(f"OCR request timed out (Attempt {attempt}/{RETRY_COUNT}). Retrying in {RETRY_DELAY} seconds...")
        except requests.exceptions.RequestException as e:
            logging.error(f"OCR request error on attempt {attempt}: {e}")
            st.error(f"OCR request error (Attempt {attempt}/{RETRY_COUNT}): {e}")
            break  # For certain exceptions, do not retry
        time.sleep(RETRY_DELAY)

    # Cleanup files
    for _, file_tuple in files:
        file_tuple[1].close()

    logging.error("All OCR request attempts failed.")
    st.error("All OCR request attempts failed. Please try again later.")
    return None, 0

def create_csv(compiled_results: pd.DataFrame) -> str:
    """
    Save the compiled_results DataFrame to a CSV file and return its path.

    Args:
        compiled_results (pd.DataFrame): The DataFrame to save.

    Returns:
        str: The file path of the saved CSV.
    """
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "ocr_results.csv")

    try:
        compiled_results.to_csv(csv_path, index=False)
        logging.info(f"Compiled results saved to CSV at {csv_path}.")
    except Exception as e:
        st.error(f"Failed to save CSV: {e}")
        logging.error(f"Failed to save CSV at {csv_path}: {e}")

    return csv_path

def extract_invoice_data(comparison_results: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract invoice data from comparison results.
    Replace this with actual extraction logic based on your OCR output.

    Args:
        comparison_results (dict): The comparison results from OCR.

    Returns:
        Tuple containing main_header, invoice_header, and list of line_items.
    """
    # Placeholder extraction logic
    main_header = {
        'invoice_number': 'INV001',
        'document_name': 'Invoice1.pdf'
    }

    invoice_header = {
        'shipper_name': 'Acme Corp',
        'biller_name': 'Global Inc',
        'invoice_date': '2023-10-05',
        'invoice_number': 'INV001',
        'document_name': 'Invoice1.pdf'
    }

    line_items = [
        {'item_description': 'Item 1', 'unit_price': 100.00, 'quantity': 2, 'total_price': 200.00},
        {'item_description': 'Item 2', 'unit_price': 50.00, 'quantity': 4, 'total_price': 200.00}
    ]

    return main_header, invoice_header, line_items

def extract_ledger_data(comparison_results: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract ledger data from comparison results.
    Replace this with actual extraction logic based on your OCR output.

    Args:
        comparison_results (dict): The comparison results from OCR.

    Returns:
        Tuple containing ledger_header and list of line_items.
    """
    # Placeholder extraction logic
    ledger_header = {
        'ledger_id': 'LDG001',
        'account_name': 'John Doe',
        'date': '2023-10-05',
        'document_name': 'Ledger1.pdf'
    }

    line_items = [
        {'transaction_description': 'Deposit', 'amount': 500.00, 'balance': 500.00},
        {'transaction_description': 'Withdrawal', 'amount': 200.00, 'balance': 300.00}
    ]

    return ledger_header, line_items

def extract_visiting_card_data(comparison_results: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract visiting card data from comparison results.
    Replace this with actual extraction logic based on your OCR output.

    Args:
        comparison_results (dict): The comparison results from OCR.

    Returns:
        Tuple containing header and list of contact_info.
    """
    # Placeholder extraction logic
    header = {
        'name': 'Jane Smith',
        'company': 'Tech Solutions',
        'position': 'Software Engineer',
        'document_name': 'VisitingCard1.png'
    }

    contact_info = [
        {'phone': '123-456-7890'},
        {'email': 'jane.smith@techsolutions.com'}
    ]

    return header, contact_info

def parse_comparison_results(parser_type: str, comparison_results: Dict[str, Any]) -> pd.DataFrame:
    """
    Parse comparison results based on the parser type.

    Args:
        parser_type (str): The type of parser (e.g., 'invoice', 'ledger', 'visiting_card').
        comparison_results (dict): The comparison results from OCR.

    Returns:
        pd.DataFrame: The parsed data as a DataFrame.
    """
    if parser_type == 'invoice':
        main_header, invoice_header, line_items = extract_invoice_data(comparison_results)
        parsed_df = parse_invoice(main_header, invoice_header, line_items)
    elif parser_type == 'ledger':
        ledger_header, line_items = extract_ledger_data(comparison_results)
        parsed_df = parse_ledger(ledger_header, line_items)
    elif parser_type == 'visiting_card':
        header, contact_info = extract_visiting_card_data(comparison_results)
        parsed_df = parse_visiting_card(header, contact_info)
    else:
        st.error(f"Unsupported parser type: {parser_type}")
        parsed_df = pd.DataFrame()
    
    return parsed_df

def parse_invoice(main_header: Dict[str, Any], invoice_header: Dict[str, Any],
                 line_items: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse invoice data into a structured DataFrame.

    Args:
        main_header (dict): Main header information.
        invoice_header (dict): Invoice-specific information.
        line_items (list): List of line items.

    Returns:
        pd.DataFrame: Parsed invoice data.
    """
    main_header_df = pd.DataFrame([main_header])
    main_header_df['record_type'] = 'Main Header'

    invoice_header_df = pd.DataFrame([invoice_header])
    invoice_header_df['record_type'] = 'Invoice Header'

    line_items_df = pd.DataFrame(line_items)
    line_items_df['record_type'] = 'Line Item'

    parsed_df = pd.concat([main_header_df, invoice_header_df, line_items_df], ignore_index=True)
    return parsed_df

def parse_ledger(ledger_header: Dict[str, Any],
                line_items: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse ledger data into a structured DataFrame.

    Args:
        ledger_header (dict): Ledger-specific information.
        line_items (list): List of ledger transactions.

    Returns:
        pd.DataFrame: Parsed ledger data.
    """
    ledger_header_df = pd.DataFrame([ledger_header])
    ledger_header_df['record_type'] = 'Ledger Header'

    line_items_df = pd.DataFrame(line_items)
    line_items_df['record_type'] = 'Ledger Transaction'

    parsed_df = pd.concat([ledger_header_df, line_items_df], ignore_index=True)
    return parsed_df

def parse_visiting_card(header: Dict[str, Any],
                        contact_info: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse visiting card data into a structured DataFrame.

    Args:
        header (dict): Header information from the visiting card.
        contact_info (list): List of contact details.

    Returns:
        pd.DataFrame: Parsed visiting card data.
    """
    header_df = pd.DataFrame([header])
    header_df['record_type'] = 'Visiting Card Header'

    contact_info_df = pd.DataFrame(contact_info)
    contact_info_df['record_type'] = 'Contact Info'

    parsed_df = pd.concat([header_df, contact_info_df], ignore_index=True)
    return parsed_df

def extract_dynamic_data(parser_type: str, comparison_results: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], bool]:
    """
    Extract and parse data dynamically based on parser type.

    Args:
        parser_type (str): The type of parser.
        comparison_results (dict): The comparison results from OCR.

    Returns:
        Tuple containing the parsed DataFrame and a boolean indicating success.
    """
    try:
        parsed_df = parse_comparison_results(parser_type, comparison_results)
        if not parsed_df.empty:
            logging.info(f"Data extracted successfully for parser type: {parser_type}")
            return parsed_df, True
        else:
            logging.warning(f"No data extracted for parser type: {parser_type}")
            st.warning(f"No data extracted for parser type: {parser_type}")
            return None, False
    except Exception as e:
        logging.error(f"Error extracting data for parser type {parser_type}: {e}")
        st.error(f"Error extracting data for parser type {parser_type}: {e}")
        return None, False

def cleanup_temp_dirs(temp_dirs: List[str]):
    """
    Cleanup all temporary directories.

    Args:
        temp_dirs (List[str]): List of temporary directory paths.
    """
    for temp_dir in temp_dirs:
        try:
            shutil.rmtree(temp_dir)
            logging.info(f"Temporary directory {temp_dir} removed successfully.")
        except Exception as e:
            logging.warning(f"Failed to remove temporary directory {temp_dir}: {e}")
    # Clear the list after cleanup
    temp_dirs.clear()
