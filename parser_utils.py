# parser_utils.py

import streamlit as st
import json
import base64
from urllib.parse import quote
from github_utils import download_parsers_from_github, upload_parsers_to_github
from ocr_runner import run_parser  # Ensure run_parser is correctly defined in ocr_runner.py
from parser_utils import add_new_parser, list_parsers  # Remove this line to prevent self-import
from ocr_utils import (
    flatten_json, 
    generate_comparison_results, 
    generate_comparison_df, 
    generate_mismatch_df, 
    send_request, 
    create_csv
)
import pandas as pd

# Define the path to the local parsers.json
LOCAL_PARSERS_FILE = "parsers.json"  # Adjust the path as needed

def save_parsers():
    try:
        with open(LOCAL_PARSERS_FILE, 'w') as f:
            json.dump(st.session_state['parsers'], f, indent=4)
    except Exception as e:
        st.error(f"Error saving parsers: {e}")

def add_new_parser():
    st.subheader("Add a New Parser")
    with st.form("add_parser_form"):
        parser_name = st.text_input("Parser Name").strip()
        api_key = st.text_input("API Key").strip()
        parser_app_id = st.text_input("Parser App ID").strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy")
        expected_response = st.text_area("Expected JSON Response (optional)")
        sample_curl = st.text_area("Sample CURL Request (optional)")
        parser_type = st.selectbox("Parser Type", ["invoice", "ledger", "visiting_card", "other"])  # Dynamic types

        submitted = st.form_submit_button("Add Parser")
        if submitted:
            if not parser_name or not api_key or not parser_app_id or not parser_type:
                st.error("Please fill in all required fields.")
            elif parser_name in st.session_state['parsers']:
                st.error(f"Parser '{parser_name}' already exists.")
            else:
                st.session_state['parsers'][parser_name] = {
                    'api_key': api_key,
                    'parser_app_id': parser_app_id,
                    'extra_accuracy': extra_accuracy,
                    'expected_response': expected_response,
                    'sample_curl': sample_curl,
                    'type': parser_type
                }
                save_parsers()
                st.success("The parser has been added successfully.")

def list_parsers():
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
            st.write(f"**Type:** {details.get('type', 'Unknown')}")

            app_id_num = app_id_count[details['parser_app_id']]  # Get the number associated with parser_app_id
            parser_page_link = f"https://ocrtesting-csxcl7uybqbmwards96kjo.streamlit.app/?parser={quote(parser_name)}&client=true&id={app_id_num}"

            # Generate and display link button
            if st.button(f"Generate Parser Page for {parser_name}", key=f"generate_{parser_name}"):
                st.write(f"**Parser Page Link:** [Click Here]({parser_page_link})")
                
            # Add Delete button
            if st.button(f"Delete {parser_name}", key=f"delete_{parser_name}"):
                del st.session_state['parsers'][parser_name]
                save_parsers()
                st.success(f"Parser '{parser_name}' has been deleted.")

def extract_data_based_on_parser_type(parser_type, comparison_results):
    """
    Extracts data based on the parser type.
    """
    if parser_type == 'invoice':
        return parse_invoice(comparison_results)
    elif parser_type == 'ledger':
        return parse_ledger(comparison_results)
    elif parser_type == 'visiting_card':
        return parse_visiting_card(comparison_results)
    else:
        st.warning(f"Unsupported parser type: {parser_type}. Data extraction may be incomplete.")
        return pd.DataFrame()

def parse_invoice(comparison_results):
    """
    Parses invoice data into a structured DataFrame.
    """
    # Placeholder extraction logic - replace with actual extraction based on comparison_results
    main_header = {
        'Invoice Number': comparison_results.get('Invoice Number', 'N/A'),
        'Document Name': comparison_results.get('Document Name', 'N/A')
    }

    invoice_header = {
        'Shipper Name': comparison_results.get('Shipper Name', 'N/A'),
        'Biller Name': comparison_results.get('Biller Name', 'N/A'),
        'Invoice Date': comparison_results.get('Invoice Date', 'N/A'),
        'Invoice Number': main_header['Invoice Number'],
        'Document Name': main_header['Document Name']
    }

    line_items = [
        {
            'Item Description': comparison_results.get('Item Description.0', 'N/A'),
            'Unit Price': comparison_results.get('Unit Price.0', 0),
            'Quantity': comparison_results.get('Quantity.0', 0),
            'Total Price': comparison_results.get('Total Price.0', 0)
        },
        {
            'Item Description': comparison_results.get('Item Description.1', 'N/A'),
            'Unit Price': comparison_results.get('Unit Price.1', 0),
            'Quantity': comparison_results.get('Quantity.1', 0),
            'Total Price': comparison_results.get('Total Price.1', 0)
        }
        # Add more line items as needed
    ]

    # Convert the data into DataFrames
    main_header_df = pd.DataFrame([main_header])
    main_header_df['Record_Type'] = 'Main Header'
    main_header_df['Invoice Number'] = main_header.get('Invoice Number', '')
    main_header_df['Shipper Name'] = ''
    main_header_df['Biller Name'] = ''
    main_header_df['Invoice Date'] = ''
    main_header_df['Item Description'] = ''
    main_header_df['Unit Price'] = ''
    main_header_df['Quantity'] = ''
    main_header_df['Total Price'] = ''

    invoice_header_df = pd.DataFrame([invoice_header])
    invoice_header_df['Record_Type'] = 'Invoice Header'
    invoice_header_df['Invoice Number'] = invoice_header.get('Invoice Number', '')
    invoice_header_df['Shipper Name'] = invoice_header.get('Shipper Name', '')
    invoice_header_df['Biller Name'] = invoice_header.get('Biller Name', '')
    invoice_header_df['Invoice Date'] = invoice_header.get('Invoice Date', '')
    invoice_header_df['Item Description'] = ''
    invoice_header_df['Unit Price'] = ''
    invoice_header_df['Quantity'] = ''
    invoice_header_df['Total Price'] = ''

    line_items_df = pd.DataFrame(line_items)
    line_items_df['Record_Type'] = 'Line Item'
    line_items_df['Invoice Number'] = invoice_header.get('Invoice Number', '')
    line_items_df['Shipper Name'] = ''
    line_items_df['Biller Name'] = ''
    line_items_df['Invoice Date'] = ''
    line_items_df['Document Name'] = invoice_header.get('Document Name', '')

    # Concatenate all DataFrames
    parsed_df = pd.concat([main_header_df, invoice_header_df, line_items_df], ignore_index=True)
    return parsed_df

def parse_ledger(comparison_results):
    """
    Parses ledger data into a structured DataFrame.
    """
    # Placeholder extraction logic - replace with actual extraction based on comparison_results
    ledger_header = {
        'Ledger ID': comparison_results.get('Ledger ID', 'N/A'),
        'Account Name': comparison_results.get('Account Name', 'N/A'),
        'Date': comparison_results.get('Date', 'N/A'),
        'Document Name': comparison_results.get('Document Name', 'N/A')
    }

    line_items = [
        {
            'Transaction Description': comparison_results.get('Transaction Description.0', 'N/A'),
            'Amount': comparison_results.get('Amount.0', 0),
            'Balance': comparison_results.get('Balance.0', 0)
        },
        {
            'Transaction Description': comparison_results.get('Transaction Description.1', 'N/A'),
            'Amount': comparison_results.get('Amount.1', 0),
            'Balance': comparison_results.get('Balance.1', 0)
        }
        # Add more line items as needed
    ]

    # Convert the data into DataFrames
    ledger_header_df = pd.DataFrame([ledger_header])
    ledger_header_df['Record_Type'] = 'Ledger Header'
    ledger_header_df['Ledger ID'] = ledger_header.get('Ledger ID', '')
    ledger_header_df['Account Name'] = ledger_header.get('Account Name', '')
    ledger_header_df['Date'] = ledger_header.get('Date', '')
    ledger_header_df['Transaction Description'] = ''
    ledger_header_df['Amount'] = ''
    ledger_header_df['Balance'] = ''

    line_items_df = pd.DataFrame(line_items)
    line_items_df['Record_Type'] = 'Ledger Line Item'
    line_items_df['Ledger ID'] = ledger_header.get('Ledger ID', '')
    line_items_df['Account Name'] = ''
    line_items_df['Date'] = ''
    line_items_df['Transaction Description'] = line_items_df.get('Transaction Description', '')
    line_items_df['Amount'] = line_items_df.get('Amount', 0)
    line_items_df['Balance'] = line_items_df.get('Balance', 0)
    line_items_df['Document Name'] = ledger_header.get('Document Name', '')

    # Concatenate all DataFrames
    parsed_df = pd.concat([ledger_header_df, line_items_df], ignore_index=True)
    return parsed_df

def parse_visiting_card(comparison_results):
    """
    Parses visiting card data into a structured DataFrame.
    """
    # Placeholder extraction logic - replace with actual extraction based on comparison_results
    header = {
        'Name': comparison_results.get('Name', 'N/A'),
        'Company': comparison_results.get('Company', 'N/A'),
        'Position': comparison_results.get('Position', 'N/A'),
        'Document Name': comparison_results.get('Document Name', 'N/A')
    }

    contact_info = [
        {
            'Phone': comparison_results.get('Phone.0', 'N/A'),
            'Email': comparison_results.get('Email.0', 'N/A')
        },
        {
            'Phone': comparison_results.get('Phone.1', 'N/A'),
            'Email': comparison_results.get('Email.1', 'N/A')
        }
        # Add more contact info as needed
    ]

    # Convert the data into DataFrames
    header_df = pd.DataFrame([header])
    header_df['Record_Type'] = 'Visiting Card Header'
    header_df['Name'] = header.get('Name', '')
    header_df['Company'] = header.get('Company', '')
    header_df['Position'] = header.get('Position', '')
    header_df['Document Name'] = header.get('Document Name', '')
    header_df['Phone'] = ''
    header_df['Email'] = ''

    contact_info_df = pd.DataFrame(contact_info)
    contact_info_df['Record_Type'] = 'Visiting Card Contact'
    contact_info_df['Name'] = header.get('Name', '')
    contact_info_df['Company'] = ''
    contact_info_df['Position'] = ''
    contact_info_df['Document Name'] = header.get('Document Name', '')
    contact_info_df['Phone'] = contact_info_df.get('Phone', 'N/A')
    contact_info_df['Email'] = contact_info_df.get('Email', 'N/A')

    # Concatenate all DataFrames
    parsed_df = pd.concat([header_df, contact_info_df], ignore_index=True)
    return parsed_df

def extract_data_based_on_parser_type(parser_type, comparison_results):
    """
    Extracts data based on the parser type.
    """
    if parser_type == 'invoice':
        return parse_invoice(comparison_results)
    elif parser_type == 'ledger':
        return parse_ledger(comparison_results)
    elif parser_type == 'visiting_card':
        return parse_visiting_card(comparison_results)
    else:
        st.warning(f"Unsupported parser type: {parser_type}. Data extraction may be incomplete.")
        return pd.DataFrame()

def run_parser(parsers):
    """
    Main function to handle OCR parsing, data extraction, and CSV generation.
    """
    # Initialize session_state at the start
    if 'file_paths' not in st.session_state:
        st.session_state.file_paths = []
    if 'temp_dirs' not in st.session_state:
        st.session_state.temp_dirs = []
    if 'image_names' not in st.session_state:
        st.session_state.image_names = []
    if 'parsers' not in st.session_state:
        st.session_state['parsers'] = {}
    if 'compiled_results' not in st.session_state:
        st.session_state.compiled_results = pd.DataFrame()

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
        st.session_state.compiled_results = pd.DataFrame()
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
                    parsed_df = extract_data_based_on_parser_type(parser_type, comparison_results)

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
