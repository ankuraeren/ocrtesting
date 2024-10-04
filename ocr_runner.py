import streamlit as st
import os
import tempfile
import shutil
from PIL import Image
from ocr_utils import send_request, generate_comparison_results, generate_comparison_df
from st_aggrid import AgGrid, GridOptionsBuilder

# Main OCR parser function with button-based parser selection
def run_parser(parsers):
    st.subheader("Run OCR Parser")

    if not parsers:
        st.info("No parsers available. Please add a parser first.")
        return

    # Create button-based parser selection with flexbox styling
    st.markdown("""
        <style>
        .button-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .button-container button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 18px;
            font-size: 14px;
            cursor: pointer;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .button-container button:hover {
            background-color: #45a049;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### Select a Parser")
    selected_parser = None

    # Container for the parser buttons
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    cols = st.columns(len(parsers))  # Create columns dynamically

    for parser_name in parsers.keys():
        if st.button(parser_name):
            selected_parser = parser_name

    st.markdown('</div>', unsafe_allow_html=True)

    if selected_parser:
        parser_info = parsers[selected_parser]

        st.write(f"**Selected Parser:** {selected_parser}")
        st.write(f"**Parser App ID:** {parser_info['parser_app_id']}")
        st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

        image_paths = []
        temp_dirs = []

        # File uploader
        uploaded_files = st.file_uploader("Choose image or PDF file(s)...", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "pdf"], accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_file.name)
                    image.save(image_path)
                    image_paths.append(image_path)
                except Exception as e:
                    st.error(f"Error processing file {uploaded_file.name}: {e}")

        # Run OCR button
        if st.button("Run OCR"):
            if not image_paths:
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

            API_ENDPOINT = st.secrets["api"]["endpoint"]

            with st.spinner("Processing OCR..."):
                response_extra, time_taken_extra = send_request(image_paths, headers, form_data, True, API_ENDPOINT)
                response_no_extra, time_taken_no_extra = send_request(image_paths, headers, form_data, False, API_ENDPOINT)

            # Cleanup temporary directories
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    st.warning(f"Could not remove temporary directory {temp_dir}: {e}")

            if response_extra and response_no_extra:
                success_extra = response_extra.status_code == 200
                success_no_extra = response_no_extra.status_code == 200

                # Display results in two columns
                col1, col2 = st.columns(2)

                if success_extra:
                    try:
                        response_json_extra = response_extra.json()
                        with col1:
                            st.expander(f"Results with Extra Accuracy - ⏱ {time_taken_extra:.2f}s").json(response_json_extra)
                    except json.JSONDecodeError:
                        with col1:
                            st.error("Failed to parse JSON response with Extra Accuracy.")
                else:
                    with col1:
                        st.error(f"Request with Extra Accuracy failed. Status code: {response_extra.status_code}")

                if success_no_extra:
                    try:
                        response_json_no_extra = response_no_extra.json()
                        with col2:
                            st.expander(f"Results without Extra Accuracy - ⏱ {time_taken_no_extra:.2f}s").json(response_json_no_extra)
                    except json.JSONDecodeError:
                        with col2:
                            st.error("Failed to parse JSON response without Extra Accuracy.")
                else:
                    with col2:
                        st.error(f"Request without Extra Accuracy failed. Status code: {response_no_extra.status_code}")

                # Generate comparison results
                st.subheader("Comparison JSON")
                if success_extra and success_no_extra:
                    comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)
                    st.expander("Comparison JSON").json(comparison_results)

                    st.subheader("Comparison Table")
                    comparison_table = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)
                    gb = GridOptionsBuilder.from_dataframe(comparison_table)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_side_bar()
                    gb.configure_selection('single')
                    grid_options = gb.build()
                    AgGrid(comparison_table, gridOptions=grid_options, height=500, theme='streamlit', enable_enterprise_modules=True)
                else:
                    st.error("Comparison failed. One or both requests were unsuccessful.")
    else:
        st.info("Please select a parser by clicking the button.")
