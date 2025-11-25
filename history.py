"""
Historical Financial Data Reference
Comprehensive dataset for generating realistic financial transaction patterns
"""

# Global constants
INFLATION_RATE = 0.03  # 3% annual inflation
SALARY_GROWTH_RATE = 0.08  # 8% annual salary growth

# Income patterns by profession
PROFESSION_INCOME_PATTERNS = {
    'software_engineer': {
        'base_salary': 120000,
        'bonus_frequency': 0.8,  # 80% chance of bonus annually
        'bonus_amount': 0.25,  # 25% of base salary
        'side_income_chance': 0.6,  # 60% chance of freelance
        'side_income_avg': 30000,
        'description': 'Software Engineer - Tech professional with variable bonuses'
    },
    'teacher': {
        'base_salary': 45000,
        'bonus_frequency': 0.3,
        'bonus_amount': 0.1,
        'side_income_chance': 0.4,
        'side_income_avg': 15000,
        'description': 'Teacher - Steady income with occasional tutoring'
    },
    'doctor': {
        'base_salary': 180000,
        'bonus_frequency': 0.9,
        'bonus_amount': 0.3,
        'side_income_chance': 0.7,
        'side_income_avg': 50000,
        'description': 'Doctor - High income with substantial bonuses and private practice'
    },
    'accountant': {
        'base_salary': 75000,
        'bonus_frequency': 0.6,
        'bonus_amount': 0.15,
        'side_income_chance': 0.5,
        'side_income_avg': 25000,
        'description': 'Accountant - Moderate income with tax season bonuses'
    },
    'student': {
        'base_salary': 15000,  # Part-time/part-time jobs
        'bonus_frequency': 0.1,
        'bonus_amount': 0.5,
        'side_income_chance': 0.3,
        'side_income_avg': 8000,
        'description': 'Student - Low, irregular income'
    },
    'retiree': {
        'base_salary': 35000,  # Pension/fixed income
        'bonus_frequency': 0.0,
        'bonus_amount': 0.0,
        'side_income_chance': 0.2,
        'side_income_avg': 12000,  # Part-time work
        'description': 'Retiree - Fixed pension income with supplemental work'
    },
    'business_owner': {
        'base_salary': 95000,  # Average business income
        'bonus_frequency': 1.0,  # Always variable based on business performance
        'bonus_amount': 0.5,  # Highly variable (±50%)
        'side_income_chance': 0.8,
        'side_income_avg': 35000,
        'description': 'Business Owner - Variable income based on business performance'
    },
    'marketing_specialist': {
        'base_salary': 65000,
        'bonus_frequency': 0.7,
        'bonus_amount': 0.12,
        'side_income_chance': 0.4,
        'side_income_avg': 20000,
        'description': 'Marketing Specialist - Performance-based bonuses'
    }
}

# Expense patterns by lifestyle and income level
EXPENSE_PATTERNS = {
    'minimalist': {
        'name': 'Minimalist Lifestyle',
        'description': 'Basic necessities with very low discretionary spending',
        'ratios': {
            'food': 0.12,
            'transportation': 0.04,
            'bills': 0.08,
            'healthcare': 0.025,
            'entertainment': 0.012,
            'shopping': 0.015,
            'education': 0.03,
        },
        'monthly_savings_rate': 0.25,
        'income_range': (20000, 40000)
    },
    'moderate': {
        'name': 'Moderate Lifestyle',
        'description': 'Balanced spending with reasonable saving',
        'ratios': {
            'food': 0.18,
            'transportation': 0.07,
            'bills': 0.11,
            'healthcare': 0.06,
            'entertainment': 0.07,
            'shopping': 0.06,
            'education': 0.05,
        },
        'monthly_savings_rate': 0.18,
        'income_range': (40000, 80000)
    },
    'comfortable': {
        'name': 'Comfortable Lifestyle',
        'description': 'Above-average comfort with good savings',
        'ratios': {
            'food': 0.15,
            'transportation': 0.08,
            'bills': 0.10,
            'healthcare': 0.055,
            'entertainment': 0.11,
            'shopping': 0.10,
            'education': 0.06,
            'other': 0.03,
        },
        'monthly_savings_rate': 0.22,
        'income_range': (80000, 150000)
    },
    'luxury': {
        'name': 'Luxury Lifestyle',
        'description': 'Premium lifestyle with high discretionary spending',
        'ratios': {
            'food': 0.12,
            'transportation': 0.10,
            'bills': 0.08,
            'healthcare': 0.06,
            'entertainment': 0.18,
            'shopping': 0.20,
            'education': 0.08,
            'other': 0.05,
        },
        'monthly_savings_rate': 0.13,
        'income_range': (150000, 300000)
    },
    'high_net_worth': {
        'name': 'High Net Worth',
        'description': 'Very high income with premium lifestyle and significant savings',
        'ratios': {
            'food': 0.10,
            'transportation': 0.08,
            'bills': 0.07,
            'healthcare': 0.04,
            'entertainment': 0.12,
            'shopping': 0.15,
            'education': 0.06,
            'other': 0.04,
            'investment': 0.08,
        },
        'monthly_savings_rate': 0.26,
        'income_range': (300000, 1000000)
    }
}

# Seasonal spending variations (multipliers)
SEASONAL_VARIATIONS = {
    1: {  # January - New Year, Tax season
        'entertainment': 1.4, 'shopping': 1.3, 'food': 1.1, 'healthcare': 0.9
    },
    2: {  # February - Valentine's, shorter month
        'entertainment': 1.5, 'shopping': 1.4, 'food': 0.95, 'transportation': 0.9
    },
    3: {  # March - End of quarter
        'entertainment': 1.1, 'shopping': 1.1, 'bills': 1.2, 'healthcare': 1.1
    },
    4: {  # April - Tax payments, Spring break
        'bills': 1.3, 'entertainment': 1.2, 'shopping': 1.1, 'food': 0.95
    },
    5: {  # May - Mother's Day, early summer
        'shopping': 1.3, 'entertainment': 1.2, 'food': 1.2, 'transportation': 1.1
    },
    6: {  # June - Father's Day, weddings
        'shopping': 1.2, 'entertainment': 1.4, 'food': 1.3, 'transportation': 1.1
    },
    7: {  # July - Summer vacation
        'entertainment': 1.5, 'transportation': 1.3, 'food': 1.4, 'shopping': 1.2
    },
    8: {  # August - Back to school
        'shopping': 1.5, 'education': 2.0, 'food': 1.1, 'entertainment': 1.1
    },
    9: {  # September - School year starts
        'education': 1.5, 'shopping': 1.2, 'entertainment': 1.0, 'food': 1.0
    },
    10: {  # October - Halloween, festivals
        'entertainment': 1.3, 'shopping': 1.2, 'food': 1.2, 'transportation': 1.0
    },
    11: {  # November - Thanksgiving, holiday shopping
        'shopping': 1.8, 'entertainment': 1.4, 'food': 1.3, 'transportation': 1.1
    },
    12: {  # December - Christmas, year-end
        'shopping': 2.0, 'entertainment': 1.6, 'food': 1.4, 'bills': 1.2
    }
}

# Monthly transaction counts by category and lifestyle
TRANSACTION_FREQUENCIES = {
    'minimalist': {
        'food': 3, 'transportation': 2, 'bills': 1, 'healthcare': 1,
        'entertainment': 1, 'shopping': 1, 'education': 1
    },
    'moderate': {
        'food': 4, 'transportation': 3, 'bills': 1, 'healthcare': 2,
        'entertainment': 3, 'shopping': 3, 'education': 1
    },
    'comfortable': {
        'food': 5, 'transportation': 4, 'bills': 1, 'healthcare': 3,
        'entertainment': 6, 'shopping': 5, 'education': 2
    },
    'luxury': {
        'food': 6, 'transportation': 5, 'bills': 2, 'healthcare': 4,
        'entertainment': 10, 'shopping': 8, 'education': 3, 'other': 3
    },
    'high_net_worth': {
        'food': 8, 'transportation': 6, 'bills': 2, 'healthcare': 4,
        'entertainment': 12, 'shopping': 10, 'education': 4, 'other': 4, 'investment': 2
    }
}

# Realistic transaction descriptions by category
TRANSACTION_DESCRIPTIONS = {
    'food': [
        'Grocery shopping - vegetables and fruits',
        'Weekly groceries at local market',
        'Restaurant dinner with family',
        'Coffee and breakfast at cafe',
        'Takeout lunch from office',
        'Farmers market fresh produce',
        'Bakery and bread purchase',
        'Dairy and milk products',
        'Meat and seafood shopping',
        'Snacks and beverages',
        'Fast food meal',
        'Gourmet meal at restaurant',
        'Ice cream and desserts',
        'Catering for party',
        'Monthly pantry stocking'
    ],
    'transportation': [
        'Monthly fuel purchase',
        'Uber ride to airport',
        'Taxi fare downtown',
        'Car maintenance and service',
        'Parking fee for event',
        'Public transport monthly pass',
        'Car wash and detailing',
        'Toll road charges',
        'Vehicle insurance premium',
        'Emergency roadside assistance',
        'Car rental for vacation',
        'Bike repair and maintenance',
        'Electric scooter rental',
        'Airport parking fee',
        'Train ticket purchase'
    ],
    'bills': [
        'Electricity bill payment',
        'Internet and WiFi subscription',
        'Mobile phone plan',
        'Water bill payment',
        'Gas utility bill',
        'Home insurance premium',
        'Car insurance payment',
        'Health insurance contribution',
        'Cable TV subscription',
        'Home phone service',
        'Security system monitoring',
        'Pest control service',
        'Home cleaning service',
        'Gardening and landscaping',
        'Condo association fees'
    ],
    'healthcare': [
        'Doctor consultation fee',
        'Pharmacy prescription',
        'Dental checkup and cleaning',
        'Gym membership monthly',
        'Medical test - blood work',
        'Wellness checkup visit',
        'Therapy session payment',
        'Medical supplies purchase',
        'Eye exam and glasses',
        'Chiropractic adjustment',
        'Nutrition consultation',
        'Mental health counseling',
        'Pharmacy OTC medications',
        'Home health aide service',
        'Medical equipment rental'
    ],
    'entertainment': [
        'Movie tickets for family',
        'Concert tickets purchase',
        'Streaming service subscription',
        'Books and magazines',
        'Video games purchase',
        'Sports event tickets',
        'Music streaming subscription',
        'Online course enrollment',
        'Theater show tickets',
        'Bowling night out',
        'Amusement park tickets',
        'Museum admission fee',
        'Art gallery visit',
        'Comedy show tickets',
        'Dancing class enrollment',
        'Photography workshop',
        'Cooking class fees',
        'Karaoke night',
        'Board game night supplies',
        'Puzzle and brain teasers'
    ],
    'shopping': [
        'Clothing purchase',
        'Electronics and gadgets',
        'Home decor items',
        'Books purchase',
        'Accessories and jewelry',
        'Gifts for occasions',
        'Furniture purchase',
        'Beauty products',
        'Shoes and footwear',
        'Kitchen appliances',
        'Garden supplies',
        'Office supplies',
        'Pet supplies',
        'Sporting goods',
        'Art supplies',
        'Craft materials',
        'Home improvement items',
        'Bathroom supplies',
        'Bedding and linens',
        'Curtains and window treatments'
    ],
    'education': [
        'Online course fees',
        'Textbook purchase',
        'Tuition payment',
        'Language learning app',
        'Skill development workshop',
        'Certification course',
        'Educational software',
        'Research materials',
        'Academic conference fee',
        'Tutoring services',
        'Test preparation course',
        'Educational toys',
        'Art supplies for education',
        'Science experiment kits',
        'Music lessons'
    ],
    'investment': [
        'Stock market investment',
        'Mutual fund SIP',
        'Bonds and fixed deposits',
        'Real estate investment',
        'Gold and precious metals',
        'Cryptocurrency purchase',
        'P2P lending investment',
        'Angel investment',
        'Retirement fund contribution',
        'Index fund investment'
    ],
    'other': [
        'Charity donation',
        'Gift purchase',
        'Party supplies',
        'Home repair service',
        'Professional services',
        'Legal consultation',
        'Financial planning advice',
        'Event planning services',
        'Travel booking fee',
        'Postage and shipping',
        'Storage unit rental',
        'Personal care service',
        'Pet grooming service',
        'Home security system',
        'Emergency home repair'
    ]
}

# Annual income adjustments (bonuses, tax refunds, etc.)
ANNUAL_INCOME_ADJUSTMENTS = {
    1: {  # January - Tax refunds
        'types': ['income'],
        'categories': ['other'],
        'amount_range': (5000, 50000),
        'frequency': 0.6,  # 60% chance
        'description': 'Tax refund payment'
    },
    3: {  # March - End of FY bonuses
        'types': ['income'],
        'categories': ['investment'],
        'amount_range': (10000, 200000),
        'frequency': 0.7,  # 70% chance
        'description': 'Annual performance bonus'
    },
    12: {  # December - Christmas bonus, year-end incentives
        'types': ['income'],
        'categories': ['investment'],
        'amount_range': (5000, 100000),
        'frequency': 0.8,  # 80% chance
        'description': 'Festival bonus'
    }
}

# Special one-time events (random occurrences)
SPECIAL_EVENTS = [
    {
        'name': 'Emergency Car Repair',
        'category': 'transportation',
        'amount_range': (5000, 25000),
        'frequency': 0.1,  # 10% chance per year
        'adjustable': True
    },
    {
        'name': 'Medical Emergency',
        'category': 'healthcare',
        'amount_range': (10000, 100000),
        'frequency': 0.05,  # 5% chance per year
        'adjustable': True
    },
    {
        'name': 'Vacation Expenses',
        'category': 'entertainment',
        'amount_range': (15000, 100000),
        'frequency': 0.6,  # 60% chance per year in summer months
        'month_bias': [6, 7, 8, 9],  # Summer months
        'adjustable': True
    },
    {
        'name': 'Home Appliance Purchase',
        'category': 'shopping',
        'amount_range': (8000, 50000),
        'frequency': 0.3,  # 30% chance per year
        'adjustable': True
    },
    {
        'name': 'Business Trip',
        'category': 'other',
        'amount_range': (10000, 40000),
        'frequency': 0.4,  # 40% chance per year
        'adjustable': True
    },
    {
        'name': 'Wedding Gift',
        'category': 'shopping',
        'amount_range': (2000, 25000),
        'frequency': 0.8,  # 80% chance per year (assuming social circle)
        'adjustable': True
    },
    {
        'name': 'Insurance Claim Refund',
        'category': 'other',
        'amount_range': (5000, 30000),
        'frequency': 0.2,  # 20% chance per year
        'adjustable': False  # Insurance refunds are exact
    },
    {
        'name': 'Investment Return',
        'category': 'investment',
        'amount_range': (1000, 50000),
        'frequency': 0.3,  # 30% chance per quarter
        'adjustable': False  # Investment returns are market-driven
    }
]

# Savings goals by income level
SAVINGS_GOALS = {
    'minimalist': [
        {'name': 'Emergency Fund', 'monthly_target': 2000, 'total_target': 60000},
        {'name': 'Basic Savings', 'monthly_target': 1000, 'total_target': 24000},
    ],
    'moderate': [
        {'name': 'Emergency Fund', 'monthly_target': 5000, 'total_target': 150000},
        {'name': 'Vacation Fund', 'monthly_target': 3000, 'total_target': 60000},
        {'name': 'Car Fund', 'monthly_target': 4000, 'total_target': 100000},
        {'name': 'Retirement', 'monthly_target': 2000, 'total_target': 50000},
    ],
    'comfortable': [
        {'name': 'Emergency Fund', 'monthly_target': 10000, 'total_target': 300000},
        {'name': 'Investment Portfolio', 'monthly_target': 15000, 'total_target': 500000},
        {'name': 'Home Down Payment', 'monthly_target': 8000, 'total_target': 200000},
        {'name': 'Children Education', 'monthly_target': 5000, 'total_target': 120000},
    ],
    'luxury': [
        {'name': 'Investment Portfolio', 'monthly_target': 25000, 'total_target': 1000000},
        {'name': 'Luxury Vacation', 'monthly_target': 15000, 'total_target': 300000},
        {'name': 'Second Home', 'monthly_target': 20000, 'total_target': 1500000},
        {'name': 'Luxury Car', 'monthly_target': 12000, 'total_target': 500000},
    ],
    'high_net_worth': [
        {'name': 'Investment Portfolio', 'monthly_target': 50000, 'total_target': 5000000},
        {'name': 'Real Estate Investment', 'monthly_target': 100000, 'total_target': 2000000},
        {'name': 'Philanthropy Fund', 'monthly_target': 25000, 'total_target': 1000000},
        {'name': 'Luxury Assets', 'monthly_target': 30000, 'total_target': 1500000},
    ]
}

# Helper functions for data generation
def get_lifestyle_for_salary(salary):
    """Determine appropriate lifestyle pattern based on salary"""
    for pattern, data in EXPENSE_PATTERNS.items():
        min_salary, max_salary = data['income_range']
        if min_salary <= salary <= max_salary:
            return pattern
    return 'moderate'  # Default fallback

def get_seasonal_multiplier(category, month):
    """Get seasonal multiplier for a category in a specific month"""
    if month in SEASONAL_VARIATIONS and category in SEASONAL_VARIATIONS[month]:
        return SEASONAL_VARIATIONS[month][category]
    return 1.0

def get_random_description(category, lifestyle='moderate'):
    """Get a random realistic transaction description"""
    if category in TRANSACTION_DESCRIPTIONS:
        descriptions = TRANSACTION_DESCRIPTIONS[category]
        return random.choice(descriptions)
    return f"{category.title()} expense"

def calculate_realistic_variance(amount, category, month):
    """Calculate realistic variance for transaction amounts"""
    base_variance = 0.25  # ±25% base variance

    # Higher variance for certain categories
    high_variance_categories = ['entertainment', 'shopping', 'other']
    if category in high_variance_categories:
        base_variance = 0.4  # ±40%

    # Seasonal variance
    seasonal_multiplier = get_seasonal_multiplier(category, month)
    if seasonal_multiplier > 1.2:
        base_variance *= 1.3  # More variance during high season

    return base_variance

def apply_inflation_adjustment(amount, base_year, target_year):
    """Apply inflation adjustment to historical amounts"""
    years_diff = target_year - base_year
    inflation_multiplier = (1 + INFLATION_RATE) ** years_diff
    return amount * inflation_multiplier

def generate_salary_progression(base_salary, start_year, end_year, profession):
    """Generate realistic salary progression over years"""
    profession_pattern = PROFESSION_INCOME_PATTERNS.get(profession, PROFESSION_INCOME_PATTERNS['software_engineer'])

    salaries = {}
    current_salary = base_salary

    for year in range(start_year, end_year + 1):
        salaries[year] = current_salary

        # Apply growth
        growth_rate = SALARY_GROWTH_RATE
        if profession == 'student':
            growth_rate = 0.15  # Higher growth for career starters
        elif profession == 'retiree':
            growth_rate = 0.02  # Lower growth for retirees

        # Add some randomness to growth
        actual_growth = growth_rate * (0.8 + random.random() * 0.4)
        current_salary *= (1 + actual_growth)

    return salaries

# ML pattern recognition helpers
def analyze_spending_patterns(transactions):
    """Analyze spending patterns for ML insights"""
    patterns = {
        'monthly_totals': {},
        'category_trends': {},
        'seasonal_patterns': {},
        'volatility_scores': {},
        'correlation_matrix': {}
    }

    # Group transactions by month and category
    monthly_data = {}
    for transaction in transactions:
        month_key = transaction.date.strftime('%Y-%m')
        category = transaction.category

        if month_key not in monthly_data:
            monthly_data[month_key] = {}
        if category not in monthly_data[month_key]:
            monthly_data[month_key][category] = 0

        monthly_data[month_key][category] += transaction.amount

    # Calculate monthly totals and trends
    for month, categories in monthly_data.items():
        patterns['monthly_totals'][month] = sum(categories.values())

        for category, amount in categories.items():
            if category not in patterns['category_trends']:
                patterns['category_trends'][category] = {}
            patterns['category_trends'][category][month] = amount

    # Calculate seasonal patterns
    for category, monthly_amounts in patterns['category_trends'].items():
        month_totals = []
        for month in range(1, 13):
            month_str = f'2024-{month:02d}'
            amount = monthly_amounts.get(month_str, 0)
            month_totals.append(amount)

        if sum(month_totals) > 0:
            patterns['seasonal_patterns'][category] = month_totals

    # Calculate volatility scores
    for category, amounts in patterns['category_trends'].items():
        if len(amounts) > 1:
            amount_values = list(amounts.values())
            mean_amount = sum(amount_values) / len(amount_values)
            variance = sum((x - mean_amount) ** 2 for x in amount_values) / len(amount_values)
            std_dev = variance ** 0.5
            cv = std_dev / mean_amount if mean_amount > 0 else 0  # Coefficient of variation

            patterns['volatility_scores'][category] = cv

    return patterns

def predict_future_expenses(category_patterns, months_ahead=3):
    """Predict future expenses based on historical patterns"""
    predictions = {}

    for category, monthly_data in category_patterns.items():
        if len(monthly_data) < 3:
            continue

        amounts = list(monthly_data.values())
        months = list(monthly_data.keys())

        # Simple moving average prediction
        recent_avg = sum(amounts[-3:]) / 3

        # Trend calculation (linear regression slope)
        x = list(range(len(amounts)))
        slope = sum((xi - sum(x)/len(x)) * (yi - sum(amounts)/len(amounts))
                   for xi, yi in zip(x, amounts)) / sum((xi - sum(x)/len(x))**2 for xi in x)

        # Project trend
        future_predictions = []
        last_amount = amounts[-1]

        for i in range(months_ahead):
            # Blend trend projection with recent average
            trend_projection = last_amount + slope * (i + 1)
            weighted_prediction = (trend_projection * 0.3) + (recent_avg * 0.7)
            future_predictions.append(max(0, weighted_prediction))  # No negative predictions

        predictions[category] = future_predictions

    return predictions
