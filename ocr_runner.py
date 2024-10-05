import os
import tempfile
import shutil
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfReader
from ocr_utils import send_request, generate_comparison_results, generate_comparison_df, generate_mismatch_df
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import json
import re

# Function to clean text for image
def clean_text_for_image(text):
    # Remove or replace any non-ASCII characters
    return re.sub(r'[^     return re.sub(r'[^\x00-    return re.sub(r'[^\x00-\x7F]+', ' ', text)

# Function to save results as a large JPEG image
def save_results_as_jpg(response_json_extra, response_json_no_extra, comparison_table, mismatch_df, file_paths):
    width, height = 1000, 1500
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    y_offset = 10

    # Add images to the JPEG
    draw.text((10, y_offset), "Uploaded Files:", font=font, fill=(0, 0, 0))
    y_offset += 20
    for file_path in file_paths:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')):
            try:
                img_file = Image.open(file_path)
                img_file.thumbnail((200, 200))
                img.paste(img_file, (10, y_offset))
                y_offset += img_file.height + 10
            except Exception as e:
                st.error(f"Error processing image {file_path} for JPEG: {e}")

    # Add expanded JSONs to the JPEG
    y_offset += 20
    draw.text((10, y_offset), "Results with Extra Accuracy:", font=font, fill=(0, 0, 0))
    y_offset += 20
    text = clean_text_for_image(json.dumps(response_json_extra, indent=4))
    draw.text((10, y_offset), text, font=font, fill=(0, 0, 0))
    y_offset += 200

    draw.text((10, y_offset), "Results without Extra Accuracy:", font=font, fill=(0, 0, 0))
    y_offset += 20
    text = clean_text_for_image(json.dumps(response_json_no_extra, indent=4))
    draw.text((10, y_offset), text, font=font, fill=(0, 0, 0))
    y_offset += 200

    # Add comparison table to the JPEG
    draw.text((10, y_offset), "Comparison Table:", font=font, fill=(0, 0, 0))
    y_offset += 20
    for i in range(len(comparison_table)):
        row = comparison_table.iloc[i]
        text = clean_text_for_image(f"{row['Attribute']}: {row['Result with Extra Accuracy']} vs {row['Result without Extra Accuracy']} - {row['Comparison']}")
        draw.text((10, y_offset), text, font=font, fill=(0, 0, 0))
        y_offset += 20

    # Add mismatched fields to the JPEG
    y_offset += 20
    draw.text((10, y_offset), "Mismatched Fields:", font=font, fill=(0, 0, 0))
    y_offset += 20
    for i in range(len(mismatch_df)):
        row = mismatch_df.iloc[i]
        text = clean_text_for_image(f"{row['Field']}: {row['Result with Extra Accuracy']} vs {row['Result without Extra Accuracy']}")
        draw.text((10, y_offset), text, font=font, fill=(0, 0, 0))
        y_offset += 20

    # Save the JPEG
    temp_dir = tempfile.mkdtemp()
    jpg_filename = os.path.join(temp_dir, "ocr_results.jpg")
    img.save(jpg_filename)
    return jpg_filename

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

        if response_extra and response_no_extra:
            success_extra = response_extra.status_code == 200
            success_no_extra = response_no_extra.status_code == 200

            if success_extra and success_no_extra:
                response_json_extra = response_extra.json()
                response_json_no_extra = response_no_extra.json()
                comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)

                # Store results in session state to prevent loss during rerun
                st.session_state['response_json_extra'] = response_json_extra
                st.session_state['response_json_no_extra'] = response_json_no_extra
                st.session_state['comparison_table'] = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)
                st.session_state['mismatch_df'] = generate_mismatch_df(response_json_extra, response_json_no_extra, comparison_results)
                st.session_state['file_paths'] = file_paths

                # Display mismatched fields in a table
                st.subheader("Mismatched Fields")
                st.dataframe(st.session_state['mismatch_df'])

                # Display the comparison table
                st.subheader("Comparison Table")
                gb = GridOptionsBuilder.from_dataframe(st.session_state['comparison_table'])
                gb.configure_pagination(paginationAutoPageSize=True)
                gb.configure_side_bar()
                gb.configure_selection('single')
                grid_options = gb.build()
                AgGrid(st.session_state['comparison_table'], gridOptions=grid_options, height=300, theme='streamlit', enable_enterprise_modules=True)

                # Generate JPEG and store in session state
                if 'jpg_filename' not in st.session_state:
                    jpg_filename = save_results_as_jpg(response_json_extra, response_json_no_extra, st.session_state['comparison_table'], st.session_state['mismatch_df'], file_paths)
                    st.session_state['jpg_filename'] = jpg_filename

                # Download JPEG button
                if 'jpg_filename' in st.session_state:
                    with open(st.session_state['jpg_filename'], "rb") as jpg_file:
                        JPGbyte = jpg_file.read()
                    st.download_button(label="Download Results as JPEG", data=JPGbyte, file_name="ocr_results.jpg", mime="image/jpeg")

        # Cleanup temporary directories after JPEG
