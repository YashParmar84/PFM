from django.contrib.auth.models import User
from django.db import models
import json


class Transaction(models.Model):
    """Model for storing financial transactions"""
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    CATEGORIES = [
        ('food', 'Food & Dining'),
        ('transport', 'Transportation'),
        ('shopping', 'Shopping'),
        ('entertainment', 'Entertainment'),
        ('bills', 'Bills & Utilities'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('savings', 'Savings'),
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
        return f"{self.transaction_type} - ₹{self.amount} ({self.get_category_display()})"

    class Meta:
        ordering = ['-date']


class Budget(models.Model):
    """Model for storing budget plans"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=Transaction.CATEGORIES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.DateField()  # Stores the first day of the month (e.g., 2023-12-01)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_category_display()} Budget - ₹{self.amount}"

    @property
    def get_current_expenses(self):
        """Get actual expenses for this budget category and month"""
        from django.db.models import Sum
        from calendar import monthrange

        year, month = self.month.year, self.month.month
        start_date = self.month.replace(day=1)
        end_date = start_date.replace(day=monthrange(year, month)[1])

        expenses = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            transaction_type='expense',
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total']

        return expenses or 0.00

    class Meta:
        unique_together = ['user', 'category', 'month']


class LoanProduct(models.Model):
    """Model for storing loan/credit products"""
    CATEGORIES = [
        ('two_wheeler', 'Two Wheeler'),
        ('four_wheeler', 'Four Wheeler'),
        ('electronics', 'Electronics'),
        ('home_loan', 'Home Loan'),
        ('personal_loan', 'Personal Loan'),
        ('gold_loan', 'Gold Loan'),
    ]

    item_id = models.CharField(max_length=20)  # Bank identifier
    category = models.CharField(max_length=20, choices=CATEGORIES)
    model_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    emi = models.DecimalField(max_digits=10, decimal_places=2)
    bank_name = models.CharField(max_length=100)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tenure_months = models.IntegerField()

    def __str__(self):
        return f"{self.model_name} - ₹{self.price} ({self.get_category_display()})"


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class UserActivity(models.Model):
    """Model to track user activities"""
    ACTIVITY_TYPES = [
        ('add_transaction', 'Add Transaction'),
        ('update_transaction', 'Update Transaction'),
        ('delete_transaction', 'Delete Transaction'),
        ('create_budget', 'Create Budget'),
        ('update_budget', 'Update Budget'),
        ('ai_consultation', 'AI Consultation'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    metadata = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.activity_type}"

    class Meta:
        ordering = ['-timestamp']


class AIConsultation(models.Model):
    """Model to store AI consultation history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    selected_item = models.ForeignKey(LoanProduct, on_delete=models.CASCADE)
    user_income = models.DecimalField(max_digits=10, decimal_places=2)
    ai_recommendation = models.TextField()
    affordability_score = models.DecimalField(max_digits=5, decimal_places=2)
    recommended_banks = models.JSONField()  # Store list of recommended banks
    risk_assessment = models.TextField()
    # New fields for plan management
    selected_plan = models.JSONField(blank=True, null=True)  # Store selected plan details
    activated_plan = models.BooleanField(default=False)  # Track if plan is activated
    plan_start_date = models.DateField(blank=True, null=True)  # When plan was activated
    plan_end_date = models.DateField(blank=True, null=True)  # When plan will end
    monthly_tracking_active = models.BooleanField(default=False)  # If monthly tracking is enabled
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Consultation for {self.user.username} - {self.selected_item.model_name}"

    @property
    def months_completed(self):
        """Calculate months completed since plan activation"""
        if not self.plan_start_date:
            return 0
        from datetime import date
        today = date.today()
        if today < self.plan_start_date:
            return 0
        months = (today.year - self.plan_start_date.year) * 12 + (today.month - self.plan_start_date.month)
        return max(0, months)

    @property
    def remaining_months(self):
        """Calculate remaining months in the plan"""
        if not self.plan_end_date:
            return 0
        from datetime import date
        today = date.today()
        if today > self.plan_end_date:
            return 0
        months = (self.plan_end_date.year - today.year) * 12 + (self.plan_end_date.month - today.month)
        return max(0, months)

    class Meta:
        ordering = ['-created_at']
