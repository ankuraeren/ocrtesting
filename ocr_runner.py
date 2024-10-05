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
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Function to clean text for image
def clean_text_for_image(text):
    # Remove or replace any non-ASCII characters
    return re.sub(r'[^\x00-\x7F]+', ' ', text)

# Function to save results as a large JPEG image
def save_results_as_jpg(response_json_extra, response_json_no_extra, comparison_table, mismatch_df, file_paths):
    width, height = 1000, 3000  # Adjusted height to ensure all content fits
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
    draw.text((10, y_offset), text[:1000], font=font, fill=(0, 0, 0))  # Limiting text length to fit
    y_offset += 200

    draw.text((10, y_offset), "Results without Extra Accuracy:", font=font, fill=(0, 0, 0))
    y_offset += 20
    text = clean_text_for_image(json.dumps(response_json_no_extra, indent=4))
    draw.text((10, y_offset), text[:1000], font=font, fill=(0, 0, 0))  # Limiting text length to fit
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

# Function to generate a PDF from results
def create_pdf(response_json_extra, response_json_no_extra, comparison_table, mismatch_df, file_paths):
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, "ocr_results.pdf")
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Add file images to PDF
    y_offset = height - 40
    c.drawString(10, y_offset, "Uploaded Files:")
    y_offset -= 30
    for file_path in file_paths:
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')):
            try:
                img_file = Image.open(file_path)
                img_file.thumbnail((200, 200))
                img_file.save(os.path.join(temp_dir, 'temp_image.jpg'))
                c.drawImage(os.path.join(temp_dir, 'temp_image.jpg'), 10, y_offset - 150, width=150, height=150)
                y_offset -= 160
            except Exception as e:
                st.error(f"Error processing image {file_path} for PDF: {e}")

    # Add expanded JSONs to the PDF
    c.drawString(10, y_offset, "Results with Extra Accuracy:")
    y_offset -= 20
    text = clean_text_for_image(json.dumps(response_json_extra, indent=4))[:1000]
    c.drawString(10, y_offset, text)
    y_offset -= 200

    c.drawString(10, y_offset, "Results without Extra Accuracy:")
    y_offset -= 20
    text = clean_text_for_image(json.dumps(response_json_no_extra, indent=4))[:1000]
    c.drawString(10, y_offset, text)
    y_offset -= 200

    # Add comparison table to the PDF
    c.drawString(10, y_offset, "Comparison Table:")
    y_offset -= 20
    for i in range(len(comparison_table)):
        row = comparison_table.iloc[i]
        text = clean_text_for_image(f"{row['Attribute']}: {row['Result with Extra Accuracy']} vs {row['Result without Extra Accuracy']} - {row['Comparison']}")
        c.drawString(10, y_offset, text)
        y_offset -= 20

    # Add mismatched fields to the PDF
    c.drawString(10, y_offset, "Mismatched Fields:")
    y_offset -= 20
    for i in range(len(mismatch_df)):
        row = mismatch_df.iloc[i]
        text = clean_text_for_image(f"{row['Field']}: {row['Result with Extra Accuracy']} vs {row['Result without Extra Accuracy']}")
        c.drawString(10, y_offset, text)
        y_offset -= 20

    # Save the PDF
    c.showPage()
    c.save()
    return pdf_path

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
        </style>
    """, unsafe_allow_html=True)

    parser_names = list(parsers.keys())
    selected_parser = st.radio("Select Parser", parser_names)
    parser_info = parsers[selected_parser]

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

    file_paths = []
    temp_dirs = []

    uploaded_files = st.file_uploader("Choose image or PDF file(s)...", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "pdf"], accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.type == "application/pdf":
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    pdf_path = os.path.join(temp_dir, uploaded_file.name)

                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.markdown(f"**Uploaded PDF:** {uploaded_file.name}")
                    file_paths.append(pdf_path)

                else:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_file.name)
                    image.save(image_path)
                    file_paths.append(image_path)

            except Exception as e:
                st.error(f"Error processing file {uploaded_file.name}: {e}")

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

                st.session_state['response_json_extra'] = response_json_extra
                st.session_state['response_json_no_extra'] = response_json_no_extra
                st.session_state['comparison_table'] = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)
                st.session_state['mismatch_df'] = generate_mismatch_df(response_json_extra, response_json_no_extra, comparison_results)
                st.session_state['file_paths'] = file_paths

                st.subheader("Mismatched Fields")
                st.dataframe(st.session_state['mismatch_df'])

                st.subheader("Comparison Table")
                gb = GridOptionsBuilder.from_dataframe(st.session_state['comparison_table'])
                gb.configure_pagination(paginationAutoPageSize=True)
                gb.configure_side_bar()
                gb.configure_selection('single')
                grid_options = gb.build()

                st.download_button(
                    label="Download Results as PDF",
                    data=open(create_pdf(response_json_extra, response_json_no_extra, st.session_state['comparison_table'], st.session_state['mismatch_df'], st.session_state['file_paths']), "rb").read(),
                    file_name="ocr_results.pdf",
                    mime="application/pdf"
                )
