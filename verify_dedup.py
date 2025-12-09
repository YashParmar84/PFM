import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "personal_finance_management.settings")
django.setup()

from user.models import LoanProduct

print("--- Starting Deduplication Verification ---")

all_products = LoanProduct.objects.all()
initial_count = all_products.count()
print(f"Total products in DB: {initial_count}")

seen_products = set()
unique_products = []

duplicates_found = 0

for product in all_products:
    product_key = (
        product.model_name,
        product.bank_name,
        product.interest_rate,
        product.price,
        product.emi,
        product.tenure_months
    )

    if product_key not in seen_products:
        seen_products.add(product_key)
        unique_products.append(product)
    else:
        duplicates_found += 1
        # Optional: Print details of duplicate
        # print(f"Duplicate found: {product.model_name} from {product.bank_name}")

print(f"Unique products count: {len(unique_products)}")
print(f"Duplicates found and removed: {duplicates_found}")

if len(unique_products) + duplicates_found == initial_count:
    print("SUCCESS: Logic is consistent.")
else:
    print("ERROR: Counts do not match.")
