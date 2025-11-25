#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_finance_management.settings')
sys.path.append(os.getcwd())
django.setup()

# Import Django models and required modules
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import random
from user.models import UserProfile, Transaction, Budget

def create_users_for_range(range_name, salary_range, count):
    """Create users with specific salary range and their historical data"""
    
    users_data = [
        {
            'username': f'testuser_{range_name.replace("-", "to")}_1',
            'email': f'testuser_{range_name.replace("-", "to")}_1@example.com',
            'password': 'testpass123',
            'first_name': f'Test{range_name.replace("-", "to").title()}1'
        },
        {
            'username': f'testuser_{range_name.replace("-", "to")}_2', 
            'email': f'testuser_{range_name.replace("-", "to")}_2@example.com',
            'password': 'testpass123',
            'first_name': f'Test{range_name.replace("-", "to").title()}2'
        }
    ]
    
    for i, user_data in enumerate(users_data[:count]):
        create_user_with_salary_data(user_data, salary_range, range_name)

def create_user_with_salary_data(user_data, salary_range, range_name):
    """Create a user with salary transactions for the last 6 months"""
    
    # Check if user already exists
    if User.objects.filter(username=user_data['username']).exists():
        print(f"User {user_data['username']} already exists. Skipping...")
        return
    
    # Create user
    user = User.objects.create_user(
        username=user_data['username'],
        email=user_data['email'],
        password=user_data['password'],
        first_name=user_data['first_name'],
        last_name='TestUser'
    )
    
    # Create user profile
    profile = UserProfile.objects.create(
        user=user,
        phone_number=f'+91{random.randint(7000000000, 9999999999)}',
        address=f'{random.randint(1, 999)}, Test Street, Test City, {random.randint(100000, 999999)}',
        date_of_birth=datetime.now().date() - timedelta(days=random.randint(6570, 10950))  # 18-30 years old
    )
    
    # Create salary transactions for last 6 months
    current_date = timezone.now().date()
    monthly_salary = random.randint(salary_range[0], salary_range[1])
    
    for i in range(6):  # Last 6 months
        month_date = current_date.replace(day=1) - timedelta(days=30*i)
        
        # Create monthly salary transaction (usually on 1st of month)
        salary_date = month_date.replace(day=1)
        Transaction.objects.create(
            user=user,
            amount=monthly_salary,
            transaction_type='income',
            category='salary',
            description=f'Monthly salary for {month_date.strftime("%B %Y")}',
            date=salary_date
        )
        
        # Create some expense transactions for this month
        create_monthly_expenses(user, month_date, monthly_salary)
        
        # Create budget for the month
        create_monthly_budget(user, month_date, monthly_salary)
    
    print(f"Created user {user.username} with salary range {range_name} (₹{monthly_salary}/month) and 6 months of historical data")

def create_monthly_expenses(user, month_date, monthly_salary):
    """Create realistic monthly expenses for a user"""
    
    # Calculate available amount after basic expenses (typically 60-70% of salary)
    available_amount = monthly_salary * 0.65  # Assume 65% can be spent on lifestyle
    
    expense_categories = [
        ('food', 0.15),      # 15% on food
        ('transportation', 0.12),  # 12% on transportation
        ('entertainment', 0.08),   # 8% on entertainment
        ('shopping', 0.10),        # 10% on shopping
        ('bills', 0.15),           # 15% on bills
        ('healthcare', 0.05),      # 5% on healthcare
    ]
    
    # Create transactions throughout the month
    current_date = month_date.replace(day=1)
    
    for category, percentage in expense_categories:
        category_amount = available_amount * percentage
        
        # Create 2-4 transactions per category
        num_transactions = random.randint(2, 4)
        
        for _ in range(num_transactions):
            # Random date within the month
            day = random.randint(1, 28)
            try:
                transaction_date = current_date.replace(day=day)
            except ValueError:
                transaction_date = current_date.replace(day=28)  # Handle shorter months
            
            # Random amount for this transaction (20-80% of category amount)
            amount = category_amount * random.uniform(0.2, 0.8)
            
            descriptions = {
                'food': ['Restaurant dinner', 'Grocery shopping', 'Office lunch', 'Cafe visit', 'Food delivery'],
                'transportation': ['Bus fare', 'Fuel', 'Taxi ride', 'Metro fare', 'Auto rickshaw'],
                'entertainment': ['Movie tickets', 'Concert', 'Streaming subscription', 'Gaming', 'Shopping mall visit'],
                'shopping': ['Clothes shopping', 'Electronics', 'Online purchase', 'Gift', 'Personal items'],
                'bills': ['Electricity bill', 'Mobile recharge', 'Internet bill', 'Water bill', 'Gas bill'],
                'healthcare': ['Doctor visit', 'Medicine', 'Health checkup', 'Gym membership', 'Health insurance']
            }
            
            Transaction.objects.create(
                user=user,
                amount=round(amount, 2),
                transaction_type='expense',
                category=category,
                description=random.choice(descriptions[category]),
                date=transaction_date
            )
    
    # Create some freelance income for variety
    if random.random() < 0.3:  # 30% chance of freelance income
        freelance_date = month_date.replace(day=random.randint(5, 25))
        freelance_amount = random.randint(5000, 15000)
        
        Transaction.objects.create(
            user=user,
            amount=freelance_amount,
            transaction_type='income',
            category='freelance',
            description='Freelance project payment',
            date=freelance_date
        )

def create_monthly_budget(user, month_date, monthly_salary):
    """Create realistic budgets for the month"""
    
    budget_categories = {
        'food': monthly_salary * 0.15,
        'transportation': monthly_salary * 0.12,
        'entertainment': monthly_salary * 0.08,
        'shopping': monthly_salary * 0.10,
        'bills': monthly_salary * 0.15,
        'healthcare': monthly_salary * 0.05,
    }
    
    for category, amount in budget_categories.items():
        Budget.objects.create(
            user=user,
            category=category,
            amount=round(amount, 2),
            month=month_date
        )

if __name__ == "__main__":
    salary_ranges = {
        '20k-25k': (20000, 25000),
        '10k-15k': (10000, 15000), 
        '40k-50k': (40000, 50000)
    }
    
    print("Creating additional test users for AI testing...")
    
    for range_name, (min_salary, max_salary) in salary_ranges.items():
        print(f"\nCreating users for salary range: {range_name}")
        create_users_for_range(range_name, (min_salary, max_salary), 2)
    
    print("\nAll users created successfully!")
