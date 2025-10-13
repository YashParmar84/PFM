from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, Budget
from django.db.models import Sum
from datetime import datetime, date
from django.utils import timezone
from decimal import Decimal


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('user:dashboard')
    return render(request, 'user/home.html')


@login_required
def dashboard(request):
    """User dashboard with financial overview"""
    user = request.user

    # Get current month transactions
    current_month = timezone.now().date().replace(day=1)
    transactions = Transaction.objects.filter(
        user=user,
        date__gte=current_month
    )

    # Calculate totals
    total_income = transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount'))['total'] or 0
    total_expense = transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount'))['total'] or 0

    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:10]

    # Get budgets for current month with expense information
    budgets = Budget.objects.filter(
        user=user,
        month__year=current_month.year,
        month__month=current_month.month
    ).select_related()

    # Add expense information to each budget
    for budget in budgets:
        current_expenses = budget.get_current_expenses
        budget.current_expenses = current_expenses
        budget.remaining_budget = budget.amount - current_expenses
        budget.is_over_budget = current_expenses > budget.amount
        budget.usage_percentage = min((current_expenses / budget.amount) * 100, 100) if budget.amount > 0 else 0
        budget.over_budget_amount = current_expenses - budget.amount if current_expenses > budget.amount else 0

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'recent_transactions': recent_transactions,
        'budgets': budgets,
    }

    return render(request, 'user/dashboard.html', context)


@login_required
def add_transaction(request):
    """Add new transaction"""
    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        date_str = request.POST.get('date')

        try:
            transaction = Transaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type=transaction_type,
                category=category,
                description=description,
                date=date_str
            )
            messages.success(request, 'Transaction added successfully!')
            return redirect('user:dashboard')
        except Exception as e:
            messages.error(request, f'Error adding transaction: {str(e)}')

    return render(request, 'user/add_transaction.html')


@login_required
def edit_transaction(request, transaction_id):
    """Edit existing transaction"""
    try:
        transaction = Transaction.objects.get(id=transaction_id, user=request.user)
    except Transaction.DoesNotExist:
        messages.error(request, 'Transaction not found!')
        return redirect('user:transaction_list')

    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        date_str = request.POST.get('date')

        try:
            transaction.amount = amount
            transaction.transaction_type = transaction_type
            transaction.category = category
            transaction.description = description
            transaction.date = date_str
            transaction.save()

            messages.success(request, 'Transaction updated successfully!')
            return redirect('user:transaction_list')
        except Exception as e:
            messages.error(request, f'Error updating transaction: {str(e)}')

    context = {
        'transaction': transaction,
        'transaction_types': Transaction.TRANSACTION_TYPES,
        'categories': Transaction.CATEGORIES,
    }
    return render(request, 'user/edit_transaction.html', context)


@login_required
def delete_transaction(request, transaction_id):
    """Delete transaction"""
    try:
        transaction = Transaction.objects.get(id=transaction_id, user=request.user)
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully!')
    except Transaction.DoesNotExist:
        messages.error(request, 'Transaction not found!')

    return redirect('user:transaction_list')


@login_required
def transaction_list(request):
    """List all transactions"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
    # Filter by type if specified
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by category if specified
    category = request.GET.get('category')
    if category:
        transactions = transactions.filter(category=category)
    
    context = {
        'transactions': transactions,
        'transaction_types': Transaction.TRANSACTION_TYPES,
        'categories': Transaction.CATEGORIES,
    }
    
    return render(request, 'user/transaction_list.html', context)


@login_required
def budget_management(request):
    """Budget management page"""
    if request.method == 'POST':
        category = request.POST.get('category')
        amount = request.POST.get('amount')
        month_str = request.POST.get('month')  # This comes as "YYYY-MM" format

        try:
            # Convert month string to date object for storage
            month_date = datetime.strptime(month_str + "-01", "%Y-%m-%d").date()

            # Calculate current expenses for this category and month
            current_expenses = Transaction.objects.filter(
                user=request.user,
                category=category,
                transaction_type='expense',
                date__year=month_date.year,
                date__month=month_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Convert amount to Decimal for comparison
            budget_amount = Decimal(amount)

            # Check if expenses exceed budget
            if current_expenses > budget_amount:
                messages.warning(
                    request,
                    f'Warning: Your current expenses (₹{current_expenses:.2f}) exceed your budget (₹{budget_amount:.2f}) by ₹{(current_expenses - budget_amount):.2f}. Consider reviewing your spending or adjusting your budget.'
                )
            elif current_expenses > 0:
                remaining_budget = budget_amount - current_expenses
                messages.info(
                    request,
                    f'Current expenses: ₹{current_expenses:.2f}. Remaining budget: ₹{remaining_budget:.2f}'
                )

            # Create or update budget
            budget, created = Budget.objects.get_or_create(
                user=request.user,
                category=category,
                month=month_date,
                defaults={'amount': amount}
            )
            if not created:
                budget.amount = amount
                budget.save()

            if created:
                messages.success(request, 'Budget created successfully!')
            else:
                messages.success(request, 'Budget updated successfully!')

        except Exception as e:
            messages.error(request, f'Error updating budget: {str(e)}')

    # Get current month budgets - filter by month string format
    current_month_str = timezone.now().strftime('%Y-%m')
    budgets = Budget.objects.filter(
        user=request.user,
        month__year=timezone.now().year,
        month__month=timezone.now().month
    )

    # Check for edit parameters from dashboard
    edit_category = request.GET.get('edit')
    edit_month = request.GET.get('month')

    # Pre-fill form if edit parameters are provided
    prefill_data = {}
    if edit_category and edit_month:
        try:
            edit_month_date = datetime.strptime(edit_month + "-01", "%Y-%m-%d").date()
            budget_to_edit = Budget.objects.get(
                user=request.user,
                category=edit_category,
                month=edit_month_date
            )
            prefill_data = {
                'category': edit_category,
                'amount': str(budget_to_edit.amount),
                'month': edit_month
            }
        except (Budget.DoesNotExist, ValueError):
            pass  # Invalid edit parameters, ignore

    context = {
        'budgets': budgets,
        'categories': Transaction.CATEGORIES,
        'prefill_data': prefill_data,
    }

    return render(request, 'user/budget_management.html', context)


def register(request):
    """User registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'user/register.html')
        
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user=user)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('user:login')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'user/register.html')


def user_login(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            return redirect('user:dashboard')
        else:
            messages.error(request, 'Invalid username or password!')
    
    return render(request, 'user/login.html')


@login_required
def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('user:home')
