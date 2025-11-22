from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    auto_adjust_budgets = models.BooleanField(default=True, help_text="Automatically adjust budgets when spending on unbudgeted categories")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    CATEGORIES = [
        ('food', 'Food & Dining'),
        ('transportation', 'Transportation'),
        ('entertainment', 'Entertainment'),
        ('shopping', 'Shopping'),
        ('bills', 'Bills & Utilities'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('salary', 'Salary'),
        ('freelance', 'Freelance'),
        ('investment', 'Investment'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.TextField(blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type.title()}: {self.amount} - {self.description}"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=Transaction.CATEGORIES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Budget for {self.category}: {self.amount}"

    @property
    def get_current_expenses(self):
        """Get current expenses for this budget's category and month"""
        from django.db.models import Sum
        import datetime

        # Extract year and month from the budget's month field
        budget_year = self.month.year
        budget_month = self.month.month

        # Debug: Show what we're looking for
        print(f"\n🧪 DEBUG: Budget Check for {self.user.username}")
        print(f"   Category: '{self.category}' | Month: {budget_year}-{budget_month:02d}")
        print(f"   Budget Amount: ₹{float(self.amount):.2f}")

        # Build query for debugging
        expenses_queryset = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            transaction_type='expense',
            date__year=budget_year,
            date__month=budget_month
        )

        # Debug: Show transaction count
        count = expenses_queryset.count()
        print(f"   Found {count} expense transactions for this category/month")

        # Show sample transactions if any found
        if count > 0:
            sample_txs = expenses_queryset[:3]  # First 3 transactions
            for tx in sample_txs:
                print(f"   💰 Transaction: {tx.date} - ₹{float(tx.amount):.2f} - {tx.description}")
        else:
            print(f"   🔍 No transactions found - checking all user's transactions...")

            # If no transactions for this category/month, show what exists
            all_user_expenses = Transaction.objects.filter(
                user=self.user,
                transaction_type='expense'
            )[:5]  # Show first 5

            for tx in all_user_expenses:
                print(f"   ✅ Existing TX: {tx.category} on {tx.date.year}-{tx.date.month:02d} - ₹{float(tx.amount):.2f}")

        # Calculate total
        total_expenses = expenses_queryset.aggregate(total=Sum('amount'))['total']
        final_amount = float(total_expenses) if total_expenses is not None else 0.0

        print(f"   ✅ Total Spent: ₹{final_amount:.2f}")
        print(f"   ⚖️ Remaining Budget: ₹{float(self.amount) - final_amount:.2f}")

        return final_amount

    class Meta:
        unique_together = ['user', 'category', 'month']


class SpendingPattern(models.Model):
    """Model to store AI-generated spending insights and patterns"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=Transaction.CATEGORIES)
    month = models.DateField()
    predicted_amount = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    trend_direction = models.CharField(max_length=10, choices=[
        ('increasing', 'Increasing'),
        ('decreasing', 'Decreasing'),
        ('stable', 'Stable')
    ])
    ai_insights = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pattern for {self.user.username} - {self.category}: {self.predicted_amount}"

    class Meta:
        unique_together = ['user', 'category', 'month']


class UserActivity(models.Model):
    """Model to track user activities and interactions"""
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('add_transaction', 'Add Transaction'),
        ('edit_transaction', 'Edit Transaction'),
        ('delete_transaction', 'Delete Transaction'),
        ('create_budget', 'Create Budget'),
        ('update_budget', 'Update Budget'),
        ('view_dashboard', 'View Dashboard'),
        ('view_transactions', 'View Transactions'),
        ('view_budget', 'View Budget'),
        ('view_predictions', 'View Predictions'),
        ('view_ai_insights', 'View AI Insights'),
        ('export_data', 'Export Data'),
        ('import_data', 'Import Data'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, null=True, help_text="Additional data about the activity")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.get_activity_type_display()} - {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]


class FinancialGoal(models.Model):
    """Model to store user's financial goals"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal_name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_date = models.DateField()
    category = models.CharField(max_length=20, choices=Transaction.CATEGORIES, blank=True)
    priority = models.IntegerField(default=1, choices=[(1, 'High'), (2, 'Medium'), (3, 'Low')])
    is_achieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.goal_name}"

    @property
    def progress_percentage(self):
        """Calculate goal progress percentage"""
        if self.target_amount > 0:
            return min((self.current_amount / self.target_amount) * 100, 100)
        return 0

    @property
    def remaining_amount(self):
        """Calculate remaining amount to reach goal"""
        return max(0, self.target_amount - self.current_amount)


# New models for AI Financial Insights and Loan Products
class LoanProduct(models.Model):
    """Model to store available loan products"""
    CATEGORIES = [
        ('two_wheeler', 'Two Wheeler'),
        ('four_wheeler', 'Four Wheeler'),
        ('electronics', 'Electronics'),
        ('home_loan', 'Home Loan'),
        ('personal_loan', 'Personal Loan'),
        ('gold_loan', 'Gold Loan'),
    ]
    
    category = models.CharField(max_length=20, choices=CATEGORIES)
    item_id = models.IntegerField()  # ID from the original dataset
    model_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    bank_name = models.CharField(max_length=100)
    loan_type = models.CharField(max_length=50)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.IntegerField()
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    emi = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.model_name} - {self.bank_name} - ₹{self.emi}/month"


class AIConsultation(models.Model):
    """Model to store AI consultation history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    selected_item = models.ForeignKey(LoanProduct, on_delete=models.CASCADE)
    user_income = models.DecimalField(max_digits=10, decimal_places=2)
    ai_recommendation = models.TextField()
    affordability_score = models.DecimalField(max_digits=5, decimal_places=2)
    recommended_banks = models.JSONField()  # Store list of recommended banks
    risk_assessment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"AI Consultation for {self.user.username} - {self.selected_item.model_name}"
