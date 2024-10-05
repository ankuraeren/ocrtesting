import streamlit as st
from github_utils import download_parsers_from_github, upload_parsers_to_github
from parser_utils import add_new_parser, list_parsers
from ocr_runner import run_parser

# Ensure session state is initialized
if 'parsers' not in st.session_state:
    st.session_state['parsers'] = {}

def main():
    # Set page config
    st.set_page_config(page_title="FRACTO OCR Parser", layout="wide")

    # Add custom CSS for radio buttons
    st.markdown("""
        <style>
        .stRadio [role=radiogroup] {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        div[role='radiogroup'] label div[data-testid='stMarkdownContainer'] {
            font-size: 18px;
            font-weight: bold;
            color: #FFFFFF;
        }
        div[role='radiogroup'] label {
            background-color: #2B2B2B;
            padding: 10px 15px;
            border-radius: 12px;
            border: 1px solid #3B3B3B;
            cursor: pointer;
        }
        div[role='radiogroup'] label:hover {
            background-color: #474747;
        }
        div[role='radiogroup'] input[type='radio']:checked + label {
            background-color: #FF5F5F;
            border-color: #FF5F5F;
        }
        div[role='radiogroup'] input[type='radio']:checked + label div[data-testid='stMarkdownContainer'] {
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)

    # App title and sidebar options
    st.title("📄 FRACTO OCR Parser Web App")

    # Check if the URL is for a client (client=true) or internal user
    is_client = st.experimental_get_query_params().get("client", ["false"])[0].lower() == "true"
    selected_parser = st.experimental_get_query_params().get("parser", [None])[0]

    # Client view: directly run the parser if a parser is selected
    if is_client and selected_parser:
        st.sidebar.header("Client View")
        st.sidebar.markdown(f"Running parser: **{selected_parser}**")

        # Ensure parsers are loaded
        if 'loaded' not in st.session_state:
            download_parsers_from_github()
            st.session_state.loaded = True

        if selected_parser in st.session_state['parsers']:
            run_parser({selected_parser: st.session_state['parsers'][selected_parser]})
        else:
            st.error(f"Parser '{selected_parser}' not found.")
        return  # Stop execution as this is a client view with only "Run Parser"

    # Internal view: show full menu
    st.sidebar.header("Navigation")
    st.sidebar.markdown("""
        <p>This app provides functionalities for:</p>
        <ul>
            <li>Add OCR parsers</li>
            <li>List existing parsers</li>
            <li>Run parsers on images</li>
        </ul>
    """, unsafe_allow_html=True)

    # Radio button menu for internal team
    menu = ["List Parsers", "Run Parser", "Add Parser"]
    choice = st.sidebar.radio("Menu", menu)

    # Ensure parsers are loaded once when the app starts
    if 'loaded' not in st.session_state:
        download_parsers_from_github()
        st.session_state.loaded = True

    # Menu options for internal users
    if choice == "Add Parser":
        add_new_parser()
    elif choice == "List Parsers":
        list_parsers()
    elif choice == "Run Parser":
        run_parser(st.session_state['parsers'])

    # GitHub actions for internal users
    st.sidebar.header("GitHub Actions")
    if st.sidebar.button("Download Parsers"):
        download_parsers_from_github()

    if st.sidebar.button("Update Parsers File"):
        upload_parsers_to_github()

if __name__ == "__main__":
    main()
