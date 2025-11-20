from django.urls import path
from . import views

app_name = 'user'  # 👈 VERY IMPORTANT!

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('edit-transaction/<int:transaction_id>/', views.edit_transaction, name='edit_transaction'),
    path('delete-transaction/<int:transaction_id>/', views.delete_transaction, name='delete_transaction'),
    path('budget/', views.budget_management, name='budget_management'),
    path('budget-prediction/', views.budget_prediction, name='budget_prediction'),
    path('ai-financial-insights/', views.ai_financial_insights, name='ai_financial_insights'),
    path('api/income-budget-data/', views.get_income_budget_data, name='income_budget_data'),
    path('api/spending-insights/', views.get_spending_insights, name='spending_insights'),
    path('api/budget-suggestions/', views.get_budget_suggestions, name='budget_suggestions'),
    path('api/budget-prediction/', views.get_budget_prediction, name='budget_prediction'),
    path('ai-chat-api/', views.ai_chat_api, name='ai_chat_api'),
    path('api/filtered-chart-data/', views.get_filtered_chart_data, name='filtered_chart_data'),
    path('api/comprehensive-chart-data/', views.get_comprehensive_chart_data, name='comprehensive_chart_data'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
