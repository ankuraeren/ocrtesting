# utils/helpers.py

import json
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import streamlit as st


def flatten_json(y):
    """
    Flatten a nested JSON object.
    """
    out = {}
    order = []

    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else:
            out[name[:-1]] = x
            order.append(name[:-1])

    flatten(y)
    return out, order


def generate_comparison_results(json1, json2):
    """
    Generate a new JSON object with tick or cross based on whether attributes match.
    """
    flat_json1, order1 = flatten_json(json1)
    flat_json2, _ = flatten_json(json2)

    comparison_results = {}

    for key in order1:
        val1 = flat_json1.get(key, "N/A")
        val2 = flat_json2.get(key, "N/A")
        match = (val1 == val2)
        comparison_results[key] = "✔" if match else "✘"

    return comparison_results


def generate_comparison_df(json1, json2, comparison_results):
    """
    Generate a DataFrame comparing two JSON objects.
    """
    flat_json1, order1 = flatten_json(json1)
    flat_json2, _ = flatten_json(json2)

    data = []
    for key in order1:
        val1 = flat_json1.get(key, "N/A")
        val2 = flat_json2.get(key, "N/A")
        match = comparison_results[key]
        data.append([key, val1, val2, match])

    df = pd.DataFrame(data, columns=['Attribute', 'Result with Extra Accuracy', 'Result without Extra Accuracy', 'Comparison'])
    return df
