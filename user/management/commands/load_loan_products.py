import pandas as pd
from django.core.management.base import BaseCommand
from django.db.models import Count
from user.models import LoanProduct


class Command(BaseCommand):
    help = 'Load loan product dataset from Excel file'

    def handle(self, *args, **options):
        try:
            # Read the Excel file
            excel_file = 'complete_loan_product_dataset.xlsx'
            
            # Read all relevant sheets
            sample_emis_df = pd.read_excel(excel_file, sheet_name='sample_emis')
            
            self.stdout.write(self.style.SUCCESS(f"Loaded {len(sample_emis_df)} loan products from dataset"))
            
            # Clear existing data
            LoanProduct.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing loan products"))
            
            # Process the data
            loan_products_created = 0
            price_cache = {}  # Cache for item prices
            
            for index, row in sample_emis_df.iterrows():
                try:
                    # Get item price (either from cache or calculate)
                    item_category = row['item_category']
                    item_id = int(row['item_id']) if pd.notna(row['item_id']) else 0
                    
                    # Cache the item price based on category and ID
                    cache_key = f"{item_category}_{item_id}"
                    if cache_key not in price_cache:
                        # Calculate original price: loan_amount / (ltv_pct/100)
                        ltv_pct = float(row['ltv_pct']) if pd.notna(row['ltv_pct']) else 90.0
                        loan_amount = float(row['loan_amount']) if pd.notna(row['loan_amount']) else 0.0
                        original_price = loan_amount / (ltv_pct / 100.0)
                        price_cache[cache_key] = original_price
                    
                    # Determine category from item_category column
                    category = self.get_category_from_item_category(item_category)
                    
                    # Clean and process the data
                    loan_product = LoanProduct(
                        category=category,
                        item_id=item_id,
                        model_name=str(row['item_model']).strip() if pd.notna(row['item_model']) else 'Unknown',
                        price=price_cache[cache_key],
                        bank_name=str(row['bank_name']).strip(),
                        loan_type=str(row['loan_type']).strip(),
                        interest_rate=float(row['rate_p.a']) if pd.notna(row['rate_p.a']) else 0.0,
                        tenure_months=int(row['tenure_months']) if pd.notna(row['tenure_months']) else 0,
                        loan_amount=float(row['loan_amount']) if pd.notna(row['loan_amount']) else 0.0,
                        emi=float(row['emi']) if pd.notna(row['emi']) else 0.0,
                    )
                    loan_product.save()
                    loan_products_created += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing row {index}: {str(e)}"))
                    continue
            
            self.stdout.write(self.style.SUCCESS(f"Successfully created {loan_products_created} loan products"))
            
            # Print summary by category
            category_summary = LoanProduct.objects.values('category').annotate(count=Count('id'))
            for cat in category_summary:
                self.stdout.write(f"  {cat['category']}: {cat['count']} products")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading dataset: {str(e)}"))
    
    def get_category_from_item_category(self, item_category):
        """Map item category to our model categories"""
        if item_category == 'two_wheeler':
            return 'two_wheeler'
        elif item_category == 'four_wheeler':
            return 'four_wheeler'
        elif item_category == 'electronics':
            return 'electronics'
        elif item_category == 'loan_example':
            # For loan examples, determine based on loan type
            return 'personal_loan'  # Default, will be refined
        else:
            return 'electronics'  # Default fallback
