#!/usr/bin/env python
# Comprehensive debugging script for AI Chat API issues
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('c:\\Users\\Yash Parmar\\OneDrive\\Desktop\\PFMfinal\\PFM')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_finance_management.settings')

django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from user.views import ai_chat_api, generate_financial_plans
import json

print("🔧 AI Chat API - Comprehensive Testing (Including Plan Generation)")
print("=" * 60)

# Test 1: Check if we can import all modules
try:
    from user.models import Transaction, LoanProduct, AIConsultation, Budget, UserProfile
    from django.contrib.auth.decorators import login_required
    from django.http import JsonResponse
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")

# Test 2: Check JSON serialization
try:
    test_data = {"message": "test", "selected_item_id": None}
    json_str = json.dumps(test_data)
    parsed = json.loads(json_str)
    print("✅ JSON serialization working")
except Exception as e:
    print(f"❌ JSON error: {e}")

# Test 3: Test Plan Generation for ALL categories
print("\n🏗️ Testing Plan Generation for ALL Loan Types")
print("=" * 50)

# Mock income for testing
test_income = 75000

# Create mock objects for each category
test_items = [
    {
        "category": "four_wheeler",
        "model_name": "Honda City",
        "price": 1500000,
        "emi": 25000,
        "display": "Four Wheeler Loan"
    },
    {
        "category": "two_wheeler",
        "model_name": "Hero Splendor",
        "price": 80000,
        "emi": 2500,
        "display": "Two Wheeler Loan"
    },
    {
        "category": "personal_loan",
        "model_name": "Personal Loan",
        "price": 500000,
        "emi": 11000,
        "display": "Personal Loan"
    },
    {
        "category": "gold_loan",
        "model_name": "Gold Loan",
        "price": 200000,
        "emi": 8800,
        "display": "Gold Loan"
    },
    {
        "category": "electronics",
        "model_name": "Laptop",
        "price": 100000,
        "emi": 3500,
        "display": "Electronics Loan"
    },
    {
        "category": "home_loan",
        "model_name": "Home Loan",
        "price": 3000000,
        "emi": 28000,
        "display": "Home Loan"
    }
]

for item_data in test_items:
    print(f"\n🧪 Testing {item_data['display']} - {item_data['model_name']}")

    # Create a mock item object
    class MockItem:
        def __init__(self, data):
            self.category = data["category"]
            self.model_name = data["model_name"]
            self.price = data["price"]
            self.emi = data["emi"]

        def get_category_display(self):
            return item_data["display"]

    mock_item = MockItem(item_data)

    try:
        plans = generate_financial_plans(test_income, mock_item)

        if plans:
            print(f"  ✅ Generated {len(plans)} plans")
            # Show top 2 plans
            for i, plan in enumerate(plans[:2]):
                print(f"    Plan {i+1}: {plan['name']}")
                print(f"      • EMI: ₹{plan['emi']:.0f}, Tenure: {plan['tenure_months']} months")
                print(f"      • Affordability: {plan['affordability_score']}/10")
                print(f"      • EMI/Income: {plan['emi_to_income_ratio']:.1f}%")
        else:
            print(f"  ❌ No plans generated!")

    except Exception as e:
        print(f"  ❌ Error: {e}")

# Test 4: Check function calls
try:
    from user.views import generate_ai_response, generate_fallback_response

    print("\n🧪 Testing generate_fallback_response...")
    fallback_result = generate_fallback_response("test", test_income, None, 7.5, "test error")
    print("✅ generate_fallback_response works")

    print("\n🧪 Testing generate_ai_response...")
    ai_result = generate_ai_response("test message", test_income, None, {})
    print("✅ generate_ai_response works")

except Exception as e:
    print(f"❌ Function error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Django request simulation
try:
    print("\n🌐 Simulating Django request...")
    factory = RequestFactory()

    # Create test user
    test_user = User(id=1, username='test')

    # Create request with test data
    test_data = {"message": "Test financial question", "selected_item_id": None}
    json_data = json.dumps(test_data)

    request = factory.post('/user/ai-chat-api/', data=json_data, content_type='application/json')
    request.user = test_user

    print("✅ Django request creation successful")
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"JSON data: {test_data}")

    # Test the actual view (this will fail due to auth but should give us clues)
    print("\n🚀 Calling ai_chat_api view...")
    try:
        response = ai_chat_api(request)
        print(f"Response status: {response.status_code}")
        print(f"Response content type: {type(response)}")
        if hasattr(response, 'content'):
            print(f"Response content preview: {response.content[:200]}")
    except Exception as e:
        print(f"🚨 View execution error: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"❌ Django request simulation error: {e}")

print("\n📋 Summary of checks completed")
print("To debug the actual 500 error, we need the full Django traceback from server logs.")
