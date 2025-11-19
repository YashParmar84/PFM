from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import Transaction, Budget, SpendingPattern, FinancialGoal
from history import (
    PROFESSION_INCOME_PATTERNS, EXPENSE_PATTERNS, SEASONAL_VARIATIONS,
    TRANSACTION_FREQUENCIES, TRANSACTION_DESCRIPTIONS, ANNUAL_INCOME_ADJUSTMENTS,
    SPECIAL_EVENTS, SAVINGS_GOALS, get_lifestyle_for_salary, get_seasonal_multiplier,
    get_random_description, calculate_realistic_variance, apply_inflation_adjustment,
    SALARY_GROWTH_RATE, INFLATION_RATE
)
import numpy as np
from datetime import datetime, timedelta
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add extensive historical financial data (12-24 months) to existing users for ML budget prediction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to add data to (adds to all users if not specified)',
            required=False
        )
        parser.add_argument(
            '--months',
            type=int,
            default=24,
            help='Number of months of historical data to generate (default: 24)'
        )
        parser.add_argument(
            '--salary',
            type=float,
            help='Monthly salary for the user (if not specified, will be estimated from existing data)',
            required=False
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing transaction data before generating new data',
        )
        parser.add_argument(
            '--specific-months',
            help='Comma-separated list of specific months to generate data for (format: YYYY-MM,YYYY-MM,...)',
            required=False
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        months = options['months']
        salary_param = options['salary']
        clear_existing = options['clear_existing']
        specific_months = options.get('specific_months')

        if user_id:
            # Single user
            try:
                user = User.objects.get(id=user_id)
                users = [user]
                if specific_months:
                    self.stdout.write(f"Adding transaction data for specific months to user: {user.username}")
                else:
                    self.stdout.write(f"Adding {months} months of historical data to user: {user.username}")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with ID {user_id} not found")
                )
                return
        else:
            # All users
            users = User.objects.all()
            if specific_months:
                self.stdout.write(f"Adding transaction data for specific months to ALL users ({len(users)} total)")
            else:
                self.stdout.write(f"Adding {months} months of historical data to ALL users ({len(users)} total)")

        total_transactions = 0
        total_users_processed = 0

        for user in users:
            try:
                self.stdout.write(f"\n--- Processing user: {user.username} ---")

                # Estimate or get salary for the user
                monthly_salary = self.estimate_user_salary(user, salary_param)

                if not monthly_salary:
                    self.stdout.write(
                        self.style.WARNING(f"No salary data found for user {user.username}, skipping...")
                    )
                    continue

                # Generate extensive historical data
                transactions_created = self.generate_historical_data_for_user(
                    user, monthly_salary, months, clear_existing, specific_months
                )

                total_transactions += transactions_created
                total_users_processed += 1

                if specific_months:
                    month_count = len(specific_months.split(','))
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {user.username}: Added {transactions_created} transactions for {month_count} specific months")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {user.username}: Added {transactions_created} transactions over {months} months")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing user {user.username}: {str(e)}")
                )
                continue

        # Generate AI insights for all processed users
        if total_users_processed > 0:
            self.stdout.write("\n--- Generating AI Insights ---")
            for user in users[:total_users_processed]:
                try:
                    self.generate_ml_insights(user)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Error generating insights for {user.username}: {str(e)}")
                    )

        self.stdout.write("\n=== FINAL SUMMARY ===")
        self.stdout.write(f"Users processed: {total_users_processed}")
        self.stdout.write(f"Total transactions created: {total_transactions}")
        self.stdout.write(f"Average transactions per user: {total_transactions // max(total_users_processed, 1)}")
        self.stdout.write(
            self.style.SUCCESS("✅ Data generation complete! ML predictions should now be much more accurate.")
        )
        self.stdout.write("💡 Tip: Use the AI suggestions feature to see budget recommendations based on historical patterns.")

    def estimate_user_salary(self, user, salary_param):
        """Estimate user's monthly salary from existing data or use provided parameter"""
        if salary_param:
            return salary_param

        # Try to estimate from existing income transactions
        recent_income = Transaction.objects.filter(
            user=user,
            transaction_type='income'
        ).order_by('-date')[:12]  # Last 12 income transactions

        if recent_income.exists():
            avg_income = sum(float(tx.amount) for tx in recent_income) / len(recent_income)
            return round(avg_income, 2)

        # Fallback: estimate based on expense patterns
        recent_expenses = Transaction.objects.filter(
            user=user,
            transaction_type='expense'
        ).aggregate(total=Decimal('0'))

        if recent_expenses['total'] > 0:
            # Assume expenses are about 70-85% of income depending on lifestyle
            total_expenses = float(recent_expenses['total'])
            # Estimate salary as expenses divided by 0.8 (assuming 20% savings)
            estimated_salary = total_expenses / 0.8
            return round(min(estimated_salary, 500000), 2)  # Cap at reasonable amount

        # Default fallback salaries based on user ID or random
        default_salaries = [45000, 65000, 85000, 105000, 125000, 150000, 180000, 220000]
        return random.choice(default_salaries)

    def generate_historical_data_for_user(self, user, monthly_salary, months, clear_existing, specific_months=None):
        """Generate extensive financial data for a user"""

        if clear_existing:
            Transaction.objects.filter(user=user).delete()
            self.stdout.write(f"Cleared existing transaction data for {user.username}")

        # Determine spending pattern from salary
        if monthly_salary < 30000:
            spending_pattern = 'minimalist'
        elif monthly_salary < 60000:
            spending_pattern = 'balanced'
        elif monthly_salary < 100000:
            spending_pattern = 'growing'
        elif monthly_salary < 200000:
            spending_pattern = 'luxury'
        else:
            spending_pattern = 'high_income_saver'

        transactions = []

        if specific_months:
            # Generate data for specific months
            month_list = [m.strip() for m in specific_months.split(',')]

            for month_str in month_list:
                try:
                    year, month = map(int, month_str.split('-'))
                    month_date = datetime(year, month, 1)

                    # Generate income transactions
                    income_txs = self.generate_monthly_income(user, month_date, monthly_salary, spending_pattern)
                    transactions.extend(income_txs)

                    # Generate expense transactions
                    expense_txs = self.generate_monthly_expenses(user, month_date, monthly_salary, spending_pattern)
                    transactions.extend(expense_txs)

                except (ValueError, IndexError) as e:
                    self.stdout.write(
                        self.style.WARNING(f"Skipping invalid month format '{month_str}': {str(e)}")
                    )
                    continue
        else:
            # Generate data from past to present
            end_date = datetime.now().replace(day=1)
            start_date = end_date.replace(year=end_date.year - (months // 12) - 1,
                                          month=(end_date.month + (months % 12)) % 12 + 1)
            if (end_date.month + (months % 12)) % 12 + 1 > 12:
                start_date = start_date.replace(year=start_date.year + 1, month=1)

            current_date = start_date
            monthly_salaries = []  # Track salary changes over time

            while current_date <= end_date:
                month_start = current_date.replace(day=1)

                # Generate salary with some growth over time
                if monthly_salaries:
                    # Add 2-8% annual salary growth
                    months_since_start = len(monthly_salaries)
                    growth_factor = 1 + (0.02 + random.random() * 0.06) * (months_since_start / 12)
                    current_salary = monthly_salary * min(growth_factor, 2.0)  # Cap at 2x original
                else:
                    current_salary = monthly_salary

                monthly_salaries.append(current_salary)

                # Generate income transactions
                income_txs = self.generate_monthly_income(user, month_start, current_salary, spending_pattern)
                transactions.extend(income_txs)

                # Generate expense transactions
                expense_txs = self.generate_monthly_expenses(user, month_start, current_salary, spending_pattern)
                transactions.extend(expense_txs)

                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

        # Bulk create all transactions
        created_txs = Transaction.objects.bulk_create(transactions)
        return len(created_txs)

    def generate_monthly_income(self, user, month_date, salary, pattern):
        """Generate income transactions for a month"""
        transactions = []
        base_date = month_date.replace(day=15)

        # Main salary income
        transactions.append(Transaction(
            user=user,
            amount=round(Decimal(salary), 2),
            transaction_type='income',
            category='salary',
            description='Monthly Salary',
            date=base_date.strftime('%Y-%m-%d')
        ))

        # Additional income based on salary level and pattern
        if salary > 100000:  # High income
            # Bonus or investment income
            if random.random() < 0.3:  # 30% chance
                bonus = salary * (0.05 + random.random() * 0.15)  # 5-20% bonus
                bonus_date = base_date + timedelta(days=random.randint(20, 25))
                transactions.append(Transaction(
                    user=user,
                    amount=round(Decimal(bonus), 2),
                    transaction_type='income',
                    category='investment',
                    description='Performance Bonus',
                    date=bonus_date.strftime('%Y-%m-%d')
                ))

        elif 50000 <= salary <= 100000:  # Middle income
            # Occasional freelance or side income
            if random.random() < 0.2:  # 20% chance
                freelance = salary * (0.1 + random.random() * 0.3)  # 10-40% of salary
                freelance_date = base_date + timedelta(days=random.randint(10, 20))
                transactions.append(Transaction(
                    user=user,
                    amount=round(Decimal(freelance), 2),
                    transaction_type='income',
                    category='freelance',
                    description='Freelance Work',
                    date=freelance_date.strftime('%Y-%m-%d')
                ))

        # Investment dividends (small amount for most users)
        if random.random() < 0.4:  # 40% chance
            dividend = salary * (0.01 + random.random() * 0.02)  # 1-3% of salary
            dividend_date = base_date + timedelta(days=random.randint(25, 28))
            transactions.append(Transaction(
                user=user,
                amount=round(Decimal(dividend), 2),
                transaction_type='income',
                category='investment',
                description='Investment Dividend',
                date=dividend_date.strftime('%Y-%m-%d')
            ))

        return transactions

    def generate_monthly_expenses(self, user, month_date, salary, pattern):
        """Generate expense transactions for a month"""
        transactions = []

        # Use expense patterns from history.py reference data
        lifestyle = get_lifestyle_for_salary(salary)
        expense_data = EXPENSE_PATTERNS.get(lifestyle, EXPENSE_PATTERNS['moderate'])
        ratios = expense_data['ratios']

        # Generate expenses with realistic variability
        for category, ratio in ratios.items():
            base_amount = salary * ratio
            num_transactions = self.get_transaction_count_for_category(category, pattern)

            for i in range(num_transactions):
                # Add realistic variation (±25%)
                variation = 0.75 + random.random() * 0.5
                amount = base_amount / num_transactions * variation

                # Generate realistic date within month
                days_in_month = 28 + (month_date.month in [1, 3, 5, 7, 8, 10, 12]) + (month_date.year % 4 == 0 and month_date.month == 2)
                tx_day = random.randint(1, min(days_in_month, 28))  # Cap at 28 for safety
                tx_date = month_date.replace(day=tx_day)

                description = self.get_expense_description(category, i, pattern)

                transactions.append(Transaction(
                    user=user,
                    amount=round(Decimal(amount), 2),
                    transaction_type='expense',
                    category=category,
                    description=description,
                    date=tx_date.strftime('%Y-%m-%d')
                ))

        return transactions

    def get_transaction_count_for_category(self, category, pattern):
        """Get minimum 20 transactions per month total across all categories"""
        # Use transaction frequencies from history.py reference data
        lifestyle_counts = TRANSACTION_FREQUENCIES.get(pattern, TRANSACTION_FREQUENCIES.get('moderate', {}))

        # For minimum 20 transactions per month total, boost most categories significantly
        base_count = lifestyle_counts.get(category, 1)

        # Distribute counts to ensure minimum 20 transactions per month
        if category == 'food':
            base_count = random.randint(6, 8)  # Weekly grocery shopping + dining out
        elif category == 'transportation':
            base_count = random.randint(4, 6)  # Fuel, rides, maintenance, parking
        elif category == 'shopping':
            base_count = random.randint(4, 6)  # Clothing, electronics, home items
        elif category == 'entertainment':
            base_count = random.randint(3, 5)  # Movies, dining, subscriptions, events
        elif category == 'bills':
            base_count = random.randint(2, 3)  # Electricity, internet, phone, water
        elif category == 'healthcare':
            base_count = random.randint(2, 3)  # Doctor visits, pharmacy, gym
        elif category == 'investment':
            base_count = random.randint(1, 2)  # Bonuses, dividends
        elif category == 'freelance':
            base_count = random.randint(0, 2)  # Occasional freelance work
        else:
            base_count = random.randint(1, 3)  # Other categories with some activity

        # Ensure at least 1 transaction for categories that should always have some activity
        return max(1, base_count)

    def get_expense_description(self, category, transaction_index, pattern):
        """Get realistic expense descriptions from history.py reference data"""
        # Use descriptions from history.py reference data
        if category in TRANSACTION_DESCRIPTIONS:
            descriptions = TRANSACTION_DESCRIPTIONS[category]
            return descriptions[transaction_index % len(descriptions)]
        return f"{category.title()} purchase"

    def generate_ml_insights(self, user):
        """Generate ML-based insights and spending patterns for the user"""
        transactions = Transaction.objects.filter(user=user, transaction_type='expense')

        if not transactions.exists():
            return

        # Group by category and month for analysis
        from collections import defaultdict
        category_monthly = defaultdict(lambda: defaultdict(float))

        for transaction in transactions:
            month_key = transaction.date.replace(day=1)
            category_monthly[transaction.category][month_key] += float(transaction.amount)

        # Generate insights for each category
        for category, monthly_data in category_monthly.items():
            if len(monthly_data) < 3:  # Need at least 3 months for meaningful insights
                continue

            amounts = list(monthly_data.values())
            months = list(monthly_data.keys())

            # Calculate trend
            trend = self.calculate_ml_trend(amounts)

            # Predict next month
            prediction = self.predict_next_month_expense(amounts, trend)

            # Calculate confidence
            confidence = self.calculate_prediction_confidence(amounts)

            # Generate AI insights
            insights = self.generate_ml_insights_text(category, amounts, trend, confidence)

            # Save or update spending patterns for the most recent month
            most_recent_month = max(months)
            pattern, created = SpendingPattern.objects.get_or_create(
                user=user,
                category=category,
                month=most_recent_month,
                defaults={
                    'predicted_amount': prediction,
                    'confidence_score': confidence,
                    'trend_direction': trend,
                    'ai_insights': insights
                }
            )

            if not created:
                pattern.predicted_amount = prediction
                pattern.confidence_score = confidence
                pattern.trend_direction = trend
                pattern.ai_insights = insights
                pattern.save()

        # Create financial goals for more realistic data
        self.create_realistic_goals(user, transactions)

    def calculate_ml_trend(self, amounts):
        """Calculate spending trend using linear regression"""
        if len(amounts) < 2:
            return 'stable'

        x = np.arange(len(amounts))
        slope = np.polyfit(x, amounts, 1)[0]
        mean_amount = np.mean(amounts)

        if mean_amount == 0:
            return 'stable'

        relative_slope = slope / mean_amount

        if relative_slope > 0.03:  # >3% increase per month
            return 'increasing'
        elif relative_slope < -0.03:  # >3% decrease per month
            return 'decreasing'
        else:
            return 'stable'

    def predict_next_month_expense(self, amounts, trend):
        """Predict next month expense using exponential smoothing"""
        if len(amounts) == 0:
            return 0

        # Use exponential smoothing
        alpha = 0.3
        smoothed = [amounts[0]]

        for i in range(1, len(amounts)):
            smoothed_val = alpha * amounts[i] + (1 - alpha) * smoothed[i-1]
            smoothed.append(smoothed_val)

        last_smoothed = smoothed[-1]

        # Apply trend adjustment
        if trend == 'increasing':
            prediction = last_smoothed * 1.05  # 5% increase
        elif trend == 'decreasing':
            prediction = last_smoothed * 0.95  # 5% decrease
        else:
            prediction = last_smoothed * (0.98 + random.random() * 0.04)  # ±2% variation

        return round(prediction, 2)

    def calculate_prediction_confidence(self, amounts):
        """Calculate confidence in prediction"""
        if len(amounts) < 2:
            return 30.0

        # Coefficient of variation (lower = more predictable = higher confidence)
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)

        if mean_amount == 0:
            return 50.0

        cv = std_amount / mean_amount

        # Sample size factor
        sample_factor = min(1.0, len(amounts) / 12)  # Normalize to 12 months

        # Consistency factor
        consistency_factor = max(0.1, 1 - cv)

        # Combined confidence score
        confidence = (consistency_factor * 0.6 + sample_factor * 0.4) * 100

        return round(min(95, max(20, confidence)), 1)

    def generate_ml_insights_text(self, category, amounts, trend, confidence):
        """Generate human-readable insights about spending patterns"""
        insights = []
        latest_amount = amounts[-1] if amounts else 0
        avg_amount = np.mean(amounts) if amounts else 0

        # Trend insights
        if trend == 'increasing':
            monthly_increase = np.mean(np.diff(amounts)) if len(amounts) > 1 else 0
            if monthly_increase > 0:
                insights.append(f"Spending in {category} is increasing by ₹{monthly_increase:.0f} per month. Consider setting a budget limit.")
            else:
                insights.append(f"Recent spending in {category} shows an upward trend. Monitor to prevent overspending.")

        elif trend == 'decreasing':
            monthly_decrease = abs(np.mean(np.diff(amounts))) if len(amounts) > 1 else 0
            if monthly_decrease > 0:
                insights.append(f"Excellent! {category} spending is decreasing by ₹{monthly_decrease:.0f} per month.")

        # Amount compared to average
        if latest_amount > avg_amount * 1.2:
            insights.append(f"This month's {category} spending (₹{latest_amount:.0f}) is significantly above average (₹{avg_amount:.0f}).")

        # Confidence level insights
        if confidence > 80:
            insights.append("Strong, consistent spending pattern detected. Budget predictions are highly reliable.")
        elif confidence < 50:
            insights.append("Variable spending pattern detected. More data needed for accurate predictions.")

        # Seasonal or volatility insights
        if len(amounts) >= 6:
            cv = np.std(amounts) / np.mean(amounts) if np.mean(amounts) > 0 else 0
            if cv > 0.4:
                insights.append(f"High variability in {category} spending. Consider smoothing out expenses across months.")

        return " | ".join(insights) if insights else f"Analyzed {len(amounts)} months of {category} spending data. Patterns established for budget prediction."

    def create_realistic_goals(self, user, transactions):
        """Create realistic financial goals based on user's transaction history"""

        # Calculate total monthly income and expenses
        monthly_income = transactions.filter(transaction_type='income').aggregate(
            total=Decimal('0'))['total'] or Decimal('0')

        monthly_expenses = transactions.filter(transaction_type='expense').aggregate(
            total=Decimal('0'))['total'] or Decimal('0')

        monthly_savings = float(monthly_income - monthly_expenses)

        # Create goals based on income level
        if monthly_savings > 50000:  # High saver
            goals = [
                {'name': 'Investment Portfolio', 'target': 2000000, 'current_pct': 0.3},
                {'name': 'Emergency Fund', 'target': 500000, 'current_pct': 0.7},
                {'name': 'Luxury Vacation', 'target': 300000, 'current_pct': 0.2},
                {'name': 'Home Down Payment', 'target': 1000000, 'current_pct': 0.1}
            ]
        elif monthly_savings > 20000:  # Moderate saver
            goals = [
                {'name': 'Emergency Fund', 'target': 300000, 'current_pct': 0.35},
                {'name': 'Vacation Fund', 'target': 150000, 'current_pct': 0.25},
                {'name': 'New Car', 'target': 400000, 'current_pct': 0.15},
                {'name': 'Home Improvement', 'target': 200000, 'current_pct': 0.4}
            ]
        else:  # Minimal or no savings
            goals = [
                {'name': 'Emergency Fund', 'target': 150000, 'current_pct': 0.15},
                {'name': 'Debt Reduction', 'target': 100000, 'current_pct': 0.08},
                {'name': 'Budget Education', 'target': 50000, 'current_pct': 0.05},
                {'name': 'Savings Habit', 'target': 25000, 'current_pct': 0.2}
            ]

        # Create goals in database
        for goal_data in goals:
            target = goal_data['target']
            current = int(target * goal_data['current_pct'])

            FinancialGoal.objects.get_or_create(
                user=user,
                goal_name=goal_data['name'],
                defaults={
                    'target_amount': target,
                    'current_amount': current,
                    'target_date': (datetime.now() + timedelta(days=random.randint(180, 730))).strftime('%Y-%m-%d'),
                    'priority': random.randint(1, 3)
                }
            )
