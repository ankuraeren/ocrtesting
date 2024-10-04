import streamlit as st
from PIL import Image
import fitz  # Correct import for PyMuPDF
import tempfile
import os
import shutil
import requests

# Function to handle image and PDF upload
def handle_file_upload(uploaded_files):
    """Process uploaded image or PDF files and convert PDFs to images."""
    image_paths = []
    temp_dirs = []
    
    for uploaded_file in uploaded_files:
        file_type = uploaded_file.type
        temp_dir = tempfile.mkdtemp()  # Create a temporary directory
        temp_dirs.append(temp_dir)

        # Handling Image files (jpg, png, etc.)
        if file_type in ["image/jpeg", "image/png"]:
            image = Image.open(uploaded_file)
            image_path = os.path.join(temp_dir, uploaded_file.name)
            image.save(image_path)
            image_paths.append(image_path)
            st.image(image, caption=uploaded_file.name, use_column_width=True)

        # Handling PDF files
        elif file_type == "application/pdf":
            # Save uploaded PDF as a temporary file
            pdf_path = os.path.join(temp_dir, uploaded_file.name)
            with open(pdf_path, 'wb') as f:
                f.write(uploaded_file.read())  # Write the uploaded file to disk
            
            # Open the saved PDF using PyMuPDF
            pdf_reader = fitz.open(pdf_path)  # Now, fitz can read it from a valid path
            for page_num in range(pdf_reader.page_count):
                page = pdf_reader.load_page(page_num)
                pix = page.get_pixmap()
                image_path = os.path.join(temp_dir, f"page_{page_num + 1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
                st.image(image_path, caption=f"Page {page_num + 1} from {uploaded_file.name}", use_column_width=True)

        else:
            st.error(f"Unsupported file type: {file_type}")

    return image_paths, temp_dirs


# Function to send images to OCR API
def send_to_ocr_api(image_paths, parser_info):
    """Send the images to the OCR API and return the result."""
    headers = {
        'x-api-key': parser_info['api_key'],  # Replace with correct API key header
    }

    form_data = {
        'parserApp': parser_info['parser_app_id'],
        'user_ip': '127.0.0.1',
        'location': 'delhi',
        'user_agent': 'Dummy-device-testing11',
    }

    files = []
    for image_path in image_paths:
        with open(image_path, 'rb') as file:
            file_extension = os.path.splitext(image_path)[1].lower()
            mime_type = f"image/{file_extension[1:]}" if file_extension != ".pdf" else "application/pdf"
            files.append(('file', (os.path.basename(image_path), file, mime_type)))

    # Retrieve the API endpoint from Streamlit secrets
    api_endpoint = st.secrets["api"]["endpoint"]

    try:
        response = requests.post(api_endpoint, headers=headers, data=form_data, files=files)
        response.raise_for_status()  # Raise exception for any errors
        return response.json()  # Assuming the API returns JSON response

    except requests.exceptions.RequestException as e:
        st.error(f"Error in OCR request: {e}")
        return None


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
        
        # Proceed with OCR processing
        with st.spinner("Processing OCR..."):
            ocr_response = send_to_ocr_api(image_paths, parser_info)

        # Display OCR result
        if ocr_response:
            st.success("OCR processing complete!")
            st.json(ocr_response)  # Display OCR result as JSON

        # Cleanup temporary directories
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir)

