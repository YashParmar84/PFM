from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import UserProfile, Transaction, Budget


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ['created_at', 'updated_at']


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('userprofile')


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'category', 'amount', 'description', 'date', 'created_at']
    list_filter = ['transaction_type', 'category', 'date', 'created_at']
    search_fields = ['user__username', 'description', 'amount']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Transaction Details', {
            'fields': ('user', 'amount', 'transaction_type', 'category', 'description', 'date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'month', 'created_at']
    list_filter = ['category', 'month', 'created_at']
    search_fields = ['user__username', 'category', 'amount']
    ordering = ['-month', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Budget Details', {
            'fields': ('user', 'category', 'amount', 'month')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Custom Admin Site
class PersonalFinanceAdminSite(admin.AdminSite):
    site_header = 'Personal Finance Management Admin'
    site_title = 'PFM Admin Portal'
    index_title = 'Welcome to Personal Finance Management Admin'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='admin_dashboard'),
            path('user/<int:user_id>/details/', self.admin_view(self.user_details_view), name='user_details'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Custom admin dashboard with statistics"""
        # Get statistics
        total_users = User.objects.count()
        total_transactions = Transaction.objects.count()
        total_budgets = Budget.objects.count()

        # Get transaction statistics
        income_transactions = Transaction.objects.filter(transaction_type='income').count()
        expense_transactions = Transaction.objects.filter(transaction_type='expense').count()

        # Get recent transactions
        recent_transactions = Transaction.objects.select_related('user').order_by('-created_at')[:10]

        # Get users for the user table
        users = User.objects.select_related('userprofile').order_by('-date_joined')[:20]

        # Get monthly statistics
        current_month = Budget.objects.filter(
            month__year=Budget.objects.latest('month').month.year,
            month__month=Budget.objects.latest('month').month.month
        ).count()

        context = {
            'total_users': total_users,
            'total_transactions': total_transactions,
            'total_budgets': total_budgets,
            'income_transactions': income_transactions,
            'expense_transactions': expense_transactions,
            'recent_transactions': recent_transactions,
            'users': users,
            'current_month_budgets': current_month,
        }

        return render(request, 'admin/dashboard.html', context)

    def user_details_view(self, request, user_id):
        """AJAX view to get detailed user information"""
        try:
            user = User.objects.select_related('userprofile').prefetch_related(
                'transaction_set', 'budget_set'
            ).get(id=user_id)

            # Get user's transactions
            transactions = user.transaction_set.order_by('-date')[:10]

            # Get user's budgets
            budgets = user.budget_set.order_by('-month')[:10]

            # Calculate user's financial summary
            total_income = user.transaction_set.filter(
                transaction_type='income'
            ).aggregate(total=Sum('amount'))['total'] or 0

            total_expenses = user.transaction_set.filter(
                transaction_type='expense'
            ).aggregate(total=Sum('amount'))['total'] or 0

            context = {
                'user': user,
                'transactions': transactions,
                'budgets': budgets,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'balance': total_income - total_expenses,
            }

            return render(request, 'admin/user_details.html', context)
        except User.DoesNotExist:
            return render(request, 'admin/error.html', {'error': 'User not found'})


# Create custom admin site instance
admin_site = PersonalFinanceAdminSite(name='personal_finance_admin')

# Register models with custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(Transaction, TransactionAdmin)
admin_site.register(Budget, BudgetAdmin)
