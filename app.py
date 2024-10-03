import pandas as pd
import streamlit as st
import requests
import os
import json
import re
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import shutil
import tempfile
import logging
import gdown
import time  # New import for tracking time
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Define the Google Drive file ID (extract from your shareable link)
GDRIVE_FILE_ID = '1bCVInNOQxx4sP2kZbCuO65RfKQ-mqq1u'  # Replace with your actual file ID
GDRIVE_DOWNLOAD_URL = f'https://drive.google.com/uc?id={GDRIVE_FILE_ID}'

# Define local parsers file path
LOCAL_PARSERS_FILE = 'parsers.json'

# API Configuration
API_ENDPOINT = 'https://prod-ml.fracto.tech/upload-file-smart-ocr'

# Initialize parsers dictionary in session state
if 'parsers' not in st.session_state:
    st.session_state['parsers'] = {}

def authenticate_drive():
    """
    Authenticate and create a GoogleDrive object using PyDrive.
    """
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Automatically handles authentication
    return GoogleDrive(gauth)

def upload_parsers_to_drive(local_file_path, drive_file_id):
    """
    Upload the updated parsers.json to Google Drive, replacing the existing file.
    """
    drive = authenticate_drive()

    # Load the file on Google Drive using its file ID
    file = drive.CreateFile({'id': drive_file_id})

    # Set the content of the file from the local parsers.json
    file.SetContentFile(local_file_path)
    
    # Upload the file to Google Drive, overwriting the existing one
    file.Upload()
    st.success("parsers.json has been successfully uploaded to Google Drive.")

# After modifying the parsers.json locally, call this function to upload:
def save_and_upload_parsers():
    """
    Saves the parsers to the local parsers.json file and uploads it back to Google Drive.
    """
    save_parsers()  # Save locally first
    upload_parsers_to_drive(LOCAL_PARSERS_FILE, GDRIVE_FILE_ID)

def download_parsers_from_drive():
    if not os.path.exists(LOCAL_PARSERS_FILE):
        logging.info("Downloading parsers.json from Google Drive...")
        try:
            gdown.download(GDRIVE_DOWNLOAD_URL, LOCAL_PARSERS_FILE, quiet=False)
            logging.info("Download completed.")
            st.success("parsers.json downloaded successfully.")
        except Exception as e:
            logging.error(f"Failed to download parsers.json: {e}")
            st.error("Failed to download parsers.json from Google Drive.")
    else:
        logging.info("parsers.json already exists locally.")
        st.info("parsers.json already exists locally.")

def load_parsers():
    if os.path.exists(LOCAL_PARSERS_FILE):
        with open(LOCAL_PARSERS_FILE, 'r') as f:
            try:
                st.session_state['parsers'] = json.load(f)
                logging.info("Parsers loaded successfully.")
                st.success("parsers.json loaded successfully.")
            except json.JSONDecodeError:
                logging.error("parsers.json is not a valid JSON file.")
                st.error("parsers.json is corrupted or not in valid JSON format.")
    else:
        st.session_state['parsers'] = {}
        logging.info("parsers.json not found. Starting with an empty parsers dictionary.")
        st.info("parsers.json not found. Starting with an empty parsers dictionary.")

def save_parsers():
    with open(LOCAL_PARSERS_FILE, 'w') as f:
        json.dump(st.session_state['parsers'], f, indent=4)
    logging.info("parsers.json updated successfully.")
    st.success("parsers.json has been updated locally. Please upload it back to Google Drive manually.")

def add_new_parser():
    st.subheader("Add a New Parser")
    with st.form("add_parser_form"):
        parser_name = st.text_input("Parser Name (e.g., 'Cheque Front')").strip()
        api_key = st.text_input("API Key").strip()
        parser_app_id = st.text_input("Parser App ID").strip()
        extra_accuracy = st.checkbox("Require Extra Accuracy")
        expected_response = st.text_area("Expected JSON Response (optional)")
        sample_curl = st.text_area("Sample CURL Request (optional)")
        
        submitted = st.form_submit_button("Add Parser")
        if submitted:
            if not parser_name or not api_key or not parser_app_id:
                st.error("Please fill in all required fields (Parser Name, API Key, Parser App ID).")
            elif parser_name in st.session_state['parsers']:
                st.error(f"Parser '{parser_name}' already exists.")
            else:
                if expected_response:
                    try:
                        json.loads(expected_response)
                    except json.JSONDecodeError:
                        st.error("Expected JSON Response is not a valid JSON.")
                        return
                
                st.session_state['parsers'][parser_name] = {
                    'api_key': api_key,
                    'parser_app_id': parser_app_id,
                    'extra_accuracy': extra_accuracy,
                    'expected_response': expected_response,
                    'sample_curl': sample_curl
                }
                save_parsers()

def list_parsers():
    st.subheader("List of All Parsers")
    if not st.session_state['parsers']:
        st.info("No parsers available. Please add a parser first.")
        return
    
    for parser_name, details in st.session_state['parsers'].items():
        with st.expander(parser_name):
            st.write(f"**API Key:** {details['api_key']}")
            st.write(f"**Parser App ID:** {details['parser_app_id']}")
            st.write(f"**Extra Accuracy:** {'Yes' if details['extra_accuracy'] else 'No'}")
            st.write(f"**Expected Response:**")
            if details['expected_response']:
                try:
                    expected_json = json.loads(details['expected_response'])
                    st.json(expected_json)
                except json.JSONDecodeError:
                    st.text(details['expected_response'])
            else:
                st.write("N/A")
            st.write(f"**Sample CURL Request:**")
            if details['sample_curl']:
                st.code(details['sample_curl'], language='bash')
            else:
                st.write("N/A")
            
            delete_button = st.button(f"Delete {parser_name}", key=f"delete_{parser_name}")
            if delete_button:
                del st.session_state['parsers'][parser_name]
                save_parsers()
                st.success(f"Parser '{parser_name}' has been deleted.")
                st.experimental_rerun()

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

    images = []  
    temp_dirs = []  

    if input_method == "Upload Image File":
        uploaded_files = st.file_uploader("Choose image(s)...", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff"], accept_multiple_files=True)
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
                        st.image(image, caption=os.path.basename(url.split('?')[0]), use_column_width=True)
                        temp_dir = tempfile.mkdtemp()
                        temp_dirs.append(temp_dir)
                        image_filename = os.path.basename(url.split('?')[0])
                        image_path = os.path.join(temp_dir, image_filename)
                        with open(image_path, 'wb') as f:
                            shutil.copyfileobj(response.raw, f)
                    else:
                        st.error(f"Failed to download image from {url}. Status Code: {response.status_code}")
                        logging.error(f"Failed to download image from {url}. Status Code: {response.status_code}")
                except Exception as e:
                    st.error(f"Error downloading image from {url}: {e}")
                    logging.error(f"Error downloading image from {url}: {e}")

    # Determine if both outputs are needed
    run_both = st.checkbox("Run OCR with and without Extra Accuracy", value=True) if parser_info['extra_accuracy'] else False

    if st.button("Run OCR"):
        if not images:
            st.error("Please provide at least one image to process.")
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

        # Function to send OCR request
        def send_ocr_request(extra_accuracy_flag):
            local_form_data = form_data.copy()
            if extra_accuracy_flag:
                local_form_data['extra_accuracy'] = 'true'
            else:
                # Ensure extra_accuracy is not in the form data
                local_form_data.pop('extra_accuracy', None)

            files = []
            for idx, image in enumerate(images):
                temp_dir = tempfile.mkdtemp()
                temp_dirs.append(temp_dir)
                image_path = os.path.join(temp_dir, f"image_{idx+1}.jpg")
                image.save(image_path)
                _, file_ext = os.path.splitext(image_path.lower())
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.bmp': 'image/bmp',
                    '.gif': 'image/gif',
                    '.tiff': 'image/tiff'
                }
                mime_type = mime_types.get(file_ext, 'application/octet-stream')
                try:
                    files.append(('file', (os.path.basename(image_path), open(image_path, 'rb'), mime_type)))
                except Exception as e:
                    st.error(f"Error opening file {image_path}: {e}")
                    logging.error(f"Error opening file {image_path}: {e}")
                    return None

            try:
                logging.info(f"Sending POST request to {API_ENDPOINT} with Extra Accuracy: {extra_accuracy_flag}")
                response = requests.post(API_ENDPOINT, headers=headers, data=local_form_data, files=files if files else None, timeout=120)
                logging.info(f"Received response: {response.status_code}")
                return response
            except requests.exceptions.RequestException as e:
                logging.error(f"Error in API request: {e}")
                st.error(f"Error in API request: {e}")
                return None
            finally:
                for _, file_tuple in files:
                    file_tuple[1].close()

        # Send OCR requests
        responses = {}
        if run_both:
            st.info("Running two OCR requests: with and without Extra Accuracy.")
            response_extra = send_ocr_request(True)
            response_no_extra = send_ocr_request(False)
            responses['with_extra_accuracy'] = response_extra
            responses['without_extra_accuracy'] = response_no_extra
        else:
            st.info("Running single OCR request based on Extra Accuracy setting.")
            response = send_ocr_request(parser_info['extra_accuracy'])
            responses['single'] = response

        # Cleanup temporary directories
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                logging.info(f"Cleaned up temporary directory {temp_dir}")
            except Exception as e:
                logging.warning(f"Could not remove temporary directory {temp_dir}: {e}")

        # Display Responses
        for key, response in responses.items():
            if response and response.status_code == 200:
                try:
                    response_json = response.json()
                    formatted_json = json.dumps(response_json, indent=4)
                    
                    if run_both:
                        if key == 'with_extra_accuracy':
                            with st.expander("Results with Extra Accuracy"):
                                st.json(response_json)
                        elif key == 'without_extra_accuracy':
                            with st.expander("Results without Extra Accuracy"):
                                st.json(response_json)
                    else:
                        with st.expander("OCR Results"):
                            st.json(response_json)

                    parsed_data = response_json.get('parsedData', {})

                    st.markdown("---")

                    st.subheader("Processed Images")
                    if images:
                        num_images = len(images)
                        cols = st.columns(min(num_images, 5))
                        for idx, img in enumerate(images):
                            cols[idx % 5].image(img, caption=f"Image {idx+1}", use_column_width=True)

                    st.markdown("---")

                    st.subheader("Summary Table")
                    if parsed_data:
                        if isinstance(parsed_data, dict) and all(not isinstance(v, (dict, list)) for v in parsed_data.values()):
                            line_items = [(key, value) for key, value in parsed_data.items()]
                            df = pd.DataFrame(line_items, columns=["Field", "Value"])
                        elif isinstance(parsed_data, dict):
                            line_items = []
                            for section, fields in parsed_data.items():
                                if isinstance(fields, dict):
                                    for key, value in fields.items():
                                        line_items.append((f"{section} - {key}", value))
                                elif isinstance(fields, list):
                                    for item in fields:
                                        if isinstance(item, dict):
                                            for key, value in item.items():
                                                line_items.append((f"{section} - {key}", value))
                            df = pd.DataFrame(line_items, columns=["Field", "Value"])
                        elif isinstance(parsed_data, list):
                            df = pd.DataFrame(parsed_data)
                        else:
                            df = pd.DataFrame()

                        if not df.empty:
                            st.dataframe(
                                df.style.applymap(lambda val: 'background-color: #f7f9fc' if pd.isna(val) else 'background-color: #e3f2fd'), 
                                width=st.sidebar.slider("Adjust table width", 800, 1200, 1000),
                                height=400  # Fixed height
                            )
                        else:
                            st.info("Parsed data format is not supported for table display.")
                    else:
                        st.info("No parsed data available to display in table format.")

                except json.JSONDecodeError:
                    logging.error("Failed to parse JSON response.")
                    st.error("Failed to parse JSON response.")
                    st.text(response.text)
            elif response:
                st.error(f"OCR Request '{key}' failed with status code {response.status_code}")
                try:
                    error_response = response.json()
                    st.json(error_response)
                except json.JSONDecodeError:
                    st.text(response.text)
            else:
                st.error(f"OCR Request '{key}' did not receive a response.")

def main():
    st.title("📄 FRACTO OCR Parser Web App")
    st.markdown("""
    Welcome to the OCR Parser Web App. Use the sidebar to navigate through different functionalities.
    
    - **Add Parser**: Add new OCR parsers by providing necessary details.
    - **List Parsers**: View all existing parsers and manage them.
    - **Run Parser**: Perform OCR tasks using the configured parsers.
    """)
    
    menu = ["List Parsers", "Run Parser", "Add Parser"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    download_parsers_from_drive()
    load_parsers()
    
    if choice == "Add Parser":
        add_new_parser()
    elif choice == "List Parsers":
        list_parsers()
    elif choice == "Run Parser":
        run_parser(st.session_state['parsers'])  
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Update parsers.json")
    st.sidebar.info("""
    After making changes (additions, deletions, updates) to the parsers, please **manually upload** the updated `parsers.json` back to Google Drive to keep it in sync.

    **Steps:**
    1. Click on the **"Download parsers.json"** button below.
    2. Upload the downloaded `parsers.json` to your Google Drive at the desired location.
    """)

    if st.sidebar.button("Download parsers.json"):
        if os.path.exists(LOCAL_PARSERS_FILE):
            with open(LOCAL_PARSERS_FILE, 'rb') as f:
                st.sidebar.download_button(
                    label="Download parsers.json",
                    data=f,
                    file_name='parsers.json',
                    mime='application/json'
                )
        else:
            st.sidebar.error("parsers.json file not found.")

if __name__ == "__main__":
    main()
