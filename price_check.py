e#!/usr/bin/env python3
"""Check car price distribution"""

import pandas as pd

excel_file = 'loan_products_and_rates_for_chatbot.xlsx'
cars_df = pd.read_excel(excel_file, sheet_name='Cars')

cars_df['Approx_Price_INR'] = pd.to_numeric(cars_df['Approx_Price_INR'], errors='coerce')

print(f"Total cars in Excel: {len(cars_df)}")

cars_sorted = cars_df.sort_values('Approx_Price_INR')

print("\nCars sorted by price (ascending):")
for i, (_, row) in enumerate(cars_sorted.iterrows(), 1):
    print(f"{i}. {row['Name']} - INR {row['Approx_Price_INR']:,.0f} ({row['Tier']})")

kia_row = cars_df[cars_df['Name'] == 'Kia Sonet']
if not kia_row.empty:
    kia_price = kia_row.iloc[0]['Approx_Price_INR']
    kia_tier = kia_row.iloc[0]['Tier']
    print(f"\nKia Sonet position: Price INR {kia_price:,.0f} ({kia_tier})")

    # How many cars are cheaper than Kia?
    cheaper_count = (cars_df['Approx_Price_INR'] < kia_price).sum()
    print(f"Cars cheaper than Kia Sonet: {cheaper_count}")
    print(f"Kia Sonet should be in position: {cheaper_count + 1}")

print(f"\nFirst 8 cars after sorting by price:")
for i, (_, row) in enumerate(cars_sorted.head(8).iterrows(), 1):
    print(f"{i}. {row['Name']} - INR {row['Approx_Price_INR']:,.0f}")

print(f"\nLast 8 cars (most expensive):")
for i, (_, row) in enumerate(cars_sorted.tail(8).iterrows(), 1):
    print(f"{cars_sorted.shape[0] - 8 + i}. {row['Name']} - INR {row['Approx_Price_INR']:,.0f}")
