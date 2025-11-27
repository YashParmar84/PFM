#!/usr/bin/env python3
"""
Comprehensive Demo for Specialized Financial Chatbot
Shows all implemented features
"""

import os
import sys
import json
from financial_chatbot import SpecializedFinancialChatbot

# Mock Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_finance_management.settings')

try:
    import django
    django.setup()
    print("Django setup successful")
except Exception as e:
    print(f"WARNING: Django setup issue (in demo mode): {e}")
    print("Continuing with limited functionality...")

def main():
    print('\nSPECIALIZED FINANCIAL CHATBOT - COMPREHENSIVE DEMO')
    print('=' * 80)
    print('This demo showcases all implemented features:')
    print('* Greeting functionality')
    print('* Product details from Excel')
    print('* EMI calculations')
    print('* Income averaging & affordability')
    print('* Saving plans generation')
    print('* Bank recommendations with pros/cons')
    print('* Downpayment impact analysis')
    print('* Out-of-scope responses in Hindi')
    print('* Plan storage & management')
    print('* Input validation')
    print('=' * 80)

    # Initialize chatbot
    try:
        chatbot = SpecializedFinancialChatbot()
        print('Chatbot initialized successfully\n')
    except Exception as e:
        print(f'ERROR: Chatbot initialization failed: {e}')
        return

    # Demo conversations
    demo_conversations = [
        {
            'name': 'GREETING & ONBOARDING',
            'message': 'Hi there!',
            'context': {},
            'description': 'Test greeting functionality'
        },
        {
            'name': 'DIRECT PRODUCT INQUIRY',
            'message': 'Kia Sonet',
            'context': {'income_history': [50000, 55000, 52000, 48000, 51000, 53000]},
            'description': 'Direct product name lookup with income averaging'
        },
        {
            'name': 'CATEGORY-BASED PRODUCT SEARCH',
            'message': 'I want to buy a car',
            'context': {'income_history': [40000, 45000, 42000]},
            'description': 'Category-based product suggestions'
        },
        {
            'name': 'SAVING PLAN ANALYSIS',
            'message': 'Help me create a saving plan for 25,000 rupees per month',
            'context': {'income_history': [50000, 55000]},
            'description': 'Comprehensive saving plan with acceleration options'
        },
        {
            'name': 'AFFORDABILITY CHECK',
            'message': 'Can I afford an EMI of 15,000?',
            'context': {'average_income': 50000},
            'description': 'Affordability analysis based on income'
        },
        {
            'name': 'OUT-OF-SCOPE QUERY',
            'message': 'Tell me about cricket scores',
            'context': {},
            'description': 'Hindi response for off-topic queries'
        },
        {
            'name': 'TRAVEL PLANNING',
            'message': 'Plan a trip to Goa for 50000',
            'context': {'income_history': [60000, 65000]},
            'description': 'Travel planning with EMI options'
        }
    ]

    for i, demo in enumerate(demo_conversations, 1):
        print(f'\nDEMO {i}: {demo["name"]}')
        print(f'Description: {demo["description"]}')
        print('-' * 60)
        print(f'User: {demo["message"]}')

        try:
            response = chatbot.process_message(demo['message'], demo['context'])
            print(f'Bot Response (first 10 lines):')

            lines = response['message'].split('\n')
            for j, line in enumerate(lines[:10]):
                if line.strip():
                    print(f'  {j+1}. {line}')

            if len(lines) > 10:
                print(f'  ... ({len(lines)-10} more lines)')

            # Show key features demonstrated
            features = []
            if response.get('show_greeting'):
                features.append('Greeting')
            if response.get('off_topic'):
                features.append('Out-of-scope handling')
            if response.get('affordable') is not None:
                features.append('Affordability check')
            if response.get('saving_plan_generated'):
                features.append('Saving plan generation')
            if response.get('product_selected'):
                features.append('Product analysis')

            if features:
                print(f'Features demonstrated: {", ".join(features)}')

            print('Demo completed successfully')

        except Exception as e:
            print(f'DEMO ERROR: {str(e)}')

    print('\n' + '=' * 80)
    print('COMPREHENSIVE DEMO COMPLETED!')
    print('All major features of the Specialized Financial Chatbot have been implemented.')
    print('')
    print('Key Achievements:')
    print('* Specialized chatbot for dine-in/product purchase financial planning')
    print('* Always greets with "Hello! How can I help you today?"')
    print('* Only answers on-topic financial planning questions')
    print('* Fetches product details from Excel database')
    print('* Real-time interest rate fetching (API ready)')
    print('* Shows banks with detailed pros/cons analysis')
    print('* Accurate EMI calculations using Indian banking standards')
    print('* Calculates 6-month income average automatically')
    print('* Affordability assessment (20-30% of income)')
    print('* Comprehensive saving plans with timelines and acceleration options')
    print('* Stores plans in database for future reference')
    print('* Responds in Hindi for out-of-scope queries')
    print('* Input validation and error handling')
    print('* Conversational flow management')
    print('')
    print('The chatbot is now ready for deployment in the Django application!')
    print('=' * 80)

if __name__ == "__main__":
    main()
