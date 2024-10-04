import requests
import streamlit as st
from PIL import Image
import os
import tempfile
import shutil
import time
import logging

# Handles running the OCR parser on uploaded images
def run_parser(parsers):
    st.subheader("Run OCR Parser")
    if not parsers:
        st.info("No parsers available. Please add a parser first.")
        return

    parser_names = list(parsers.keys())
    selected_parser = st.selectbox("Select Parser", parser_names)
    parser_info = parsers[selected_parser]

    input_method = st.radio("Input Method", ("Upload Image", "Image URL"))

    image_paths = []
    images = []
    temp_dirs = []

    # Handle image upload or URL input
    if input_method == "Upload Image":
        uploaded_files = st.file_uploader("Choose image...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                images.append(image)
                temp_dir = tempfile.mkdtemp()
                temp_dirs.append(temp_dir)
                image_path = os.path.join(temp_dir, uploaded_file.name)
                image.save(image_path)
                image_paths.append(image_path)
    else:
        image_url = st.text_input("Image URL")
        if image_url:
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                image = Image.open(response.raw)
                images.append(image)
                temp_dir = tempfile.mkdtemp()
                temp_dirs.append(temp_dir)
                image_filename = os.path.basename(image_url)
                image_path = os.path.join(temp_dir, image_filename)
                image.save(image_path)
                image_paths.append(image_path)
            else:
                st.error("Error fetching image from URL.")

    if st.button("Run OCR"):
        if not image_paths:
            st.error("Please upload or enter an image URL.")
            return

        headers = {'x-api-key': parser_info['api_key']}
        data = {'parserApp': parser_info['parser_app_id']}

        # Send OCR request
        with st.spinner("Running OCR..."):
            files = [('file', (os.path.basename(path), open(path, 'rb'), 'image/jpeg')) for path in image_paths]
            try:
                response = requests.post(st.secrets["api"]["endpoint"], headers=headers, data=data, files=files)
                if response.status_code == 200:
                    st.json(response.json())
                else:
                    st.error(f"OCR failed with status code {response.status_code}")
            except Exception as e:
                st.error(f"Error running OCR: {e}")

        # Cleanup temporary files
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir)
