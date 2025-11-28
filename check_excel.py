import pandas as pd
import os

excel_file = 'loan_products_and_rates_for_chatbot.xlsx'

if os.path.exists(excel_file):
    print('Excel file exists. Checking contents...')
    xls = pd.ExcelFile(excel_file)
    print('Sheets:', xls.sheet_names)

    for sheet in xls.sheet_names:
        print(f'\n{sheet.upper()} SHEET:')
        df = pd.read_excel(excel_file, sheet_name=sheet)
        print(f'Shape: {df.shape}')
        print(f'Columns: {list(df.columns)}')
        print('First 3 rows:')
        print(df.head(3))
        print('\n' + '='*50)
else:
    print('Excel file not found!')
