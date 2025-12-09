from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import Transaction, UserProfile
from datetime import datetime, timedelta, date
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Generate historical financial data for 20 Indian users with 12 months of transactions'

    def add_arguments(self, parser):
        # No arguments needed for this command
        pass

    def handle(self, *args, **options):
        self.stdout.write("Starting generation of 20 test users...")

        # Define User Groups
        groups = [
            {
                'name_prefix': 'mid_income',
                'count': 5,
                'min_income': 25000,
                'max_income': 30000,
                'desc': 'Income ₹25k-30k',
                'expense_ratios': { # Allocation of income to expenses (approx)
                    'rent': 0.30, 'food': 0.20, 'emi': 0.0, 'utilities': 0.10, 'transport': 0.10,
                    'shopping': 0.05, 'entertainment': 0.05, 'healthcare': 0.05, 'travel': 0.05
                }
            },
            {
                'name_prefix': 'low_mid_income',
                'count': 5,
                'min_income': 10000,
                'max_income': 15000,
                'desc': 'Income ₹10k-15k',
                'expense_ratios': {
                    'rent': 0.35, 'food': 0.25, 'emi': 0.0, 'utilities': 0.10, 'transport': 0.10,
                    'shopping': 0.05, 'entertainment': 0.05, 'healthcare': 0.05, 'travel': 0.02
                }
            },
            {
                'name_prefix': 'low_income',
                'count': 5,
                'min_income': 5000,
                'max_income': 9999,
                'desc': 'Income < ₹10k',
                'expense_ratios': {
                    'rent': 0.40, 'food': 0.30, 'emi': 0.0, 'utilities': 0.10, 'transport': 0.10,
                    'shopping': 0.02, 'entertainment': 0.02, 'healthcare': 0.04, 'travel': 0.0
                }
            },
            {
                'name_prefix': 'high_income',
                'count': 5,
                'min_income': 200000,
                'max_income': 500000,
                'desc': 'Income ₹2L-5L',
                'expense_ratios': {
                    'rent': 0.15, 'food': 0.10, 'emi': 0.20, 'utilities': 0.05, 'transport': 0.05,
                    'shopping': 0.15, 'entertainment': 0.10, 'healthcare': 0.05, 'travel': 0.10
                }
            }
        ]

        # Categories for expenses (9 categories)
        expense_categories = [
            'food', 'transport', 'rent', 'EMIs', 'utilities',
            'shopping', 'entertainment', 'healthcare', 'travel'
        ]

        total_users_created = 0
        all_transactions = []

        # Generate last 12 months from today
        today = date.today()
        months_to_generate = []
        for i in range(12):
            # Calculate the month i months ago
            target_date = today.replace(day=1) - timedelta(days=30 * i)
            months_to_generate.append((target_date.year, target_date.month))

        for group in groups:
            for i in range(group['count']):
                username = f"{group['name_prefix']}_{i+1}"
                email = f"{username}@example.com"

                # Cleanup existing
                try:
                    u = User.objects.get(username=username)
                    u.delete()
                except User.DoesNotExist:
                    pass

                # Create User
                user = User.objects.create_user(username=username, email=email, password='123456')
                UserProfile.objects.get_or_create(user=user) # Ensure profile exists

                # Determine Monthly Salary for this user (fixed for all months for consistency or slight variation)
                salary_base = random.randint(group['min_income'], group['max_income'])

                self.stdout.write(f"Created {username} (Salary: {salary_base})")

                for year, month in months_to_generate:
                    # 1. Salary Credit (Income)
                    salary_date = date(year, month, 1) + timedelta(days=random.randint(0, 4)) # 1st-5th of month
                    all_transactions.append(Transaction(
                        user=user,
                        transaction_type='income',
                        amount=salary_base,
                        category='salary', # Assumption: 'salary' is a valid category or mapped to 'other'
                        description='Monthly Salary Credit',
                        date=salary_date
                    ))

                    # 2. Expenses (9 transactions)
                    # We have 9 categories. We will create 1 transaction per category.

                    # Calculate total expenses to target savings?
                    # Generally expenses < income usually, but for low income might be close.
                    # We use expense_ratios to determine amounts.

                    ratios = group['expense_ratios']

                    for cat in expense_categories:
                        cat_key = cat
                        if cat == 'EMIs' and 'emi' in ratios: 
                            ratio_key = 'emi'
                        elif cat == 'transport':
                            ratio_key = 'transport'
                        else:
                            ratio_key = cat

                        ratio = ratios.get(ratio_key, 0.05)

                        # Amount with some randomization
                        amount = salary_base * ratio * random.uniform(0.8, 1.2)

                        # Fix for 0 ratio (e.g. low income travel) -> minimal amount or skip?
                        # Prompt says "generate the remaining 9 transactions". So must exist.
                        if amount < 10:
                            amount = random.randint(50, 200) # Nominal amount

                        # Random date in the month
                        # Avoid checking valid days too hard, just use 1-28
                        day = random.randint(1, 28)
                        tx_date = date(year, month, day)

                        # Map category to model choices if needed.
                        # Using 'food', 'transportation', 'rent', 'emi', 'utilities', 'shopping', 'entertainment', 'healthcare', 'travel'
                        # Adjust 'transport' to 'transportation' if that's the model key.
                        model_cat = cat
                        if cat == 'transport': model_cat = 'transportation'
                        if cat == 'EMIs': model_cat = 'emi'

                        all_transactions.append(Transaction(
                            user=user,
                            transaction_type='expense',
                            amount=round(amount, 2),
                            category=model_cat,
                            description=f"Monthly {cat} expense",
                            date=tx_date
                        ))

                total_users_created += 1

        # Bulk Create
        Transaction.objects.bulk_create(all_transactions)

        self.stdout.write(self.style.SUCCESS(f"Successfully generated data for {total_users_created} users."))
        self.stdout.write(f"Total transactions: {len(all_transactions)}")

# No additional methods needed
