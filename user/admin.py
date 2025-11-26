from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import UserProfile, Transaction, Budget, LoanProduct, AIConsultation


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ['get_created_at', 'get_updated_at']

    def get_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if obj.created_at else '-'
    get_created_at.short_description = 'Created At'
    get_created_at.admin_order_field = 'created_at'

    def get_updated_at(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M:%S') if obj.updated_at else '-'
    get_updated_at.short_description = 'Updated At'
    get_updated_at.admin_order_field = 'updated_at'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined', 'transaction_count', 'view_transactions_link', 'view_budgets_link']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('userprofile')

    def transaction_count(self, obj):
        return Transaction.objects.filter(user=obj).count()
    transaction_count.short_description = 'Transactions'

    def view_transactions_link(self, obj):
        """Link to view this user's transactions"""
        url = '/admin/user/transaction/?user__id__exact={}'.format(obj.id)
        return '<a href="{}" target="_blank">🇹 View Transactions ({})</a>'.format(url, Transaction.objects.filter(user=obj).count())
    view_transactions_link.short_description = 'Transactions'
    view_transactions_link.allow_tags = True

    def view_budgets_link(self, obj):
        """Link to view this user's budgets"""
        url = '/admin/user/budget/?user__id__exact={}'.format(obj.id)
        return '<a href="{}" target="_blank">💰 View Budgets ({})</a>'.format(url, Budget.objects.filter(user=obj).count())
    view_budgets_link.short_description = 'Budgets'
    view_budgets_link.allow_tags = True


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'category', 'amount', 'description', 'date', 'created_at']
    list_filter = ['user', 'transaction_type', 'category', 'date', 'created_at']
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
    list_filter = ['user', 'category', 'month', 'created_at']
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

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = [
        'model_name', 'price', 'emi', 'bank_name',
        'category', 'interest_rate', 'tenure_months'
    ]

    list_filter = ['category', 'bank_name', 'interest_rate']
    search_fields = ['model_name', 'bank_name', 'category']
    ordering = ['model_name']

    # Removed invalid fields that do not exist in the model
    readonly_fields = []  

    fieldsets = (
        ('Product Details', {
            'fields': (
                'item_id', 'category', 'model_name', 'price', 'emi',
                'bank_name', 'interest_rate', 'tenure_months'
            )
        }),
    )

    def has_add_permission(self, request):
        """Allow only superusers to add loan products"""
        return request.user.is_superuser

@admin.register(AIConsultation)
class AIConsultationAdmin(admin.ModelAdmin):
    list_display = ['user', 'selected_item', 'user_income', 'affordability_score', 'created_at', 'get_plan_status']
    list_filter = ['created_at', 'affordability_score', 'selected_plan']
    search_fields = ['user__username', 'selected_item__model_name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'months_completed', 'remaining_months']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'selected_item', 'user_income', 'ai_recommendation', 'affordability_score')
        }),
        ('Risk Assessment', {
            'fields': ('risk_assessment', 'recommended_banks')
        }),
        ('Plan Management', {
            'fields': ('selected_plan', 'activated_plan', 'plan_start_date', 'plan_end_date', 'monthly_tracking_active'),
            'classes': ('collapse',)
        }),
        ('Calculated Fields', {
            'fields': ('months_completed', 'remaining_months'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_plan_status(self, obj):
        if obj.activated_plan:
            return "Activated"
        elif obj.selected_plan:
            return "Selected"
        else:
            return "None"
    get_plan_status.short_description = "Plan Status"
    get_plan_status.admin_order_field = 'activated_plan'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'selected_item')


# Register models with custom admin site
admin_site.register(User, CustomUserAdmin)
admin_site.register(Transaction, TransactionAdmin)
admin_site.register(Budget, BudgetAdmin)
admin_site.register(LoanProduct, LoanProductAdmin)
admin_site.register(AIConsultation, AIConsultationAdmin)


# User Self-Administration Site
class UserSelfAdminSite(admin.AdminSite):
    site_header = 'Personal Finance Manager'
    site_title = 'User Finance Portal'
    index_title = 'Manage Your Finances'
    login_template = 'admin/login.html'  # Use Django's built-in login template

    def has_permission(self, request):
        """Ensure only authenticated users can access"""
        return request.user.is_authenticated

    def each_context(self, request):
        """Add user context to all admin pages"""
        context = super().each_context(request)
        context['user'] = request.user
        return context


# User-specific Transaction Admin
class UserTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'category', 'amount', 'description', 'date']
    list_filter = ['transaction_type', 'category', 'date']
    search_fields = ['description', 'amount']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Transaction Details', {
            'fields': ('amount', 'transaction_type', 'category', 'description', 'date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filter to show only current user's transactions"""
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        """Automatically assign transaction to current user"""
        obj.user = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """Users can only change their own transactions"""
        if obj is None:
            return True
        return obj.user == request.user

    def has_delete_permission(self, request, obj=None):
        """Users can only delete their own transactions"""
        if obj is None:
            return True
        return obj.user == request.user


# User-specific Budget Admin
class UserBudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'month']
    list_filter = ['category', 'month', 'created_at']
    search_fields = ['category', 'amount']
    ordering = ['-month', '-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Budget Details', {
            'fields': ('category', 'amount', 'month')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filter to show only current user's budgets"""
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        """Automatically assign budget to current user"""
        obj.user = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """Users can only change their own budgets"""
        if obj is None:
            return True
        return obj.user == request.user

    def has_delete_permission(self, request, obj=None):
        """Users can only delete their own budgets"""
        if obj is None:
            return True
        return obj.user == request.user


# Create user admin site instance
user_admin_site = UserSelfAdminSite(name='user_finance_admin')

# Register only user's own data models
user_admin_site.register(Transaction, UserTransactionAdmin)
user_admin_site.register(Budget, UserBudgetAdmin)
