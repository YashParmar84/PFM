from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import Transaction, Budget, SpendingPattern, FinancialGoal, UserProfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load and process Indian personal finance dataset from Kaggle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to the CSV dataset file',
            default='indian_financial_data.csv'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to associate the data with',
            required=True
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data for the user before loading',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        user_id = options['user_id']
        clear_existing = options['clear_existing']

        try:
            # Get the user
            user = User.objects.get(id=user_id)
            self.stdout.write(f"Loading data for user: {user.username}")

            # Check if file exists
            if not os.path.exists(file_path):
                self.stdout.write(
                    self.style.ERROR(f"Dataset file not found: {file_path}")
                )
                self.stdout.write("Creating sample dataset for demonstration...")
                self.create_sample_dataset(user, clear_existing)
                return

            # Load and process the dataset
            self.load_and_process_dataset(file_path, user, clear_existing)

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"User with ID {user_id} not found")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error loading dataset: {str(e)}")
            )

    def create_sample_dataset(self, user, clear_existing):
        """Create a sample dataset for demonstration"""
        if clear_existing:
            self.clear_user_data(user)

        # Generate sample financial data
        self.stdout.write("Generating sample financial data...")

        # Sample income data
        income_data = [
            {'amount': 75000, 'category': 'salary', 'description': 'Monthly Salary', 'date': '2025-01-15'},
            {'amount': 15000, 'category': 'freelance', 'description': 'Freelance Project', 'date': '2025-01-20'},
            {'amount': 85000, 'category': 'salary', 'description': 'Monthly Salary', 'date': '2025-02-15'},
            {'amount': 12000, 'category': 'investment', 'description': 'Stock Dividends', 'date': '2025-02-25'},
            {'amount': 90000, 'category': 'salary', 'description': 'Monthly Salary', 'date': '2025-03-15'},
        ]

        # Sample expense data
        expense_data = [
            {'amount': 25000, 'category': 'food', 'description': 'Monthly Groceries', 'date': '2025-01-05'},
            {'amount': 8000, 'category': 'transportation', 'description': 'Fuel & Maintenance', 'date': '2025-01-10'},
            {'amount': 15000, 'category': 'entertainment', 'description': 'Movies & Dining', 'date': '2025-01-15'},
            {'amount': 12000, 'category': 'shopping', 'description': 'Clothing & Accessories', 'date': '2025-01-20'},
            {'amount': 5000, 'category': 'healthcare', 'description': 'Medical Checkup', 'date': '2025-01-25'},
            {'amount': 30000, 'category': 'food', 'description': 'Monthly Groceries', 'date': '2025-02-05'},
            {'amount': 9000, 'category': 'transportation', 'description': 'Fuel & Maintenance', 'date': '2025-02-10'},
            {'amount': 18000, 'category': 'entertainment', 'description': 'Weekend Getaway', 'date': '2025-02-15'},
            {'amount': 35000, 'category': 'food', 'description': 'Monthly Groceries', 'date': '2025-03-05'},
            {'amount': 10000, 'category': 'transportation', 'description': 'Car Service', 'date': '2025-03-10'},
        ]

        # Create transactions
        all_transactions = []
        for income in income_data:
            transaction = Transaction(
                user=user,
                amount=income['amount'],
                transaction_type='income',
                category=income['category'],
                description=income['description'],
                date=income['date']
            )
            all_transactions.append(transaction)

        for expense in expense_data:
            transaction = Transaction(
                user=user,
                amount=expense['amount'],
                transaction_type='expense',
                category=expense['category'],
                description=expense['description'],
                date=expense['date']
            )
            all_transactions.append(transaction)

        # Bulk create transactions
        Transaction.objects.bulk_create(all_transactions)

        # Generate AI insights and patterns
        self.generate_ai_insights(user)

        self.stdout.write(
            self.style.SUCCESS(f"Dataset loaded successfully for user {user.username}")
        )
        self.stdout.write("You can now use AI budget predictions and suggestions!")

        self.stdout.write(
            self.style.SUCCESS(f"Sample dataset created for user {user.username}")
        )

    def load_and_process_dataset(self, file_path, user, clear_existing):
        """Load and process actual dataset file"""
        if clear_existing:
            self.clear_user_data(user)

        try:
            # Load the dataset
            df = pd.read_csv(file_path)
            self.stdout.write(f"Loaded dataset with {len(df)} rows")

            # Clean and process the data
            cleaned_df = self.clean_dataset(df)

            # Create transactions from the dataset
            transactions_created = self.create_transactions_from_dataset(cleaned_df, user)

            # Generate AI insights
            self.generate_ai_insights(user)

            self.stdout.write(
                self.style.SUCCESS(f"Successfully processed {transactions_created} transactions for user {user.username}")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error processing dataset: {str(e)}")
            )

    def clean_dataset(self, df):
        """Clean and standardize the dataset"""
        # Handle missing values
        df = df.dropna(subset=['Amount', 'Category', 'Type'])

        # Standardize column names
        df.columns = df.columns.str.lower().str.replace(' ', '_')

        # Ensure amount is numeric
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        # Standardize categories
        category_mapping = {
            'food': 'food',
            'food & dining': 'food',
            'transport': 'transportation',
            'travel': 'transportation',
            'entertainment': 'entertainment',
            'shopping': 'shopping',
            'utilities': 'bills',
            'bills': 'bills',
            'healthcare': 'healthcare',
            'medical': 'healthcare',
            'education': 'education',
            'salary': 'salary',
            'income': 'salary',
            'freelance': 'freelance',
            'investment': 'investment',
            'other': 'other'
        }

        df['category'] = df['category'].str.lower().str.strip().map(category_mapping).fillna('other')

        # Standardize transaction types
        df['type'] = df['type'].str.lower().str.strip()
        df['transaction_type'] = df['type'].map({'income': 'income', 'expense': 'expense'}).fillna('expense')

        # Generate dates if not present
        if 'date' not in df.columns:
            df['date'] = pd.date_range(start='2025-01-01', periods=len(df), freq='D')

        return df

    def create_transactions_from_dataset(self, df, user):
        """Create transactions from cleaned dataset"""
        transactions = []

        for _, row in df.iterrows():
            try:
                transaction = Transaction(
                    user=user,
                    amount=row['amount'],
                    transaction_type=row['transaction_type'],
                    category=row['category'],
                    description=row.get('description', f"Auto-imported {row['transaction_type']}"),
                    date=row['date']
                )
                transactions.append(transaction)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Skipping invalid row: {str(e)}")
                )

        # Bulk create transactions
        created = Transaction.objects.bulk_create(transactions)
        return len(created)

    def clear_user_data(self, user):
        """Clear existing data for user"""
        Transaction.objects.filter(user=user).delete()
        Budget.objects.filter(user=user).delete()
        SpendingPattern.objects.filter(user=user).delete()
        FinancialGoal.objects.filter(user=user).delete()

        self.stdout.write(f"Cleared existing data for user {user.username}")

    def generate_ai_insights(self, user):
        """Generate AI insights and patterns based on user's transaction data"""
        # Get user's transactions by category and month
        transactions = Transaction.objects.filter(user=user)

        if not transactions.exists():
            return

        # Group by category and month
        from django.db.models import Sum
        from collections import defaultdict

        category_monthly = defaultdict(lambda: defaultdict(float))

        for transaction in transactions:
            month_key = transaction.date.replace(day=1)
            category_monthly[transaction.category][month_key] += float(transaction.amount)

        # Generate spending patterns
        for category, monthly_data in category_monthly.items():
            for month, amount in monthly_data.items():
                # Calculate trend (simple moving average logic)
                trend = self.calculate_trend(category, monthly_data, month)

                # Generate prediction
                predicted_amount = self.predict_next_month(amount, trend)

                # Calculate confidence score
                confidence = self.calculate_confidence(monthly_data)

                # Create or update spending pattern
                pattern, created = SpendingPattern.objects.get_or_create(
                    user=user,
                    category=category,
                    month=month,
                    defaults={
                        'predicted_amount': predicted_amount,
                        'confidence_score': confidence,
                        'trend_direction': trend,
                        'ai_insights': self.generate_insights(category, amount, trend, confidence)
                    }
                )

                if not created:
                    pattern.predicted_amount = predicted_amount
                    pattern.confidence_score = confidence
                    pattern.trend_direction = trend
                    pattern.ai_insights = self.generate_insights(category, amount, trend, confidence)
                    pattern.save()

        # Generate sample financial goals
        self.create_sample_goals(user)

    def calculate_trend(self, category, monthly_data, current_month):
        """Calculate spending trend for a category"""
        amounts = list(monthly_data.values())
        if len(amounts) < 2:
            return 'stable'

        # Simple trend calculation
        recent_avg = np.mean(amounts[-3:]) if len(amounts) >= 3 else amounts[-1]
        earlier_avg = np.mean(amounts[:-1]) if len(amounts) > 1 else amounts[0]

        if recent_avg > earlier_avg * 1.1:
            return 'increasing'
        elif recent_avg < earlier_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'

    def predict_next_month(self, current_amount, trend):
        """Predict next month's spending"""
        if trend == 'increasing':
            return current_amount * 1.05  # 5% increase
        elif trend == 'decreasing':
            return current_amount * 0.95  # 5% decrease
        else:
            return current_amount  # Stable

    def calculate_confidence(self, monthly_data):
        """Calculate confidence score for predictions"""
        amounts = list(monthly_data.values())
        if len(amounts) < 2:
            return 50.00  # Low confidence for insufficient data

        # Calculate coefficient of variation
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)

        if mean_amount > 0:
            cv = (std_amount / mean_amount) * 100
            confidence = max(10, 100 - cv)  # Higher variation = lower confidence
            return round(confidence, 2)

        return 50.00

    def generate_insights(self, category, amount, trend, confidence):
        """Generate AI insights for spending patterns"""
        insights = []

        # Trend-based insights
        if trend == 'increasing':
            insights.append(f"Your {category} spending is increasing. Consider reviewing your expenses in this category.")
        elif trend == 'decreasing':
            insights.append(f"Great! Your {category} spending is decreasing, indicating better financial control.")

        # Amount-based insights
        if amount > 50000:
            insights.append(f"High spending in {category} category. Consider setting a budget limit.")
        elif amount < 5000:
            insights.append(f"Low spending in {category} category. This might indicate underspending or missed opportunities.")

        # Confidence-based insights
        if confidence < 30:
            insights.append("Limited data available for accurate predictions. More transactions will improve insights.")
        elif confidence > 80:
            insights.append("Strong spending pattern detected. Predictions are highly reliable.")

        return " ".join(insights) if insights else "Continue monitoring your spending patterns for better insights."

    def create_sample_goals(self, user):
        """Create sample financial goals"""
        goals_data = [
            {
                'goal_name': 'Emergency Fund',
                'target': 200000,
                'current': 50000,
                'target_date': '2025-12-31',
                'category': '',
                'priority': 1
            },
            {
                'goal_name': 'Vacation Fund',
                'target': 100000,
                'current': 25000,
                'target_date': '2025-06-30',
                'category': 'entertainment',
                'priority': 2
            },
            {
                'goal_name': 'New Smartphone',
                'target': 50000,
                'current': 15000,
                'target_date': '2025-04-30',
                'category': 'shopping',
                'priority': 3
            }
        ]

        for goal_data in goals_data:
            goal, created = FinancialGoal.objects.get_or_create(
                user=user,
                goal_name=goal_data['goal_name'],
                defaults={
                    'target_amount': goal_data['target'],
                    'current_amount': goal_data['current'],
                    'target_date': goal_data['target_date'],
                    'category': goal_data['category'],
                    'priority': goal_data['priority']
                }
            )

            if created:
                self.stdout.write(f"Created goal: {goal.goal_name}")
