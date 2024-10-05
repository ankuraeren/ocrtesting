import os
import tempfile
import shutil
import streamlit as st
from PIL import Image
from PyPDF2 import PdfReader
from ocr_utils import send_request
from parser_utils import parse_comparison_results
from st_aggrid import AgGrid, GridOptionsBuilder
import json
import pandas as pd
import atexit

# ===========================
# 1. Define Helper Functions
# ===========================

def initialize_session_state():
    """
    Initialize all required session_state variables.
    """
    if 'file_paths' not in st.session_state:
        st.session_state.file_paths = []
    if 'temp_dirs' not in st.session_state:
        st.session_state.temp_dirs = []
    if 'image_names' not in st.session_state:
        st.session_state.image_names = []
    if 'response_extra' not in st.session_state:
        st.session_state.response_extra = None
    if 'response_no_extra' not in st.session_state:
        st.session_state.response_no_extra = None
    if 'time_taken_extra' not in st.session_state:
        st.session_state.time_taken_extra = None
    if 'time_taken_no_extra' not in st.session_state:
        st.session_state.time_taken_no_extra = None
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    if 'comparison_table' not in st.session_state:
        st.session_state.comparison_table = None
    if 'mismatch_df' not in st.session_state:
        st.session_state.mismatch_df = None
    if 'parser_selected' not in st.session_state:
        st.session_state.parser_selected = None
    if 'parser_info' not in st.session_state:
        st.session_state.parser_info = None
    if 'response_json_extra' not in st.session_state:
        st.session_state.response_json_extra = None
    if 'response_json_no_extra' not in st.session_state:
        st.session_state.response_json_no_extra = None
    if 'csv_data' not in st.session_state:
        st.session_state.csv_data = None
    if 'csv_filename' not in st.session_state:
        st.session_state.csv_filename = None
    if 'compiled_results' not in st.session_state:
        st.session_state.compiled_results = pd.DataFrame(columns=[
            'Document Name', 'Record_Type', 'Invoice Number', 'Shipper Name', 'Biller Name',
            'Invoice Date', 'Item Description', 'Unit Price', 'Quantity', 'Total Price',
            'Ledger ID', 'Account Name', 'Date', 'Transaction Description', 'Amount', 'Balance',
            'Name', 'Company', 'Position', 'Phone', 'Email'
        ])

def create_csv(compiled_results):
    """
    Save the compiled_results DataFrame to a CSV file and return its path.
    """
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "ocr_results.csv")

    # Save to CSV
    compiled_results.to_csv(csv_path, index=False)

    return csv_path

def cleanup_temp_dirs():
    """
    Cleanup all temporary directories stored in session_state.temp_dirs.
    """
    for temp_dir in st.session_state.temp_dirs:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            st.warning(f"Could not remove temporary directory {temp_dir}: {e}")
    st.session_state.temp_dirs = []

# Register cleanup on app exit
atexit.register(cleanup_temp_dirs)

# ===========================
# 2. Define Main OCR Parser Function
# ===========================

def run_parser(parsers):
    """
    Main function to handle OCR parsing, data extraction, and CSV generation.
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
    st.session_state.parser_selected = selected_parser
    st.session_state.parser_info = parser_info

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

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

            except Exception as e:
                st.error(f"Error processing file {uploaded_file.name}: {e}")

    # "Run OCR" and "Refresh" buttons
    col_run, col_refresh = st.columns([3, 1])
    with col_run:
        run_ocr = st.button("Run OCR")
    with col_refresh:
        refresh = st.button("Refresh")

    # Handle Refresh button
    if refresh:
        # Clear relevant session_state variables
        st.session_state.file_paths = []
        st.session_state.temp_dirs = []
        st.session_state.image_names = []
        st.session_state.response_extra = None
        st.session_state.response_no_extra = None
        st.session_state.time_taken_extra = None
        st.session_state.time_taken_no_extra = None
        st.session_state.comparison_results = None
        st.session_state.comparison_table = None
        st.session_state.mismatch_df = None
        st.session_state.parser_selected = None
        st.session_state.parser_info = None
        st.session_state.response_json_extra = None
        st.session_state.response_json_no_extra = None
        st.session_state.csv_data = None
        st.session_state.csv_filename = None
        st.session_state.compiled_results = pd.DataFrame(columns=[
            'Document Name', 'Record_Type', 'Invoice Number', 'Shipper Name', 'Biller Name',
            'Invoice Date', 'Item Description', 'Unit Price', 'Quantity', 'Total Price',
            'Ledger ID', 'Account Name', 'Date', 'Transaction Description', 'Amount', 'Balance',
            'Name', 'Company', 'Position', 'Phone', 'Email'
        ])
        st.experimental_rerun()

    # Run OCR processing
    if run_ocr:
        if not st.session_state.file_paths:
            st.error("Please upload at least one image or PDF before running OCR.")
        else:
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

            if response_extra and response_no_extra:
                success_extra = response_extra.status_code == 200
                success_no_extra = response_no_extra.status_code == 200

                # Display results in two columns
                col1, col2 = st.columns(2)

                if success_extra:
                    try:
                        response_json_extra = response_extra.json()
                        st.session_state.response_json_extra = response_json_extra
                        with col1:
                            st.expander(f"Results with Extra Accuracy - ⏱ {time_taken_extra:.2f}s").json(response_json_extra)
                    except json.JSONDecodeError:
                        with col1:
                            st.error("Failed to parse JSON response with Extra Accuracy.")
                else:
                    with col1:
                        st.error(f"Request with Extra Accuracy failed. Status code: {response_extra.status_code}")

                if success_no_extra:
                    try:
                        response_json_no_extra = response_no_extra.json()
                        st.session_state.response_json_no_extra = response_json_no_extra
                        with col2:
                            st.expander(f"Results without Extra Accuracy - ⏱ {time_taken_no_extra:.2f}s").json(response_json_no_extra)
                    except json.JSONDecodeError:
                        with col2:
                            st.error("Failed to parse JSON response without Extra Accuracy.")
                else:
                    with col2:
                        st.error(f"Request without Extra Accuracy failed. Status code: {response_no_extra.status_code}")

                # Generate comparison results
                if success_extra and success_no_extra:
                    comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)
                    st.session_state.comparison_results = comparison_results

                    # Generate mismatch DataFrame
                    mismatch_df = generate_mismatch_df(response_json_extra, response_json_no_extra, comparison_results)
                    st.session_state.mismatch_df = mismatch_df

                    # Generate comparison DataFrame
                    comparison_table = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)
                    st.session_state.comparison_table = comparison_table

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

                    # Extract parser type from parser_info
                    parser_type = st.session_state.parser_info.get('type', 'unknown')

                    # Parse comparison results based on parser type
                    parsed_df = parse_comparison_results(parser_type, comparison_results)

                    if not parsed_df.empty:
                        # Append parsed data to compiled_results
                        st.session_state.compiled_results = pd.concat(
                            [st.session_state.compiled_results, parsed_df],
                            ignore_index=True
                        )

                        # Show cumulative results so far
                        st.subheader("Cumulative Results")
                        st.dataframe(st.session_state.compiled_results)

                        # Generate and provide the CSV download
                        csv_file_path = create_csv(st.session_state.compiled_results)
                        with open(csv_file_path, "rb") as csv_file:
                            st.session_state.csv_data = csv_file.read()
                            st.session_state.csv_filename = "ocr_results.csv"

                        st.download_button(
                            label="Download OCR Results as CSV",
                            data=st.session_state.csv_data,
                            file_name=st.session_state.csv_filename,
                            mime="text/csv"
                        )
                    else:
                        st.error("Parsed DataFrame is empty. Check parser logic.")
                else:
                    st.error("Comparison failed. One or both requests were unsuccessful.")
            else:
                st.error("OCR processing failed. Please try again.")
