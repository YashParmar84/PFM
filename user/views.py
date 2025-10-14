from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, Budget, SpendingPattern, FinancialGoal
from django.db.models import Sum, Count
from datetime import datetime, date
from django.utils import timezone
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


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

    # Calculate total budgeted amount across all categories
    total_budgeted = budgets.aggregate(total=Sum('amount'))['total'] or 0

    # Add expense information to each budget
    for budget in budgets:
        current_expenses = budget.get_current_expenses
        budget.current_expenses = current_expenses
        budget.remaining_budget = budget.amount - current_expenses
        budget.is_over_budget = current_expenses > budget.amount
        budget.usage_percentage = min((current_expenses / budget.amount) * 100, 100) if budget.amount > 0 else 0
        budget.over_budget_amount = current_expenses - budget.amount if current_expenses > budget.amount else 0

    # Calculate overall budget usage percentage (total budgeted / total income)
    overall_budget_usage = min((total_budgeted / total_income) * 100, 100) if total_income > 0 else 0

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'recent_transactions': recent_transactions,
        'budgets': budgets,
        'total_budgeted': total_budgeted,
        'overall_budget_usage': overall_budget_usage,
        'available_for_budget': total_income - total_budgeted,
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
            # Create the transaction first
            transaction = Transaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type=transaction_type,
                category=category,
                description=description,
                date=date_str
            )

            # If it's an expense, check if we need to auto-adjust budgets
            if transaction_type == 'expense':
                # Check if user has auto-adjustment enabled
                try:
                    user_profile = UserProfile.objects.get(user=request.user)
                    if user_profile.auto_adjust_budgets:
                        adjustments_made = auto_adjust_budgets_for_expense(request.user, category, amount, date_str)
                        if adjustments_made:
                            messages.info(request, f'Budget automatically adjusted for {category.title()} expense. Other category budgets were reduced proportionally to accommodate this expense.')
                except UserProfile.DoesNotExist:
                    # If no profile exists, create one with auto-adjustment enabled by default
                    UserProfile.objects.create(user=request.user, auto_adjust_budgets=True)
                    adjustments_made = auto_adjust_budgets_for_expense(request.user, category, amount, date_str)
                    if adjustments_made:
                        messages.info(request, f'Budget automatically adjusted for {category.title()} expense. Other category budgets were reduced proportionally to accommodate this expense.')

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
def budget_prediction(request):
    """Budget prediction page with AI-powered recommendations"""
    return render(request, 'user/budget_prediction.html')


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

            # Validate budget amount is reasonable (not extremely high)
            try:
                budget_amount = Decimal(amount)
                # Prevent extremely high budget amounts (e.g., more than 10 million)
                if budget_amount > Decimal('10000000'):
                    messages.error(
                        request,
                        'Error: Budget amount is too high. Please enter a reasonable amount.'
                    )
                    return redirect('user:budget_management')
            except (ValueError, TypeError):
                messages.error(
                    request,
                    'Error: Please enter a valid budget amount.'
                )
                return redirect('user:budget_management')

            # Calculate total income for the selected month
            total_income = Transaction.objects.filter(
                user=request.user,
                transaction_type='income',
                date__year=month_date.year,
                date__month=month_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Calculate sum of all existing budgets for this month
            # If editing, we need to check if this budget already exists
            existing_budget_amount = 0
            if category:
                try:
                    existing_budget = Budget.objects.get(
                        user=request.user,
                        category=category,
                        month=month_date
                    )
                    existing_budget_amount = existing_budget.amount
                except Budget.DoesNotExist:
                    existing_budget_amount = 0

            # Get total of all OTHER budgets (excluding the current one being edited)
            all_other_budgets = Budget.objects.filter(
                user=request.user,
                month=month_date
            ).exclude(category=category) if category else Budget.objects.filter(
                user=request.user,
                month=month_date
            )

            total_other_budgets = all_other_budgets.aggregate(total=Sum('amount'))['total'] or 0

            # Ensure we're working with Decimal for accurate calculations
            total_other_budgets = Decimal(str(total_other_budgets)) if total_other_budgets else Decimal('0')
            budget_amount = Decimal(str(budget_amount)) if budget_amount else Decimal('0')
            total_income = Decimal(str(total_income)) if total_income else Decimal('0')

            # Calculate what the total budget would be after this change
            # If editing existing budget: (total_other + new_amount)
            # If creating new budget: (total_other + new_amount)
            total_budget_after_adding = total_other_budgets + budget_amount

            if total_budget_after_adding > total_income:
                excess_amount = total_budget_after_adding - total_income
                messages.error(
                    request,
                    f'Error: Your total budget across all categories (₹{total_budget_after_adding:.2f}) would exceed your monthly income (₹{total_income:.2f}) by ₹{excess_amount:.2f}. You can only set budgets up to your total income amount. Please reduce this budget or increase your income first.'
                )
                # Don't save the budget if it exceeds income
                return redirect('user:budget_management')
            else:
                # Calculate current expenses for this category and month
                current_expenses = Transaction.objects.filter(
                    user=request.user,
                    category=category,
                    transaction_type='expense',
                    date__year=month_date.year,
                    date__month=month_date.month
                ).aggregate(total=Sum('amount'))['total'] or 0

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


@login_required
@require_GET
def get_income_budget_data(request):
    """API endpoint to get income and budget data for a specific month"""
    month_str = request.GET.get('month')  # Format: YYYY-MM

    if not month_str:
        return JsonResponse({'error': 'Month parameter is required'}, status=400)

    try:
        # Parse the month string
        month_date = datetime.strptime(month_str + "-01", "%Y-%m-%d").date()

        # Calculate total income for the selected month
        total_income = Transaction.objects.filter(
            user=request.user,
            transaction_type='income',
            date__year=month_date.year,
            date__month=month_date.month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate total budgeted amount for the selected month
        total_budgeted = Budget.objects.filter(
            user=request.user,
            month=month_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate available budget and usage percentage
        available_budget = total_income - total_budgeted
        budget_usage = (total_budgeted / total_income * 100) if total_income > 0 else 0

        # Get month name for display
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        current_month = f"{month_names[month_date.month - 1]} {month_date.year}"

        # Return JSON response
        return JsonResponse({
            'total_income': f"{total_income:.2f}",
            'total_budgeted': f"{total_budgeted:.2f}",
            'available_budget': f"{available_budget:.2f}",
            'budget_usage': f"{budget_usage:.1f}",
            'current_month': current_month
        })

    except (ValueError, TypeError) as e:
        return JsonResponse({'error': 'Invalid month format'}, status=400)


@login_required
@require_GET
def get_spending_insights(request):
    """API endpoint to get AI-powered spending insights and predictions"""
    try:
        current_month = datetime.now().replace(day=1)

        # Get spending patterns for current month
        patterns = SpendingPattern.objects.filter(
            user=request.user,
            month=current_month
        )

        insights_data = []
        for pattern in patterns:
            insights_data.append({
                'category': pattern.get_category_display(),
                'predicted_amount': float(pattern.predicted_amount),
                'confidence_score': float(pattern.confidence_score),
                'trend_direction': pattern.trend_direction,
                'ai_insights': pattern.ai_insights
            })

        # Get financial goals
        goals = FinancialGoal.objects.filter(user=request.user, is_achieved=False)
        goals_data = []
        for goal in goals:
            goals_data.append({
                'name': goal.goal_name,
                'target_amount': float(goal.target_amount),
                'current_amount': float(goal.current_amount),
                'progress_percentage': goal.progress_percentage,
                'remaining_amount': float(goal.remaining_amount),
                'target_date': goal.target_date.strftime('%Y-%m-%d'),
                'priority': goal.get_priority_display()
            })

        # Generate category-wise spending analysis
        category_analysis = get_category_spending_analysis(request.user)

        response_data = {
            'spending_patterns': insights_data,
            'financial_goals': goals_data,
            'category_analysis': category_analysis,
            'summary': {
                'total_patterns': len(insights_data),
                'total_goals': len(goals_data),
                'high_confidence_predictions': len([p for p in insights_data if p['confidence_score'] > 70])
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_budget_suggestions(request):
    """API endpoint to get AI-powered budget suggestions"""
    try:
        # Get user's spending patterns
        patterns = SpendingPattern.objects.filter(user=request.user)

        if not patterns.exists():
            return JsonResponse({
                'suggestions': [],
                'total_suggestions': 0,
                'message': 'No spending patterns available yet. Add more transactions to get suggestions.'
            })

        # Get current budgets
        current_month = datetime.now().replace(day=1)
        budgets = Budget.objects.filter(user=request.user, month=current_month)

        suggestions = []

        # Analyze each category
        for pattern in patterns:
            existing_budget = budgets.filter(category=pattern.category).first()

            if existing_budget:
                # Compare predicted vs actual budget
                predicted = float(pattern.predicted_amount)
                current_budget = float(existing_budget.amount)

                if predicted > current_budget * 1.2:
                    suggestions.append({
                        'type': 'increase',
                        'category': pattern.get_category_display(),
                        'current_budget': current_budget,
                        'suggested_budget': predicted,
                        'reason': f'Your predicted {pattern.get_category_display()} spending (₹{predicted:.0f}) is ₹{predicted - current_budget:.0f} higher than current budget (₹{current_budget:.0f})',
                        'confidence': float(pattern.confidence_score)
                    })
                elif predicted < current_budget * 0.8:
                    suggestions.append({
                        'type': 'decrease',
                        'category': pattern.get_category_display(),
                        'current_budget': current_budget,
                        'suggested_budget': predicted,
                        'reason': f'You can reduce {pattern.get_category_display()} budget by ₹{current_budget - predicted:.0f} based on spending patterns',
                        'confidence': float(pattern.confidence_score)
                    })
            else:
                # Suggest creating budget for category with high spending
                if float(pattern.predicted_amount) > 10000:  # Only suggest for significant amounts
                    suggestions.append({
                        'type': 'create',
                        'category': pattern.get_category_display(),
                        'suggested_budget': float(pattern.predicted_amount),
                        'reason': f'Consider setting a budget for {pattern.get_category_display()} category (predicted: ₹{float(pattern.predicted_amount):.0f})',
                        'confidence': float(pattern.confidence_score)
                    })

        # Sort by confidence score
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)

        return JsonResponse({
            'suggestions': suggestions[:10],  # Top 10 suggestions
            'total_suggestions': len(suggestions)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_budget_prediction(request):
    """API endpoint to get ML-powered budget predictions based on salary and historical data"""
    try:
        salary_str = request.GET.get('salary')
        if not salary_str:
            return JsonResponse({'error': 'Salary parameter is required'}, status=400)

        try:
            monthly_salary = float(salary_str)
        except ValueError:
            return JsonResponse({'error': 'Invalid salary amount'}, status=400)

        # Get user's historical spending data with ML analysis
        historical_data = get_user_historical_spending_ml(request.user)

        if not historical_data or historical_data['total_months'] < 2:
            # Insufficient data - use ML-enhanced standard ratios
            return JsonResponse(create_ml_enhanced_budget_recommendation(monthly_salary))

        # Use ML algorithms to analyze patterns and predict budget
        budget_recommendation = analyze_with_ml_algorithms(request.user, monthly_salary, historical_data)

        return JsonResponse(budget_recommendation)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_user_historical_spending(user, months=6):
    """Get user's historical spending data for analysis"""
    from datetime import timedelta

    end_date = datetime.now().replace(day=1)
    start_date = end_date - timedelta(days=months*30)  # Approximate months

    # Get monthly spending by category
    monthly_spending = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lt=end_date
    ).values('category').annotate(
        total_amount=Sum('amount'),
        transaction_count=Count('id')
    ).order_by('-total_amount')

    if not monthly_spending:
        return None

    # Calculate average monthly spending per category
    category_averages = {}
    total_spent = sum(float(item['total_amount']) for item in monthly_spending)

    for item in monthly_spending:
        category = item['category']
        avg_monthly = float(item['total_amount']) / months
        percentage = (float(item['total_amount']) / total_spent * 100) if total_spent > 0 else 0

        category_averages[category] = {
            'category': category,
            'category_display': dict(Transaction.CATEGORIES).get(category, category),
            'avg_monthly': avg_monthly,
            'total_amount': float(item['total_amount']),
            'percentage': round(percentage, 2),
            'transaction_count': item['transaction_count']
        }

    return {
        'total_avg_monthly': total_spent / months,
        'categories': category_averages,
        'months_analyzed': months
    }


def get_user_historical_spending_ml(user, months=12):
    """Get enhanced historical spending data for ML analysis"""
    from datetime import timedelta
    import numpy as np

    end_date = datetime.now().replace(day=1)
    start_date = end_date - timedelta(days=months*30)

    # Get detailed monthly breakdown
    monthly_data = {}
    category_monthly = {}

    # Get all expense transactions
    transactions = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lt=end_date
    ).order_by('date')

    if not transactions:
        return None

    # Group by month and category
    for trans in transactions:
        month_key = trans.date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'total': 0, 'categories': {}}

        monthly_data[month_key]['total'] += float(trans.amount)
        category = trans.category

        if category not in monthly_data[month_key]['categories']:
            monthly_data[month_key]['categories'][category] = 0
        monthly_data[month_key]['categories'][category] += float(trans.amount)

        if category not in category_monthly:
            category_monthly[category] = []
        category_monthly[category].append((month_key, float(trans.amount)))

    # Calculate ML features for each category
    category_analysis = {}
    total_months = len(monthly_data)

    for category, month_amounts in category_monthly.items():
        amounts = [amount for _, amount in month_amounts]
        amounts_array = np.array(amounts)

        # ML features
        mean_spending = np.mean(amounts_array)
        median_spending = np.median(amounts_array)
        std_spending = np.std(amounts_array)
        min_spending = np.min(amounts_array)
        max_spending = np.max(amounts_array)

        # Trend analysis (linear regression slope)
        if len(amounts) > 1:
            x = np.arange(len(amounts))
            slope = np.polyfit(x, amounts, 1)[0]
            trend = 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable'
        else:
            trend = 'stable'

        # Seasonality detection (coefficient of variation)
        cv = (std_spending / mean_spending) if mean_spending > 0 else 0
        volatility = 'high' if cv > 0.5 else 'medium' if cv > 0.2 else 'low'

        # Prediction using exponential smoothing
        if len(amounts) >= 3:
            alpha = 0.3  # Smoothing parameter
            smoothed = [amounts[0]]
            for i in range(1, len(amounts)):
                smoothed_val = alpha * amounts[i] + (1 - alpha) * smoothed[i-1]
                smoothed.append(smoothed_val)

            # Predict next month
            last_smoothed = smoothed[-1]
            if trend == 'increasing':
                predicted = last_smoothed * 1.05
            elif trend == 'decreasing':
                predicted = last_smoothed * 0.95
            else:
                predicted = last_smoothed
        else:
            predicted = mean_spending

        # Confidence score based on data quality
        confidence = min(95, (len(amounts) / total_months) * 100)
        if volatility == 'high':
            confidence *= 0.7  # Reduce confidence for volatile categories

        category_analysis[category] = {
            'category': category,
            'category_display': dict(Transaction.CATEGORIES).get(category, category),
            'mean_monthly': round(mean_spending, 2),
            'median_monthly': round(median_spending, 2),
            'std_monthly': round(std_spending, 2),
            'min_monthly': round(min_spending, 2),
            'max_monthly': round(max_spending, 2),
            'trend': trend,
            'volatility': volatility,
            'predicted_amount': round(max(0, predicted), 2),
            'confidence_score': round(confidence, 2),
            'months_observed': len(amounts),
            'total_amount': round(sum(amounts), 2)
        }

    # Overall statistics
    total_spending = sum(cat['total_amount'] for cat in category_analysis.values())
    avg_monthly_total = total_spending / total_months if total_months > 0 else 0

    return {
        'total_months': total_months,
        'total_avg_monthly': round(avg_monthly_total, 2),
        'categories': category_analysis,
        'monthly_breakdown': monthly_data,
        'analysis_features': {
            'most_stable_category': min(category_analysis.items(), key=lambda x: x[1]['std_monthly'])[0] if category_analysis else None,
            'most_volatile_category': max(category_analysis.items(), key=lambda x: x[1]['std_monthly'])[0] if category_analysis else None,
            'highest_spending_category': max(category_analysis.items(), key=lambda x: x[1]['mean_monthly'])[0] if category_analysis else None,
        }
    }


def create_standard_budget_recommendation(monthly_salary):
    """Create budget recommendation based on standard financial ratios"""
    # Standard budget allocation percentages (50/30/20 rule as base)
    needs_percentage = 50  # Essential expenses
    wants_percentage = 30  # Non-essential expenses
    savings_percentage = 20  # Savings and investments

    # Adjust based on salary range
    if monthly_salary < 15000:
        # Lower income - prioritize essentials
        needs_percentage = 60
        wants_percentage = 20
        savings_percentage = 20
    elif monthly_salary > 100000:
        # Higher income - can afford more wants and savings
        needs_percentage = 40
        wants_percentage = 35
        savings_percentage = 25

    total_budget = monthly_salary
    savings_amount = total_budget * (savings_percentage / 100)
    available_for_expenses = total_budget - savings_amount

    # Standard category allocations within needs and wants
    standard_allocations = {
        'food': {'percentage': 15, 'type': 'needs', 'priority': 1},
        'transportation': {'percentage': 10, 'type': 'needs', 'priority': 2},
        'bills': {'percentage': 12, 'type': 'needs', 'priority': 3},
        'healthcare': {'percentage': 8, 'type': 'needs', 'priority': 4},
        'education': {'percentage': 5, 'type': 'needs', 'priority': 5},
        'entertainment': {'percentage': 10, 'type': 'wants', 'priority': 6},
        'shopping': {'percentage': 15, 'type': 'wants', 'priority': 7},
        'other': {'percentage': 5, 'type': 'wants', 'priority': 8},
    }

    budget_breakdown = []
    for category, allocation in standard_allocations.items():
        if allocation['type'] == 'needs':
            amount = available_for_expenses * (allocation['percentage'] / 100)
        else:
            amount = available_for_expenses * (allocation['percentage'] / 100)

        budget_breakdown.append({
            'category': category,
            'category_display': dict(Transaction.CATEGORIES).get(category, category),
            'suggested_amount': round(amount, 2),
            'percentage': allocation['percentage'],
            'type': allocation['type'],
            'priority': allocation['priority']
        })

    return {
        'salary': monthly_salary,
        'budget_breakdown': budget_breakdown,
        'total_budgeted': round(available_for_expenses, 2),
        'savings_amount': round(savings_amount, 2),
        'savings_percentage': savings_percentage,
        'analysis_type': 'standard_ratios',
        'recommendations': [
            f'Allocate ₹{round(savings_amount, 2)} ({savings_percentage}%) of your salary for savings and investments',
            f'Keep essential expenses under ₹{round(available_for_expenses * 0.5, 2)} ({needs_percentage}% of salary)',
            f'Limit non-essential expenses to ₹{round(available_for_expenses * 0.3, 2)} ({wants_percentage}% of salary)',
            'Review and adjust these allocations based on your actual spending patterns'
        ]
    }


def create_ml_enhanced_budget_recommendation(monthly_salary):
    """Create ML-enhanced budget recommendation using advanced algorithms"""
    import numpy as np

    # Advanced ML-based allocation using multiple factors
    # Factor 1: Income-based adjustment using polynomial regression concepts
    income_factor = monthly_salary / 100000  # Normalize to 100k baseline

    # Factor 2: Essential vs Discretionary ratio optimization
    if monthly_salary < 20000:
        # Low income: Maximize essentials, minimize discretionary
        needs_percentage = 65 + (income_factor * 5)  # 65-70%
        wants_percentage = 15 - (income_factor * 2)  # 15-13%
        savings_percentage = 20 + (income_factor * 2)  # 20-22%
    elif monthly_salary < 50000:
        # Middle income: Balanced approach
        needs_percentage = 55 + (income_factor * 3)  # 55-58%
        wants_percentage = 25 + (income_factor * 2)  # 25-27%
        savings_percentage = 20 + (income_factor * 1)  # 20-21%
    else:
        # High income: Can afford more discretionary and savings
        needs_percentage = 45 + (income_factor * 2)  # 45-47%
        wants_percentage = 30 + (income_factor * 3)  # 30-33%
        savings_percentage = 25 + (income_factor * 2)  # 25-27%

    # Ensure percentages sum to 100
    total_pct = needs_percentage + wants_percentage + savings_percentage
    if total_pct != 100:
        # Normalize to ensure sum is 100
        needs_percentage = (needs_percentage / total_pct) * 100
        wants_percentage = (wants_percentage / total_pct) * 100
        savings_percentage = (savings_percentage / total_pct) * 100

    total_budget = monthly_salary
    savings_amount = total_budget * (savings_percentage / 100)
    available_for_expenses = total_budget - savings_amount

    # ML-optimized category allocations using research-based ratios
    ml_allocations = {
        'food': {
            'percentage': max(12, 18 - (income_factor * 2)),  # 12-16% (lower for higher income)
            'type': 'needs',
            'priority': 1,
            'confidence': 0.95
        },
        'transportation': {
            'percentage': min(15, 8 + (income_factor * 3)),  # 8-11% (higher for higher income)
            'type': 'needs',
            'priority': 2,
            'confidence': 0.88
        },
        'bills': {
            'percentage': 15 - (income_factor * 1),  # 15-14% (slightly lower for higher income)
            'type': 'needs',
            'priority': 3,
            'confidence': 0.92
        },
        'healthcare': {
            'percentage': max(8, 12 - (income_factor * 2)),  # 8-10% (lower for higher income)
            'type': 'needs',
            'priority': 4,
            'confidence': 0.85
        },
        'education': {
            'percentage': min(8, 3 + (income_factor * 2)),  # 3-5% (higher for higher income)
            'type': 'needs',
            'priority': 5,
            'confidence': 0.80
        },
        'entertainment': {
            'percentage': max(8, 15 - (income_factor * 3)),  # 8-12% (lower for higher income)
            'type': 'wants',
            'priority': 6,
            'confidence': 0.75
        },
        'shopping': {
            'percentage': min(18, 10 + (income_factor * 4)),  # 10-14% (higher for higher income)
            'type': 'wants',
            'priority': 7,
            'confidence': 0.70
        },
        'other': {
            'percentage': max(3, 8 - (income_factor * 2)),  # 3-6% (lower for higher income)
            'type': 'wants',
            'priority': 8,
            'confidence': 0.65
        },
    }

    budget_breakdown = []
    for category, allocation in ml_allocations.items():
        if allocation['type'] == 'needs':
            amount = available_for_expenses * (allocation['percentage'] / 100)
        else:
            amount = available_for_expenses * (allocation['percentage'] / 100)

        budget_breakdown.append({
            'category': category,
            'category_display': dict(Transaction.CATEGORIES).get(category, category),
            'suggested_amount': round(amount, 2),
            'percentage': round(allocation['percentage'], 2),
            'type': allocation['type'],
            'priority': allocation['priority'],
            'confidence': round(allocation['confidence'] * 100, 1),
            'ml_optimized': True
        })

    # Generate ML-based recommendations
    recommendations = generate_ml_based_recommendations(
        monthly_salary, needs_percentage, wants_percentage, savings_percentage,
        budget_breakdown, income_factor
    )

    return {
        'salary': monthly_salary,
        'budget_breakdown': budget_breakdown,
        'total_budgeted': round(available_for_expenses, 2),
        'savings_amount': round(savings_amount, 2),
        'savings_percentage': round(savings_percentage, 2),
        'needs_percentage': round(needs_percentage, 2),
        'wants_percentage': round(wants_percentage, 2),
        'analysis_type': 'ml_enhanced_standard',
        'ml_confidence': round(np.mean([item['confidence'] for item in budget_breakdown]), 1),
        'recommendations': recommendations
    }


def analyze_with_ml_algorithms(user, monthly_salary, historical_data):
    """Analyze historical data using advanced ML algorithms"""
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    categories = historical_data['categories']
    total_months = historical_data['total_months']

    # Prepare features for ML model
    X = []  # Features
    y = []  # Target (next month prediction)

    for category_data in categories.values():
        # Extract time series data for this category
        monthly_breakdown = historical_data['monthly_breakdown']

        # Create feature matrix
        category_amounts = []
        for month_data in monthly_breakdown.values():
            category_amounts.append(month_data['categories'].get(category_data['category'], 0))

        if len(category_amounts) >= 3:
            # Create lag features (previous months as features)
            for i in range(2, len(category_amounts)):
                features = [
                    category_amounts[i-1],  # Previous month
                    category_amounts[i-2],  # Two months ago
                    np.mean(category_amounts[:i]),  # Historical average
                    np.std(category_amounts[:i]),   # Historical volatility
                    i / total_months,  # Time progression
                ]
                X.append(features)
                y.append(category_amounts[i])  # Current month as target

    # Train ML model if we have enough data
    predictions = {}
    if len(X) >= 5:  # Minimum data for ML
        X = np.array(X)
        y = np.array(y)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train linear regression model
        model = LinearRegression()
        model.fit(X_scaled, y)

        # Make predictions for each category
        for category, category_data in categories.items():
            # Use recent data for prediction
            recent_amounts = []
            for month_data in list(historical_data['monthly_breakdown'].values())[-3:]:
                recent_amounts.append(month_data['categories'].get(category, 0))

            if len(recent_amounts) >= 2:
                # Create feature vector for prediction
                features = [
                    recent_amounts[-1],  # Last month
                    recent_amounts[-2],  # Two months ago
                    np.mean(recent_amounts),  # Recent average
                    np.std(recent_amounts),   # Recent volatility
                    1.0,  # Current time factor
                ]

                # Scale and predict
                features_scaled = scaler.transform([features])
                predicted = max(0, model.predict(features_scaled)[0])

                # Adjust prediction based on salary vs historical spending
                historical_avg = category_data['mean_monthly']
                if monthly_salary >= historical_data['total_avg_monthly']:
                    # Can afford to spend more
                    adjustment_factor = monthly_salary / historical_data['total_avg_monthly']
                    predicted *= adjustment_factor
                else:
                    # Need to cut back
                    adjustment_factor = monthly_salary / historical_data['total_avg_monthly']
                    predicted *= adjustment_factor

                predictions[category] = {
                    'ml_predicted': round(predicted, 2),
                    'confidence': category_data['confidence_score'],
                    'method': 'linear_regression'
                }

    # Fallback to exponential smoothing if ML data insufficient
    budget_breakdown = []
    total_predicted = 0

    for category, category_data in categories.items():
        if category in predictions:
            # Use ML prediction
            suggested_amount = predictions[category]['ml_predicted']
            method = 'ML Prediction'
            confidence = predictions[category]['confidence']
        else:
            # Use exponential smoothing fallback
            alpha = 0.3
            amounts = [month_data['categories'].get(category, 0)
                      for month_data in historical_data['monthly_breakdown'].values()]

            if len(amounts) >= 2:
                smoothed = [amounts[0]]
                for i in range(1, len(amounts)):
                    smoothed_val = alpha * amounts[i] + (1 - alpha) * smoothed[i-1]
                    smoothed.append(smoothed_val)

                # Predict next month with trend adjustment
                last_smoothed = smoothed[-1]
                trend = category_data['trend']
                if trend == 'increasing':
                    predicted = last_smoothed * 1.05
                elif trend == 'decreasing':
                    predicted = last_smoothed * 0.95
                else:
                    predicted = last_smoothed

                suggested_amount = max(0, predicted)
                method = 'Exponential Smoothing'
                confidence = category_data['confidence_score'] * 0.8  # Slightly lower confidence
            else:
                suggested_amount = category_data['mean_monthly']
                method = 'Historical Average'
                confidence = 50.0

        # Adjust for salary constraints
        if monthly_salary < historical_data['total_avg_monthly']:
            reduction_factor = monthly_salary / historical_data['total_avg_monthly']
            suggested_amount *= reduction_factor

        budget_breakdown.append({
            'category': category,
            'category_display': category_data['category_display'],
            'suggested_amount': round(suggested_amount, 2),
            'historical_avg': round(category_data['mean_monthly'], 2),
            'ml_prediction': round(suggested_amount, 2),
            'percentage': round((suggested_amount / monthly_salary) * 100, 2),
            'adjustment': 'salary_adjusted',
            'priority': get_category_priority(category),
            'confidence': round(confidence, 1),
            'method': method,
            'trend': category_data['trend'],
            'volatility': category_data['volatility']
        })

        total_predicted += suggested_amount

    # Calculate savings
    if monthly_salary > total_predicted:
        savings_amount = monthly_salary - total_predicted
        savings_percentage = (savings_amount / monthly_salary) * 100
    else:
        savings_amount = 0
        savings_percentage = 0

    # Generate ML-based recommendations
    recommendations = generate_ml_based_recommendations(
        monthly_salary, total_predicted, savings_amount, budget_breakdown, historical_data
    )

    return {
        'salary': monthly_salary,
        'budget_breakdown': budget_breakdown,
        'total_budgeted': round(total_predicted, 2),
        'savings_amount': round(savings_amount, 2),
        'savings_percentage': round(savings_percentage, 2),
        'historical_avg_monthly': round(historical_data['total_avg_monthly'], 2),
        'analysis_type': 'ml_powered_historical',
        'months_analyzed': total_months,
        'ml_model_used': 'linear_regression' if predictions else 'exponential_smoothing',
        'avg_confidence': round(np.mean([item['confidence'] for item in budget_breakdown]), 1),
        'recommendations': recommendations
    }


def generate_ml_based_recommendations(salary, total_budgeted, savings, budget_breakdown, historical_data=None):
    """Generate ML-based personalized recommendations"""
    recommendations = []

    if savings > 0:
        savings_pct = (savings / salary) * 100
        recommendations.append(
            f'🎯 ML Analysis: You can save ₹{round(savings, 2)} ({round(savings_pct, 1)}%) of your salary based on predicted spending patterns'
        )
    else:
        deficit = abs(savings)
        recommendations.append(
            f'⚠️ ML Warning: Predicted spending (₹{round(total_budgeted, 2)}) may exceed your salary by ₹{round(deficit, 2)}. Consider reducing expenses in volatile categories'
        )

    # ML-specific insights
    high_volatility_categories = [item for item in budget_breakdown if item['volatility'] == 'high']
    if high_volatility_categories:
        categories_str = ", ".join([cat['category_display'] for cat in high_volatility_categories[:2]])
        recommendations.append(
            f'📊 High Volatility Detected: {categories_str} show unpredictable spending patterns. Consider fixed budgets for these categories'
        )

    # Trend-based recommendations
    increasing_trends = [item for item in budget_breakdown if item['trend'] == 'increasing']
    if increasing_trends:
        categories_str = ", ".join([cat['category_display'] for cat in increasing_trends[:2]])
        recommendations.append(
            f'📈 Increasing Trends: {categories_str} spending is rising. Monitor these categories closely'
        )

    # Confidence-based recommendations
    low_confidence = [item for item in budget_breakdown if item['confidence'] < 60]
    if low_confidence:
        recommendations.append(
            f'📚 Limited Data: Some categories have low prediction confidence. Add more transactions for better accuracy'
        )

    # Top spending insights
    top_categories = sorted(budget_breakdown, key=lambda x: x['suggested_amount'], reverse=True)[:3]
    if top_categories:
        top_str = ", ".join([f"{cat['category_display']} (₹{cat['suggested_amount']})" for cat in top_categories])
        recommendations.append(
            f'💡 Top Categories: Focus on {top_str} as they represent your largest expenses'
        )

    # ML model performance insights
    if historical_data and 'analysis_features' in historical_data:
        features = historical_data['analysis_features']
        if features['most_volatile_category']:
            recommendations.append(
                f'🎲 Most Volatile: {features["most_volatile_category"]} category needs closer monitoring due to high spending variation'
            )

    recommendations.extend([
        '🤖 ML Suggestion: Review and adjust predictions monthly as new data becomes available',
        '📱 Pro Tip: Use automatic categorization for consistent and accurate predictions',
        '🎯 Goal Setting: Consider setting financial goals based on these ML-powered insights'
    ])

    return recommendations


def analyze_and_create_budget(user, monthly_salary, historical_data):
    """Analyze historical data and create personalized budget recommendation"""
    total_avg_monthly = historical_data['total_avg_monthly']
    categories = historical_data['categories']

    # Calculate savings as difference between salary and average spending
    if monthly_salary > total_avg_monthly:
        savings_amount = monthly_salary - total_avg_monthly
        savings_percentage = (savings_amount / monthly_salary) * 100
    else:
        # Spending more than salary - need to cut back
        savings_amount = 0
        savings_percentage = 0

    # Create budget breakdown based on historical patterns but adjusted for salary
    budget_breakdown = []

    for category_data in categories.values():
        category = category_data['category']
        avg_monthly = category_data['avg_monthly']
        percentage = category_data['percentage']

        # Adjust amount based on salary vs historical average
        if monthly_salary >= total_avg_monthly:
            # Can afford historical average or slightly more
            suggested_amount = avg_monthly * (monthly_salary / total_avg_monthly)
        else:
            # Need to reduce spending proportionally
            reduction_factor = monthly_salary / total_avg_monthly
            suggested_amount = avg_monthly * reduction_factor

        budget_breakdown.append({
            'category': category,
            'category_display': category_data['category_display'],
            'suggested_amount': round(suggested_amount, 2),
            'historical_avg': round(avg_monthly, 2),
            'percentage': round((suggested_amount / monthly_salary) * 100, 2),
            'adjustment': 'increased' if suggested_amount > avg_monthly else 'decreased',
            'priority': get_category_priority(category)
        })

    # Sort by suggested amount (highest first)
    budget_breakdown.sort(key=lambda x: x['suggested_amount'], reverse=True)

    # Generate personalized recommendations
    recommendations = generate_personalized_recommendations(
        monthly_salary, total_avg_monthly, savings_amount, budget_breakdown
    )

    return {
        'salary': monthly_salary,
        'budget_breakdown': budget_breakdown,
        'total_budgeted': round(sum(item['suggested_amount'] for item in budget_breakdown), 2),
        'savings_amount': round(savings_amount, 2),
        'savings_percentage': round(savings_percentage, 2),
        'historical_avg_monthly': round(total_avg_monthly, 2),
        'analysis_type': 'personalized_historical',
        'months_analyzed': historical_data['months_analyzed'],
        'recommendations': recommendations
    }


def get_category_priority(category):
    """Get priority level for budget categories"""
    priority_map = {
        'food': 1,
        'bills': 2,
        'transportation': 3,
        'healthcare': 4,
        'education': 5,
        'entertainment': 6,
        'shopping': 7,
        'other': 8
    }
    return priority_map.get(category, 8)


def generate_personalized_recommendations(salary, historical_avg, savings, budget_breakdown):
    """Generate personalized budget recommendations"""
    recommendations = []

    if savings > 0:
        recommendations.append(
            f'Great! You can save ₹{round(savings, 2)} ({round((savings/salary)*100, 1)}%) of your salary based on your historical spending patterns'
        )
    else:
        deficit = abs(savings)
        recommendations.append(
            f'Warning: Your historical spending (₹{round(historical_avg, 2)}) exceeds your salary by ₹{round(deficit, 2)}. Consider reducing expenses in high-spending categories'
        )

    # Find top spending categories
    top_categories = sorted(budget_breakdown, key=lambda x: x['suggested_amount'], reverse=True)[:3]

    if top_categories:
        recommendations.append(
            f'Your top spending categories are: {", ".join([cat["category_display"] for cat in top_categories[:3]])}'
        )

    # Check if any category is taking too much of the budget
    for category in budget_breakdown:
        if category['percentage'] > 25:
            recommendations.append(
                f'Consider reviewing your {category["category_display"]} spending - it accounts for {category["percentage"]:.1f}% of your salary'
            )

    recommendations.extend([
        'Track your expenses regularly to stay within budget',
        'Consider setting up automatic transfers to savings',
        'Review and adjust your budget monthly based on actual spending'
    ])

    return recommendations


def get_category_spending_analysis(user, months=12):
    """Analyze spending patterns by category"""
    from datetime import timedelta

    end_date = datetime.now().replace(day=1)
    start_date = end_date - timedelta(days=months*30)  # Look at last N months

    # Get spending by category across the specified period
    category_spending = Transaction.objects.filter(
        user=user,
        transaction_type='expense',
        date__gte=start_date,
        date__lt=end_date
    ).values('category').annotate(
        total_amount=Sum('amount'),
        transaction_count=Count('id')
    ).order_by('-total_amount')

    analysis = []
    total_spent = sum(float(item['total_amount']) for item in category_spending)

    for item in category_spending:
        percentage = (float(item['total_amount']) / total_spent * 100) if total_spent > 0 else 0
        analysis.append({
            'category': item['category'],
            'category_display': dict(Transaction.CATEGORIES).get(item['category'], item['category']),
            'total_amount': float(item['total_amount']),
            'transaction_count': item['transaction_count'],
            'percentage': round(percentage, 2)
        })

    return analysis


def auto_adjust_budgets_for_expense(user, expense_category, expense_amount, expense_date):
    """
    Automatically adjust budgets when user spends money on unbudgeted categories
    or when they overspend their existing budgets.

    Logic:
    1. If expense is in a category without budget → Create budget from other categories
    2. If expense exceeds budget → Reduce other category budgets proportionally
    3. Maintain total budget within income limits

    Returns:
        bool: True if adjustments were made, False otherwise
    """
    adjustments_made = False

    try:
        # Parse expense date
        expense_date_obj = datetime.strptime(expense_date, "%Y-%m-%d").date()

        # Get current month
        current_month = expense_date_obj.replace(day=1)

        # Calculate total income for the month
        total_income = Transaction.objects.filter(
            user=user,
            transaction_type='income',
            date__year=current_month.year,
            date__month=current_month.month
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Get all budgets for the current month
        all_budgets = Budget.objects.filter(
            user=user,
            month=current_month
        )

        # Check if there's already a budget for this expense category
        existing_budget = all_budgets.filter(category=expense_category).first()

        if existing_budget:
            # Check if this expense exceeds the existing budget
            current_expenses = Transaction.objects.filter(
                user=user,
                category=expense_category,
                transaction_type='expense',
                date__year=current_month.year,
                date__month=current_month.month
            ).aggregate(total=Sum('amount'))['total'] or 0

            if current_expenses > existing_budget.amount:
                # Expense exceeds budget - need to adjust
                excess_amount = current_expenses - existing_budget.amount
                adjustments_made = adjust_budgets_for_excess(user, all_budgets, expense_category, excess_amount, total_income)
        else:
            # No budget for this category - need to create budget from other categories
            adjustments_made = create_budget_from_others(user, all_budgets, expense_category, expense_amount, total_income)

        return adjustments_made

    except Exception as e:
        # Log the error but don't interrupt the transaction creation
        print(f"Error in auto_adjust_budgets_for_expense: {str(e)}")
        return False


def adjust_budgets_for_excess(user, all_budgets, expense_category, excess_amount, total_income):
    """
    Adjust other category budgets when expense exceeds budget for a category

    Returns:
        bool: True if adjustments were made, False otherwise
    """
    try:
        # Get budgets excluding the current expense category
        other_budgets = all_budgets.exclude(category=expense_category)

        if not other_budgets.exists():
            # No other budgets to adjust
            return False

        # Calculate total amount available in other budgets
        total_other_budget = other_budgets.aggregate(total=Sum('amount'))['total'] or 0

        if total_other_budget <= 0:
            return False

        # Calculate proportional reduction for each budget
        budgets_adjusted = 0
        for budget in other_budgets:
            reduction_ratio = budget.amount / total_other_budget
            reduction_amount = excess_amount * reduction_ratio

            # Ensure we don't reduce below 0
            new_amount = max(0, budget.amount - reduction_amount)

            # Update the budget
            budget.amount = new_amount
            budget.save()
            budgets_adjusted += 1

        # Log the adjustment (you could also send a notification to the user)
        print(f"Auto-adjusted budgets for user {user.username}: Reduced other category budgets by ₹{excess_amount} to accommodate {expense_category} expense")

        return budgets_adjusted > 0

    except Exception as e:
        print(f"Error adjusting budgets for excess: {str(e)}")
        return False


def create_budget_from_others(user, all_budgets, new_category, required_amount, total_income):
    """
    Create budget for new category by reducing other category budgets proportionally

    Returns:
        bool: True if budget was created, False otherwise
    """
    try:
        budget_created = False

        if not all_budgets.exists():
            # No existing budgets - create new budget if within income limits
            if required_amount <= total_income:
                Budget.objects.create(
                    user=user,
                    category=new_category,
                    amount=required_amount,
                    month=datetime.now().replace(day=1)
                )
                budget_created = True
            return budget_created

        # Calculate total current budgeted amount
        total_budgeted = all_budgets.aggregate(total=Sum('amount'))['total'] or 0

        # Check if we can accommodate the new budget
        if total_budgeted + required_amount > total_income:
            # Need to reduce existing budgets proportionally
            available_for_redistribution = total_income - total_budgeted

            if available_for_redistribution > 0:
                # Reduce existing budgets proportionally to free up space
                budgets_reduced = 0
                for budget in all_budgets:
                    reduction_ratio = budget.amount / total_budgeted
                    reduction_amount = available_for_redistribution * reduction_ratio

                    budget.amount = max(0, budget.amount - reduction_amount)
                    budget.save()
                    budgets_reduced += 1

                # Create new budget with available amount
                Budget.objects.create(
                    user=user,
                    category=new_category,
                    amount=min(required_amount, available_for_redistribution),
                    month=datetime.now().replace(day=1)
                )
                budget_created = True
        else:
            # Enough budget space available - create new budget as is
            Budget.objects.create(
                user=user,
                category=new_category,
                amount=required_amount,
                month=datetime.now().replace(day=1)
            )
            budget_created = True

        print(f"Auto-created budget for {new_category}: ₹{required_amount} for user {user.username}")
        return budget_created

    except Exception as e:
        print(f"Error creating budget from others: {str(e)}")
        return False


@login_required
@require_GET
def get_comprehensive_chart_data(request):
    """API endpoint to get comprehensive chart data for different chart types"""
    try:
        chart_type = request.GET.get('chart_type', 'spending_breakdown')  # 'spending_breakdown', 'income_breakdown', 'savings_trends', 'monthly_trends'
        date_range = request.GET.get('date_range', 'last_12_months')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        # Determine date range
        end_date = timezone.now().date()
        if date_range == 'last_6_months':
            start_date = end_date - timezone.timedelta(days=180)
        elif date_range == 'last_12_months':
            start_date = end_date - timezone.timedelta(days=365)
        elif date_range == 'last_3_months':
            start_date = end_date - timezone.timedelta(days=90)
        elif date_range == 'current_year':
            start_date = end_date.replace(month=1, day=1)
        elif date_range == 'custom' and start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:  # last_12_months default
            start_date = end_date - timezone.timedelta(days=365)

        data = {}

        if chart_type == 'spending_breakdown' or chart_type == 'all':
            # Spending by category
            expense_data = Transaction.objects.filter(
                user=request.user,
                transaction_type='expense',
                date__gte=start_date,
                date__lte=end_date
            ).values('category').annotate(
                total_amount=Sum('amount'),
                transaction_count=Count('id')
            ).order_by('-total_amount')

            spending_analysis = []
            total_expenses = sum(float(item['total_amount']) for item in expense_data)

            for item in expense_data:
                percentage = (float(item['total_amount']) / total_expenses * 100) if total_expenses > 0 else 0
                spending_analysis.append({
                    'category': item['category'],
                    'category_display': dict(Transaction.CATEGORIES).get(item['category'], item['category']),
                    'total_amount': float(item['total_amount']),
                    'transaction_count': item['transaction_count'],
                    'percentage': round(percentage, 2)
                })

            data['spending_breakdown'] = {
                'analysis': spending_analysis,
                'summary': {
                    'total_amount': total_expenses,
                    'total_transactions': sum(item['transaction_count'] for item in expense_data),
                    'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                }
            }

        if chart_type == 'income_breakdown' or chart_type == 'all':
            # Income by category
            income_data = Transaction.objects.filter(
                user=request.user,
                transaction_type='income',
                date__gte=start_date,
                date__lte=end_date
            ).values('category').annotate(
                total_amount=Sum('amount'),
                transaction_count=Count('id')
            ).order_by('-total_amount')

            income_analysis = []
            total_income = sum(float(item['total_amount']) for item in income_data)

            for item in income_data:
                percentage = (float(item['total_amount']) / total_income * 100) if total_income > 0 else 0
                income_analysis.append({
                    'category': item['category'],
                    'category_display': dict(Transaction.CATEGORIES).get(item['category'], item['category']),
                    'total_amount': float(item['total_amount']),
                    'transaction_count': item['transaction_count'],
                    'percentage': round(percentage, 2)
                })

            data['income_breakdown'] = {
                'analysis': income_analysis,
                'summary': {
                    'total_amount': total_income,
                    'total_transactions': sum(item['transaction_count'] for item in income_data),
                    'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                }
            }

        if chart_type == 'savings_trends' or chart_type == 'all':
            # Monthly savings trends (Income - Expenses)
            monthly_savings = []

            # Get all months in the date range
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                month_start = current_date.replace(day=1)
                if current_date.month == 12:
                    month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timezone.timedelta(days=1)
                else:
                    month_end = current_date.replace(month=current_date.month + 1, day=1) - timezone.timedelta(days=1)

                # Calculate income and expenses for this month
                month_income = Transaction.objects.filter(
                    user=request.user,
                    transaction_type='income',
                    date__gte=month_start,
                    date__lte=min(month_end, end_date)
                ).aggregate(total=Sum('amount'))['total'] or 0

                month_expenses = Transaction.objects.filter(
                    user=request.user,
                    transaction_type='expense',
                    date__gte=month_start,
                    date__lte=min(month_end, end_date)
                ).aggregate(total=Sum('amount'))['total'] or 0

                monthly_savings.append({
                    'month': current_date.strftime('%Y-%m'),
                    'month_display': current_date.strftime('%b %Y'),
                    'income': float(month_income),
                    'expenses': float(month_expenses),
                    'savings': float(month_income - month_expenses),
                    'savings_rate': ((month_income - month_expenses) / month_income * 100) if month_income > 0 else 0
                })

                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

            data['savings_trends'] = {
                'monthly_data': monthly_savings,
                'summary': {
                    'total_months': len(monthly_savings),
                    'avg_monthly_savings': sum(item['savings'] for item in monthly_savings) / len(monthly_savings) if monthly_savings else 0,
                    'best_savings_month': max(monthly_savings, key=lambda x: x['savings'])['month_display'] if monthly_savings else 'N/A',
                    'worst_savings_month': min(monthly_savings, key=lambda x: x['savings'])['month_display'] if monthly_savings else 'N/A'
                }
            }

        if chart_type == 'monthly_trends' or chart_type == 'all':
            # Monthly income vs expenses trends
            monthly_trends = []

            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                month_start = current_date.replace(day=1)
                if current_date.month == 12:
                    month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timezone.timedelta(days=1)
                else:
                    month_end = current_date.replace(month=current_date.month + 1, day=1) - timezone.timedelta(days=1)

                month_income = Transaction.objects.filter(
                    user=request.user,
                    transaction_type='income',
                    date__gte=month_start,
                    date__lte=min(month_end, end_date)
                ).aggregate(total=Sum('amount'))['total'] or 0

                month_expenses = Transaction.objects.filter(
                    user=request.user,
                    transaction_type='expense',
                    date__gte=month_start,
                    date__lte=min(month_end, end_date)
                ).aggregate(total=Sum('amount'))['total'] or 0

                monthly_trends.append({
                    'month': current_date.strftime('%Y-%m'),
                    'month_display': current_date.strftime('%b %Y'),
                    'income': float(month_income),
                    'expenses': float(month_expenses),
                    'balance': float(month_income - month_expenses)
                })

                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

            data['monthly_trends'] = {
                'monthly_data': monthly_trends,
                'summary': {
                    'total_months': len(monthly_trends),
                    'avg_monthly_income': sum(item['income'] for item in monthly_trends) / len(monthly_trends) if monthly_trends else 0,
                    'avg_monthly_expenses': sum(item['expenses'] for item in monthly_trends) / len(monthly_trends) if monthly_trends else 0,
                    'profitable_months': len([item for item in monthly_trends if item['balance'] > 0])
                }
            }

        return JsonResponse({
            'data': data,
            'chart_type': chart_type,
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'success': True
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_filtered_chart_data(request):
    """API endpoint to get filtered chart data based on date range and chart type"""
    try:
        # Get filter parameters
        chart_type = request.GET.get('chart_type', 'expense')  # 'expense' or 'income'
        date_range = request.GET.get('date_range', 'current_month')  # 'current_month', 'last_7_days', 'last_30_days', 'last_90_days'
        start_date_str = request.GET.get('start_date')  # Custom date range start (YYYY-MM-DD)
        end_date_str = request.GET.get('end_date')  # Custom date range end (YYYY-MM-DD)

        # Determine date range
        end_date = timezone.now().date()
        if date_range == 'last_7_days':
            start_date = end_date - timezone.timedelta(days=7)
        elif date_range == 'last_30_days':
            start_date = end_date - timezone.timedelta(days=30)
        elif date_range == 'last_90_days':
            start_date = end_date - timezone.timedelta(days=90)
        elif date_range == 'custom' and start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:  # current_month or default
            start_date = end_date.replace(day=1)

        # Get filtered transactions
        transactions = Transaction.objects.filter(
            user=request.user,
            transaction_type=chart_type,
            date__gte=start_date,
            date__lte=end_date
        )

        # Generate category-wise analysis
        category_analysis = transactions.values('category').annotate(
            total_amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total_amount')

        analysis_data = []
        total_amount = sum(float(item['total_amount']) for item in category_analysis)

        for item in category_analysis:
            percentage = (float(item['total_amount']) / total_amount * 100) if total_amount > 0 else 0
            analysis_data.append({
                'category': item['category'],
                'category_display': dict(Transaction.CATEGORIES).get(item['category'], item['category']),
                'total_amount': float(item['total_amount']),
                'transaction_count': item['transaction_count'],
                'percentage': round(percentage, 2)
            })

        # Get summary statistics
        summary = {
            'total_amount': total_amount,
            'total_transactions': transactions.count(),
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'chart_type': chart_type,
            'avg_transaction': total_amount / transactions.count() if transactions.count() > 0 else 0
        }

        return JsonResponse({
            'category_analysis': analysis_data,
            'summary': summary,
            'success': True
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
