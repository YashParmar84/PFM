from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, Budget
from django.db.models import Sum
from datetime import datetime, date
from django.utils import timezone


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
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
    
    # Get budgets for current month
    budgets = Budget.objects.filter(user=user, month=current_month)
    
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
        description = request.POST.get('description')
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
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Error adding transaction: {str(e)}')
    
    return render(request, 'user/add_transaction.html')


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
        month = request.POST.get('month')
        
        try:
            budget, created = Budget.objects.get_or_create(
                user=request.user,
                category=category,
                month=month,
                defaults={'amount': amount}
            )
            if not created:
                budget.amount = amount
                budget.save()
            
            messages.success(request, 'Budget updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating budget: {str(e)}')
    
    # Get current month budgets
    current_month = timezone.now().date().replace(day=1)
    budgets = Budget.objects.filter(user=request.user, month=current_month)
    
    context = {
        'budgets': budgets,
        'categories': Transaction.CATEGORIES,
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
            return redirect('login')
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
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password!')
    
    return render(request, 'user/login.html')


@login_required
def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')
