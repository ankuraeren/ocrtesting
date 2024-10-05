
### Updated ocr_runner.py ###

import os
import tempfile
import shutil
import streamlit as st
from PIL import Image
from PyPDF2 import PdfReader
from ocr_utils import send_request, generate_comparison_results, generate_comparison_df, generate_mismatch_df
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
from fpdf import FPDF
import base64

# Function to save results as PDF
def save_results_as_pdf(response_json_extra, response_json_no_extra, comparison_table, mismatch_df, file_paths):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Add images to the PDF
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 10, txt="Uploaded Files:", ln=True, align='L')
    for file_path in file_paths:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')):
            pdf.cell(200, 10, txt=os.path.basename(file_path), ln=True, align='L')
            pdf.image(file_path, x=10, w=100)

    # Add expanded JSONs to the PDF
    pdf.add_page()
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 10, txt="Results with Extra Accuracy:", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=json.dumps(response_json_extra, indent=4))

    pdf.add_page()
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 10, txt="Results without Extra Accuracy:", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=json.dumps(response_json_no_extra, indent=4))

    # Add comparison table to the PDF
    pdf.add_page()
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 10, txt="Comparison Table:", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    for i in range(len(comparison_table)):
        row = comparison_table.iloc[i]
        pdf.cell(200, 10, txt=f"{row['Attribute']}: {row['Result with Extra Accuracy']} vs {row['Result without Extra Accuracy']} - {row['Comparison']}", ln=True, align='L')

    # Add mismatched fields to the PDF
    pdf.add_page()
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 10, txt="Mismatched Fields:", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    for i in range(len(mismatch_df)):
        row = mismatch_df.iloc[i]
        pdf.cell(200, 10, txt=f"{row['Field']}: {row['Result with Extra Accuracy']} vs {row['Result without Extra Accuracy']}", ln=True, align='L')

    # Save the PDF
    pdf_filename = "ocr_results.pdf"
    pdf.output(pdf_filename)
    return pdf_filename

# Function to create a download link for the PDF
def create_download_link(file_path, link_text):
    with open(file_path, "rb") as f:
        pdf_data = f.read()
    b64 = base64.b64encode(pdf_data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_path}">{link_text}</a>'
    return href

# Main OCR parser function
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
    selected_parser = st.radio("Select Parser", parser_names)
    parser_info = parsers[selected_parser]

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

    file_paths = []
    temp_dirs = []

    # File uploader
    uploaded_files = st.file_uploader("Choose image or PDF file(s)...", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "pdf"], accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.type == "application/pdf":
                    # Handle PDF files
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    pdf_path = os.path.join(temp_dir, uploaded_file.name)

                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Display PDF filename
                    st.markdown(f"**Uploaded PDF:** {uploaded_file.name}")
                    file_paths.append(pdf_path)

                else:
                    # Handle image files
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_file.name)
                    image.save(image_path)
                    file_paths.append(image_path)

            except Exception as e:
                st.error(f"Error processing file {uploaded_file.name}: {e}")

    # Run OCR button
    if st.button("Run OCR"):
        if not file_paths:
            st.error("Please provide at least one image or PDF.")
            return

        headers = {
            'x-api-key': parser_info['api_key'],
        }

        form_data = {
            'parserApp': parser_info['parser_app_id'],
            'user_ip': '127.0.0.1',
            'location': 'delhi',
            'user_agent': 'Dummy-device-testing11',
        }

        API_ENDPOINT = st.secrets["api"]["endpoint"]

        with st.spinner("Processing OCR..."):
            response_extra, time_taken_extra = send_request(file_paths, headers, form_data, True, API_ENDPOINT)
            response_no_extra, time_taken_no_extra = send_request(file_paths, headers, form_data, False, API_ENDPOINT)

        # Store results in session state
        st.session_state['response_extra'] = response_extra
        st.session_state['response_no_extra'] = response_no_extra
        st.session_state['file_paths'] = file_paths
        st.session_state['temp_dirs'] = temp_dirs

    # Display results if available in session state
    if 'response_extra' in st.session_state and 'response_no_extra' in st.session_state:
        response_extra = st.session_state['response_extra']
        response_no_extra = st.session_state['response_no_extra']
        file_paths = st.session_state['file_paths']

        if response_extra and response_no_extra:
            success_extra = response_extra.status_code == 200
            success_no_extra = response_no_extra.status_code == 200

            if success_extra and success_no_extra:
                response_json_extra = response_extra.json()
                response_json_no_extra = response_no_extra.json()
                comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)

                # Display mismatched fields in a table
                st.subheader("Mismatched Fields")
                mismatch_df = generate_mismatch_df(response_json_extra, response_json_no_extra, comparison_results)
                st.dataframe(mismatch_df)

                # Display the comparison table
                st.subheader("Comparison Table")
                comparison_table = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)
                gb = GridOptionsBuilder.from_dataframe(comparison_table)
                gb.configure_pagination(paginationAutoPageSize=True)
                gb.configure_side_bar()
                gb.configure_selection('single')
                grid_options = gb.build()
                AgGrid(comparison_table, gridOptions=grid_options, height=300, theme='streamlit', enable_enterprise_modules=True)

                # Save as PDF button
                if st.button("Save Results as PDF"):
                    pdf_filename = save_results_as_pdf(response_json_extra, response_json_no_extra, comparison_table, mismatch_df, file_paths)
                    st.markdown(create_download_link(pdf_filename, "Click here to download the PDF"), unsafe_allow_html=True)
                    st.success("Results saved as ocr_results.pdf")
            else:
                st.error("Comparison failed. One or both requests were unsuccessful.")

        # Cleanup temporary directories
        if 'temp_dirs' in st.session_state:
            for temp_dir in st.session_state['temp_dirs']:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    st.warning(f"Could not remove temporary directory {temp_dir}: {e}")
