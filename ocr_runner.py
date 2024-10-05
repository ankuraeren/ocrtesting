# ocr_runner.py

import os
import tempfile
import shutil
import streamlit as st
from PIL import Image
from ocr_utils import (
    send_request, 
    generate_comparison_results, 
    generate_comparison_df, 
    generate_mismatch_df
)
from parser_utils import (
    parse_comparison_results, 
    get_field_mappings, 
    get_parser_type
)
from session_state import (
    initialize_session_state, 
    reset_session_state, 
    add_session_state_key, 
    get_session_state_key, 
    set_session_state_key, 
    initialize_dynamic_keys
)
from st_aggrid import AgGrid, GridOptionsBuilder
import json
import pandas as pd
import atexit
import logging

# ===========================
# 1. Configure Logging
# ===========================

logging.basicConfig(
    filename='ocr_runner.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ===========================
# 2. Define Helper Functions
# ===========================

def create_csv(compiled_results: pd.DataFrame) -> str:
    """
    Save the compiled_results DataFrame to a CSV file and return its path.
    
    Args:
        compiled_results (pd.DataFrame): The DataFrame containing OCR results.
    
    Returns:
        str: The file path to the saved CSV.
    """
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "ocr_results.csv")

    try:
        # Save to CSV
        compiled_results.to_csv(csv_path, index=False)
        logging.info(f"Compiled results saved to CSV at {csv_path}.")
    except Exception as e:
        st.error(f"Failed to save CSV: {e}")
        logging.error(f"Failed to save CSV: {e}")
    
    return csv_path

def cleanup_temp_dirs():
    """
    Cleanup all temporary directories stored in session_state.temp_dirs.
    """
    for temp_dir in st.session_state.temp_dirs:
        try:
            shutil.rmtree(temp_dir)
            logging.info(f"Temporary directory {temp_dir} removed successfully.")
        except Exception as e:
            st.warning(f"Could not remove temporary directory {temp_dir}: {e}")
            logging.warning(f"Could not remove temporary directory {temp_dir}: {e}")
    st.session_state.temp_dirs = []

# Register cleanup on app exit
atexit.register(cleanup_temp_dirs)

def display_ocr_results(response_extra: requests.Response, response_no_extra: requests.Response, time_extra: float, time_no_extra: float):
    """
    Display OCR results from responses with and without extra accuracy.

    Args:
        response_extra (requests.Response): OCR response with extra accuracy.
        response_no_extra (requests.Response): OCR response without extra accuracy.
        time_extra (float): Time taken for extra accuracy request.
        time_no_extra (float): Time taken for no extra accuracy request.
    """
    success_extra = response_extra and response_extra.status_code == 200
    success_no_extra = response_no_extra and response_no_extra.status_code == 200

    # Display results in two columns
    col1, col2 = st.columns(2)

    if success_extra:
        try:
            response_json_extra = response_extra.json()
            st.session_state.response_json_extra = response_json_extra
            with col1:
                st.expander(f"Results with Extra Accuracy - ⏱ {time_extra:.2f}s").json(response_json_extra)
                logging.info("Displayed OCR results with extra accuracy.")
        except json.JSONDecodeError:
            with col1:
                st.error("Failed to parse JSON response with Extra Accuracy.")
            logging.error("Failed to parse JSON response with Extra Accuracy.")
    else:
        with col1:
            status_code = response_extra.status_code if response_extra else "No Response"
            st.error(f"Request with Extra Accuracy failed. Status code: {status_code}")
            logging.error(f"Request with Extra Accuracy failed. Status code: {status_code}")

    if success_no_extra:
        try:
            response_json_no_extra = response_no_extra.json()
            st.session_state.response_json_no_extra = response_json_no_extra
            with col2:
                st.expander(f"Results without Extra Accuracy - ⏱ {time_no_extra:.2f}s").json(response_json_no_extra)
                logging.info("Displayed OCR results without extra accuracy.")
        except json.JSONDecodeError:
            with col2:
                st.error("Failed to parse JSON response without Extra Accuracy.")
            logging.error("Failed to parse JSON response without Extra Accuracy.")
    else:
        with col2:
            status_code = response_no_extra.status_code if response_no_extra else "No Response"
            st.error(f"Request without Extra Accuracy failed. Status code: {status_code}")
            logging.error(f"Request without Extra Accuracy failed. Status code: {status_code}")

def generate_and_display_comparisons():
    """
    Generate comparison results, display mismatched fields, and show comparison tables.
    """
    comparison_results = generate_comparison_results(
        st.session_state.response_json_extra, 
        st.session_state.response_json_no_extra
    )
    st.session_state.comparison_results = comparison_results
    logging.info("Comparison results generated.")

    # Generate mismatch DataFrame
    mismatch_df = generate_mismatch_df(
        st.session_state.response_json_extra, 
        st.session_state.response_json_no_extra, 
        comparison_results
    )
    st.session_state.mismatch_df = mismatch_df
    logging.info("Mismatch DataFrame generated.")

    # Generate comparison DataFrame
    comparison_table = generate_comparison_df(
        st.session_state.response_json_extra, 
        st.session_state.response_json_no_extra, 
        comparison_results
    )
    st.session_state.comparison_table = comparison_table
    logging.info("Comparison DataFrame generated.")

    # Display mismatched fields in a table
    st.subheader("Mismatched Fields")
    st.dataframe(mismatch_df)

    # Display the comparison table using AgGrid
    st.subheader("Comparison Table")
    gb = GridOptionsBuilder.from_dataframe(comparison_table)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_selection('single')
    grid_options = gb.build()
    AgGrid(comparison_table, gridOptions=grid_options, height=500, theme='streamlit', enable_enterprise_modules=True)

    # Display the full comparison JSON after the table
    st.subheader("Comparison JSON")
    st.expander("Comparison JSON").json(comparison_results)
    logging.info("Displayed comparison tables and JSON.")

def parse_and_compile_results(parser_type: str, comparison_results: Dict[str, str]):
    """
    Parse the comparison results based on the parser type and compile them into the results DataFrame.

    Args:
        parser_type (str): The type of the parser (e.g., 'invoice', 'ledger', 'visiting_card').
        comparison_results (dict): The comparison results between OCR responses.
    """
    parsed_df = parse_comparison_results(parser_type, comparison_results)
    st.session_state.compiled_results = pd.concat(
        [st.session_state.compiled_results, parsed_df],
        ignore_index=True
    )
    logging.info(f"Parsed and compiled results for parser type '{parser_type}'.")

def display_compiled_results():
    """
    Display the cumulative compiled results and provide a download button for the CSV.
    """
    if not st.session_state.compiled_results.empty:
        st.subheader("Cumulative Results")
        st.dataframe(st.session_state.compiled_results)

        # Generate and provide the CSV download
        csv_file_path = create_csv(st.session_state.compiled_results)
        try:
            with open(csv_file_path, "rb") as csv_file:
                st.session_state.csv_data = csv_file.read()
                st.session_state.csv_filename = "ocr_results.csv"
            st.download_button(
                label="Download OCR Results as CSV",
                data=st.session_state.csv_data,
                file_name=st.session_state.csv_filename,
                mime="text/csv"
            )
            logging.info("Provided CSV download button.")
        except Exception as e:
            st.error(f"Failed to prepare CSV for download: {e}")
            logging.error(f"Failed to prepare CSV for download: {e}")
    else:
        st.info("No compiled results to display.")

def run_ocr_process():
    """
    Execute the OCR process by sending requests, handling responses, generating comparisons,
    parsing results, and compiling them.
    """
    headers = {
        'x-api-key': st.session_state.parser_info['api_key'],
    }

    form_data = {
        'parserApp': st.session_state.parser_info['parser_app_id'],
        'user_ip': '127.0.0.1',
        'location': 'delhi',
        'user_agent': 'Dummy-device-testing11',
    }

    API_ENDPOINT = st.secrets["api"]["endpoint"]

    with st.spinner("Processing OCR..."):
        response_extra, time_taken_extra = send_request(
            st.session_state.file_paths, 
            headers, 
            form_data, 
            st.session_state.parser_info['extra_accuracy'], 
            API_ENDPOINT
        )
        response_no_extra, time_taken_no_extra = send_request(
            st.session_state.file_paths, 
            headers, 
            form_data, 
            False, 
            API_ENDPOINT
        )

    # Store responses and time taken in session_state
    st.session_state.response_extra = response_extra
    st.session_state.response_no_extra = response_no_extra
    st.session_state.time_taken_extra = time_taken_extra
    st.session_state.time_taken_no_extra = time_taken_no_extra

    display_ocr_results(response_extra, response_no_extra, time_taken_extra, time_taken_no_extra)

    # Generate comparison results if both responses are successful
    if response_extra and response_no_extra and response_extra.status_code == 200 and response_no_extra.status_code == 200:
        generate_and_display_comparisons()

        # Extract parser type from parser_info
        parser_type = get_parser_type(st.session_state.parser_selected)

        # Parse comparison results based on parser type
        parse_and_compile_results(parser_type, st.session_state.comparison_results)

        # Display compiled results and provide download option
        display_compiled_results()
    else:
        st.error("OCR processing failed for one or both requests.")
        logging.error("OCR processing failed for one or both requests.")

# ===========================
# 3. Define Main OCR Runner Function
# ===========================

def run_parser(parsers: Dict[str, Dict[str, Any]]):
    """
    Main function to handle OCR parsing, data extraction, and CSV generation.

    Args:
        parsers (dict): A dictionary of available parsers with their configurations.
    """
    # Initialize session_state at the start
    initialize_session_state()

    st.subheader("Run OCR Parser")
    if not parsers:
        st.info("No parsers available. Please add a parser first.")
        return

    # Add custom CSS for horizontal, scrollable radio buttons
    st.markdown("""
        <style>
        .stRadio [role=radiogroup] {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            gap: 10px;
        }
        div[role='radiogroup'] label div[data-testid='stMarkdownContainer'] {
            font-size: 18px;
            font-weight: bold;
            color: #FFFFFF;
        }
        div[role='radiogroup'] label {
            background-color: #2B2B2B;
            padding: 10px 15px;
            border-radius: 12px;
            border: 1px solid #3B3B3B;
            cursor: pointer;
            white-space: nowrap;
        }
        div[role='radiogroup'] label:hover {
            background-color: #474747;
        }
        div[role='radiogroup'] input[type='radio']:checked + label {
            background-color: #FF5F5F;
            border-color: #FF5F5F;
        }
        div[role='radiogroup'] input[type='radio']:checked + label div[data-testid='stMarkdownContainer'] {
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)

    # Convert parser selection into horizontal scrollable radio buttons
    parser_names = list(parsers.keys())
    selected_parser = st.radio("Select Parser", parser_names, key='parser_radio')
    parser_info = parsers[selected_parser]

    # Store selected parser in session_state
    set_session_state_key('parser_selected', selected_parser)
    set_session_state_key('parser_info', parser_info)

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")
    st.write(f"**Parser Type:** {parser_info.get('type', 'Unknown')}")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an image or PDF file... (Limit 20MB per file)", 
        type=["jpg", "jpeg", "png", "pdf"], 
        accept_multiple_files=False
    )

    if uploaded_file:
        if uploaded_file.size > 20 * 1024 * 1024:  # 20 MB limit
            st.error("File size exceeds the 20 MB limit. Please upload a smaller file.")
        else:
            try:
                if uploaded_file.type == "application/pdf":
                    # Handle PDF files
                    temp_dir = tempfile.mkdtemp()
                    st.session_state.temp_dirs.append(temp_dir)
                    pdf_path = os.path.join(temp_dir, uploaded_file.name)

                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    st.markdown(f"**Uploaded PDF:** {uploaded_file.name}")
                    st.session_state.file_paths.append(pdf_path)
                    st.session_state.image_names.append(uploaded_file.name)

                else:
                    # Handle image files
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    st.session_state.temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_file.name)
                    image.save(image_path)
                    st.session_state.file_paths.append(image_path)
                    st.session_state.image_names.append(uploaded_file.name)

                logging.info(f"Uploaded file: {uploaded_file.name}")

            except Exception as e:
                st.error(f"Error processing file {uploaded_file.name}: {e}")
                logging.error(f"Error processing file {uploaded_file.name}: {e}")

    # "Run OCR" and "Refresh" buttons
    col_run, col_refresh = st.columns([3, 1])
    with col_run:
        run_ocr = st.button("Run OCR")
    with col_refresh:
        refresh = st.button("Refresh")

    # Handle Refresh button
    if refresh:
        # Reset session state
        reset_session_state()
        st.success("All results have been cleared.")
        logging.info("Session state reset by user.")
        st.experimental_rerun()

    # Run OCR processing
    if run_ocr:
        run_ocr_process()
