import streamlit as st
from github_utils import download_parsers_from_github, upload_parsers_to_github
from parser_utils import add_new_parser, list_parsers
from ocr_runner import run_parser

# Ensure session state is initialized
if 'parsers' not in st.session_state:
    st.session_state['parsers'] = {}


def main():
    # Other logic here

    st.set_page_config(page_title="FRACTO OCR Parser", layout="wide")

    st.markdown("""
        <style>
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 24px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 8px;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
            padding-top: 20px;
            height: 100%;
        }
        .sidebar .sidebar-content h2 {
            color: #333;
        }
        .sidebar .sidebar-content p {
            color: #555;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📄 FRACTO OCR Parser Web App")
    st.sidebar.header("Navigation")
    st.sidebar.markdown("""
        <p>This app provides functionalities for:</p>
        <ul>
            <li>Add OCR parsers</li>
            <li>List existing parsers</li>
            <li>Run parsers on images</li>
        </ul>
    """, unsafe_allow_html=True)

    menu = ["List Parsers", "Run Parser", "Add Parser"]
    choice = st.sidebar.radio("Menu", menu)

    # Ensure parsers are loaded once when the app starts
    if 'loaded' not in st.session_state:
        download_parsers_from_github()  # This will also call load_parsers internally
        st.session_state.loaded = True

    if choice == "Add Parser":
        add_new_parser()
    elif choice == "List Parsers":
        list_parsers()
    elif choice == "Run Parser":
        run_parser(st.session_state['parsers'])

    st.sidebar.header("GitHub Actions")
    if st.sidebar.button("Download Parsers"):
        download_parsers_from_github()

    if st.sidebar.button("Update Parsers File"):
        upload_parsers_to_github()

if __name__ == "__main__":
    main()
