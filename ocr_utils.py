### Updated ocr_utils.py ###

import os
import json
import requests
import time
import pandas as pd
import streamlit as st

# Function to flatten nested JSON with better handling of lists
def flatten_json(y):
    out = {}
    order = []

    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], f"{name}{a}__")
        elif isinstance(x, list):
            for i, a in enumerate(x):
                # If the list items are dictionaries with a unique key, use it
                if isinstance(a, dict) and 'Sr_No' in a:
                    identifier = a.get('Sr_No', i)
                    flatten(a, f"{name}{identifier}__")
                else:
                    flatten(a, f"{name}{i}__")
        else:
            out[name[:-2]] = x  # Remove the trailing '__'
            order.append(name[:-2])

    flatten(y)
    return out, order


# Function to generate comparison results (ignoring case differences)
def generate_comparison_results(json1, json2):
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

# Function to generate a DataFrame for the comparison
def generate_comparison_df(json1, json2, comparison_results):
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

# Function to generate a DataFrame with only mismatched fields
def generate_mismatch_df(json1, json2, comparison_results):
    flat_json1, order1 = flatten_json(json1)
    flat_json2, _ = flatten_json(json2)

    data = []
    for key in order1:
        val1 = flat_json1.get(key, "N/A")
        val2 = flat_json2.get(key, "N/A")
        if comparison_results[key] == "✘":  # Only include mismatched fields
            data.append([key, val1, val2])

    # Create a DataFrame with only the mismatched fields
    df = pd.DataFrame(data, columns=['Field', 'Result with Extra Accuracy', 'Result without Extra Accuracy'])
    return df

# Function to send OCR request
def send_request(image_paths, headers, form_data, extra_accuracy, API_ENDPOINT):
    local_headers = headers.copy()
    local_form_data = form_data.copy()

    if extra_accuracy:
        local_form_data['extra_accuracy'] = 'true'

    # List of files to upload
    files = []
    for image_path in image_paths:
        _, file_ext = os.path.splitext(image_path.lower())
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif',
            '.tiff': 'image/tiff',
            '.pdf': 'application/pdf'
        }
        mime_type = mime_types.get(file_ext, 'application/octet-stream')
        try:
            files.append(('file', (os.path.basename(image_path), open(image_path, 'rb'), mime_type)))
        except Exception as e:
            st.error(f"Error opening file {image_path}: {e}")
            return None, 0

    try:
        start_time = time.time()
        response = requests.post(API_ENDPOINT, headers=local_headers, data=local_form_data, files=files if files else None, timeout=120)
        time_taken = time.time() - start_time
        return response, time_taken
    except requests.exceptions.RequestException as e:
        st.error(f"Error in OCR request: {e}")
        return None, 0
    finally:
        # Cleanup files
        for _, file_tuple in files:
            file_tuple[1].close()
