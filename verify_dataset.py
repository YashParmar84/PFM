import pandas as pd
import os

file_path = 'final_emis_corrected.xlsx'
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

try:
    print(f"Reading {file_path}...")
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names: {xl.sheet_names}")
    
    if 'sample_emis' in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name='sample_emis')
        print(f"Successfully read 'sample_emis' sheet. Rows: {len(df)}")
        print("Columns:", list(df.columns))
        
        required_cols = ['item_category', 'loan_type', 'bank_name', 'emi', 'rate_p.a', 'tenure_months']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"WARNING: Missing columns: {missing}")
        else:
            print("All core columns present.")
    else:
        print("ERROR: 'sample_emis' sheet not found!")
        # Check first sheet as fallback
        first_sheet = xl.sheet_names[0]
        print(f"Checking first sheet '{first_sheet}' instead...")
        df = pd.read_excel(file_path, sheet_name=first_sheet)
        print("Columns:", list(df.columns))

except Exception as e:
    print(f"Error reading file: {e}")
