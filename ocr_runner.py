# parsers/ocr_runner.py

import os
import json
import requests
import streamlit as st
import logging
import tempfile
import shutil
from PIL import Image
from io import BytesIO
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import base64
import time

from ..utils.helpers import flatten_json, generate_comparison_results, generate_comparison_df


def run_parser(parsers):
    st.subheader("Run OCR Parser")
    if not parsers:
        st.info("No parsers available. Please add a parser first.")
        return

    parser_names = list(parsers.keys())
    selected_parser = st.selectbox("Select Parser", parser_names)
    parser_info = parsers[selected_parser]

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Parser App ID:** {parser_info['parser_app_id']}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

    input_method = st.radio("Choose Input Method", ("Upload Image File", "Enter Image URL"))

    image_paths = []
    images = []
    temp_dirs = []

    if input_method == "Upload Image File":
        uploaded_files = st.file_uploader(
            "Choose image(s)...",
            type=["jpg", "jpeg", "png", "bmp", "gif", "tiff"],
            accept_multiple_files=True
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    image = Image.open(uploaded_file)
                    images.append(image)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_file.name)
                    image.save(image_path)
                    image_paths.append(image_path)
                except Exception as e:
                    st.error(f"Error processing file {uploaded_file.name}: {e}")
                    logging.error(f"Error processing file {uploaded_file.name}: {e}")
    else:
        image_urls = st.text_area("Enter Image URLs (one per line)")
        if image_urls:
            urls = image_urls.strip().split('\n')
            for url in urls:
                try:
                    response = requests.get(url.strip(), stream=True, timeout=30)
                    if response.status_code == 200:
                        image = Image.open(BytesIO(response.content))
                        images.append(image)
                        image_caption = os.path.basename(url.split('?')[0]) or "Image"
                        st.image(image, caption=image_caption, use_column_width=True)
                        temp_dir = tempfile.mkdtemp()
                        temp_dirs.append(temp_dir)
                        image_filename = os.path.basename(url.split('?')[0]) or "image.jpg"
                        image_path = os.path.join(temp_dir, image_filename)
                        with open(image_path, 'wb') as f:
                            shutil.copyfileobj(response.raw, f)
                        image_paths.append(image_path)
                    else:
                        st.error(f"Failed to download image from {url}. Status Code: {response.status_code}")
                        logging.error(f"Failed to download image from {url}. Status Code: {response.status_code}")
                except Exception as e:
                    st.error(f"Error downloading image from {url}: {e}")
                    logging.error(f"Error downloading image from {url}: {e}")

    if st.button("Run OCR"):
        if not image_paths and not images:
            st.error("Please provide at least one image.")
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

        def send_request(extra_accuracy):
            local_headers = headers.copy()
            local_form_data = form_data.copy()
            if extra_accuracy:
                local_form_data['extra_accuracy'] = 'true'

            # List of files to upload
            files = []
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif',
                '.tiff': 'image/tiff'
            }

            try:
                for image_path in image_paths:
                    _, file_ext = os.path.splitext(image_path.lower())
                    mime_type = mime_types.get(file_ext, 'application/octet-stream')
                    files.append(('file', (os.path.basename(image_path), open(image_path, 'rb'), mime_type)))
            except Exception as e:
                st.error(f"Error opening file {image_path}: {e}")
                logging.error(f"Error opening file {image_path}: {e}")
                return None, 0

            try:
                start_time = time.time()
                logging.info(f"Sending POST request to {st.secrets['api']['endpoint']} with Parser App ID: {local_form_data['parserApp']}, Extra Accuracy: {extra_accuracy}")
                response = requests.post(st.secrets["api"]["endpoint"], headers=local_headers, data=local_form_data, files=files if files else None, timeout=120)
                time_taken = time.time() - start_time
                logging.info(f"Received response: {response.status_code} in {time_taken:.2f} seconds")
                return response, time_taken
            except requests.exceptions.RequestException as e:
                logging.error(f"Error in API request: {e}")
                st.error(f"Error in API request: {e}")
                return None, 0
            finally:
                # Cleanup files
                for _, file_tuple in files:
                    file_tuple[1].close()

        with st.spinner("Processing OCR..."):
            response_extra, time_taken_extra = send_request(True)
            response_no_extra, time_taken_no_extra = send_request(False)

        # Cleanup temporary directories
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                logging.info(f"Cleaned up temporary directory {temp_dir}")
            except Exception as e:
                logging.warning(f"Could not remove temporary directory {temp_dir}: {e}")

        if response_extra and response_no_extra:
            success_extra = response_extra.status_code == 200
            success_no_extra = response_no_extra.status_code == 200

            # Create two columns for side-by-side display
            col1, col2 = st.columns(2)

            if success_extra:
                try:
                    response_json_extra = response_extra.json()
                    with col1:
                        st.expander(f"Results with Extra Accuracy - ⏱ {time_taken_extra:.2f}s").json(response_json_extra)
                except json.JSONDecodeError:
                    with col1:
                        st.error("Failed to parse JSON response with Extra Accuracy.")
                        logging.error("Failed to parse JSON response with Extra Accuracy.")
            else:
                with col1:
                    st.error("Request with Extra Accuracy failed.")
                    logging.error(f"Request with Extra Accuracy failed with status code: {response_extra.status_code}")

            if success_no_extra:
                try:
                    response_json_no_extra = response_no_extra.json()
                    with col2:
                        st.expander(f"Results without Extra Accuracy - ⏱ {time_taken_no_extra:.2f}s").json(response_json_no_extra)
                except json.JSONDecodeError:
                    with col2:
                        st.error("Failed to parse JSON response without Extra Accuracy.")
                        logging.error("Failed to parse JSON response without Extra Accuracy.")
            else:
                with col2:
                    st.error("Request without Extra Accuracy failed.")
                    logging.error(f"Request without Extra Accuracy failed with status code: {response_no_extra.status_code}")

            # Comparison JSON
            st.subheader("Comparison JSON")
            if success_extra and success_no_extra:
                comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)
                st.expander("Comparison JSON").json(comparison_results)
            else:
                st.error("Cannot generate Comparison JSON as one or both OCR requests failed.")

            # Comparison Table
            st.subheader("Comparison Table")
            if success_extra and success_no_extra:
                comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)
                comparison_table = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)

                if not comparison_table.empty:
                    gb = GridOptionsBuilder.from_dataframe(comparison_table)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_side_bar()
                    gb.configure_selection('single')
                    grid_options = gb.build()

                    # Use a valid theme, e.g., 'streamlit'
                    AgGrid(comparison_table, gridOptions=grid_options, height=500, theme='streamlit', enable_enterprise_modules=True)
                else:
                    st.info("No common fields to compare in the OCR results.")
            else:
                st.error("Cannot display Comparison Table as one or both OCR requests failed.")

            if success_extra and success_no_extra:
                st.success("Both OCR requests completed successfully.")
            else:
                st.error("One or both OCR requests failed. Please check the logs for more details.")
        else:
            st.error("One or both OCR requests did not receive a response.")
