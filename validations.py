# utils/validations.py

import json
import streamlit as st
import logging

# Placeholder for AI-based analysis function
def analyze_ocr_results(ocr_responses):
    """
    Analyze OCR responses to identify inconsistencies or errors.
    Use AI models or heuristics to suggest improvements.
    """
    # Example: Check for missing fields or inconsistent data
    analysis = {}
    for parser_name, response in ocr_responses.items():
        if response['status'] == 'success':
            data = response.get('data', {})
            missing_fields = [key for key, value in data.items() if not value]
            if missing_fields:
                analysis[parser_name] = f"Missing fields: {', '.join(missing_fields)}"
            else:
                analysis[parser_name] = "All fields are present."
        else:
            analysis[parser_name] = f"Error: {response.get('error', 'Unknown error')}"
    return analysis


def suggest_validations(analysis_results):
    """
    Based on analysis, suggest validations or prompt improvements.
    """
    suggestions = {}
    for parser, analysis in analysis_results.items():
        if "Missing fields" in analysis:
            suggestions[parser] = "Please ensure all required fields are present in the OCR output."
        elif "Error" in analysis:
            suggestions[parser] = "Check the parser configuration and API integration."
        else:
            suggestions[parser] = "No issues detected."
    return suggestions
