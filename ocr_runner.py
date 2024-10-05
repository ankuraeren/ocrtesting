
### Updated ocr_runner.py ###

import os
import tempfile
import shutil
import streamlit as st
from PIL import Image
from PyPDF2 import PdfReader
from ocr_utils import send_request, generate_comparison_results, generate_comparison_df, generate_mismatch_df
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud

# Main OCR parser function
def run_parser(parsers):
    st.subheader("Run OCR Parser")
    if not parsers:
        st.info("No parsers available. Please add a parser first.")
        return

    # Add custom CSS for horizontal, scrollable radio buttons
    st.markdown("""
        <style>
        .stRadio [role=radiogroup] {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
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
            white-space: nowrap;
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

    # Convert parser selection into horizontal scrollable radio buttons
    parser_names = list(parsers.keys())
    selected_parser = st.radio("Select Parser", parser_names)
    parser_info = parsers[selected_parser]

    st.write(f"**Selected Parser:** {selected_parser}")
    st.write(f"**Extra Accuracy Required:** {'Yes' if parser_info['extra_accuracy'] else 'No'}")

    file_paths = []
    temp_dirs = []

    # File uploader
    uploaded_files = st.file_uploader("Choose image or PDF file(s)...", type=["jpg", "jpeg", "png", "bmp", "gif", "tiff", "pdf"], accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                if uploaded_file.type == "application/pdf":
                    # Handle PDF files
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    pdf_path = os.path.join(temp_dir, uploaded_file.name)

                    with open(pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Display PDF filename
                    st.markdown(f"**Uploaded PDF:** {uploaded_file.name}")
                    file_paths.append(pdf_path)

                else:
                    # Handle image files
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                    temp_dir = tempfile.mkdtemp()
                    temp_dirs.append(temp_dir)
                    image_path = os.path.join(temp_dir, uploaded_file.name)
                    image.save(image_path)
                    file_paths.append(image_path)

            except Exception as e:
                st.error(f"Error processing file {uploaded_file.name}: {e}")

    # Run OCR button
    if st.button("Run OCR"):
        if not file_paths:
            st.error("Please provide at least one image or PDF.")
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
            response_extra, time_taken_extra = send_request(file_paths, headers, form_data, True, API_ENDPOINT)
            response_no_extra, time_taken_no_extra = send_request(file_paths, headers, form_data, False, API_ENDPOINT)

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
            if success_extra and success_no_extra:
                comparison_results = generate_comparison_results(response_json_extra, response_json_no_extra)

                # Collapsible section for metrics and insights
                with st.expander("Metrics and Insights"):
                    # Display mismatched fields in a table
                    st.subheader("Mismatched Fields")
                    mismatch_df = generate_mismatch_df(response_json_extra, response_json_no_extra, comparison_results)
                    st.dataframe(mismatch_df)

                    # Display the comparison table
                    st.subheader("Comparison Table")
                    comparison_table = generate_comparison_df(response_json_extra, response_json_no_extra, comparison_results)
                    gb = GridOptionsBuilder.from_dataframe(comparison_table)
                    gb.configure_pagination(paginationAutoPageSize=True)
                    gb.configure_side_bar()
                    gb.configure_selection('single')
                    grid_options = gb.build()
                    AgGrid(comparison_table, gridOptions=grid_options, height=300, theme='streamlit', enable_enterprise_modules=True)

                    # Display analytics and insights with pie charts and 3D effects
                    st.subheader("Analytics and Insights")

                    # Matched vs Mismatched Fields
                    match_count = sum(1 for v in comparison_results.values() if v == "✔")
                    mismatch_count = sum(1 for v in comparison_results.values() if v == "✘")
                    match_data = [match_count, mismatch_count]
                    labels = ['Matched', 'Mismatched']
                    colors = ['#4caf50', '#f44336']

                    fig1, ax1 = plt.subplots()
                    ax1.pie(match_data, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, shadow=True, explode=(0.1, 0), wedgeprops={'edgecolor': 'black', 'linewidth': 1.5})
                    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                    plt.title('Matched vs. Mismatched Fields')
                    st.pyplot(fig1)

                    # Processing Time Comparison
                    st.subheader("Processing Time Comparison")
                    time_data = [time_taken_extra, time_taken_no_extra]
                    labels = ['With Extra Accuracy', 'Without Extra Accuracy']
                    colors = ['#2196f3', '#ff9800']

                    fig2, ax2 = plt.subplots()
                    ax2.pie(time_data, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, shadow=True, explode=(0.1, 0), wedgeprops={'edgecolor': 'black', 'linewidth': 1.5})
                    ax2.axis('equal')
                    plt.title('Processing Time Comparison')
                    st.pyplot(fig2)

                    # Field Match Percentage
                    st.subheader("Field Match Percentage")
                    match_percentage = (match_count / len(comparison_results)) * 100
                    mismatch_percentage = 100 - match_percentage
                    percentages = [match_percentage, mismatch_percentage]
                    labels = ['Matched', 'Mismatched']

                    fig3, ax3 = plt.subplots()
                    ax3.pie(percentages, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, shadow=True, explode=(0.1, 0), wedgeprops={'edgecolor': 'black', 'linewidth': 1.5})
                    ax3.axis('equal')
                    plt.title('Field Match Percentage')
                    st.pyplot(fig3)

                    # Word Cloud (if applicable)
                    try:
                        all_text = " ".join(flatten_json(response_json_extra)[0].values())
                        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)

                        st.subheader("Word Cloud of Extracted Text")
                        fig4, ax4 = plt.subplots()
                        ax4.imshow(wordcloud, interpolation='bilinear')
                        ax4.axis('off')
                        st.pyplot(fig4)
                    except Exception as e:
                        st.warning(f"Could not generate word cloud: {e}")

                # Display the full comparison JSON after the table
                st.subheader("Comparison JSON")
                st.expander("Comparison JSON").json(comparison_results)

            else:
                st.error("Comparison failed. One or both requests were unsuccessful.")
