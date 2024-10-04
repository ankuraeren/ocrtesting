import streamlit as st
from github_utils import download_parsers_from_github, upload_parsers_to_github
from parser_utils import add_new_parser, list_parsers
from ocr_utils import run_parser

# Handles only UI aspects and delegates logic to appropriate functions
def app_ui():
    st.sidebar.header("Navigation")
    st.sidebar.markdown("""
        <ul>
            <li>Add OCR parsers</li>
            <li>List existing parsers</li>
            <li>Run parsers on images</li>
        </ul>
    """, unsafe_allow_html=True)

    # Menu choices
    menu = ["List Parsers", "Run Parser", "Add Parser"]
    choice = st.sidebar.radio("Menu", menu)

    # Ensure parsers are loaded when the app starts
    if 'loaded' not in st.session_state:
        download_parsers_from_github()
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

# For testing purposes
if __name__ == "__main__":
    app_ui()
