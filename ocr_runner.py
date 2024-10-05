import os
import tempfile
import shutil
import streamlit as st
from PIL import Image
from PyPDF2 import PdfReader
from ocr_utils import send_request, generate_comparison_results, generate_comparison_df, generate_mismatch_df
from st_aggrid import AgGrid, GridOptionsBuilder
import json
import pandas as pd
import atexit

# ===========================
# 1. Initialize session_state
# ===========================

# Initialize session_state variables
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

# ===========================
# 2. Define Helper Functions
# ===========================

def create_csv(main_header_df, invoice_header_df, line_items_df):
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "ocr_results.csv")

    # Combine all DataFrames with appropriate labels
    main_header_df['Record_Type'] = 'Main Header'
    invoice_header_df['Record_Type'] = 'Invoice Header'
    line_items_df['Record_Type'] = 'Line Item'

    # Concatenate all DataFrames
    combined_df = pd.concat([main_header_df, invoice_header_df, line_items_df], ignore_index=True)

    # Save to CSV
    combined_df.to_csv(csv_path, index=False)

    return csv_path


def cleanup_temp_dirs():
    for temp_dir in st.session_state.temp_dirs:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            st.warning(f"Could not remove temporary directory {temp_dir}: {e}")
    st.session_state.temp_dirs = []

# Register cleanup on app exit
atexit.register(cleanup_temp_dirs)

# ===========================
# 3. Define Main OCR Parser Function
# ===========================

def run_parser(parsers):
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
    uploaded_files = st.file_uploader(
        "Choose image or PDF file(s)... (Limit 20MB per file)", 
        type=["jpg", "jpeg", "png", "pdf"], 
        accept_multiple_files=False
    )

    if uploaded_files:
        if uploaded_files.size > 20 * 1024 * 1024:  # 20 MB limit
            st.error("File size exceeds the 20 MB limit. Please upload a smaller file.")
        else:
            try:
                if uploaded_files.type == "application/pdf":
                    temp_dir = tempfile.mkdtemp()
                    st.session_state.temp_dirs.append(temp_dir)
                    pdf_path = os.path.join(temp_dir, uploaded_files.name)

                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_files.getbuffer())

                    st.markdown(f"**Uploaded PDF:** {uploaded_files.name}")
                    st.session_state.file_paths.append(pdf_path)
                    st.session_state.image_names.append(uploaded_files.name)

                else:
                    image = Image.open(uploaded_files)
                    st.image(image, caption=uploaded_files.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    st.session_state.temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_files.name)
                    image.save(image_path)
                    st.session_state.file_paths.append(image_path)
                    st.session_state.image_names.append(uploaded_files.name)

            except Exception as e:
                st.error(f"Error processing file {uploaded_files.name}: {e}")

    # "Run OCR" and "Refresh" buttons
    col_run, col_refresh = st.columns([3, 1])
    with col_run:
        run_ocr = st.button("Run OCR")
    with col_refresh:
        refresh = st.button("Refresh")

    # Handle Refresh button
    if refresh:
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
                    True, 
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

                # Store results from both extra accuracy and no extra accuracy cases
                if success_extra and success_no_extra:
                    try:
                        response_json_extra = response_extra.json()
                        st.session_state.response_json_extra = response_json_extra
                        response_json_no_extra = response_no_extra.json()
                        st.session_state.response_json_no_extra = response_json_no_extra

                        # Display the results and let user download CSV
                        main_header = {
                            'Invoice Number': 'INV001',  # Example, replace with actual data
                            'Document Name': uploaded_files.name
                        }
                        invoice_header = {
                            'Shipper Name': 'Acme Corp',
                            'Biller Name': 'Global Inc',
                            'Invoice Date': '2023-10-05',
                            'Document Name': uploaded_files.name
                        }
                        line_items = [
                            {'Item Description': 'Item 1', 'Unit Price': 100.00, 'Quantity': 2, 'Total Price': 200.00},
                            {'Item Description': 'Item 2', 'Unit Price': 50.00, 'Quantity': 4, 'Total Price': 200.00}
                        ]

                        # Convert the data into DataFrames
                        main_header_df = pd.DataFrame([main_header])
                        invoice_header_df = pd.DataFrame([invoice_header])
                        line_items_df = pd.DataFrame(line_items)

                        # Generate CSV with multi-level data
                        csv_file_path = create_csv(main_header_df, invoice_header_df, line_items_df)

                        with open(csv_file_path, "rb") as csv_file:
                            st.session_state.csv_data = csv_file.read()
                            st.session_state.csv_filename = "ocr_results.csv"

                        # Download the CSV
                        st.download_button(
                            label="Download Invoice Results as CSV",
                            data=st.session_state.csv_data,
                            file_name=st.session_state.csv_filename,
                            mime="text/csv"
                        )

                    except json.JSONDecodeError:
                        st.error("Failed to parse JSON response.")

            else:
                st.error("OCR processing failed. Please try again.")
