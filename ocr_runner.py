import streamlit as st
from PIL import Image
import fitz  # Correct import for PyMuPDF
import tempfile
import os
import shutil

import streamlit as st
from PIL import Image
import PyMuPDF  # PyMuPDF (or fitz) to handle PDFs
import tempfile
import os

# Function to handle image and PDF upload
def handle_file_upload(uploaded_files):
    """Process uploaded image or PDF files and convert PDFs to images."""
    image_paths = []
    temp_dirs = []

    for uploaded_file in uploaded_files:
        file_type = uploaded_file.type
        temp_dir = tempfile.mkdtemp()  # Create a temporary directory
        temp_dirs.append(temp_dir)

        # Save the uploaded file to the temp directory first
        file_path = os.path.join(temp_dir, uploaded_file.name)

        # Write the uploaded file to the temporary file path
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        # Handling Image files (jpg, png, etc.)
        if file_type in ["image/jpeg", "image/png"]:
            image = Image.open(file_path)
            image_paths.append(file_path)
            st.image(image, caption=uploaded_file.name, use_column_width=True)

        # Handling PDF files
        elif file_type == "application/pdf":
            pdf_reader = PyMuPDF.open(file_path)
            for page_num in range(pdf_reader.page_count):
                page = pdf_reader.load_page(page_num)
                image = page.get_pixmap()
                image_path = os.path.join(temp_dir, f"page_{page_num + 1}.png")
                image.save(image_path)
                image_paths.append(image_path)
                st.image(image_path, caption=f"Page {page_num + 1} from {uploaded_file.name}", use_column_width=True)
        else:
            st.error(f"Unsupported file type: {file_type}")

    return image_paths, temp_dirs



def run_parser(parsers):
    """Run the selected OCR parser."""
    st.subheader("Run OCR Parser")
    if not parsers:
        st.info("No parsers available. Please add a parser first.")
        return

    # Parser selection dropdown
    parser_names = list(parsers.keys())
    selected_parser = st.selectbox("Select Parser", parser_names)
    parser_info = parsers[selected_parser]

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Parser App ID:** {parser_info['parser_app_id']}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

    # Adding file upload section
    input_method = st.radio("Choose Input Method", ("Upload Image/PDF File", "Enter Image URL"))

    image_paths = []
    temp_dirs = []

    if input_method == "Upload Image/PDF File":
        # Allow uploading multiple image or PDF files
        uploaded_files = st.file_uploader(
            "Choose image or PDF file(s)...",
            type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "pdf"],  # Supports image and PDF file types
            accept_multiple_files=True
        )
        if uploaded_files:
            image_paths, temp_dirs = handle_file_upload(uploaded_files)
    
    elif input_method == "Enter Image URL":
        # Handle URL input (if needed)
        image_urls = st.text_area("Enter Image URLs (one per line)")
        # Process URLs here...
    
    if st.button("Run OCR"):
        if not image_paths:
            st.error("Please provide at least one image or PDF.")
            return
        
        # Proceed with OCR processing (e.g., send images to OCR API)
        # ...

        # Cleanup temporary directories
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir)
