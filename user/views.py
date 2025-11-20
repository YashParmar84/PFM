from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta
from django.db.models import Sum
from user.models import Transaction, LoanProduct, AIConsultation, Budget, UserProfile


@login_required
def ai_financial_insights(request):
    """View for AI Financial Insights page"""
    # Get user's income data for last 6 months
    six_months_ago = datetime.now() - timedelta(days=180)
    
    income_transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type='income',
        date__gte=six_months_ago
    ).order_by('-date')
    
    # Calculate average monthly income
    monthly_income = {}
    for transaction in income_transactions:
        month_key = f"{transaction.date.year}-{transaction.date.month}"
        if month_key not in monthly_income:
            monthly_income[month_key] = 0
        monthly_income[month_key] += float(transaction.amount)
    
    average_monthly_income = sum(monthly_income.values()) / len(monthly_income) if monthly_income else 0
    
    # Get available loan products
    loan_products = LoanProduct.objects.all()
    
    # Get consultation history
    consultations = AIConsultation.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'average_monthly_income': average_monthly_income,
        'loan_products': loan_products,
        'consultations': consultations,
        'monthly_income_data': json.dumps(monthly_income)
    }
    
    return render(request, 'user/ai_financial_insights.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def ai_chat_api(request):
    """API endpoint for AI chat with financial insights"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        selected_item_id = data.get('selected_item_id')
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Get user's income data for last 6 months
        six_months_ago = datetime.now() - timedelta(days=180)
        
        income_transactions = Transaction.objects.filter(
            user=request.user,
            transaction_type='income',
            date__gte=six_months_ago
        )
        
        # Calculate average monthly income
        monthly_income = {}
        for transaction in income_transactions:
            month_key = f"{transaction.date.year}-{transaction.date.month}"
            if month_key not in monthly_income:
                monthly_income[month_key] = 0
            monthly_income[month_key] += float(transaction.amount)
        
        average_monthly_income = sum(monthly_income.values()) / len(monthly_income) if monthly_income else 0
        
        # Get selected loan product if provided
        selected_item = None
        if selected_item_id:
            selected_item = get_object_or_404(LoanProduct, id=selected_item_id)
        
        # Generate AI response using DeepSeek API
        ai_response = generate_ai_response(user_message, average_monthly_income, selected_item, monthly_income)
        
        # If we have a selected item, save the consultation
        if selected_item:
            consultation = AIConsultation.objects.create(
                user=request.user,
                selected_item=selected_item,
                user_income=average_monthly_income,
                ai_recommendation=ai_response['recommendation'],
                affordability_score=ai_response['affordability_score'],
                recommended_banks=ai_response['recommended_banks'],
                risk_assessment=ai_response['risk_assessment']
            )
        
        return JsonResponse({
            'reply': ai_response['message'],
            'item_details': {
                'name': selected_item.model_name if selected_item else None,
                'price': float(selected_item.price) if selected_item else None,
                'emi': float(selected_item.emi) if selected_item else None,
                'bank': selected_item.bank_name if selected_item else None
            } if selected_item else None,
            'affordability_analysis': ai_response.get('affordability_analysis', {})
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def generate_ai_response(user_message, average_monthly_income, selected_item, monthly_income):
    """Generate AI response using DeepSeek API"""
    try:
        import requests
        
        # Prepare context for DeepSeek API
        context = f"""
        You are a financial advisor AI. User's average monthly income: ₹{average_monthly_income:.2f}
        User's recent income pattern: {monthly_income}
        
        """
        
        if selected_item:
            context += f"""
            User is asking about: {selected_item.model_name}
            Item Price: ₹{float(selected_item.price):,.2f}
            Monthly EMI: ₹{float(selected_item.emi):,.2f}
            Bank: {selected_item.bank_name}
            Interest Rate: {float(selected_item.interest_rate)}% p.a.
            Tenure: {selected_item.tenure_months} months
            """
        
        # Calculate affordability
        affordability_score = 0
        recommended_banks = []
        risk_assessment = ""
        
        if selected_item:
            emi = float(selected_item.emi)
            income = average_monthly_income
            
            # EMI should not exceed 30% of monthly income
            emi_ratio = (emi / income) * 100 if income > 0 else 100
            
            if emi_ratio <= 20:
                affordability_score = 9.0
                risk_assessment = "Excellent - This EMI is very manageable and won't strain your budget."
            elif emi_ratio <= 30:
                affordability_score = 7.5
                risk_assessment = "Good - This EMI is within acceptable limits but monitor your other expenses."
            elif emi_ratio <= 40:
                affordability_score = 5.0
                risk_assessment = "Caution - This EMI might strain your budget. Consider a longer tenure or larger down payment."
            else:
                affordability_score = 2.0
                risk_assessment = "High Risk - This EMI exceeds recommended limits. Not advisable at current income level."
            
            # Get other banks with lower EMI for same item
            similar_items = LoanProduct.objects.filter(
                item_id=selected_item.item_id,
                category=selected_item.category
            ).order_by('emi')
            
            recommended_banks = []
            for item in similar_items[:3]:
                recommended_banks.append({
                    'bank': item.bank_name,
                    'emi': float(item.emi),
                    'rate': float(item.interest_rate)
                })
        
        # Prepare DeepSeek API request
        headers = {
            'Authorization': 'Bearer c5f7fc0363629ac6cd1692451463845f74d3a64b774d41e04d5ad1ac2189c85c',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful financial advisor AI specializing in loan recommendations and financial planning. Provide practical, personalized advice based on the user's financial situation."
                },
                {
                    "role": "user", 
                    "content": f"{context}\n\nUser Question: {user_message}\n\nProvide a helpful, personalized response."
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            ai_message = response.json()['choices'][0]['message']['content']
        else:
            ai_message = "I apologize, but I'm having trouble connecting to my AI service right now. Please try again in a moment."
            
    except Exception as e:
        # Fallback response without API
        ai_message = generate_fallback_response(user_message, average_monthly_income, selected_item, affordability_score, risk_assessment)
    
    return {
        'message': ai_message,
        'recommendation': f"Based on your income of ₹{average_monthly_income:.2f}/month, {selected_item.model_name if selected_item else 'this purchase'} has an affordability score of {affordability_score}/10." if selected_item else "Here's your financial analysis:",
        'affordability_score': affordability_score,
        'recommended_banks': recommended_banks,
        'risk_assessment': risk_assessment,
        'affordability_analysis': {
            'monthly_income': average_monthly_income,
            'emi': float(selected_item.emi) if selected_item else 0,
            'emi_percentage': ((float(selected_item.emi) / average_monthly_income) * 100) if selected_item and average_monthly_income > 0 else 0
        } if selected_item else {}
    }


def generate_fallback_response(user_message, average_monthly_income, selected_item, affordability_score, risk_assessment):
    """Generate fallback response when API is unavailable"""
    if selected_item:
        emi = float(selected_item.emi)
        return f"""
        Based on your average monthly income of ₹{average_monthly_income:.2f}, here's my analysis of the {selected_item.model_name}:

        💰 **Financial Analysis:**
        • Item Price: ₹{float(selected_item.price):,.2f}
        • Monthly EMI: ₹{emi:.2f}
        • EMI as % of Income: {(emi/average_monthly_income*100):.1f}%

        📊 **Affordability Score: {affordability_score}/10**

        ⚠️ **Risk Assessment:** {risk_assessment}

        💡 **Recommendations:**
        • Consider this {"✅ Good choice" if affordability_score >= 7 else "⚠️ Proceed with caution"}
        • Your EMI should ideally not exceed 30% of monthly income
        • {"This fits well within your budget" if emi/average_monthly_income <= 0.3 else "Consider a larger down payment or longer tenure"}

        Would you like me to show you alternative options from other banks?
        """
    else:
        return f"""
        Based on your average monthly income of ₹{average_monthly_income:.2f}, I can help you find suitable financial products.

        I can assist you with:
        • Analyzing your affordability for various purchases
        • Comparing loan options from different banks
        • Providing personalized financial recommendations
        • Suggesting budget-friendly alternatives

        What specific purchase are you considering? I can help you evaluate if it fits your budget!
        """


# Additional views for existing functionality
def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('user:dashboard')
    return render(request, 'user/home.html')


@login_required
def dashboard(request):
    """User dashboard view"""
    six_months_ago = datetime.now() - timedelta(days=180)
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-date')[:10]
    
    # Calculate income and expenses for current month
    current_month = datetime.now().replace(day=1)
    current_month_transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=current_month
    )
    
    monthly_income = sum(float(t.amount) for t in current_month_transactions if t.transaction_type == 'income')
    monthly_expenses = sum(float(t.amount) for t in current_month_transactions if t.transaction_type == 'expense')
    
    # Get budget data
    budgets = Budget.objects.filter(user=request.user, month__gte=six_months_ago)
    
    context = {
        'recent_transactions': recent_transactions,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'net_savings': monthly_income - monthly_expenses,
        'budgets': budgets,
    }
    
    return render(request, 'user/dashboard.html', context)


@login_required
def add_transaction(request):
    """Add new transaction view"""
    if request.method == 'POST':
        # Transaction creation logic here
        pass
    return render(request, 'user/add_transaction.html')


@login_required
def transaction_list(request):
    """Transaction list view"""
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    return render(request, 'user/transaction_list.html', {'transactions': transactions})


@login_required
def edit_transaction(request, transaction_id):
    """Edit transaction view"""
    # Transaction editing logic here
    pass


@login_required
def delete_transaction(request, transaction_id):
    """Delete transaction view"""
    # Transaction deletion logic here
    pass


@login_required
def budget_management(request):
    """Budget management view"""
    return render(request, 'user/budget_management.html')


@login_required
def budget_prediction(request):
    """Budget prediction view"""
    return render(request, 'user/budget_prediction.html')


# API Views for existing functionality
@login_required
def get_income_budget_data(request):
    """API to get income and budget data"""
    # Calculate user's income and expenses
    six_months_ago = datetime.now() - timedelta(days=180)
    
    income_transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type='income',
        date__gte=six_months_ago
    )
    
    expense_transactions = Transaction.objects.filter(
        user=request.user,
        transaction_type='expense',
        date__gte=six_months_ago
    )
    
    total_income = sum(float(t.amount) for t in income_transactions)
    total_expenses = sum(float(t.amount) for t in expense_transactions)
    
    # Category breakdown
    expense_by_category = {}
    for transaction in expense_transactions:
        category = transaction.get_category_display()
        expense_by_category[category] = expense_by_category.get(category, 0) + float(transaction.amount)
    
    return JsonResponse({
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': total_income - total_expenses,
        'expense_breakdown': expense_by_category
    })


@login_required
def get_spending_insights(request):
    """API to get spending insights"""
    # Generate financial goals and insights
    return JsonResponse({
        'financial_goals': [
            {
                'name': 'Emergency Fund',
                'current_amount': 25000,
                'target_amount': 100000,
                'progress_percentage': 25.0,
                'priority': 'High'
            },
            {
                'name': 'Vacation Fund',
                'current_amount': 15000,
                'target_amount': 50000,
                'progress_percentage': 30.0,
                'priority': 'Medium'
            }
        ],
        'spending_insights': 'Your spending patterns show room for optimization in the entertainment category.'
    })


@login_required
def get_budget_suggestions(request):
    """API to get budget suggestions"""
    return JsonResponse({
        'suggestions': [
            {
                'category': 'Food & Dining',
                'type': 'decrease',
                'reason': 'You spent 25% more than budget this month',
                'confidence': 85,
                'suggested_budget': 8000
            },
            {
                'category': 'Transportation',
                'type': 'increase',
                'reason': 'Recent trends show increased travel costs',
                'confidence': 70,
                'suggested_budget': 6000
            }
        ]
    })


@login_required
def get_budget_prediction(request):
    """API to get budget predictions"""
    return JsonResponse({
        'predictions': 'Based on your spending patterns, we predict a 10% increase in discretionary spending next month.',
        'confidence': 78
    })


@login_required
def get_filtered_chart_data(request):
    """API to get filtered chart data"""
    chart_type = request.GET.get('chart_type', 'spending_breakdown')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Return sample chart data based on type
    if chart_type == 'spending_breakdown':
        return JsonResponse({
            'chart_data': {
                'labels': ['Food', 'Transport', 'Shopping', 'Entertainment'],
                'data': [15000, 8000, 12000, 5000]
            }
        })
    else:
        return JsonResponse({'chart_data': {'labels': [], 'data': []}})


@login_required
def get_comprehensive_chart_data(request):
    """API to get comprehensive chart data with proper structure"""
    chart_type = request.GET.get('chart_type', 'spending_breakdown')
    date_range = request.GET.get('date_range', 'last_6_months')
    
    # Get user's transaction data for the last 6 months
    if date_range == 'last_3_months':
        days_ago = 90
    elif date_range == 'last_6_months':
        days_ago = 180
    elif date_range == 'last_12_months':
        days_ago = 365
    else:
        days_ago = 180
    
    start_date = datetime.now() - timedelta(days=days_ago)
    
    # Get transactions
    transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date
    )
    
    # Build comprehensive chart data
    chart_data = {
        'spending_breakdown': {
            'analysis': [],
            'summary': {'total_amount': 0}
        },
        'income_breakdown': {
            'analysis': [],
            'summary': {'total_amount': 0}
        },
        'savings_trends': {
            'monthly_data': []
        },
        'monthly_trends': {
            'monthly_data': []
        }
    }
    
    # Calculate spending breakdown
    expense_transactions = transactions.filter(transaction_type='expense')
    spending_by_category = {}
    
    for transaction in expense_transactions:
        category = transaction.get_category_display()
        spending_by_category[category] = spending_by_category.get(category, 0) + float(transaction.amount)
    
    total_spending = sum(spending_by_category.values())
    
    for category, amount in spending_by_category.items():
        chart_data['spending_breakdown']['analysis'].append({
            'category': category,
            'category_display': category,
            'total_amount': amount
        })
    
    chart_data['spending_breakdown']['summary']['total_amount'] = total_spending
    
    # Calculate income breakdown
    income_transactions = transactions.filter(transaction_type='income')
    income_by_category = {}
    
    for transaction in income_transactions:
        category = transaction.get_category_display()
        income_by_category[category] = income_by_category.get(category, 0) + float(transaction.amount)
    
    total_income = sum(income_by_category.values())
    
    for category, amount in income_by_category.items():
        chart_data['income_breakdown']['analysis'].append({
            'category': category,
            'category_display': category,
            'total_amount': amount
        })
    
    chart_data['income_breakdown']['summary']['total_amount'] = total_income
    
    # Generate monthly data for trends
    for i in range(min(12, days_ago // 30 + 1)):
        month_date = datetime.now() - timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_transactions = transactions.filter(date__range=[month_start, month_end])
        
        month_income = sum(float(t.amount) for t in month_transactions if t.transaction_type == 'income')
        month_expenses = sum(float(t.amount) for t in month_transactions if t.transaction_type == 'expense')
        month_savings = month_income - month_expenses
        
        chart_data['savings_trends']['monthly_data'].append({
            'month': month_start.strftime('%Y-%m'),
            'month_display': month_start.strftime('%b %Y'),
            'income': month_income,
            'expenses': month_expenses,
            'savings': month_savings
        })
        
        chart_data['monthly_trends']['monthly_data'].append({
            'month': month_start.strftime('%Y-%m'),
            'month_display': month_start.strftime('%b %Y'),
            'income': month_income,
            'expenses': month_expenses,
            'balance': month_savings
        })
    
    # Reverse the monthly data to show oldest first
    chart_data['savings_trends']['monthly_data'].reverse()
    chart_data['monthly_trends']['monthly_data'].reverse()
    
    return JsonResponse({'data': chart_data})


@login_required
def ai_chat_response(request):
    """Legacy AI chat response (if needed)"""
    return JsonResponse({'response': 'Legacy response'})


# User authentication views
def register(request):
    """User registration view"""
    if request.method == 'POST':
        from django.contrib.auth.models import User
        from django.contrib import messages
        
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return render(request, 'user/register.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'user/register.html')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'user/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'user/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'user/register.html')
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        messages.success(request, 'Account created successfully! You can now log in.')
        return redirect('user:login')
    
    return render(request, 'user/register.html')


def user_login(request):
    """User login view"""
    if request.method == 'POST':
        from django.contrib.auth import authenticate, login
        from django.contrib import messages
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('user:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please enter both username and password.')
    
    return render(request, 'user/login.html')


def user_logout(request):
    """User logout view"""
    from django.contrib.auth import logout
    logout(request)
    return redirect('user:home')
