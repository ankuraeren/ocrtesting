
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
            try:
                # Convert unsupported image formats to JPEG
                img = Image.open(file_path)
                if file_path.lower().endswith(('.png', '.bmp', '.gif', '.tiff')):
                    rgb_im = img.convert('RGB')
                    converted_path = file_path + ".jpg"
                    rgb_im.save(converted_path, format="JPEG")
                    file_path = converted_path
                pdf.cell(200, 10, txt=os.path.basename(file_path), ln=True, align='L')
                pdf.image(file_path, x=10, w=100)
            except Exception as e:
                st.error(f"Error processing image {file_path} for PDF: {e}")

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
            padding: 10px 15px
