import streamlit as st
from github_utils import download_parsers_from_github, upload_parsers_to_github
from parser_utils import add_new_parser, list_parsers
from ocr_runner import run_parser
from urllib.parse import parse_qs

# Ensure session state is initialized
if 'parsers' not in st.session_state:
    st.session_state['parsers'] = {}

def main():
    # Set page config
    st.set_page_config(page_title="FRACTO OCR Parser", layout="wide")

    # Get URL parameters (e.g., parser and client flag)
    query_params = st.experimental_get_query_params()
    requested_parser = query_params.get("parser", [None])[0]
    client_view = query_params.get("client", [False])[0]

    # Ensure parsers are loaded once when the app starts
    if 'loaded' not in st.session_state:
        download_parsers_from_github()
        st.session_state.loaded = True

    # Client View: Display the Run Parser page for a specific parser
    if client_view and requested_parser:
        if requested_parser in st.session_state['parsers']:
            st.title(f"Run Parser: {requested_parser}")
            parser_details = st.session_state['parsers'][requested_parser]
            run_parser({requested_parser: parser_details})
        else:
            st.error("This parser no longer exists. Please contact support.")
        return

    # Internal Team View: Normal app with navigation
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

    # Radio button menu
    menu = ["List Parsers", "Run Parser", "Add Parser"]
    choice = st.sidebar.radio("Menu", menu)

    # Menu options
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
