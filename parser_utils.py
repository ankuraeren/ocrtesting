import pandas as pd
import streamlit as st

def parse_invoice(main_header, invoice_header, line_items):
    """
    Parse invoice data into a structured DataFrame.
    """
    main_header_df = pd.DataFrame([main_header])
    main_header_df['Record_Type'] = 'Main Header'
    main_header_df['Parser Type'] = 'invoice'
    main_header_df['Invoice Number'] = main_header.get('Invoice Number', '')
    main_header_df['Shipper Name'] = ''
    main_header_df['Biller Name'] = ''
    main_header_df['Invoice Date'] = ''
    main_header_df['Item Description'] = ''
    main_header_df['Unit Price'] = ''
    main_header_df['Quantity'] = ''
    main_header_df['Total Price'] = ''
    main_header_df['Document Name'] = main_header.get('Document Name', '')

    invoice_header_df = pd.DataFrame([invoice_header])
    invoice_header_df['Record_Type'] = 'Invoice Header'
    invoice_header_df['Parser Type'] = 'invoice'
    invoice_header_df['Invoice Number'] = invoice_header.get('Invoice Number', '')
    invoice_header_df['Shipper Name'] = invoice_header.get('Shipper Name', '')
    invoice_header_df['Biller Name'] = invoice_header.get('Biller Name', '')
    invoice_header_df['Invoice Date'] = invoice_header.get('Invoice Date', '')
    invoice_header_df['Item Description'] = ''
    invoice_header_df['Unit Price'] = ''
    invoice_header_df['Quantity'] = ''
    invoice_header_df['Total Price'] = ''
    invoice_header_df['Document Name'] = invoice_header.get('Document Name', '')

    line_items_df = pd.DataFrame(line_items)
    line_items_df['Record_Type'] = 'Line Item'
    line_items_df['Parser Type'] = 'invoice'
    line_items_df['Invoice Number'] = invoice_header.get('Invoice Number', '')
    line_items_df['Shipper Name'] = ''
    line_items_df['Biller Name'] = ''
    line_items_df['Invoice Date'] = ''
    line_items_df['Document Name'] = invoice_header.get('Document Name', '')

    return pd.concat([main_header_df, invoice_header_df, line_items_df], ignore_index=True)

def parse_ledger(ledger_header, line_items):
    """
    Parse ledger data into a structured DataFrame.
    """
    ledger_header_df = pd.DataFrame([ledger_header])
    ledger_header_df['Record_Type'] = 'Ledger Header'
    ledger_header_df['Parser Type'] = 'ledger'
    ledger_header_df['Ledger ID'] = ledger_header.get('Ledger ID', '')
    ledger_header_df['Account Name'] = ledger_header.get('Account Name', '')
    ledger_header_df['Date'] = ledger_header.get('Date', '')
    ledger_header_df['Transaction Description'] = ''
    ledger_header_df['Amount'] = ''
    ledger_header_df['Balance'] = ''
    ledger_header_df['Item Description'] = ''
    ledger_header_df['Unit Price'] = ''
    ledger_header_df['Quantity'] = ''
    ledger_header_df['Total Price'] = ''
    ledger_header_df['Document Name'] = ledger_header.get('Document Name', '')

    line_items_df = pd.DataFrame(line_items)
    line_items_df['Record_Type'] = 'Ledger Line Item'
    line_items_df['Parser Type'] = 'ledger'
    line_items_df['Ledger ID'] = ledger_header.get('Ledger ID', '')
    line_items_df['Account Name'] = ledger_header.get('Account Name', '')
    line_items_df['Date'] = ledger_header.get('Date', '')
    line_items_df['Transaction Description'] = line_items_df.get('Transaction Description', '')
    line_items_df['Amount'] = line_items_df.get('Amount', '')
    line_items_df['Balance'] = line_items_df.get('Balance', '')
    line_items_df['Item Description'] = ''
    line_items_df['Unit Price'] = ''
    line_items_df['Quantity'] = ''
    line_items_df['Total Price'] = ''
    line_items_df['Document Name'] = ledger_header.get('Document Name', '')

    return pd.concat([ledger_header_df, line_items_df], ignore_index=True)

def parse_visiting_card(header, contact_info):
    """
    Parse visiting card data into a structured DataFrame.
    """
    header_df = pd.DataFrame([header])
    header_df['Record_Type'] = 'Visiting Card Header'
    header_df['Parser Type'] = 'visiting_card'
    header_df['Name'] = header.get('Name', '')
    header_df['Company'] = header.get('Company', '')
    header_df['Position'] = header.get('Position', '')
    header_df['Document Name'] = header.get('Document Name', '')
    # Initialize other fields
    header_df['Invoice Number'] = ''
    header_df['Shipper Name'] = ''
    header_df['Biller Name'] = ''
    header_df['Invoice Date'] = ''
    header_df['Item Description'] = ''
    header_df['Unit Price'] = ''
    header_df['Quantity'] = ''
    header_df['Total Price'] = ''
    header_df['Ledger ID'] = ''
    header_df['Account Name'] = ''
    header_df['Date'] = ''
    header_df['Transaction Description'] = ''
    header_df['Amount'] = ''
    header_df['Balance'] = ''

    contact_info_df = pd.DataFrame(contact_info)
    contact_info_df['Record_Type'] = 'Visiting Card Contact'
    contact_info_df['Parser Type'] = 'visiting_card'
    contact_info_df['Name'] = header.get('Name', '')
    contact_info_df['Company'] = ''
    contact_info_df['Position'] = ''
    contact_info_df['Document Name'] = header.get('Document Name', '')
    # Initialize other fields
    contact_info_df['Invoice Number'] = ''
    contact_info_df['Shipper Name'] = ''
    contact_info_df['Biller Name'] = ''
    contact_info_df['Invoice Date'] = ''
    contact_info_df['Item Description'] = ''
    contact_info_df['Unit Price'] = ''
    contact_info_df['Quantity'] = ''
    contact_info_df['Total Price'] = ''
    contact_info_df['Ledger ID'] = ''
    contact_info_df['Account Name'] = ''
    contact_info_df['Date'] = ''
    contact_info_df['Transaction Description'] = ''
    contact_info_df['Amount'] = ''
    contact_info_df['Balance'] = ''

    return pd.concat([header_df, contact_info_df], ignore_index=True)

def parse_comparison_results(parser_type, comparison_results):
    """
    Dynamically call the appropriate parser function based on parser_type.

    Parameters:
        parser_type (str): Type of the parser (e.g., 'invoice', 'ledger', 'visiting_card').
        comparison_results (dict): The comparison results from OCR.

    Returns:
        parsed_df (pd.DataFrame): The parsed data as a DataFrame.
    """
    if parser_type == 'invoice':
        main_header, invoice_header, line_items = extract_invoice_data(comparison_results)
        parsed_df = parse_invoice(main_header, invoice_header, line_items)
    elif parser_type == 'ledger':
        ledger_header, line_items = extract_ledger_data(comparison_results)
        parsed_df = parse_ledger(ledger_header, line_items)
    elif parser_type == 'visiting_card':
        header, contact_info = extract_visiting_card_data(comparison_results)
        parsed_df = parse_visiting_card(header, contact_info)
    else:
        st.error(f"Unsupported parser type: {parser_type}")
        parsed_df = pd.DataFrame()

    return parsed_df

def extract_invoice_data(comparison_results):
    """
    Extract main_header, invoice_header, and line_items from comparison_results.
    Replace this with actual extraction logic based on your OCR output.
    """
    # TODO: Implement your actual extraction logic here based on comparison_results
    # Placeholder extraction logic
    main_header = {
        'Invoice Number': 'INV001',
        'Document Name': 'Invoice1.pdf'
    }

    invoice_header = {
        'Shipper Name': 'Acme Corp',
        'Biller Name': 'Global Inc',
        'Invoice Date': '2023-10-05',
        'Invoice Number': 'INV001',
        'Document Name': 'Invoice1.pdf'
    }

    line_items = [
        {'Item Description': 'Item 1', 'Unit Price': 100.00, 'Quantity': 2, 'Total Price': 200.00},
        {'Item Description': 'Item 2', 'Unit Price': 50.00, 'Quantity': 4, 'Total Price': 200.00}
    ]

    return main_header, invoice_header, line_items

def extract_ledger_data(comparison_results):
    """
    Extract ledger_header and line_items from comparison_results.
    Replace this with actual extraction logic based on your OCR output.
    """
    # TODO: Implement your actual extraction logic here based on comparison_results
    # Placeholder extraction logic
    ledger_header = {
        'Ledger ID': 'LDG001',
        'Account Name': 'John Doe',
        'Date': '2023-10-05',
        'Document Name': 'Ledger1.pdf'
    }

    line_items = [
        {'Transaction Description': 'Deposit', 'Amount': 500.00, 'Balance': 500.00},
        {'Transaction Description': 'Withdrawal', 'Amount': 200.00, 'Balance': 300.00}
    ]

    return ledger_header, line_items

def extract_visiting_card_data(comparison_results):
    """
    Extract header and contact_info from comparison_results.
    Replace this with actual extraction logic based on your OCR output.
    """
    # TODO: Implement your actual extraction logic here based on comparison_results
    # Placeholder extraction logic
    header = {
        'Name': 'Jane Smith',
        'Company': 'Tech Solutions',
        'Position': 'Software Engineer',
        'Document Name': 'VisitingCard1.png'
    }

    contact_info = [
        {'Phone': '123-456-7890'},
        {'Email': 'jane.smith@techsolutions.com'}
    ]

    return header, contact_info
