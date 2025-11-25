from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import Transaction, Budget, SpendingPattern, FinancialGoal, UserProfile
import numpy as np
from datetime import datetime, timedelta
import random
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create 10 test users with 3 months of diverse financial data for testing ML algorithms'

    def handle(self, *args, **options):
        self.stdout.write("Creating 10 test users with diverse financial data...")

        # User profiles with different income levels and spending patterns
        user_profiles = [
            {
                'username': 'high_income_saver',
                'email': 'high.saver@example.com',
                'monthly_salary': 150000,
                'spending_pattern': 'conservative',  # High savings rate
                'description': 'High income professional with conservative spending'
            },
            {
                'username': 'middle_income_balanced',
                'email': 'middle.balanced@example.com',
                'monthly_salary': 75000,
                'spending_pattern': 'balanced',  # Moderate savings
                'description': 'Middle-class family with balanced finances'
            },
            {
                'username': 'low_income_struggler',
                'email': 'low.struggler@example.com',
                'monthly_salary': 25000,
                'spending_pattern': 'high_spending',  # Low/negative savings
                'description': 'Low income with high expense ratio'
            },
            {
                'username': 'freelancer_variable',
                'email': 'freelancer.var@example.com',
                'monthly_salary': 60000,
                'spending_pattern': 'variable',  # Irregular income/expenses
                'description': 'Freelancer with variable income patterns'
            },
            {
                'username': 'student_part_time',
                'email': 'student.part@example.com',
                'monthly_salary': 15000,
                'spending_pattern': 'minimalist',  # Very low expenses
                'description': 'Student with part-time job, minimal expenses'
            },
            {
                'username': 'luxury_spender',
                'email': 'luxury.spender@example.com',
                'monthly_salary': 200000,
                'spending_pattern': 'luxury',  # High discretionary spending
                'description': 'High earner with luxury lifestyle'
            },
            {
                'username': 'family_provider',
                'email': 'family.provider@example.com',
                'monthly_salary': 80000,
                'spending_pattern': 'family_focused',  # Family-oriented expenses
                'description': 'Family provider with household expenses'
            },
            {
                'username': 'entrepreneur_risky',
                'email': 'entrepreneur.risky@example.com',
                'monthly_salary': 100000,
                'spending_pattern': 'volatile',  # High risk, high reward
                'description': 'Entrepreneur with volatile income/expenses'
            },
            {
                'username': 'retiree_fixed',
                'email': 'retiree.fixed@example.com',
                'monthly_salary': 40000,
                'spending_pattern': 'stable',  # Fixed, predictable patterns
                'description': 'Retiree with stable, predictable finances'
            },
            {
                'username': 'young_professional',
                'email': 'young.prof@example.com',
                'monthly_salary': 55000,
                'spending_pattern': 'growing',  # Increasing expenses over time
                'description': 'Young professional with growing career and expenses'
            }
        ]

        total_transactions = 0
        total_patterns = 0

        for profile in user_profiles:
            self.stdout.write(f"\n--- Creating user: {profile['username']} ---")

            # Create user
            user, created = User.objects.get_or_create(
                username=profile['username'],
                defaults={
                    'email': profile['email'],
                    'first_name': profile['username'].replace('_', ' ').title()
                }
            )

            if created:
                user.set_password('123456')
                user.save()
                UserProfile.objects.get_or_create(user=user, defaults={'auto_adjust_budgets': True})

            # Clear existing data for this user
            Transaction.objects.filter(user=user).delete()
            SpendingPattern.objects.filter(user=user).delete()
            FinancialGoal.objects.filter(user=user).delete()

            # Generate 12 months of data instead of 3 for better ML training
            transactions_created, patterns_created = self.generate_user_data(user, profile)
            total_transactions += transactions_created
            total_patterns += patterns_created

            self.stdout.write(
                self.style.SUCCESS(f"✓ {profile['username']}: {transactions_created} transactions, {patterns_created} patterns")
            )

        self.stdout.write("\n=== SUMMARY ===")
        self.stdout.write(f"Total transactions created: {total_transactions}")
        self.stdout.write(f"Total spending patterns: {total_patterns}")
        self.stdout.write(f"Total users: {len(user_profiles)}")
        self.stdout.write(
            self.style.SUCCESS("All test users created successfully!")
        )
        self.stdout.write("You can now test ML algorithms with diverse user patterns.")

    def generate_user_data(self, user, profile):
        """Generate financial data from January 2024 to current day with exactly 20 transactions per month"""
        monthly_salary = profile['monthly_salary']
        pattern = profile['spending_pattern']

        transactions = []
        start_date = datetime(2024, 1, 1)  # Start from January 2024
        end_date = datetime.now().replace(day=1) + timedelta(days=32)  # Current month + buffer

        current_date = start_date
        while current_date <= end_date:
            month_start = current_date.replace(day=1)

            # Generate income for this month (1-3 transactions)
            income_txs = self.generate_monthly_income(user, month_start, monthly_salary, pattern)
            transactions.extend(income_txs)

            # Generate exactly 20 expense transactions for this month
            expense_txs = self.generate_monthly_expenses_exact_20(user, month_start, monthly_salary, pattern)
            transactions.extend(expense_txs)

            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        # Bulk create all transactions
        created_txs = Transaction.objects.bulk_create(transactions)

        # Generate AI insights
        self.generate_comprehensive_ai_insights(user)

        return len(created_txs), SpendingPattern.objects.filter(user=user).count()

    def generate_monthly_income(self, user, month_date, base_salary, pattern):
        """Generate realistic income for a month"""
        transactions = []
        base_date = month_date.replace(day=15)  # Mid-month salary

        # Primary salary (always present)
        salary_amount = base_salary
        if pattern in ['variable', 'volatile']:
            # Add randomness for variable income
            salary_amount *= (0.8 + random.random() * 0.4)  # ±20% variation

        transactions.append(Transaction(
            user=user,
            amount=round(salary_amount, 2),
            transaction_type='income',
            category='salary',
            description='Monthly Salary',
            date=base_date.strftime('%Y-%m-%d')
        ))

        # Additional income based on pattern
        if pattern in ['high_income_saver', 'luxury_spender']:
            # Bonus income
            bonus = salary_amount * (0.1 + random.random() * 0.2)  # 10-30% bonus
            transactions.append(Transaction(
                user=user,
                amount=round(bonus, 2),
                transaction_type='income',
                category='investment',
                description='Performance Bonus',
                date=(base_date + timedelta(days=random.randint(20, 25))).strftime('%Y-%m-%d')
            ))

        elif pattern == 'freelancer_variable':
            # Freelance income (irregular)
            freelance_amounts = [5000, 8000, 12000, 15000, 20000]
            for i in range(random.randint(1, 3)):
                tx_date = base_date + timedelta(days=random.randint(5, 25))
                transactions.append(Transaction(
                    user=user,
                    amount=random.choice(freelance_amounts),
                    transaction_type='income',
                    category='freelance',
                    description=f'Freelance Project {i+1}',
                    date=tx_date.strftime('%Y-%m-%d')
                ))

        elif pattern == 'entrepreneur_risky':
            # Business income (highly variable)
            business_income = base_salary * (0.5 + random.random() * 1.0)  # 50-150% of salary
            transactions.append(Transaction(
                user=user,
                amount=round(business_income, 2),
                transaction_type='income',
                category='investment',
                description='Business Revenue',
                date=(base_date + timedelta(days=random.randint(25, 28))).strftime('%Y-%m-%d')
            ))

        return transactions

    def generate_monthly_expenses(self, user, month_date, monthly_salary, pattern):
        """Generate realistic expenses for a month"""
        transactions = []

        # Base expense ratios by pattern
        expense_ratios = {
            'conservative': {'food': 0.15, 'transportation': 0.08, 'bills': 0.10, 'healthcare': 0.05, 'entertainment': 0.05, 'shopping': 0.03},
            'balanced': {'food': 0.20, 'transportation': 0.10, 'bills': 0.12, 'healthcare': 0.08, 'entertainment': 0.08, 'shopping': 0.08},
            'high_spending': {'food': 0.25, 'transportation': 0.12, 'bills': 0.15, 'healthcare': 0.10, 'entertainment': 0.15, 'shopping': 0.12},
            'variable': {'food': 0.18, 'transportation': 0.09, 'bills': 0.11, 'healthcare': 0.07, 'entertainment': 0.10, 'shopping': 0.06},
            'minimalist': {'food': 0.12, 'transportation': 0.05, 'bills': 0.08, 'healthcare': 0.03, 'entertainment': 0.02, 'shopping': 0.02},
            'luxury': {'food': 0.15, 'transportation': 0.12, 'bills': 0.10, 'healthcare': 0.08, 'entertainment': 0.20, 'shopping': 0.18},
            'family_focused': {'food': 0.25, 'transportation': 0.08, 'bills': 0.15, 'healthcare': 0.12, 'entertainment': 0.06, 'shopping': 0.05},
            'volatile': {'food': 0.22, 'transportation': 0.11, 'bills': 0.13, 'healthcare': 0.09, 'entertainment': 0.12, 'shopping': 0.10},
            'stable': {'food': 0.18, 'transportation': 0.08, 'bills': 0.12, 'healthcare': 0.07, 'entertainment': 0.06, 'shopping': 0.05},
            'growing': {'food': 0.19, 'transportation': 0.09, 'bills': 0.11, 'healthcare': 0.08, 'entertainment': 0.09, 'shopping': 0.07}
        }

        ratios = expense_ratios.get(pattern, expense_ratios['balanced'])

        # Generate expenses for each category
        for category, ratio in ratios.items():
            base_amount = monthly_salary * ratio

            # Add category-specific variations
            if category == 'food':
                # 3-4 transactions per month for food
                num_txs = random.randint(3, 4)
                for i in range(num_txs):
                    amount = base_amount / num_txs * (0.7 + random.random() * 0.6)  # ±30% variation
                    tx_date = month_date + timedelta(days=random.randint(1, 28))
                    transactions.append(Transaction(
                        user=user,
                        amount=round(amount, 2),
                        transaction_type='expense',
                        category=category,
                        description=f'Grocery shopping {i+1}',
                        date=tx_date.strftime('%Y-%m-%d')
                    ))

            elif category == 'transportation':
                # 2-3 transportation expenses
                num_txs = random.randint(2, 3)
                for i in range(num_txs):
                    amount = base_amount / num_txs * (0.8 + random.random() * 0.4)
                    tx_date = month_date + timedelta(days=random.randint(5, 25))
                    transactions.append(Transaction(
                        user=user,
                        amount=round(amount, 2),
                        transaction_type='expense',
                        category=category,
                        description=random.choice(['Fuel', 'Uber ride', 'Car maintenance', 'Public transport']),
                        date=tx_date.strftime('%Y-%m-%d')
                    ))

            elif category == 'entertainment':
                # 2-4 entertainment expenses
                num_txs = random.randint(2, 4)
                for i in range(num_txs):
                    amount = base_amount / num_txs * (0.5 + random.random() * 1.0)
                    tx_date = month_date + timedelta(days=random.randint(1, 28))
                    transactions.append(Transaction(
                        user=user,
                        amount=round(amount, 2),
                        transaction_type='expense',
                        category=category,
                        description=random.choice(['Movie tickets', 'Restaurant', 'Concert', 'Streaming service', 'Games']),
                        date=tx_date.strftime('%Y-%m-%d')
                    ))

            elif category == 'shopping':
                # 1-3 shopping transactions
                num_txs = random.randint(1, 3)
                for i in range(num_txs):
                    amount = base_amount / num_txs * (0.6 + random.random() * 0.8)
                    tx_date = month_date + timedelta(days=random.randint(10, 28))
                    transactions.append(Transaction(
                        user=user,
                        amount=round(amount, 2),
                        transaction_type='expense',
                        category=category,
                        description=random.choice(['Clothing', 'Electronics', 'Home decor', 'Books', 'Accessories']),
                        date=tx_date.strftime('%Y-%m-%d')
                    ))

            else:
                # Single transaction for other categories
                amount = base_amount * (0.8 + random.random() * 0.4)
                tx_date = month_date + timedelta(days=random.randint(1, 28))
                transactions.append(Transaction(
                    user=user,
                    amount=round(amount, 2),
                    transaction_type='expense',
                    category=category,
                    description=f'{category.title()} expense',
                    date=tx_date.strftime('%Y-%m-%d')
                ))

        return transactions

    def generate_monthly_expenses_exact_20(self, user, month_date, monthly_salary, pattern):
        """Generate exactly 20 expense transactions for a month"""
        transactions = []

        # Base expense ratios by pattern
        expense_ratios = {
            'conservative': {'food': 0.15, 'transportation': 0.08, 'bills': 0.10, 'healthcare': 0.05, 'entertainment': 0.05, 'shopping': 0.03},
            'balanced': {'food': 0.20, 'transportation': 0.10, 'bills': 0.12, 'healthcare': 0.08, 'entertainment': 0.08, 'shopping': 0.08},
            'high_spending': {'food': 0.25, 'transportation': 0.12, 'bills': 0.15, 'healthcare': 0.10, 'entertainment': 0.15, 'shopping': 0.12},
            'variable': {'food': 0.18, 'transportation': 0.09, 'bills': 0.11, 'healthcare': 0.07, 'entertainment': 0.10, 'shopping': 0.06},
            'minimalist': {'food': 0.12, 'transportation': 0.05, 'bills': 0.08, 'healthcare': 0.03, 'entertainment': 0.02, 'shopping': 0.02},
            'luxury': {'food': 0.15, 'transportation': 0.12, 'bills': 0.10, 'healthcare': 0.08, 'entertainment': 0.20, 'shopping': 0.18},
            'family_focused': {'food': 0.25, 'transportation': 0.08, 'bills': 0.15, 'healthcare': 0.12, 'entertainment': 0.06, 'shopping': 0.05},
            'volatile': {'food': 0.22, 'transportation': 0.11, 'bills': 0.13, 'healthcare': 0.09, 'entertainment': 0.12, 'shopping': 0.10},
            'stable': {'food': 0.18, 'transportation': 0.08, 'bills': 0.12, 'healthcare': 0.07, 'entertainment': 0.06, 'shopping': 0.05},
            'growing': {'food': 0.19, 'transportation': 0.09, 'bills': 0.11, 'healthcare': 0.08, 'entertainment': 0.09, 'shopping': 0.07}
        }

        ratios = expense_ratios.get(pattern, expense_ratios['balanced'])

        # Calculate exactly 20 transactions distributed across categories
        transaction_distribution = {
            'food': 6,           # Most frequent - daily/weekly shopping
            'transportation': 3, # Regular transport expenses
            'entertainment': 3,  # Weekend activities, dining out
            'shopping': 3,       # Clothing, home items, etc.
            'bills': 2,          # Monthly bills (electricity, internet, etc.)
            'healthcare': 2,     # Doctor visits, pharmacy
            'other': 1           # Miscellaneous expenses
        }

        # Ensure total is exactly 20
        total_assigned = sum(transaction_distribution.values())
        if total_assigned != 20:
            # Adjust if needed
            transaction_distribution['food'] += (20 - total_assigned)

        # Generate transactions for each category
        for category, count in transaction_distribution.items():
            ratio = ratios.get(category, 0.05)  # Default 5% for other category
            base_amount = monthly_salary * ratio

            for i in range(count):
                # Distribute amount across transactions with variation
                variation = 0.7 + random.random() * 0.6  # ±30% variation
                amount = (base_amount / count) * variation

                # Generate realistic dates throughout the month
                if category == 'food':
                    # Spread food shopping throughout the month
                    day = random.randint(1, 31)
                elif category == 'bills':
                    # Bills around mid-month
                    day = random.randint(10, 20)
                elif category == 'transportation':
                    # Transportation spread out
                    day = random.randint(1, 31)
                elif category == 'healthcare':
                    # Healthcare appointments spread out
                    day = random.randint(5, 28)
                else:
                    # Other categories randomly throughout month
                    day = random.randint(1, 31)

                # Ensure valid day for month (not exceeding month length)
                try:
                    tx_date = month_date.replace(day=min(day, 28))
                    if day > 28 and month_date.month in [1, 3, 5, 7, 8, 10, 12]:
                        tx_date = month_date.replace(day=min(day, 31))
                    elif day > 28 and month_date.month in [4, 6, 9, 11]:
                        tx_date = month_date.replace(day=min(day, 30))
                    else:
                        tx_date = month_date.replace(day=min(day, 28))
                except ValueError:
                    tx_date = month_date.replace(day=15)  # Fallback to mid-month

                # Get description based on category
                description = self.get_transaction_description(category, i, pattern)

                transactions.append(Transaction(
                    user=user,
                    amount=round(Decimal(amount), 2),
                    transaction_type='expense',
                    category=category,
                    description=description,
                    date=tx_date.strftime('%Y-%m-%d')
                ))

        return transactions

    def get_transaction_description(self, category, index, pattern):
        """Generate realistic transaction descriptions for exactly 20 transactions"""
        descriptions = {
            'food': [
                'Grocery shopping at local market',
                'Weekly supermarket visit',
                'Fresh vegetables and fruits',
                'Meat and poultry purchase',
                'Bakery and bread items',
                'Dairy products and milk'
            ],
            'transportation': [
                'Fuel for car',
                'Uber ride to office',
                'Monthly metro pass',
            ],
            'entertainment': [
                'Movie tickets and popcorn',
                'Restaurant dinner',
                'Streaming service subscription'
            ],
            'shopping': [
                'New clothing items',
                'Home decor purchase',
                'Electronics and gadgets'
            ],
            'bills': [
                'Electricity bill payment',
                'Internet and mobile bill'
            ],
            'healthcare': [
                'Doctor consultation fee',
                'Pharmacy medicines'
            ],
            'other': [
                'Miscellaneous expenses'
            ]
        }

        category_descriptions = descriptions.get(category, [f'{category.title()} expense'])
        return category_descriptions[index % len(category_descriptions)]

    def generate_comprehensive_ai_insights(self, user):
        """Generate comprehensive AI insights for the user"""
        transactions = Transaction.objects.filter(user=user, transaction_type='expense')

        if not transactions.exists():
            return

        # Group by category and month
        from collections import defaultdict
        category_monthly = defaultdict(lambda: defaultdict(float))

        for transaction in transactions:
            month_key = transaction.date.replace(day=1)
            category_monthly[transaction.category][month_key] += float(transaction.amount)

        # Generate spending patterns for each category and month
        for category, monthly_data in category_monthly.items():
            for month, amount in monthly_data.items():
                # Enhanced trend calculation
                trend = self.calculate_advanced_trend(category, monthly_data, month)

                # ML-based prediction
                predicted_amount = self.predict_with_ml(amount, trend, monthly_data)

                # Advanced confidence calculation
                confidence = self.calculate_ml_confidence(monthly_data, amount)

                # Create or update spending pattern
                pattern, created = SpendingPattern.objects.get_or_create(
                    user=user,
                    category=category,
                    month=month,
                    defaults={
                        'predicted_amount': predicted_amount,
                        'confidence_score': confidence,
                        'trend_direction': trend,
                        'ai_insights': self.generate_advanced_insights(category, amount, trend, confidence, monthly_data)
                    }
                )

                if not created:
                    pattern.predicted_amount = predicted_amount
                    pattern.confidence_score = confidence
                    pattern.trend_direction = trend
                    pattern.ai_insights = self.generate_advanced_insights(category, amount, trend, confidence, monthly_data)
                    pattern.save()

        # Create diverse financial goals
        self.create_diverse_goals(user)

    def calculate_advanced_trend(self, category, monthly_data, current_month):
        """Calculate advanced trend using linear regression"""
        amounts = list(monthly_data.values())
        if len(amounts) < 2:
            return 'stable'

        # Use linear regression for trend
        x = np.arange(len(amounts))
        y = np.array(amounts)

        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            # Normalize slope by mean to get relative trend
            mean_amount = np.mean(y)
            relative_slope = slope / mean_amount if mean_amount > 0 else 0

            if relative_slope > 0.05:  # 5% increase relative to mean
                return 'increasing'
            elif relative_slope < -0.05:  # 5% decrease relative to mean
                return 'decreasing'
            else:
                return 'stable'
        else:
            return 'stable'

    def predict_with_ml(self, current_amount, trend, monthly_data):
        """Predict next month using ML-inspired approach"""
        amounts = list(monthly_data.values())

        if len(amounts) >= 3:
            # Use exponential smoothing with trend adjustment
            alpha = 0.3
            smoothed = [amounts[0]]

            for i in range(1, len(amounts)):
                smoothed_val = alpha * amounts[i] + (1 - alpha) * smoothed[i-1]
                smoothed.append(smoothed_val)

            # Trend-based prediction
            last_smoothed = smoothed[-1]
            if trend == 'increasing':
                # Increase by 5-15% based on historical volatility
                volatility_factor = min(0.15, np.std(amounts) / np.mean(amounts) if np.mean(amounts) > 0 else 0.05)
                return last_smoothed * (1 + 0.05 + volatility_factor)
            elif trend == 'decreasing':
                volatility_factor = min(0.15, np.std(amounts) / np.mean(amounts) if np.mean(amounts) > 0 else 0.05)
                return last_smoothed * (1 - 0.05 - volatility_factor)
            else:
                return last_smoothed * (0.95 + random.random() * 0.1)  # ±5% random walk
        else:
            return current_amount * (0.9 + random.random() * 0.2)  # ±10% variation

    def calculate_ml_confidence(self, monthly_data, current_amount):
        """Calculate confidence using ML metrics"""
        amounts = list(monthly_data.values())

        if len(amounts) < 2:
            return 30.0  # Very low confidence

        # Calculate multiple confidence factors
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)
        cv = std_amount / mean_amount if mean_amount > 0 else 1  # Coefficient of variation

        # Sample size factor
        sample_factor = min(1.0, len(amounts) / 12)  # Normalize to 12 months

        # Consistency factor (lower CV = higher confidence)
        consistency_factor = max(0.1, 1 - cv)

        # Recency factor (more recent data = higher confidence)
        recency_factor = 0.8 + (0.2 * sample_factor)

        # Combine factors
        confidence = (consistency_factor * 0.5 + sample_factor * 0.3 + recency_factor * 0.2) * 100

        return round(min(95, max(10, confidence)), 2)

    def generate_advanced_insights(self, category, amount, trend, confidence, monthly_data):
        """Generate advanced AI insights"""
        insights = []
        amounts = list(monthly_data.values())

        # Trend insights
        if trend == 'increasing':
            avg_increase = np.mean(np.diff(amounts)) if len(amounts) > 1 else 0
            insights.append(f"Your {category} spending is increasing by ~₹{abs(avg_increase):.0f} per month.")
        elif trend == 'decreasing':
            avg_decrease = np.mean(np.diff(amounts)) if len(amounts) > 1 else 0
            insights.append(f"Great! Your {category} spending is decreasing by ~₹{abs(avg_decrease):.0f} per month.")

        # Volatility insights
        if len(amounts) >= 3:
            cv = np.std(amounts) / np.mean(amounts) if np.mean(amounts) > 0 else 0
            if cv > 0.5:
                insights.append(f"High volatility in {category} spending. Consider setting stricter budgets.")
            elif cv < 0.1:
                insights.append(f"Very consistent {category} spending pattern. Good financial discipline!")

        # Amount-based insights
        if amount > 50000:
            insights.append(f"High {category} expenditure this month. Review for potential savings.")
        elif amount < 10000 and category in ['food', 'bills']:
            insights.append(f"Low {category} spending. Ensure all essential needs are met.")

        # Confidence insights
        if confidence > 80:
            insights.append("Strong prediction confidence. Spending patterns are well-established.")
        elif confidence < 40:
            insights.append("Low prediction confidence. More data needed for accurate insights.")

        return " | ".join(insights) if insights else "Continue monitoring spending patterns for better insights."

    def create_diverse_goals(self, user):
        """Create diverse financial goals for the user"""
        user_goals = [
            {
                'goal_name': 'Emergency Fund',
                'target': 300000,
                'current': random.randint(50000, 150000),
                'target_date': '2025-12-31',
                'category': '',
                'priority': 1
            },
            {
                'goal_name': 'Vacation to Europe',
                'target': 200000,
                'current': random.randint(30000, 80000),
                'target_date': '2025-08-15',
                'category': 'entertainment',
                'priority': 2
            },
            {
                'goal_name': 'New Car Down Payment',
                'target': 400000,
                'current': random.randint(100000, 200000),
                'target_date': '2025-06-30',
                'category': 'transportation',
                'priority': 2
            },
            {
                'goal_name': 'Home Improvement',
                'target': 150000,
                'current': random.randint(20000, 60000),
                'target_date': '2025-05-01',
                'category': 'shopping',
                'priority': 3
            }
        ]

        for goal_data in user_goals:
            FinancialGoal.objects.get_or_create(
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
