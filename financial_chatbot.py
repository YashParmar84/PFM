"""
Specialized Financial Planning Chatbot
Handles product purchase planning, EMI calculations, affordability checks, and saving plans.
"""

import json
import requests
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import math
import random
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.models import User
from django.conf import settings
from user.models import SavedPlan

class SpecializedFinancialChatbot:
    """Specialized chatbot for financial planning with product analysis"""

    def __init__(self):
        # Load Excel data
        self.excel_file = 'loan_products_and_rates_for_chatbot.xlsx'
        self.load_excel_data()

        # Initialize Groq API client for enhanced NLP capabilities
        self.groq_api_key = getattr(settings, 'GROQ_API_KEY', None)
        self.enable_nlp_enhancement = bool(self.groq_api_key)
        print(f"Groq NLP Enhancement: {'Enabled' if self.enable_nlp_enhancement else 'Disabled'}")

        # Fallback interest rates (used when Excel data is not available)
        self.fallback_rates = {
            'four_wheeler': 9.0,
            'two_wheeler': 9.0,
            'electronics': 12.0,
            'home_loan': 8.0,
            'personal_loan': 10.0,
            'gold_loan': 8.5,
            'travel': 10.0,
            'hospitality': 10.0
        }

        # Bank options for fallbacks
        self.bank_options = [
            {'name': 'State Bank of India', 'rate_adjustment': 0.0},
            {'name': 'HDFC Bank', 'rate_adjustment': 0.25},
            {'name': 'ICICI Bank', 'rate_adjustment': 0.15},
            {'name': 'Kotak Mahindra Bank', 'rate_adjustment': 0.20},
            {'name': 'Axis Bank', 'rate_adjustment': 0.10}
        ]

        # Product categories and keywords for detection
        self.product_keywords = {
            'home_loan': ['house', 'home', 'apartment', 'property', 'flat', 'villa', 'real estate', 'realestate'],
            'personal_loan': ['personal loan', 'personal finance', 'education', 'marriage'],
            'gold_loan': ['gold loan', 'gold finance', 'gold jewelry', 'ornament'],
            'two_wheeler': ['bike', 'scooter', 'motorcycle', 'two wheeler', 'moped'],
            'four_wheeler': ['car', 'automobile', 'vehicle', 'suv', 'sedan'],
            'electronics': ['laptop', 'phone', 'mobile', 'tv', 'computer', 'electronics', 'smartphone', 'tablet', 'ac', 'refrigerator', 'electronic items', 'gadgets', 'devices', 'camera', 'fridge'],
            'travel': ['vacation', 'holiday', 'trip', 'travel', 'tour'],
            'hospitality': ['hotel', 'resort', 'stays', 'accommodation', 'hospitality']
        }

        # Allowed domains mapping
        self.allowed_domains = {
            'product_purchase': ['buy', 'purchase', 'loan', 'finance', 'emi', 'installment'],
            'saving_plans': ['save', 'saving', 'savings', 'plan', 'budget', 'timeline'],
            'affordability': ['afford', 'budget', 'income', 'salary', 'cost', 'expenses'],
            'travel': ['travel', 'vacation', 'holiday', 'trip', 'tour'],
            'hospitality': ['hotel', 'resort', 'stay', 'accommodation']
        }

        # Mapping from Excel categories to chatbot categories
        self.category_mapping = {
            'four_wheeler': 'Cars',
            'two_wheeler': 'Bikes',
            'electronics': 'Electronics',
            'home_loan': 'HomeLoan',
            'personal_loan': 'PersonalLoan',
            'gold_loan': 'GoldLoan'
        }

        # Conversation state tracking (will be per user in Django)
        self.conversation_states = {}

        # Initialize conversation history
        self.conversation_history = {}



    def load_excel_data(self):
        """Load data from Excel file"""
        try:
            self.cars_df = pd.read_excel(self.excel_file, sheet_name='Cars')
            self.bikes_df = pd.read_excel(self.excel_file, sheet_name='Bikes')
            self.electronics_df = pd.read_excel(self.excel_file, sheet_name='Electronics')
            self.banks_rates_df = pd.read_excel(self.excel_file, sheet_name='Banks_and_Rates')

            # Convert price columns to float
            for df in [self.cars_df, self.bikes_df, self.electronics_df]:
                df['Approx_Price_INR'] = pd.to_numeric(df['Approx_Price_INR'], errors='coerce')

            # Convert bank rate columns to float
            rate_columns = [col for col in self.banks_rates_df.columns if col.endswith('_Start_%')]
            for col in rate_columns:
                self.banks_rates_df[col] = pd.to_numeric(self.banks_rates_df[col], errors='coerce')

            print("Excel data loaded successfully!")

        except Exception as e:
            print(f"Error loading Excel data: {e}")
            # Set empty DataFrames as fallback
            self.cars_df = pd.DataFrame()
            self.bikes_df = pd.DataFrame()
            self.electronics_df = pd.DataFrame()
            self.banks_rates_df = pd.DataFrame()

    def _is_on_topic(self, question: str) -> bool:
        """Check if question is within allowed domains"""
        question_lower = question.lower()

        # Check for product keywords
        for category, keywords in self.product_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return True

        # Check for domain keywords
        for domain, keywords in self.allowed_domains.items():
            if any(keyword in question_lower for keyword in keywords):
                return True

        return False

    def _detect_product_category(self, question: str) -> Optional[str]:
        """Detect product category from question"""
        question_lower = question.lower()

        for category, keywords in self.product_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return category

        return None

    def _detect_category_from_product_name(self, question: str) -> Optional[str]:
        """Enhanced category detection: Check if message contains actual product names from our database"""
        question_lower = question.lower()

        # Search through all categories for product matches
        all_categories = ['four_wheeler', 'two_wheeler', 'electronics', 'home_loan', 'personal_loan', 'gold_loan', 'travel', 'hospitality']

        for category in all_categories:
            suggestions = self._get_product_suggestions(category)
            for product in suggestions:
                product_name_lower = product['name'].lower()
                # Check for exact match or if product name is contained in question
                if product_name_lower in question_lower or question_lower in product_name_lower:
                    return category

        return None

    def _extract_product_price(self, question: str) -> Optional[float]:
        """Extract product price from question"""
        # Look for patterns like ₹50,000, Rs. 50000, 50000 rupees, etc.
        patterns = [
            r'[₹rs\.]*\b(\d+(?:,\d+)*)\b.*?(?:rupees|rs|inr)?',
            r'[₹rs\.]*\b(\d+(?:,\d+)*)\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, question.lower())
            for match in matches:
                try:
                    price = float(match.replace(',', ''))
                    # Reasonable price range for loans
                    if 5000 <= price <= 10000000:
                        return price
                except ValueError:
                    continue

        return None

    def _get_real_time_rates(self, category: str) -> List[Dict]:
        """
        Fetch real-time interest rates from APIs
        Returns list of bank options with rates
        """
        rates = []

        try:
            # For Indian banks, we could use RBI or bank APIs
            # For demo, using a free API or mock data
            # TODO: Implement actual RBI/bank API integration

            # Fallback to mock rates with slight variations
            base_rate = self.fallback_rates.get(category, 12.0)

            for bank in self.bank_options:
                adjusted_rate = base_rate + bank['rate_adjustment']
                rates.append({
                    'bank': bank['name'],
                    'rate': round(adjusted_rate, 2)
                })

        except Exception as e:
            # If real-time fetch fails, use fallback
            print(f"Real-time rate fetch failed: {e}")
            return self._get_fallback_rates(category)

        return rates

    def _get_fallback_rates(self, category: str) -> List[Dict]:
        """Get fallback interest rates"""
        base_rate = self.fallback_rates.get(category, 12.0)

        return [
            {'bank': 'State Bank of India', 'rate': base_rate},
            {'bank': 'HDFC Bank', 'rate': base_rate + 0.25},
            {'bank': 'ICICI Bank', 'rate': base_rate + 0.15},
            {'bank': 'Kotak Mahindra', 'rate': base_rate + 0.20}
        ]

    def calculate_emi(self, principal_amount: float, annual_interest_rate: float, tenure_months: int) -> float:
        """Calculate EMI using standard Indian banking formula with 2-decimal precision"""
        if tenure_months <= 0 or principal_amount <= 0 or annual_interest_rate < 0:
            return 0

        # RBI-approved EMI formula for loan calculations
        r = annual_interest_rate / (12 * 100)  # Monthly interest rate (decimal)
        p = principal_amount  # Principal amount
        n = tenure_months  # Tenure in months

        # EMI = [P x r x (1+r)^n] / [(1+r)^n - 1]
        if r == 0:
            return round(p / n, 2)  # Simple division for 0% interest

        numerator = p * r * (1 + r) ** n
        denominator = (1 + r) ** n - 1

        emi = numerator / denominator
        return round(emi, 2)  # 2-decimal places as per banking standards

    def calculate_downpayment_impact(self, product_price: float, downpayment_percent: float) -> Dict:
        """Calculate downpayment impact on loan amount and EMI"""
        if downpayment_percent < 0 or downpayment_percent > 100:
            downpayment_percent = 20.0 if downpayment_percent < 20 else 0.0

        downpayment_amount = product_price * (downpayment_percent / 100)
        loan_amount = product_price - downpayment_amount

        return {
            'downpayment_percent': downpayment_percent,
            'downpayment_amount': round(downpayment_amount, 2),
            'loan_amount': round(loan_amount, 2)
        }

    def check_affordability(self, emi: float, monthly_income: float) -> Dict:
        """Check if EMI is affordable based on income"""
        if monthly_income <= 0:
            return {'affordable': False, 'ratio': 100, 'message': 'Cannot assess affordability without income data'}

        emi_ratio = (emi / monthly_income) * 100

        if emi_ratio <= 30:
            return {
                'affordable': True,
                'ratio': round(emi_ratio, 1),
                'comfort': 'comfortable' if emi_ratio <= 20 else 'manageable',
                'message': f"This EMI is { 'very comfortable' if emi_ratio <= 20 else 'manageable'} for your income."
            }
        else:
            return {
                'affordable': False,
                'ratio': round(emi_ratio, 1),
                'comfort': 'high_risk',
                'message': f"This EMI exceeds 40% of your income and may cause financial strain."
            }

    def generate_saving_plan(self, target_amount: float, current_savings: float = 0, monthly_contribution: Optional[float] = None,
                           contribution_type: str = 'amount', income_ratio: Optional[float] = None) -> Dict:
        """Generate saving plan with timelines and scenarios"""
        if monthly_contribution is None and income_ratio is None:
            return {'error': 'Need either monthly contribution amount or income ratio'}

        if monthly_contribution is None and income_ratio:
            monthly_contribution = income_ratio / 100  # Ratio provided as percentage

        months_needed = math.ceil((target_amount - current_savings) / monthly_contribution)

        # Scenarios
        scenarios = {
            'conservative': lambda amt: amt,  # No growth
            'balanced': lambda amt, months: amt * (1 + 0.05/12)**(months),  # 5% APY
            'aggressive': lambda amt, months: amt * (1 + 0.08/12)**(months),  # 8% APY
        }

        plans = {}
        for scenario, growth_func in scenarios.items():
            if scenario == 'conservative':
                total_accumulated = current_savings + (monthly_contribution * months_needed)
                final_amount = total_accumulated
            else:
                total_accumulated = current_savings + (monthly_contribution * months_needed)
                final_amount = growth_func(total_accumulated, months_needed)

            # Investment options
            investment_options = []
            if scenario == 'conservative':
                investment_options = ['FD', 'Savings Account']
            elif scenario == 'balanced':
                investment_options = ['RD', 'Debt Mutual Funds']
            else:
                investment_options = ['Equity Mutual Funds', 'SIP']

            plans[scenario] = {
                'months': months_needed,
                'monthly_contribution': monthly_contribution,
                'total_contributed': total_accumulated,
                'final_amount': round(final_amount, 2),
                'investment_options': investment_options
            }

        return plans

    def process_message(self, message: str, user_context: Dict = None, user: User = None) -> Dict:
        """
        Main message processing function with updated rules

        Args:
            message: User's message
            user_context: Dict with user data like income_history, current_product, etc.
            user: Django User object (optional)

        Returns:
            Response dict with message, data, and state info
        """
        if user_context is None:
            user_context = {}

        message_lower = message.lower().strip()
        greeting = "Hello! How can I help you today?"



        # Extract user information from context
        income_history = user_context.get('income_history', [])
        average_income = user_context.get('average_income')

        # Calculate average income if not provided
        if not average_income and income_history:
            total_income = sum(income_history)
            average_income = total_income / len(income_history) if income_history else 0

        # Update context with current message for processing
        user_context['last_message'] = message

        # CHECK FOR AFFORDABILITY YES/NO RESPONSES FIRST
        # Handle yes/no responses to affordability queries (should be first priority)
        if 'affordable' in user_context and user_context.get('affordable') == False and user_context.get('awaiting_affordability_response'):
            if any(word in message_lower for word in ['yes', 'yup', 'sure', 'okay', 'ok', 'proceed']):
                # User said yes, start saving plan flow
                return self._handle_saving_plan_flow(user_context, greeting)
            elif any(word in message_lower for word in ['no', 'nope', 'nevermind', 'skip']):
                # User said no, suggest alternatives
                return self._handle_affordability_alternatives(user_context, greeting)
            # Clear the affordability response waiting state
            del user_context['awaiting_affordability_response']

        # CHECK FOR PLAN MODIFICATION INPUTS
        # Handle plan modification responses (e.g., "change downpayment to 25%")
        if user_context.get('awaiting_plan_modification') and user_context.get('modifying_plan_id'):
            return self._handle_plan_modification_input(message, user_context, user)

        # Check for greetings FIRST - but always start with greeting if it's a greeting or direct product ask
        greeting_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
        is_greeting = any(word in message_lower for word in greeting_words) and len(message_lower.split()) <= 5

        if any(k in message_lower for k in self.product_keywords.get('personal_loan', [])):
            return self._handle_personal_loan_inquiry(message, user_context)

        # Check if this is a direct product name mention (like "Kia Sonet") - EXTENDED CHECK
        direct_product_info = self._detect_direct_product_name(message)
        is_direct_product_ask = bool(direct_product_info) or self._contains_product_keywords(message) or any(word in message_lower for word in ['pricing', 'cost', 'rate', 'loan for'])

        # Always start with greeting for greetings or direct product asks
        if is_greeting or is_direct_product_ask:
            if is_greeting:
                greeting_response = f"{greeting}\n\nI can assist you with product purchase planning, EMI calculations, affordability checks, and saving plans for purchases, travel, or hospitality. What would you like to discuss?"
                return {
                    'message': greeting_response,
                    'is_greeting_response': True,
                    'show_greeting': True
                }
            # For direct product asks, proceed but will add greeting

        # If not greeting but direct product ask, proceed with greeting
        if not is_greeting and is_direct_product_ask:
            pass  # Continue to handle

        if direct_product_info:
            product, category = direct_product_info
            response = self._handle_direct_product_selection(product, category, user_context)
            # Prepend greeting unless it's already a greeting response
            if not response.get('is_greeting_response', False):
                response['message'] = f"{greeting}\n\n{response['message']}"
                response['show_greeting'] = True
            return response

        # Check if this is a direct product request or selection
        product_category = self._detect_product_category(message)

        # ENHANCED: If no category detected but message contains purchase intent, try to find a direct product anyway
        if not product_category and ('buy' in message.lower() or 'purchase' in message.lower() or 'finance' in message.lower() or 'emi' in message.lower()):
            product_category = self._detect_category_from_product_name(message)

        if product_category and self._contains_product_keywords(message):
            # Get suggestions for the category
            suggestions = self._get_product_suggestions(product_category)
            # Check if the message contains a specific product name
            direct_product = self._parse_direct_product(message, suggestions)
            if direct_product:
                # User specified a product directly, go straight to analysis
                user_context = self._ensure_context(user_context, 'available_suggestions', suggestions)
                response = self._handle_direct_product_selection(direct_product, product_category, user_context)
                response['message'] = f"{greeting}\n\n{response['message']}"
                response['show_greeting'] = True
                return response
            else:
                # Show suggestions
                response = self._handle_product_inquiry(message, product_category, user_context)
                response['message'] = f"{greeting}\n\n{response['message']}"
                response['show_greeting'] = True
                return response
        elif product_category:
            # Handle product inquiry even without explicit purchase keywords (e.g., "Kia Sonet")
            suggestions = self._get_product_suggestions(product_category)
            direct_product = self._parse_direct_product(message, suggestions)
            if direct_product:
                # User specified a product directly, go straight to analysis
                response = self._handle_direct_product_selection(direct_product, product_category, user_context)
                response['message'] = f"{greeting}\n\n{response['message']}"
                response['show_greeting'] = True
                return response
            else:
                # Show suggestions
                response = self._handle_product_inquiry(message, product_category, user_context)
                response['message'] = f"{greeting}\n\n{response['message']}"
                response['show_greeting'] = True
                return response

        # Handle specific commands (check for save plan commands first - take precedence over general saving inquiries)
        if 'save this plan' in message_lower:
            response = self._handle_save_plan(message, user_context, user)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Check for save plan with number/pattern (must come before general saving check)
        if re.search(r'save\s+plan\s+\d+', message_lower):
            response = self._handle_save_plan(message, user_context, user)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        if 'show my saved plans' in message_lower:
            response = self._handle_show_saved_plans(message, user_context)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Handle modify saved plans - check for specific plan modification first
        if 'modify' in message_lower and ('plan' in message_lower or 'saved' in message_lower or 'plans' in message_lower):
            # Check if user specified a specific plan number (e.g., "modify plan 1")
            if 'plan' in message_lower and re.search(r'\d+', message_lower):
                plan_num_match = re.search(r'modify\s+plan\s*(?:#|)(\w+)', message.lower())
                if plan_num_match:
                    plan_id = f"plan_{plan_num_match.group(1)}" if not plan_num_match.group(1).startswith('plan_') else plan_num_match.group(1)
                    response = self._handle_modify_specific_plan(plan_id, user_context, user if 'user' in locals() else None)
                else:
                    response = self._handle_modify_saved_plans(message, user_context, user if 'user' in locals() else None)
            else:
                response = self._handle_modify_saved_plans(message, user_context, user if 'user' in locals() else None)

            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Handle unsave plan
        if ('unsave' in message_lower or 'cancel' in message_lower) and 'plan' in message_lower:
            response = self._handle_unsave_plan(message, user_context, user if 'user' in locals() else None)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Product inquiry flow
        if product_category:
            response = self._handle_product_inquiry(message, product_category, user_context)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Saving plan inquiry
        if any(word in message_lower for word in ['saving', 'savings', 'save']):
            response = self._handle_saving_inquiry(message, user_context)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Affordability check
        if any(word in message_lower for word in ['afford', 'can i afford']):
            response = self._handle_affordability_inquiry(message, user_context)
            response['message'] = f"{greeting}\n\n{response['message']}"
            response['show_greeting'] = True
            return response

        # Check if off-topic - only if not product/saving/affordability related
        if not self._is_on_topic(message):
            greeting = "Hello! How can I help you today?"
            return {
                'message': f"{greeting}\n\nI can assist you with product purchase planning, EMI calculations, affordability checks, and saving plans for purchases, travel, or hospitality. Please ask me something related to financial planning.",
                'off_topic': True
            }

        # Generic domain response with greeting
        response_lines = [greeting]
        response_lines.append("I can help you with product purchase planning, EMI calculations, affordability checks, and saving plans for purchases, travel, or hospitality. Please specify what you'd like to discuss.")
        return {
            'message': "\n".join(response_lines),
            'show_greeting': True
        }

    def _contains_product_keywords(self, message: str) -> bool:
        """Check if message contains immediate product request"""
        message_lower = message.lower()
        product_indicators = ['want to buy', 'buy', 'purchase', 'get', 'loan for', 'finance', 'emi for']
        return any(indicator in message_lower for indicator in product_indicators)

    def _handle_personal_loan_inquiry(self, message: str, user_context: Dict) -> Dict:
        greeting = "Hello! How can I help you today?"
        income_history = user_context.get('income_history', [])
        avg_income = 0.0
        if income_history:
            if len(income_history) >= 6:
                avg_income = sum(income_history[-6:]) / 6
            else:
                avg_income = sum(income_history) / len(income_history)

        base_rate = self.fallback_rates.get('personal_loan', 10.0)
        rates = self._get_fallback_rates('personal_loan')
        extra_bank_rates = [
            {'bank': b['name'], 'rate': round(base_rate + b['rate_adjustment'], 2)}
            for b in self.bank_options
        ]
        additional_banks = [
            {'bank': 'Bank of Baroda', 'rate': base_rate + 0.10},
            {'bank': 'Punjab National Bank', 'rate': base_rate + 0.05},
            {'bank': 'Union Bank', 'rate': base_rate + 0.12},
            {'bank': 'IDFC First Bank', 'rate': base_rate + 0.35},
            {'bank': 'IndusInd Bank', 'rate': base_rate + 0.30},
            {'bank': 'Yes Bank', 'rate': base_rate + 0.25}
        ]
        all_rates = rates + extra_bank_rates + additional_banks
        # Deduplicate by bank name
        seen = set()
        unique_rates = []
        for rt in all_rates:
            name = rt['bank']
            name_norm = re.sub(r"\s+bank$", "", name.strip(), flags=re.I)
            if name_norm not in seen:
                seen.add(name_norm)
                unique_rates.append({'bank': name_norm if name_norm else name, 'rate': round(rt['rate'], 2)})

        emi_cap = avg_income * 0.30 if avg_income > 0 else 0
        selected_best = min(unique_rates, key=lambda x: x['rate']) if unique_rates else {'bank': 'Bank', 'rate': base_rate}
        plans = []

        # Generate multiple affordable plans per bank with varied amounts and tenures
        for rt in unique_rates:
            r = rt['rate'] / (12 * 100)
            for tenure in [24, 36, 48]:
                if emi_cap <= 0:
                    continue
                num = (1 + r) ** tenure - 1
                den = r * (1 + r) ** tenure
                principal_max = emi_cap * (num / den)
                if principal_max <= 0:
                    continue
                # Propose 2 amounts per bank-tenure: 60% and 90% of max principal
                for factor in [0.6, 0.9]:
                    amount = principal_max * factor
                    rounded_amount = math.floor(amount / 10000) * 10000
                    if rounded_amount <= 0:
                        continue
                    emi_val = self.calculate_emi(rounded_amount, rt['rate'], tenure)
                    if emi_val <= emi_cap:
                        plans.append({
                            'bank': rt['bank'],
                            'rate': rt['rate'],
                            'amount': rounded_amount,
                            'tenure': tenure,
                            'emi': emi_val
                        })

        # Ensure unique (bank, amount) pairs and at least 10 suggestions
        unique_pairs = {}
        for p in plans:
            key = (p['bank'], p['amount'])
            if key not in unique_pairs:
                unique_pairs[key] = p
        plans = list(unique_pairs.values())
        # Sort by EMI ascending then tenure
        plans.sort(key=lambda x: (x['emi'], x['tenure']))
        plans = plans[:10]

        low_income_note = ""
        if avg_income and avg_income < 25000:
            low_income_note = "\nSafety tip: Consider smaller loan amounts and longer tenure to keep EMI manageable."

        specific = message.lower()
        if any(k in specific for k in ['interest rate', 'rates']):
            resp = f"{greeting}\n\nPersonal loan interest rates:"
            for rt in rates[:3]:
                resp += f"\n• {rt['bank']}: {rt['rate']}%"
            return {'message': resp, 'show_greeting': True}

        amt_match = re.search(r'(\d[\d,]*)\s*(?:rs|inr|₹|rupees|amount|loan)', specific)
        if any(k in specific for k in ['emi']) and amt_match:
            try:
                loan_amt = float(amt_match.group(1).replace(',', ''))
            except Exception:
                loan_amt = 0
            if loan_amt > 0:
                details = []
                for n in [12, 24, 36]:
                    emi_v = self.calculate_emi(loan_amt, selected_best['rate'], n)
                    ok = emi_v <= emi_cap if emi_cap > 0 else False
                    details.append((n, emi_v, ok))
                msg = f"{greeting}\n\nEMI estimates for ₹{loan_amt:,.0f} at {selected_best['rate']}%:"
                for n, e, ok in details:
                    msg += f"\n• {n} months: ₹{e:,.0f} {'(affordable)' if ok else '(high vs income)'}"
                if emi_cap > 0:
                    msg += f"\n\nRecommended EMI should be ≤ ₹{emi_cap:,.0f} (30% of your average monthly income)."
                return {'message': msg, 'show_greeting': True}

        if any(k in specific for k in ['eligibility']):
            msg = f"{greeting}\n\nEligibility is assessed against your income. Plans below keep EMI ≤ 30% of your average monthly income. Bank may also check credit score and obligations."
            return {'message': msg, 'show_greeting': True}

        if any(k in specific for k in ['document', 'documents', 'doc']):
            msg = f"{greeting}\n\nCommon documents: ID (PAN/Aadhaar), address proof, income proof (salary slips/bank statements), and bank account details."
            return {'message': msg, 'show_greeting': True}

        if plans:
            lines = [
                f"{greeting}",
                "",
                "Based on your income, here are 10 affordable personal-loan plans:",
            ]
            for idx, p in enumerate(plans, start=1):
                total_payable = p['emi'] * p['tenure']
                lines.append(f"Plan {idx}: {p['bank']} - {p['rate']:.2f}%")
                # lines.append(f"Downpayment     \t ₹0")
                lines.append(f"Loan Amount     \t ₹{p['amount']:,.0f}")
                lines.append(f"Tenure          \t {p['tenure']} months")
                lines.append(f"EMI             \t ₹{p['emi']:,.0f}")
                lines.append(f"Interest Rate   \t {p['rate']:.2f}%")
                lines.append(f"Total Payable   \t ₹{total_payable:,.0f}")
                lines.append("")
            if emi_cap > 0:
                lines.append(f"EMI cap used: ₹{emi_cap:,.0f} (30% of your average monthly income).")
            if low_income_note:
                lines.append(low_income_note)
            return {'message': "\n".join(lines), 'show_greeting': True}

        msg = f"{greeting}\n\nI could not find a safe plan within your income profile. Consider a smaller loan amount or longer tenure to reduce EMI."
        if unique_rates:
            msg += f"\nCurrent indicative rate: {selected_best['rate']}% ({selected_best['bank']})."
        return {'message': msg, 'show_greeting': True}

    def _handle_product_inquiry(self, message: str, category: str, user_context: Dict) -> Dict:
        """Handle product-specific inquiries following the structured flow with immediate analysis after selection"""
        greeting = "Hello! How can I help you today!"

        # Calculate 6-month average income automatically (NEVER ask)
        income_history = user_context.get('income_history', [])
        average_income_6months = None
        if income_history and len(income_history) >= 6:
            # Use last 6 months for 6-month average
            total_income_6months = sum(income_history[-6:])  # Last 6 months
            average_income_6months = total_income_6months / 6
        elif income_history:
            # If less than 6 months, use whatever is available
            total_income = sum(income_history)
            average_income_6months = total_income / len(income_history)

        # Check if user is making a selection (number or name) from previous suggestions
        if 'available_suggestions' in user_context:
            selected_product = self._parse_product_selection(message, user_context['available_suggestions'])
            if selected_product:
                # User selected a product, go straight to analysis
                user_context['selected_product'] = selected_product
                user_context['product_selected'] = True
                return self._provide_product_analysis(selected_product, category, average_income_6months, greeting, user_context)

        # Check if user is in product selection phase
        if not user_context.get('product_selected', False):
            # Phase 1: Suggest products based on category
            return self._suggest_products(category, greeting, user_context)

        # User has selected a product, proceed with analysis
        selected_product = user_context.get('selected_product')
        if not selected_product:
            return {
                'message': f"{greeting}\nPlease select a product first or specify which product you want to buy.",
                'show_greeting': True
            }

        # Phase 2: Confirm product and provide details
        return self._provide_product_analysis(selected_product, category, average_income_6months, greeting, user_context)

    def _handle_saving_inquiry(self, message: str, user_context: Dict) -> Dict:
        """Handle saving plan inquiries with acceleration options"""
        greeting = "Hello! How can I help you today?"

        # Calculate average income from last 6 months automatically
        income_history = user_context.get('income_history', [])
        average_income = None
        if income_history:
            total_income = sum(income_history)
            average_income = total_income / len(income_history) if income_history else None

        # Extract monthly savings amount (absolute or percentage)
        savings = None
        savings_type = 'amount'  # 'amount' or 'percentage'

        # First check for percentage
        percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', message.lower())
        if percent_match:
            try:
                percent = float(percent_match.group(1))
                if average_income:
                    savings = average_income * (percent / 100)
                    savings_type = 'percentage'
                    original_percent = percent
                else:
                    return {
                        'message': f"{greeting}\nTo create a saving plan based on {percent}% of your income, I need your income data. This is calculated automatically from your last 6 months of transactions.",
                        'awaiting_response': 'income_for_percent_calc',
                        'savings_percent': percent,
                        'show_greeting': True
                    }
            except ValueError:
                pass
        else:
            # Check for absolute amount
            amount_patterns = [r'save\s*[₹rs\.]*\b(\d+(?:,\d+)*)\b', r'(\d+(?:,\d+)*)\s*per month']
            message_lower = message.lower()
            for pattern in amount_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    try:
                        savings = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue

        # If no savings amount specified, ask for it
        if savings is None:
            return {
                'message': f"{greeting}\nI'll help you create a personalized saving plan!\n\nPlease tell me how much you can save per month:\n• Specific amount (e.g., ₹5,000)\n• Percentage of income (e.g., 10%)",
                'awaiting_response': 'monthly_savings',
                'show_greeting': True
            }

        # Get target amount (what they're saving for)
        target_amount = user_context.get('target_amount')

        # Try to extract target from message if not in context
        if target_amount is None:
            target_patterns = [
                r'target\s*[₹rs\.]*\b(\d+(?:,\d+)*)\b',
                r'save for\s*[₹rs\.]*\b(\d+(?:,\d+)*)\b',
                r'goal\s*[₹rs\.]*\b(\d+(?:,\d+)*)\b'
            ]
            for pattern in target_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    try:
                        target_amount = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue

        # If still no target, ask for it
        if target_amount is None:
            user_context['temp_savings'] = savings
            user_context['temp_savings_type'] = savings_type
            return {
                'message': f"{greeting}\nGreat! You can save ₹{savings:,.0f} per month{(' (' + str(int(original_percent)) + '% of income)' if savings_type == 'percentage' and 'original_percent' in locals() else '')}.\n\nWhat's the target amount you're saving for (e.g., ₹50,000 for a vacation)?",
                'awaiting_response': 'target_amount',
                'monthly_savings': savings,
                'savings_type': savings_type,
                'show_greeting': True
            }

        # Generate comprehensive saving plan with acceleration options
        base_plan = self.generate_saving_plan(target_amount, monthly_contribution=savings)

        # Create acceleration scenarios (10%, 20%, 50% increases)
        acceleration_scenarios = {}
        accelerations = [0, 10, 20, 50]  # 0% = baseline

        for accel_pct in accelerations:
            accel_amount = savings * (1 + accel_pct / 100)
            accel_plan = self.generate_saving_plan(target_amount, monthly_contribution=accel_amount)

            scenario_key = f"{'base' if accel_pct == 0 else f'{accel_pct}%_accelerated'}"
            acceleration_scenarios[scenario_key] = {
                'monthly_contribution': accel_amount,
                'acceleration': accel_pct,
                'months_needed': accel_plan['conservative']['months'],
                'final_amount': accel_plan['conservative']['final_amount']
            }

        # Get real-time interest rates for investment options
        try:
            fd_rates = self._get_real_time_fd_rates()
            sip_rates = self._get_real_time_sip_rates()
        except Exception:
            fd_rates = {'standard': 5.5, 'senior_citizen': 6.0}
            sip_rates = {'equity_savings': 8.5, 'balanced': 7.2, 'debt': 6.0}

        # Build detailed response
        response = f"{greeting}\n\n"
        response += f"**Saving Plan Analysis**\n"
        response += f"Target Amount: ₹{target_amount:,.0f}\n"
        response += f"Monthly Savings: ₹{savings:,.0f}"
        if savings_type == 'percentage' and 'original_percent' in locals():
            response += f" ({original_percent}% of income)"
        response += "\n\n"

        # Base plan summary
        base_months = base_plan['conservative']['months']
        response += f"**Base Plan (Current Savings)**\n"
        response += f"• Time to Goal: {base_months} months ({base_months//12} years, {base_months%12} months)\n"
        response += f"• Total Saved: ₹{base_plan['conservative']['total_contributed']:,.0f}\n"
        response += f"• Investment Options: Savings Account\n\n"

        # Acceleration options
        response += "**Acceleration Options**\n"
        for scenario, accel_data in acceleration_scenarios.items():
            if accel_data['acceleration'] == 0:
                continue  # Skip base plan

            accel_pct = accel_data['acceleration']
            faster_by_months = base_months - accel_data['months_needed']
            response += f"• **{accel_pct}% Increase** (₹{accel_data['monthly_contribution']:,.0f}/month):\n"
            response += f"  - Reach goal {faster_by_months} months sooner\n"
            response += f"  - Save ₹{target_amount:,.0f}\n\n"

        # Interest-bearing investment options with current rates
        response += "**Interest-Bearing Options (Current Rates)**\n"
        response += f"• **FD (Fixed Deposit)**: {fd_rates.get('standard', 5.5)}% p.a.\n"
        response += f"  - Safe, guaranteed returns\n"
        response += f"  - Minimum ₹1,000, flexible tenure\n\n"

        response += f"• **RD (Recurring Deposit)**: {fd_rates.get('standard', 5.5) + 0.2}% p.a.\n"
        response += f"  - Disciplined monthly savings\n"
        response += f"  - Minimum ₹100/month\n\n"

        response += f"• **SIP (Systematic Investment Plan)**: {sip_rates.get('balanced', 7.2)}% avg. returns\n"
        response += f"  - Equity exposure for higher returns\n"
        response += f"  - Minimum ₹500/month, diversified\n\n"

        # Practical advice
        response += "**Practical Tips**\n"
        response += f"• Start with RD for {min(24, base_months)} months to build discipline\n"
        response += f"• Consider SIP for long-term growth if you have >24 months\n"
        response += f"• Emergency fund first before aggressive investing\n\n"

        response += "**Say 'save this plan' if you'd like to store these recommendations.**"

        return {
            'message': response,
            'target_amount': target_amount,
            'monthly_savings': savings,
            'savings_type': savings_type,
            'base_plan': base_plan,
            'acceleration_scenarios': acceleration_scenarios,
            'investment_rates': {
                'fd_rates': fd_rates,
                'sip_rates': sip_rates
            },
            'show_greeting': True
        }

    def _handle_affordability_inquiry(self, message: str, user_context: Dict) -> Dict:
        """Handle affordability check requests"""
        greeting = "Hello! How can I help you today?"

        income = user_context.get('average_income')
        expense = user_context.get('monthly_expense') or user_context.get('emi')

        if income is None:
            return {
                'message': f"{greeting}\nTo check affordability, please provide your average monthly income.",
                'awaiting_response': 'income_for_affordability',
                'show_greeting': True
            }

        if expense is None:
            return {
                'message': f"{greeting}\nWhat monthly expense are you checking for affordability (EMI amount)?",
                'awaiting_response': 'expense_amount',
                'show_greeting': True
            }

        aff_check = self.check_affordability(expense, income)

        response = f"{greeting}\n\n**Affordability Analysis:**\n"
        response += f"Monthly Income: ₹{income:,.0f}\n"
        response += f"Monthly Expense: ₹{expense:,.0f}\n"
        response += f"Expense Ratio: {aff_check['ratio']}%\n\n"
        response += f"**{aff_check['message']}**"

        return {
            'message': response,
            'affordability': aff_check,
            'show_greeting': True
        }

    def _confirm_product_name(self, message: str, category: str) -> Optional[str]:
        """Confirm product name with user (simplified logic)"""
        # For demo, just return the category - in production, would ask user if ambiguous
        if category in ['four_wheeler', 'car', 'automobile']:
            return 'car'
        elif category in ['two_wheeler', 'bike', 'motorcycle']:
            return 'two_wheeler'
        elif category in ['electronics', 'laptop', 'phone', 'mobile']:
            return 'electronics'
        else:
            return category

    def _get_product_variants(self, category: str) -> Dict:
        """Get product variants and models (simulated)"""
        variants = {
            'car': {
                'name': 'Car (Four Wheeler)',
                'variants': ['Sedan', 'SUV', 'Hatchback', 'Luxury', 'Electric']
            },
            'two_wheeler': {
                'name': 'Two Wheeler',
                'variants': ['Standard Bike', 'Sports Bike', 'Scooter', 'Electric']
            },
            'electronics': {
                'name': 'Electronic Device',
                'variants': ['Smartphone', 'Laptop', 'Tablet', 'TV', 'Refrigerator']
            },
            'home_loan': {
                'name': 'Home Loan',
                'variants': ['1BHK Flat', '2BHK Flat', '3BHK Flat', 'Villa', 'Plot']
            },
            'personal_loan': {
                'name': 'Personal Loan',
                'variants': ['Education', 'Marriage', 'Medical', 'Travel', 'Home Improvement']
            },
            'gold_loan': {
                'name': 'Gold Loan',
                'variants': ['Jewelry', 'Gold Coins', 'Gold Bars', 'Ornaments']
            },
            'travel': {
                'name': 'Travel Package',
                'variants': ['Domestic Vacation', 'International Trip', 'Adventure Tour', 'Luxury Travel']
            },
            'hospitality': {
                'name': 'Hospitality Stay',
                'variants': ['Budget Hotel', 'Business Hotel', 'Resort', 'Luxury Suite']
            }
        }

        return variants.get(category, {'name': category.replace('_', ' ').title(), 'variants': []})

    def _get_real_time_banks_and_rates(self, category: str) -> List[Dict]:
        """Fetch banking options with rates from Excel data"""
        try:
            if self.banks_rates_df.empty:
                print("Banks data not loaded, using fallback")
                return self._get_fallback_banks_and_rates(category)

            # Map category to Excel column
            category_column_map = {
                'four_wheeler': 'CarLoan_Start_%',
                'two_wheeler': 'TwoWheelerLoan_Start_%',
                'electronics': 'ElectronicsLoan_Start_%',
                'home_loan': 'HomeLoan_Start_%',
                'personal_loan': 'PersonalLoan_Start_%',
                'gold_loan': 'GoldLoan_Start_%'
            }

            column_name = category_column_map.get(category, 'CarLoan_Start_%')

            if column_name not in self.banks_rates_df.columns:
                print(f"Column {column_name} not found, using fallback")
                return self._get_fallback_banks_and_rates(category)

            # Build bank data from Excel
            banks_data = []
            bank_pros_cons = {
                'State Bank of India (SBI)': {
                    'pros': ['Government backed', 'Maximum loan amount', 'Flexible tenure'],
                    'cons': ['Higher processing fees', 'More documentation']
                },
                'HDFC Bank': {
                    'pros': ['Quick approval', 'Online application', 'Competitive rates'],
                    'cons': ['Higher interest for bad credit']
                },
                'ICICI Bank': {
                    'pros': ['Fast disbursement', 'Low processing fees', 'Good customer service'],
                    'cons': ['Strict eligibility criteria']
                },
                'Kotak Mahindra Bank': {
                    'pros': ['Digital first bank', 'Minimal documentation', 'Flexible EMIs'],
                    'cons': ['Limited branches', 'Variable rates']
                },
                'Axis Bank': {
                    'pros': ['Balanced rates', 'Good rewards program', 'Online banking'],
                    'cons': ['Average processing time']
                },
                'Punjab National Bank (PNB)': {
                    'pros': ['Long-standing reputation', 'Wide network', 'Reliable service'],
                    'cons': ['Average processing time', 'Standard rates']
                },
                'Bank of Baroda': {
                    'pros': ['Growing digital presence', 'Competitive rates', 'Good customer support'],
                    'cons': ['Branch-intensive processes', 'Documentation requirements']
                },
                'IDFC First Bank': {
                    'pros': ['Low processing fees', 'Fast approval', 'Digital banking'],
                    'cons': ['Limited branch network', 'Variable terms']
                },
                'Yes Bank': {
                    'pros': ['Modern banking', 'Low interest premiums', 'Quick processing'],
                    'cons': ['Availability constraints', 'Standard eligibility']
                },
                'Bajaj Finserv': {
                    'pros': ['Easily available', 'Flexible terms', 'Quick disbursement'],
                    'cons': ['Slightly higher rates', 'Limited loan amounts']
                }
            }

            for _, row in self.banks_rates_df.iterrows():
                bank_name = row['Bank']
                base_rate = row[column_name]

                if pd.isna(base_rate):
                    continue  # Skip if rate not available

                bank_info = {
                    'name': bank_name,
                    'rate': float(base_rate),
                    'pros': bank_pros_cons.get(bank_name, {}).get('pros', ['Standard banking features']),
                    'cons': bank_pros_cons.get(bank_name, {}).get('cons', ['Standard terms apply'])
                }
                banks_data.append(bank_info)

            # Sort by rate (lowest first) and return top 5
            banks_data.sort(key=lambda x: x['rate'])
            return banks_data[:5]

        except Exception as e:
            print(f"Error getting bank rates from Excel: {e}")
            return self._get_fallback_banks_and_rates(category)

    def _get_fallback_banks_and_rates(self, category: str) -> List[Dict]:
        """Fallback banking data"""
        base_rate = self.fallback_rates.get(category, 12.0)

        return [
            {
                'name': 'State Bank of India',
                'rate': base_rate,
                'pros': ['Trustworthy', 'Wide presence'],
                'cons': ['Bureaucratic process']
            },
            {
                'name': 'HDFC Bank',
                'rate': base_rate + 0.25,
                'pros': ['Reliable service'],
                'cons': ['Higher rates']
            },
            {
                'name': 'ICICI Bank',
                'rate': base_rate + 0.15,
                'pros': ['Modern banking'],
                'cons': ['Strict policies']
            }
        ]

    def _determine_affordability_threshold(self, product_price: float, category: str, income: float) -> float:
        """Determine affordability threshold based on product and income"""
        # Base threshold between 20-30% based on product type and price
        base_threshold = 25.0

        # Higher priced items get lower threshold (more conservative)
        if product_price > 500000:  # High value items
            base_threshold = 22.0
        elif product_price > 100000:  # Medium value items
            base_threshold = 24.0
        else:  # Low value items
            base_threshold = 28.0

        # Category adjustments
        if category in ['travel', 'hospitality']:
            base_threshold = 25.0  # More flexible for discretionary spending
        elif category in ['home_loan']:
            base_threshold = 23.0  # More conservative for long-term commitments

        # Income-based adjustment (higher income = can afford higher ratio)
        if income > 100000:
            base_threshold += 2.0
        elif income < 25000:
            base_threshold -= 3.0

        return max(20.0, min(30.0, base_threshold))  # Clamp between 20-30%

    def _recommend_tenure(self, price: float, emi: float, income: float, threshold: float) -> int:
        """Recommend optimal tenure based on calculations"""
        # Try to find tenure that gives comfortable EMI
        tenures = [6, 12, 24, 36, 48]
        best_tenure = 12  # Default

        for tenure in tenures:
            calculated_emi = self.calculate_emi(price, self.fallback_rates.get('four_wheeler', 13.0), tenure)
            ratio = (calculated_emi / income) * 100

            if ratio <= threshold and ratio > threshold * 0.7:  # Good balance
                best_tenure = tenure
                break

        return best_tenure

    def _handle_save_plan(self, message: str, user_context: Dict, user: User = None) -> Dict:
        """Handle saving a financial plan - supports saving specific plans by number"""
        greeting = "Hello! How can I help you today?"

        message_lower = message.lower()

        # Check for specific plan selection (e.g., "save plan 1", "save plan_1", etc.)
        plan_selection_match = re.search(r'save\s+plan\s*(?:#|)(\w+)', message_lower)
        selected_plan_number = None

        if plan_selection_match:
            try:
                # Extract plan number (could be "1", "2", "_1", etc.)
                plan_indicator = plan_selection_match.group(1)
                # Clean up the indicator - remove underscore if present or convert to int
                if plan_indicator.startswith('plan_'):
                    plan_indicator = plan_indicator.replace('plan_', '')
                selected_plan_number = int(plan_indicator)

                # Validate plan number (1-5 is reasonable based on our plan generation)
                if not (1 <= selected_plan_number <= 5):
                    return {
                        'message': f"{greeting}\nInvalid plan number. Please select plan 1-5.",
                        'show_greeting': True
                    }
            except (ValueError, IndexError):
                return {
                    'message': f"{greeting}\nCould not understand plan number. Please say 'save plan X' where X is 1, 2, 3, etc.",
                    'show_greeting': True
                }

        # Get current recommendation from context
        selected_product = user_context.get('selected_product')
        category = user_context.get('category')

        # Get product price
        if selected_product and isinstance(selected_product, dict) and 'price' in selected_product:
            product_price = selected_product['price']
        elif user_context.get('product_price'):
            product_price = user_context.get('product_price', 0)
        else:
            if selected_product and hasattr(selected_product, 'price'):
                product_price = float(selected_product.price)
            else:
                product_price = 0

        if product_price <= 0:
            return {
                'message': f"{greeting}\nI don't have a current plan to save. Please discuss a product purchase first.",
                'show_greeting': True
            }

        # Get available bank options from context
        bank_options = user_context.get('bank_options', [])
        if not bank_options or len(bank_options) < 5:
            # Fallback to default banks if not enough options
            bank_options = [
                {'name': 'State Bank of India', 'rate': 9.0},
                {'name': 'HDFC Bank', 'rate': 9.25},
                {'name': 'ICICI Bank', 'rate': 9.15},
                {'name': 'Kotak Mahindra Bank', 'rate': 9.20},
                {'name': 'Axis Bank', 'rate': 9.10}
            ]

        # Determine which plan to save
        if selected_plan_number and selected_plan_number <= len(bank_options):
            # Save specific plan by number
            selected_bank = bank_options[selected_plan_number - 1]  # 0-indexed
            plan_index = selected_plan_number - 1
        else:
            # Default to first plan if no specific plan selected or invalid number
            selected_bank = bank_options[0]
            plan_index = 0

        # Calculate EMI for selected plan (48-month tenure)
        downpayment_amount = product_price * 0.2
        loan_amount = product_price * 0.8
        emi_value = self.calculate_emi(loan_amount, selected_bank['rate'], 48)
        total_payable = round(emi_value * 48 + downpayment_amount, 2)

        # Create recommendation for saving
        recommendation = {
            'downpayment': 20.0,
            'loan_amount': loan_amount,
            'interest_rate': selected_bank['rate'],
            'tenure': 48,
            'emi': emi_value,
            'total_cost': total_payable,
        }

        # Save to database if user is provided
        if user:
            try:
                # Find next plan ID for this user by extracting the highest plan number
                existing_plans = SavedPlan.objects.filter(user=user)
                if existing_plans.exists():
                    # Extract all plan numbers and find the max
                    plan_numbers = []
                    for plan in existing_plans:
                        try:
                            plan_num = int(plan.plan_id.split('_')[-1])
                            plan_numbers.append(plan_num)
                        except (ValueError, IndexError):
                            continue

                    if plan_numbers:
                        # Set to next number after the highest existing number
                        plan_num = max(plan_numbers) + 1
                    else:
                        plan_num = 1
                else:
                    plan_num = 1

                plan_id = f"plan_{plan_num}"

                SavedPlan.objects.create(
                    user=user,
                    plan_id=plan_id,
                    product=user_context.get('selected_product', {}).get('name', 'Unknown Product'),
                    price=Decimal(str(product_price)),
                    downpayment=Decimal(str(recommendation.get('downpayment', 20.0))),
                    loan_amount=Decimal(str(recommendation.get('loan_amount', 0))),
                    interest_rate=Decimal(str(recommendation.get('interest_rate', selected_bank['rate']))),
                    tenure=recommendation.get('tenure', 48),
                    emi=Decimal(str(recommendation.get('emi', emi_value))),
                    total_paid=Decimal(str(recommendation.get('total_cost', total_payable))),
                    notes=f"Saved plan {selected_plan_number or 1}: {selected_bank['name']} - {selected_bank['rate']}% for {user_context.get('selected_product', {}).get('name', 'product')}",
                )

                # Determine plan description for response
                if selected_plan_number:
                    plan_desc = f"Plan {selected_plan_number} ({selected_bank['name']} - {selected_bank['rate']}%)"
                else:
                    plan_desc = f"Plan 1 ({selected_bank['name']} - {selected_bank['rate']}%)"

                return {
                    'message': f"{greeting}\n✅ **{plan_desc} saved successfully!**\n\n**Saved Plan #{plan_id}**\n• Product: {user_context.get('selected_product', {}).get('name', 'Unknown')}\n• Bank: {selected_bank['name']}\n• Interest Rate: {selected_bank['rate']}%\n• Monthly EMI: ₹{emi_value:,.0f}\n• Tenure: 48 months\n• Total Cost: ₹{total_payable:,.0f}\n\nSay 'show my saved plans' to view all saved plans.",
                    'saved_plan': {
                        'plan_id': plan_id,
                        'product': user_context.get('selected_product', {}).get('name', 'Unknown'),
                        'price': product_price,
                        'bank': selected_bank['name'],
                        'downpayment': recommendation.get('downpayment', 20.0),
                        'loan_amount': recommendation.get('loan_amount', 0),
                        'interest_rate': recommendation.get('interest_rate', selected_bank['rate']),
                        'tenure': recommendation.get('tenure', 48),
                        'emi': recommendation.get('emi', emi_value),
                        'total_paid': recommendation.get('total_cost', total_payable),
                        'created_at': datetime.now().isoformat(),
                        'user_id': user.id if user else None,
                        'selected_plan_number': selected_plan_number
                    },
                    'show_greeting': True
                }

            except Exception as e:
                print(f"Error saving plan to database: {e}")
                return {
                    'message': f"{greeting}\n❌ ERROR: Failed to save plan to database. Please try again.",
                    'show_greeting': True
                }
        else:
            # Fallback to context saving if no user
            plan_id = f"plan_{len(user_context.get('saved_plans', [])) + 1}"
            plan_desc = f"Plan {selected_plan_number or 1} ({selected_bank['name']} - {selected_bank['rate']}%)"

            saved_plan = {
                'plan_id': plan_id,
                'product': user_context.get('selected_product', {}).get('name', 'Unknown'),
                'price': product_price,
                'bank': selected_bank['name'],
                'downpayment': recommendation.get('downpayment', 20.0),
                'loan_amount': recommendation.get('loan_amount', 0),
                'interest_rate': recommendation.get('interest_rate', selected_bank['rate']),
                'tenure': recommendation.get('tenure', 48),
                'emi': recommendation.get('emi', emi_value),
                'total_paid': recommendation.get('total_cost', total_payable),
                'notes': f"Saved {plan_desc} for {user_context.get('selected_product', {}).get('name', 'product')}",
                'created_at': datetime.now().isoformat(),
                'user_id': user_context.get('user_id'),
                'selected_plan_number': selected_plan_number
            }

            # Add to saved plans
            if 'saved_plans' not in user_context:
                user_context['saved_plans'] = []
            user_context['saved_plans'].append(saved_plan)

            return {
                'message': f"{greeting}\n✅ **{plan_desc} saved successfully!**\n\n**Saved Plan #{plan_id}**\n• Product: {saved_plan['product']}\n• Bank: {selected_bank['name']}\n• Interest Rate: {selected_bank['rate']}%\n• Monthly EMI: ₹{saved_plan['emi']:,.0f}\n• Tenure: 48 months\n• Total Cost: ₹{saved_plan['total_paid']:,.0f}\n\nSay 'show my saved plans' to view all saved plans.",
                'saved_plan': saved_plan,
                'show_greeting': True
            }

    def _handle_show_saved_plans(self, message: str, user_context: Dict, user: User = None) -> Dict:
        """Show user's saved plans"""
        greeting = "Hello! How can I help you today?"

        saved_plans = []

        if user:
            # Get plans from database
            db_plans = SavedPlan.objects.filter(user=user).order_by('-created_at')
            for plan in db_plans:
                saved_plans.append({
                    'plan_id': plan.plan_id,
                    'product': plan.product,
                    'price': float(plan.price),
                    'downpayment': float(plan.downpayment),
                    'loan_amount': float(plan.loan_amount),
                    'interest_rate': float(plan.interest_rate),
                    'tenure': plan.tenure,
                    'emi': float(plan.emi),
                    'total_paid': float(plan.total_paid),
                    'notes': plan.notes,
                    'created_at': plan.created_at.isoformat(),
                    'user_id': plan.user.id
                })

        if not saved_plans:
            return {
                'message': f"{greeting}\nYou don't have any saved plans yet. Discuss a product purchase to create and save a financial plan.",
                'show_greeting': True
            }

        response = f"{greeting}\n\n**Your Saved Financial Plans**\n\n"
        for plan in saved_plans:
            response += f"**Plan #{plan['plan_id']} - {plan['product']}**\n"
            response += f"• Price: ₹{plan['price']:,.0f}\n"
            response += f"• Downpayment: {plan['downpayment']}%\n"
            response += f"• EMI: ₹{plan['emi']:,.0f} ({plan['tenure']} months)\n"
            response += f"• Total Paid: ₹{plan['total_paid']:,.0f}\n"
            response += f"• Saved: {plan['created_at']}\n\n"

        response += "To modify or unsave a plan, let me know the plan number."

        return {
            'message': response,
            'saved_plans': saved_plans,
            'show_greeting': True
        }

    def _get_real_time_fd_rates(self) -> Dict:
        """Get current FD rates from various banks"""
        # Simulated real-time FD rates
        return {
            'SBI': 5.3,
            'HDFC': 5.5,
            'ICICI': 5.4,
            'Axis': 5.6,
            'Kotak': 5.8,
            'standard': 5.5,
            'senior_citizen': 6.0
        }

    def _get_real_time_sip_rates(self) -> Dict:
        """Get current SIP/mutual fund expected returns"""
        # Simulated current market rates
        return {
            'conservative_hybrid': 8.0,
            'balanced_advantage': 9.5,
            'multi_asset': 10.0,
            'equity_savings': 8.5,
            'aggressive_hybrid': 11.0,
            'equity_large_cap': 12.0,
            'balanced': 7.2,
            'debt': 6.0
        }

    def _suggest_products(self, category: str, greeting: str, user_context: Dict) -> Dict:
        """Phase 1: Suggest 3-5 relevant products based on category"""
        suggestions = self._get_product_suggestions(category)

        response = f"{greeting}\n\nHere are some popular {category.replace('_', ' ')} options with current market prices:\n\n"

        for i, product in enumerate(suggestions, 1):
            response += f"**{i}. {product['name']}**\n"
            response += f"• Price: ₹{product['price']:,.0f}\n"
            response += f"• Key Features: {product['specs']}\n"
            if 'variants' in product:
                response += f"• Variants: {', '.join(product['variants'][:2])}\n"
            response += "\n"

        response += f"Which option interests you? Please tell me the name (e.g., \"{suggestions[0]['name']}\") or specify your preferred choice."

        # Set user context for product selection phase
        user_context['product_selected'] = False
        user_context['available_suggestions'] = suggestions
        user_context['category'] = category

        return {
            'message': response,
            'phase': 'product_suggestion',
            'suggestions': suggestions,
            'category': category,
            'awaiting_response': 'product_selection',
            'show_greeting': True
        }

    def _get_product_suggestions(self, category: str) -> List[Dict]:
        """Get product suggestions with current prices and specs from Excel file"""
        try:
            # Map chatbot categories to Excel sheet names
            excel_sheet_map = {
                'four_wheeler': 'Cars',
                'two_wheeler': 'Bikes',
                'electronics': 'Electronics'
            }

            # For loan categories, use fallback
            if category in ['home_loan', 'personal_loan', 'gold_loan', 'travel', 'hospitality']:
                fallbacks = {
                    'home_loan': [
                        {'name': '1BHK Flat', 'price': 2000000, 'specs': 'Standard amenities, metro connectivity'},
                        {'name': '2BHK Flat', 'price': 3500000, 'specs': 'Premium location, modern facilities'},
                        {'name': '3BHK Villa', 'price': 6000000, 'specs': 'Luxury lifestyle, garden, pool'}
                    ],
                    'personal_loan': [
                        {'name': 'Education Loan', 'price': 500000, 'specs': 'For higher education abroad'},
                        {'name': 'Wedding Loan', 'price': 300000, 'specs': 'Complete wedding package financing'},
                        {'name': 'Medical Loan', 'price': 200000, 'specs': 'Emergency medical expenses'}
                    ],
                    'gold_loan': [
                        {'name': 'Gold Jewelry', 'price': 100000, 'specs': '24K pure gold ornaments'},
                        {'name': 'Gold Coins', 'price': 200000, 'specs': 'Investment grade gold coins'},
                        {'name': 'Gold Bars', 'price': 500000, 'specs': 'Pure gold investment bars'}
                    ],
                    'travel': [
                        {'name': 'Domestic Vacation', 'price': 50000, 'specs': '4-star hotels, inclusive tours'},
                        {'name': 'International Trip', 'price': 150000, 'specs': 'Economy class, package deal'},
                        {'name': 'Luxury Travel', 'price': 300000, 'specs': 'Business class, premium hotels'}
                    ],
                    'hospitality': [
                        {'name': 'Business Hotel', 'price': 80000, 'specs': 'Business class, conference facilities'},
                        {'name': 'Resort Stay', 'price': 150000, 'specs': 'Premium resort, spa included'},
                        {'name': 'Luxury Suite', 'price': 250000, 'specs': '5-star presidential suite'}
                    ]
                }
                return fallbacks.get(category, [
                    {'name': f'Generic {category.replace("_", " ").title()} Option A', 'price': 50000, 'specs': 'Standard features'},
                    {'name': f'Generic {category.replace("_", " ").title()} Option B', 'price': 75000, 'specs': 'Premium features'}
                ])

            # Get Excel data for cars, bikes, electronics
            sheet_name = excel_sheet_map.get(category)
            if sheet_name == 'Cars':
                df = self.cars_df
            elif sheet_name == 'Bikes':
                df = self.bikes_df
            elif sheet_name == 'Electronics':
                df = self.electronics_df
            else:
                # Fallback to hardcoded data if sheet not found
                return [
                    {'name': 'Generic Product A', 'price': 50000, 'specs': 'Standard features'},
                    {'name': 'Generic Product B', 'price': 75000, 'specs': 'Premium features'},
                    {'name': 'Generic Product C', 'price': 100000, 'specs': 'Top-tier features'}
                ]

            if df.empty:
                return [
                    {'name': 'Generic Product A', 'price': 50000, 'specs': 'Standard features'},
                    {'name': 'Generic Product B', 'price': 75000, 'specs': 'Premium features'}
                ]

            # Convert DataFrame to list of dicts
            products = []
            for _, row in df.iterrows():
                if pd.notna(row['Approx_Price_INR']):
                    product_dict = {
                        'name': row['Name'],
                        'price': float(row['Approx_Price_INR']),
                        'specs': f"{row['Category']} - {row['Tier']} tier" if pd.notna(row['Tier']) else f"{row['Category']} - Standard tier",
                        'tier': row['Tier'] if pd.notna(row['Tier']) else 'Standard'
                    }
                    products.append(product_dict)

            # Get representative product selection based on price range for consistency
            if not products:
                return self._get_fallback_products(category)

            # Sort products by price for consistent selection
            products.sort(key=lambda x: x['price'])

            # Distribute products across price ranges for variety
            total_products = len(products)
            selected_products = []

            # Select from different price segments if available
            if total_products >= 8:
                # Take 2 from lower third, 4 from middle third, 2 from upper third
                indices = [
                    0, max(1, total_products//6),  # low price
                    total_products//3, total_products//2,  # mid-low price
                    total_products//2, (2*total_products)//3,  # mid-high price
                    (4*total_products)//6, (5*total_products)//6  # high price
                ]
                for idx in indices[:8]:  # Limit to 8 products max
                    if idx < total_products:
                        selected_products.append(products[idx])

            elif total_products >= 5:
                # For smaller datasets, take from different intervals
                step = max(1, total_products // 5)
                for i in range(0, min(total_products, 8), step):
                    selected_products.append(products[i])

            else:
                # For very small datasets, take all available
                selected_products = products[:8]

            # Ensure we have at least 3 products for meaningful suggestions
            if len(selected_products) < 3 and products:
                # If not enough after selection, take first 3
                selected_products = products[:3]

            return selected_products

        except Exception as e:
            print(f"Error getting product suggestions: {e}")
            return self._get_fallback_products(category)

    def _get_fallback_products(self, category: str) -> List[Dict]:
        """Get fallback products when Excel data is not available"""
        fallback_products = {
            'four_wheeler': [
                {'name': 'Hatchback Car', 'price': 600000, 'specs': 'Fuel efficient compact car'},
                {'name': 'Sedan Car', 'price': 800000, 'specs': 'Comfortable family sedan'},
                {'name': 'SUV', 'price': 1200000, 'specs': 'Spacious family SUV'}
            ],
            'two_wheeler': [
                {'name': 'Standard Motorcycle', 'price': 80000, 'specs': 'Fuel efficient commuter bike'},
                {'name': 'Scooter', 'price': 60000, 'specs': 'Easy handling for daily commute'},
                {'name': 'Sports Bike', 'price': 150000, 'specs': 'High performance motorcycle'}
            ],
            'electronics': [
                {'name': 'Smartphone', 'price': 25000, 'specs': 'Latest Android smartphone'},
                {'name': 'Laptop', 'price': 50000, 'specs': 'Mid-range laptop for work/study'},
                {'name': 'Smart TV', 'price': 40000, 'specs': '43-inch LED smart TV'}
            ],
            'home_loan': [
                {'name': '1BHK Flat', 'price': 2000000, 'specs': 'Standard amenities, metro connectivity'},
                {'name': '2BHK Flat', 'price': 3500000, 'specs': 'Premium location, modern facilities'}
            ],
            'personal_loan': [
                {'name': 'Education Loan', 'price': 500000, 'specs': 'For higher education abroad'},
                {'name': 'Wedding Loan', 'price': 300000, 'specs': 'Complete wedding package financing'}
            ],
            'gold_loan': [
                {'name': 'Gold Jewelry', 'price': 100000, 'specs': '24K pure gold ornaments'},
                {'name': 'Gold Coins', 'price': 200000, 'specs': 'Investment grade gold coins'}
            ],
            'travel': [
                {'name': 'Domestic Vacation', 'price': 50000, 'specs': '4-star hotels, inclusive tours'},
                {'name': 'International Trip', 'price': 150000, 'specs': 'Economy class, package deal'}
            ],
            'hospitality': [
                {'name': 'Business Hotel', 'price': 80000, 'specs': 'Business class, conference facilities'},
                {'name': 'Luxury Resort', 'price': 150000, 'specs': 'Premium resort, spa included'}
            ]
        }
        return fallback_products.get(category, [
            {'name': 'Generic Product A', 'price': 50000, 'specs': 'Standard features'},
            {'name': 'Generic Product B', 'price': 75000, 'specs': 'Premium features'}
        ])

    def _provide_product_analysis(self, selected_product: Dict, category: str, income: float, greeting: str, user_context: Dict) -> Dict:
        """Phase 2: Provide complete product analysis with EMIs"""
        # Confirm exact product name
        product_name = selected_product['name']
        product_price = selected_product['price']

        response = f"{greeting}\n\n"

        # Calculate average income (last 6 months)
        affordability_threshold = 20.0  # STRICT 20% rule

        # Check if product is affordable before proceeding
        if income:
            # Simulate EMI calculation for affordability check
            # Use 48 months (max tenure) to check if matches even the most lenient option
            loan_amount = product_price * 0.8
            mock_rate = self.fallback_rates.get(category, 12.0)
            
            # initial check with max tenure (48m) to see if product is at all viable
            affordable_emi = self.calculate_emi(loan_amount, mock_rate, 48)
            emi_ratio = (affordable_emi / income) * 100

            if emi_ratio > affordability_threshold:
                # Set context flags for flow management
                user_context['affordable'] = False
                user_context['awaiting_affordability_response'] = True
                user_context['selected_product'] = selected_product
                user_context['product_price'] = product_price
                user_context['category'] = category
                user_context['emi_ratio'] = emi_ratio
                user_context['threshold'] = affordability_threshold
                user_context['average_income'] = income

                response += f"**Price Analysis Alert**\n"
                response += f"Based on your average income of ₹{income:,.0f}, this product at ₹{product_price:,.0f} "
                response += f"would require an EMI of approximately ₹{affordable_emi:.0f}/month.\n"
                response += f"This represents {emi_ratio:.1f}% of your income, which exceeds the recommended {affordability_threshold}% threshold.\n\n"
                response += f"You may want to consider:\n"
                response += f"• A lower-priced variant\n"
                response += f"• Increasing your downpayment\n"
                response += f"• Creating a saving plan for this purchase\n\n"
                response += f"Would you like me to generate EMI plans anyway (Yes/No), or help you with saving options?"

                return {
                    'message': response,
                    'product_selected': True,
                    'selected_product': selected_product,
                    'affordable': False,
                    'emi_ratio': emi_ratio,
                    'threshold': affordability_threshold,
                    'awaiting_affordability_response': True,
                    'show_greeting': True
                }

        # Fetch real-time interest rates from trusted EMI providers
        try:
            banks_data = self._get_real_time_banks_and_rates(category)
            rate_source = "real-time rates from trusted banking sources"
        except Exception as e:
            banks_data = self._get_fallback_banks_and_rates(category)
            rate_source = "latest market rates"

        # Initialize empty breakdown for return statement
        emi_breakdown = []
        dp_options = []

        # Generate simple plans for different banks and tenures
        # Generate complete set of 10 plans (3x12m, 3x24m, 4x48m)
        downpayment_amount = product_price * 0.2
        loan_amount = product_price * 0.8

        target_structure = [
            (12, 3),  # 3 plans for 12 months
            (24, 3),  # 3 plans for 24 months
            (48, 4)   # 4 plans for 48 months
        ]

        plans = []
        plan_counter = 1
        available_banks = banks_data if banks_data else [{'name': 'Standard Bank', 'rate': 12.0}]

        for tenure, count in target_structure:
            for i in range(count):
                # Cycle through banks
                bank_idx = (i + (tenure // 12)) % len(available_banks)
                bank = available_banks[bank_idx]
                
                emi = self.calculate_emi(loan_amount, bank['rate'], tenure)
                
                # FILTER: Strictly enforce 20% affordability rule
                if income:
                    ratio = (emi / income) * 100
                    if ratio > 20.0:
                        continue # Skip unaffordable plans

                total_payable = round(emi * tenure + downpayment_amount, 2)

                # Add to emi_breakdown
                emi_breakdown.append({
                    'tenure': tenure,
                    'emi': emi,
                    'total_payable': total_payable,
                    'interest_paid': total_payable - product_price
                })

                plan = f"Plan {plan_counter}: {bank['name']} - {bank['rate']}%\n"
                if category != 'personal_loan':
                     plan += f"Downpayment\t₹{downpayment_amount:,.0f}\n"
                plan += f"Loan Amount\t₹{loan_amount:,.0f}\n"
                plan += f"Tenure\t\t{tenure} months\n"
                plan += f"EMI\t\t₹{emi:.0f}\n"
                plan += f"Interest Rate\t{bank['rate']}%\n"
                plan += f"Total Payable\t₹{total_payable:,.0f}\n\n"

                plans.append(plan)
                plan_counter += 1

        response += "".join(plans)
        response += "**Say 'save plan X' (e.g., 'save plan 1') to save a specific plan for later.**"

        return {
            'message': response,
            'product_selected': True,
            'selected_product': selected_product,
            'product_name': product_name,
            'product_price': product_price,
            'category': category,
            'average_income': income,
            'affordability_threshold': affordability_threshold,
            'emi_breakdown': emi_breakdown,
            'bank_options': banks_data,
            'downpayment_analysis': dp_options,
            'rate_source': rate_source,
            'affordable': True,
            'show_greeting': True
        }

    def _parse_direct_product(self, message: str, available_suggestions: List[Dict]) -> Optional[Dict]:
        """Parse direct product mention in message (e.g., "Honda City")"""
        message_lower = message.lower().strip()

        # Check if any product name is mentioned directly in the message
        for product in available_suggestions:
            product_name_lower = product['name'].lower()
            if product_name_lower in message_lower or message_lower == product_name_lower:
                return product

        return None

    def _ensure_context(self, user_context: Dict, key: str, value: Any) -> Dict:
        """Ensure context has a specific key-value pair"""
        if key not in user_context:
            user_context[key] = value
        return user_context

    def _handle_direct_product_selection(self, selected_product: Dict, category: str, user_context: Dict) -> Dict:
        """Handle direct product selection and go straight to analysis"""
        # Calculate 6-month average income automatically (NEVER ask)
        income_history = user_context.get('income_history', [])
        average_income_6months = None
        if income_history and len(income_history) >= 6:
            # Use last 6 months for 6-month average
            total_income_6months = sum(income_history[-6:])  # Last 6 months
            average_income_6months = total_income_6months / 6
        elif income_history:
            # If less than 6 months, use whatever is available
            total_income = sum(income_history)
            average_income_6months = total_income / len(income_history)

        greeting = "Hello! How can I help you today!"
        return self._provide_product_analysis(selected_product, category, average_income_6months, greeting, user_context)

    def _detect_direct_product_name(self, message: str) -> Optional[Tuple[Dict, str]]:
        """Detect if message contains a direct product name from our database"""
        message_lower = message.lower().strip()

        # Search through all categories for product matches
        all_categories = ['four_wheeler', 'two_wheeler', 'electronics', 'home_loan', 'personal_loan', 'gold_loan', 'travel', 'hospitality']

        for category in all_categories:
            suggestions = self._get_product_suggestions(category)
            for product in suggestions:
                product_name_lower = product['name'].lower()
                # Match if product name is contained in message or vice versa
                if product_name_lower in message_lower or message_lower in product_name_lower:
                    return product, category

        return None

    def _parse_product_selection(self, message: str, available_suggestions: List[Dict]) -> Optional[Dict]:
        """Parse user selection from suggestions - accepts number (1,2,3...) or name"""
        message_lower = message.lower().strip()

        # Check if it's a number selection (1, 2, 3, etc.)
        try:
            selection_num = int(message_lower)
            if 1 <= selection_num <= len(available_suggestions):
                return available_suggestions[selection_num - 1]  # 0-indexed
        except ValueError:
            pass

        # Check if it matches a product name (partial or full match)
        for product in available_suggestions:
            product_name_lower = product['name'].lower()
            if product_name_lower in message_lower or message_lower in product_name_lower:
                return product

        return None

    def validate_numeric_input(self, input_str: str) -> Optional[float]:
        """Validate and convert numeric input, ask for corrections if malformed"""
        try:
            # Remove currency symbols and commas
            clean_input = input_str.replace('₹', '').replace('rs', '').replace('Rs', '').replace(',', '').replace('.', '', input_str.count('.')-1 if '.' in input_str else 0)

            # Check for multiple decimal points
            if clean_input.count('.') > 1:
                raise ValueError("Multiple decimal points")

            value = float(clean_input)

            if value < 0:
                raise ValueError("Negative value")

            return value

        except (ValueError, AttributeError):
            return None

    def _enhance_response_with_groq(self, user_question: str, current_response: str, user_context: Dict) -> Dict:
        """
        Enhance chatbot response using Groq API for more intelligent financial advice
        Only used for complex queries that benefit from NLP understanding
        """
        if not self.enable_nlp_enhancement:
            return {'enhanced': False, 'response': current_response}

        try:
            # Import required modules for Groq API
            import requests

            # Prepare context for Groq API
            context_info = f"""
            User Context:
            - Average monthly income: ₹{user_context.get('average_income', 0):,.0f}
            - Available income history (last 6 months): {[f"₹{x:,.0f}" for x in user_context.get('income_history', [])[-6:]] if user_context.get('income_history') else 'Not available'}
            - Current product inquiry: {user_context.get('selected_product', {}).get('name', 'None')}
            - Product category: {user_context.get('category', 'None')}
            - Affordability threshold: 30% of monthly income

            Current chatbot response follows standard financial planning guidelines for Indian users:
            1. EMI should not exceed 30% of monthly income
            2. Prefer shorter loan tenures for cost savings
            3. Higher downpayments reduce EMI burden
            4. Personal loans and gold loans require careful consideration
            5. Always have emergency fund before major purchases
            """

            prompt = f"""
            You are an expert Indian financial advisor AI. Take the current chatbot response and enhance it with more personalized and intelligent financial advice.

            User Question: "{user_question}"

            Context Information:
            {context_info}

            Current Chatbot Response:
            {current_response}

            Instructions:
            1. Analyze the user's financial context and question depth
            2. Enhance the response with personalized financial insights
            3. Add specific Indian financial planning tips relevant to the situation
            4. Include relevant market context (e.g., current RBI policies, bank rate trends)
            5. Suggest alternatives or considerations not covered in the base response
            6. Keep responses focused on financial planning within allowed domains (products, EMIs, affordability, saving plans, travel, hospitality)
            7. Respond in English as the system uses English responses
            8. Keep response length reasonable (add 20-30% more content, not double)

            Do NOT mention that you're using any external AI or API. Present the enhanced advice seamlessly.
            """

            # Prepare Groq API request
            groq_payload = {
                "model": "llama3-8b-8192",  # Using Llama 3 model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior financial advisor specializing in Indian financial markets and consumer lending. Provide personalized, practical financial guidance while following Indian banking regulations and best practices."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "top_p": 0.95
            }

            # Make API call
            groq_response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json=groq_payload,
                timeout=10
            )

            if groq_response.status_code == 200:
                api_result = groq_response.json()
                enhanced_content = api_result['choices'][0]['message']['content'].strip()

                # Clean up the enhanced content to remove any system mentions
                enhanced_content = re.sub(r'^(I\'ll enhance|Based on|As an AI|)',
                                        '', enhanced_content, flags=re.MULTILINE).strip()

                return {
                    'enhanced': True,
                    'response': enhanced_content,
                    'original_response': current_response
                }
            else:
                print(f"Groq API error: {groq_response.status_code} - {groq_response.text}")
                return {'enhanced': False, 'response': current_response}

        except Exception as e:
            print(f"Error enhancing response with Groq: {e}")
            return {'enhanced': False, 'response': current_response}

    def _should_use_enhanced_nlp(self, question: str, response_type: str) -> bool:
        """
        Determine if the query would benefit from enhanced NLP analysis
        """
        if not self.enable_nlp_enhancement:
            return False

        # Use enhanced NLP for complex financial scenarios
        complex_indicators = [
            'complex financial situation',
            'multiple income sources',
            'tax implications',
            'investment strategy',
            'long-term planning',
            'budget optimization',
            'financial restructuring',
            'detailed analysis of',
            'compare options',
            'what if scenarios',
            'pros and cons analysis'
        ]

        question_lower = question.lower()

        # Check for complexity indicators
        for indicator in complex_indicators:
            if indicator in question_lower or 'multiple' in question_lower:
                return True

        # Use for savings and investment advice
        if response_type in ['saving_plan', 'affordability_check', 'investment_advice']:
            return True

        # Use for product analyses that involve multiple considerations
        if response_type == 'product_analysis' and any(word in question_lower for word in ['best', 'compare', 'pros', 'cons', 'analysis']):
            return True

        return False

    def _handle_saving_plan_flow(self, user_context: Dict, greeting: str) -> Dict:
        """Handle comprehensive saving plan flow when user says yes to unaffordable product"""
        selected_product = user_context.get('selected_product')
        average_income = user_context.get('average_income', 0)

        # Handle both dict and object types for selected_product
        if isinstance(selected_product, dict):
            product_name = selected_product.get('name', 'Unknown Product')
            product_price = selected_product.get('price', 0)
        else:
            # Handle object type (LoanProduct instance)
            product_name = selected_product.model_name if selected_product else 'Unknown Product'
            product_price = float(selected_product.price) if selected_product and selected_product.price else 0

        if not product_name or not average_income or average_income <= 0:
            return {
                'message': f"{greeting}\nUnable to create saving plan - missing product details or income data.",
                'show_greeting': True
            }

        # Check if this is a follow-up response for monthly savings amount
        if user_context.get('awaiting_monthly_savings_response'):
            # User has already provided monthly savings, now create the plan
            return self._create_comprehensive_saving_plan(user_context, greeting, product_name, product_price, average_income)

        # Initial step: Ask for monthly saving amount (fixed or percentage)
        response = f"{greeting}\n\nI can help you create a comprehensive savings plan for this **{product_name}** (₹{product_price:,.0f}).\n\n"

        # Use 6-month average income
        income_history = user_context.get('income_history', [])
        if income_history and len(income_history) >= 6:
            six_month_avg = sum(income_history[-6:]) / 6
            response += f"Your average monthly income (6 months): ₹{six_month_avg:,.0f}\n\n"
            display_income = six_month_avg
        else:
            response += f"Your average monthly income: ₹{average_income:,.0f}\n\n"
            display_income = average_income

        # Calculate suggested savings (between 20-30% of income for affordability)
        suggested_savings_min = int(display_income * 0.20)
        suggested_savings_max = int(display_income * 0.30)
        suggested_percent_min = 20
        suggested_percent_max = 30

        response += f"**How much can you save every month for this purchase?**\n\n"
        response += f"**Suggested savings:** ₹{suggested_savings_min:,.0f} to ₹{suggested_savings_max:,.0f}/month\n"
        response += f"   ({suggested_percent_min}%-{suggested_percent_max}% of your income)\n\n"

        response += f"**Please tell me your monthly savings:**\n"
        response += f"• Specific amount (e.g., ₹{suggested_savings_min:,.0f})\n"
        response += f"• Percentage of income (e.g., 25%)\n\n"
        response += f"• Or tell me 'I want EMI-free purchase' if you want to save the full amount upfront."

        # Set context for waiting for savings input
        user_context['awaiting_monthly_savings_response'] = True
        user_context['saving_plan_target_product'] = product_name
        user_context['saving_plan_target_price'] = product_price
        user_context['saving_plan_income'] = display_income

        return {
            'message': response,
            'awaiting_response': 'monthly_savings_amount',
            'saving_plan_target': product_price,
            'saving_plan_product': product_name,
            'suggested_savings': {'min': suggested_savings_min, 'max': suggested_savings_max},
            'show_greeting': True
        }

    def _create_comprehensive_saving_plan(self, user_context: Dict, greeting: str, product_name: str, product_price: float, average_income: float) -> Dict:
        """Create comprehensive saving plan with all required calculations and scenarios"""

        # Extract monthly savings from user's previous input
        user_message = user_context.get('last_message', '').strip().lower()

        # Parse monthly savings amount from user's response
        monthly_savings = None
        savings_type = 'amount'  # 'amount' or 'percentage'

        # Check for percentage first
        percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', user_message)
        if percent_match:
            try:
                percent = float(percent_match.group(1))
                monthly_savings = average_income * (percent / 100)
                savings_type = 'percentage'
            except ValueError:
                pass

        # Check for absolute amount if percentage not found
        if monthly_savings is None:
            amount_patterns = [
                r'save\s*[₹rs\.]*\b(\d+(?:,\d+)*)\b',
                r'(\d+(?:,\d+)*)\s*per month',
                r'(\d+(?:,\d+)*)\s*month',
                r'₹?\s*(\d+(?:,\d+)*)'
            ]
            for pattern in amount_patterns:
                match = re.search(pattern, user_message)
                if match:
                    try:
                        monthly_savings = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue

        # Check for EMI-free request
        if 'emi-free' in user_message or 'full amount' in user_message or 'upfront' in user_message:
            # Calculate savings needed for EMI-free purchase (aim for 24-36 months)
            target_tenure = 24 if product_price < 100000 else (36 if product_price < 500000 else 48)
            monthly_savings = product_price / target_tenure
            savings_type = 'emi_free'

        # Validate savings amount
        if monthly_savings is None or monthly_savings <= 100:
            # Invalid or too low - ask again
            return {
                'message': f"{greeting}\n\nI couldn't understand your monthly savings amount. Please provide:\n• A specific amount (e.g., ₹5,000)\n• A percentage of your income (e.g., 25%)\n• Or 'EMI-free purchase' for full upfront payment plan.",
                'awaiting_response': 'monthly_savings_amount',
                'saving_plan_target': product_price,
                'saving_plan_product': product_name,
                'show_greeting': True
            }

        # Calculate target amount (assume 20% downpayment for loan portion, full amount for savings)
        downpayment = product_price * 0.20
        remaining_amount = product_price - downpayment  # This is what we save for

        # Generate comprehensive saving plan
        response = f"{greeting}\n\n**Comprehensive Saving Plan for {product_name}**\n\n"
        response += f"**Target Purchase:** ₹{product_price:,.0f}\n"
        response += f"**Planned Downpayment:** ₹{downpayment:,.0f} (20%)\n"
        response += f"**Amount to Save:** ₹{remaining_amount:,.0f}\n"
        response += f"**Your Monthly Savings:** ₹{monthly_savings:,.0f} "
        if savings_type == 'percentage' and 'percent_match' in locals():
            response += f"({int(float(percent_match.group(1)))}% of income)"
        elif savings_type == 'emi_free':
            response += f"(EMI-free target)"
        response += f"\n**Average Monthly Income:** ₹{average_income:,.0f}\n\n"

        # Calculate base timeline
        months_needed = math.ceil(remaining_amount / monthly_savings)
        years_needed = months_needed // 12
        remaining_months = months_needed % 12

        response += f"**Base Saving Timeline**\n"
        response += f"• **{months_needed} months** ({years_needed} years, {remaining_months} months)\n"
        response += f"• **Total Saved:** ₹{remaining_amount:,.0f}\n"
        if savings_type != 'emi_free':
            response += f"• **Savings Gap:** ₹{monthly_savings * months_needed - remaining_amount:,.0f} (can build emergency fund)\n\n"
        else:
            response += f"• **EMI-Free Purchase** - No loan needed!\n\n"

        # Acceleration scenarios (10%, 20%, 50% increases in monthly saving)
        if savings_type != 'emi_free':
            response += "**Acceleration Scenarios**\n"
            acceleration_rates = [10, 20, 50]

            for accel_rate in acceleration_rates:
                faster_savings = monthly_savings * (1 + accel_rate / 100)
                accel_months = math.ceil(remaining_amount / faster_savings)
                savings_years = accel_months // 12
                savings_rem_months = accel_months % 12
                time_saved = months_needed - accel_months

                response += f"• **{accel_rate}% Increase:** Save ₹{faster_savings:,.0f}/month\n"
                response += f"  - Reach goal in **{accel_months} months** ({savings_years}y {savings_rem_months}m)\n"
                response += f"  - **{time_saved} months sooner!**\n"
                if accel_months <= 12:
                    response += f"  - Excellent - achieve in under 1 year!\n"
                elif accel_months <= 24:
                    response += f"  - Great - achieve within 2 years!\n"
                response += "\n"

        # Income growth scenarios (5%, 10%, 20% income increases)
        response += "**Income Growth Scenarios**\n"
        response += f"If your income increases, you can accelerate your savings plan!\n\n"

        income_growth_rates = [5, 10, 20]

        for growth_rate in income_growth_rates:
            # New income with growth
            new_income = average_income * (1 + growth_rate / 100)

            # Calculate new monthly savings based on user's savings type
            if savings_type == 'percentage' and 'percent_match' in locals():
                # If user saves as percentage, more income means more monthly savings
                original_percent = float(percent_match.group(1))
                new_monthly_savings = new_income * (original_percent / 100)
                savings_increase = new_monthly_savings - monthly_savings
                response += f"• **{growth_rate}% Income Growth:** ₹{new_income:,.0f}/month\n"
                response += f"  - Monthly savings increase: ₹{savings_increase:,.0f} (maintain {original_percent}% rate)\n"
            else:
                # For fixed amount or EMI-free savings, keep the same monthly savings
                new_monthly_savings = monthly_savings
                response += f"• **{growth_rate}% Income Growth:** ₹{new_income:,.0f}/month\n"
                response += f"  - Continue saving ₹{monthly_savings:,.0f}/month unchanged\n"

            growth_months = math.ceil(remaining_amount / new_monthly_savings)
            growth_years = growth_months // 12
            growth_rem_months = growth_months % 12
            income_time_saved = months_needed - growth_months

            response += f"  - Could reach goal in **{growth_months} months** ({growth_years}y {growth_rem_months}m)\n"
            response += f"  - **{income_time_saved} months sooner!**\n"
            if growth_months <= 6:
                response += f"  - Amazing - achieve in 6 months!\n"
            elif growth_months <= 12:
                response += f"  - Strong growth pays off!\n"
            response += "\n"

        # Practical recommendations
        response += "**Practical Recommendations**\n"
        if months_needed > 36:
            response += "• **Long-term Plan:** Consider investments like RD/SIP for better returns\n"
            response += "• **Split Strategy:** Save for downpayment now, finance remaining later\n"
        elif months_needed > 24:
            response += "• **Medium-term Plan:** Use RD (Recurring Deposit) for disciplined savings\n"
            response += "• **Check Promotions:** Look for discounts and offers\n"
        else:
            response += "• **Short-term Goal:** High five! You can achieve this quickly\n"
            response += "• **Emergency Fund:** Maintain 3-6 months of expenses as backup\n"

        # Monthly tracking advice
        response += "\n**Tracking Your Progress**\n"
        response += f"• **Monthly Target:** ₹{monthly_savings:,.0f}\n"
        response += f"• **Total Months:** {months_needed}\n"
        response += f"• **Cumulative Savings:**\n"

        # Show quarterly milestones
        cumulative = 0
        for quarter in range(1, min(9, (months_needed // 3) + 2)):
            quarter_savings = monthly_savings * min(3, months_needed - ((quarter-1) * 3))
            cumulative += quarter_savings
            response += f"  - Quarter {quarter}: ₹{cumulative:,.0f}\n"

        # Savings methods and investment options
        response += "\n**Savings Methods (ROI as of 2024)**\n"
        response += "• **RD (Recurring Deposit):** 5.5-6.5% p.a.\n"
        response += "• **Savings Account:** 3-4% p.a. (safe)\n"
        response += "• **FD (Fixed Deposit):** 5.3-6.0% p.a.\n"
        response += "• **SIP (Systematic Investment):** 8-12% p.a. (higher risk, higher return)\n\n"

        response += "**Say 'save this plan' to store these recommendations for future reference.**"

        # Clear the awaiting response state
        user_context['awaiting_monthly_savings_response'] = False

        return {
            'message': response,
            'saving_plan_generated': True,
            'product_name': product_name,
            'product_price': product_price,
            'monthly_savings': monthly_savings,
            'savings_type': savings_type,
            'base_timeline': {
                'months': months_needed,
                'years': years_needed,
                'remaining_months': remaining_months
            },
            'acceleration_scenarios': [
                {
                    'rate': accel_rate,
                    'monthly_savings': monthly_savings * (1 + accel_rate / 100),
                    'months_needed': math.ceil(remaining_amount / (monthly_savings * (1 + accel_rate / 100))),
                    'time_saved': months_needed - math.ceil(remaining_amount / (monthly_savings * (1 + accel_rate / 100)))
                } for accel_rate in [10, 20, 50] if savings_type != 'emi_free'
            ],
            'income_growth_scenarios': [
                {
                    'growth_rate': growth_rate,
                    'new_income': average_income * (1 + growth_rate / 100),
                    'months_needed': math.ceil(remaining_amount / monthly_savings),
                    'time_saved': months_needed - math.ceil(remaining_amount / monthly_savings)
                } for growth_rate in [5, 10, 20]
            ],
            'show_greeting': True
        }

    def _handle_affordability_alternatives(self, user_context: Dict, greeting: str) -> Dict:
        """Handle when user says no to unaffordable product - suggest affordable alternatives"""
        if user_context is None:
            user_context = {}

        average_income = user_context.get('average_income', 0)
        category = user_context.get('category', '')

        # Acknowledge the answer and start with required message
        response = f"Thank you for your answer. Now I will show products that are affordable for you.\n\n"

        # Calculate affordable price range based on recommended EMI threshold (30% of income)
        if average_income > 0:
            affordable_emi_max = average_income * 0.30  # 30% threshold for EMI
            # Calculate maximum affordable price using standard loan assumption (24 months, 13% rate, 20% down)
            # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
            r = 0.13 / 12  # Monthly rate (13% APR)
            n = 24  # Standard 24-month tenure
            # Rearranged formula for principal: P = EMI * ((1+r)^n - 1) / (r * (1+r)^n)
            denominator = r * (1 + r) ** n
            numerator = (1 + r) ** n - 1
            max_principal = affordable_emi_max * (numerator / denominator)

            # Account for 20% downpayment
            max_affordable_price = max_principal / 0.8

            response += f"**Affordable Price Range**\n"
            response += f"• Based on ₹{average_income:,.0f}/month income\n"
            response += f"• Maximum EMI: ₹{affordable_emi_max:,.0f}/month (30% of income)\n"
            response += f"• Maximum price range: ₹{max_affordable_price:,.0f}\n\n"
        else:
            max_affordable_price = 100000  # Default if no income data

        # Get suggestions and find affordable ones
        suggestions = self._get_product_suggestions(category)
        affordable_products = []

        if suggestions and average_income:
            for product in suggestions:
                if product['price'] <= max_affordable_price and product['price'] > 0:
                    # Quick EMI calculation to verify affordability
                    loan_amount = product['price'] * 0.8
                    emi = self.calculate_emi(loan_amount, self.fallback_rates.get(category, 13.0), 24)
                    ratio = (emi / average_income) * 100

                    if ratio <= 30:  # Only include truly affordable ones
                        product_copy = product.copy()
                        product_copy['estimated_emi'] = emi
                        product_copy['emi_ratio'] = ratio
                        affordable_products.append(product_copy)

        # Limit to top 3-4 suggestions
        affordable_products = affordable_products[:4]

        if affordable_products:
            response += "**Suggested Affordable Products**\n\n"
            for i, product in enumerate(affordable_products, 1):
                response += f"**{i}. {product['name']}**\n"
                response += f"• Price: ₹{product['price']:,.0f}\n"
                response += f"• EMI: ₹{product['estimated_emi']:,.0f}/month\n"
                response += f"• Specs: {product['specs']}\n\n"

            response += "Select a product by number (1-4) or name to proceed with EMI planning."

            # Set context for user selection
            user_context['available_suggestions'] = affordable_products
            user_context['awaiting_response'] = 'product_selection'
        else:
            response += "No products found in your affordable price range. Consider:\n\n"
            response += "• Checking other product categories\n"
            response += "• Creating a saving plan for more expensive options\n"
            response += "• Exploring used/refurbished products"

        return {
            'message': response,
            'affordable_products': affordable_products,
            'calculated_price_range': max_affordable_price,
            'max_affordable_emi': affordable_emi_max if 'affordable_emi_max' in locals() else None,
            'awaiting_response': 'product_selection' if affordable_products else 'explore_alternatives'
        }

    def _handle_modify_saved_plans(self, message: str, user_context: Dict, user: User = None) -> Dict:
        """Handle request to modify saved plans - show plans and allow selection for modification"""
        greeting = "Hello! How can I help you today?"

        # Check if user wants to modify a specific plan
        plan_num_match = re.search(r'modify\s+plan\s*(?:#|)(\w+)', message.lower())
        if plan_num_match:
            plan_id = f"plan_{plan_num_match.group(1)}"
            return self._handle_modify_specific_plan(plan_id, user_context, user)

        # Otherwise, show all saved plans for modification
        saved_plans = []

        if user:
            # Get plans from database
            db_plans = SavedPlan.objects.filter(user=user).order_by('-created_at')
            for plan in db_plans:
                saved_plans.append({
                    'plan_id': plan.plan_id,
                    'product': plan.product,
                    'price': float(plan.price),
                    'downpayment': float(plan.downpayment),
                    'loan_amount': float(plan.loan_amount),
                    'interest_rate': float(plan.interest_rate),
                    'tenure': plan.tenure,
                    'emi': float(plan.emi),
                    'total_paid': float(plan.total_paid),
                    'notes': plan.notes,
                    'created_at': plan.created_at.isoformat(),
                })

        if not saved_plans:
            return {
                'message': f"{greeting}\nYou don't have any saved plans to modify. Create a plan first by discussing a product purchase.",
                'show_greeting': True
            }

        response = f"{greeting}\n\n**Your Saved Financial Plans - Select Plan to Modify**\n\n"
        for i, plan in enumerate(saved_plans, 1):
            response += f"**{i}. Plan #{plan['plan_id']} - {plan['product']}**\n"
            response += f"   • Price: ₹{plan['price']:,.0f}\n"
            response += f"   • EMI: ₹{plan['emi']:,.0f} ({plan['tenure']} months)\n"
            response += f"   • Total Paid: ₹{plan['total_paid']:,.0f}\n\n"

        response += "**To modify a plan, tell me the plan number** (e.g., \"modify plan 1\" or \"modify plan_1\")\n\n"
        response += "**What parameter would you like to change?**\n"
        response += "• Downpayment percentage\n"
        response += "• Loan tenure (months)\n"
        response += "• Interest rate\n\n"
        response += "**Current example:** Say \"modify plan 1\" to change the first plan."

        return {
            'message': response,
            'saved_plans': saved_plans,
            'action': 'show_plans_for_modification',
            'show_greeting': True
        }

    def _handle_modify_specific_plan(self, plan_id: str, user_context: Dict, user: User = None) -> Dict:
        """Handle modification of a specific saved plan"""
        greeting = "Hello! How can I help you today?"

        if not user:
            return {
                'message': f"{greeting}\nPlease log in to modify plans.",
                'show_greeting': True
            }

        try:
            plan = SavedPlan.objects.get(user=user, plan_id=plan_id)
        except SavedPlan.DoesNotExist:
            return {
                'message': f"{greeting}\nPlan {plan_id} not found. Please check your saved plans.",
                'show_greeting': True
            }

        # Show current plan details and modification options
        response = f"{greeting}\n\n**Modifying Plan #{plan_id} - {plan.product}**\n\n"
        response += f"**Current Plan Details:**\n"
        response += f"• Product: {plan.product}\n"
        response += f"• Price: ₹{plan.price:,.0f}\n"
        response += f"• Downpayment: {plan.downpayment}%\n"
        response += f"• Loan Amount: ₹{plan.loan_amount:,.0f}\n"
        response += f"• Interest Rate: {plan.interest_rate}%\n"
        response += f"• Tenure: {plan.tenure} months\n"
        response += f"• EMI: ₹{plan.emi:,.0f}\n"
        response += f"• Total Paid: ₹{plan.total_paid:,.0f}\n\n"

        response += "**What would you like to change?**\n\n"
        response += "**Available Options:**\n"
        response += "1. **Change downpayment** - Reply \"change downpayment to 25%\"\n"
        response += "2. **Change tenure** - Reply \"change tenure to 36 months\"\n"
        response += "3. **Change interest rate** - Reply \"change rate to 12.5%\"\n\n"

        response += "**Examples:**\n"
        response += "• \"change downpayment to 30%\"\n"
        response += "• \"change tenure to 48 months\"\n"
        response += "• \"change rate to 11.5%\"\n\n"

        response += "**The new EMI and total cost will be recalculated automatically.**"

        # Set context for awaiting modification input
        user_context['awaiting_plan_modification'] = True
        user_context['modifying_plan_id'] = plan_id
        user_context['current_plan_data'] = {
            'product': plan.product,
            'price': float(plan.price),
            'original_downpayment': float(plan.downpayment),
            'original_tenure': plan.tenure,
            'original_rate': float(plan.interest_rate)
        }

        return {
            'message': response,
            'awaiting_plan_modification': True,
            'modifying_plan_id': plan_id,
            'current_plan': {
                'plan_id': plan.plan_id,
                'product': plan.product,
                'price': float(plan.price),
                'downpayment': float(plan.downpayment),
                'tenure': plan.tenure,
                'interest_rate': float(plan.interest_rate),
                'emi': float(plan.emi),
                'total_paid': float(plan.total_paid)
            },
            'show_greeting': True
        }

    def _handle_unsave_plan(self, message: str, user_context: Dict, user: User = None) -> Dict:
        """Handle request to unsave/cancel a plan"""
        greeting = "Hello! How can I help you today?"

        # Extract plan ID from message
        plan_match = re.search(r'(?:unsave|cancel)\s+plan\s*(?:#|)(\w+)', message.lower())
        if not plan_match:
            return {
                'message': f"{greeting}\nPlease specify which plan to remove. Example: \"unsave plan_1\" or \"cancel plan 2\"",
                'show_greeting': True
            }

        plan_id_indicator = plan_match.group(1)
        plan_id = f"plan_{plan_id_indicator}" if not plan_id_indicator.startswith('plan_') else plan_id_indicator

        if not user:
            return {
                'message': f"{greeting}\nPlease log in to manage plans.",
                'show_greeting': True
            }

        try:
            plan = SavedPlan.objects.get(user=user, plan_id=plan_id)
            product_name = plan.product
            plan.delete()

            return {
                'message': f"{greeting}\n✅ **Plan unsaved successfully!**\n\nRemoved plan for **{product_name}**.\n\nSay \"show my saved plans\" to see remaining plans.",
                'plan_removed': plan_id,
                'product_name': product_name,
                'show_greeting': True
            }

        except SavedPlan.DoesNotExist:
            return {
                'message': f"{greeting}\nPlan {plan_id} not found. Please check your saved plans.",
                'show_greeting': True
            }
        except Exception as e:
            return {
                'message': f"{greeting}\n❌ Error removing plan: {str(e)}",
                'show_greeting': True
            }

    def _handle_plan_modification_input(self, message: str, user_context: Dict, user: User = None) -> Dict:
        """Handle user input for plan modification (e.g., 'change downpayment to 25%')"""
        greeting = "Hello! How can I help you today?"

        # Extract modification parameters from the message
        message_lower = message.lower().strip()

        if not user:
            return {
                'message': f"{greeting}\nPlease log in to modify plans.",
                'show_greeting': True
            }

        # Get plan ID from context
        plan_id = user_context.get('modifying_plan_id')
        if not plan_id:
            return {
                'message': f"{greeting}\nNo plan selected for modification. Please say 'modify saved plans' first.",
                'show_greeting': True
            }

        try:
            plan = SavedPlan.objects.get(user=user, plan_id=plan_id)
        except SavedPlan.DoesNotExist:
            return {
                'message': f"{greeting}\nPlan {plan_id} not found. Please check your saved plans.",
                'show_greeting': True
            }

        # Get original values for recalculation
        original_data = user_context.get('current_plan_data', {})

        new_downpayment_pct = original_data.get('original_downpayment', float(plan.downpayment))
        new_tenure = original_data.get('original_tenure', plan.tenure)
        new_rate = original_data.get('original_rate', float(plan.interest_rate))

        changes_made = []

        # Parse downpayment changes
        dp_match = re.search(r'change\s+downpayment\s+to\s*(\d+(?:\.\d+)?)\s*%', message_lower)
        if dp_match:
            try:
                new_downpayment_pct = float(dp_match.group(1))
                # Validate downpayment percentage
                if 0 <= new_downpayment_pct <= 100:
                    changes_made.append(f"Downpayment: {new_downpayment_pct}%")
                else:
                    return {
                        'message': f"{greeting}\n❌ Invalid downpayment percentage. Please use a value between 0% and 100%.",
                        'awaiting_plan_modification': True,
                        'modifying_plan_id': plan_id,
                        'show_greeting': True
                    }
            except ValueError:
                pass

        # Parse tenure changes
        tenure_match = re.search(r'change\s+tenure\s+to\s*(\d+)\s*month', message_lower)
        if tenure_match:
            try:
                new_tenure = int(tenure_match.group(1))
                # Validate tenure (6-60 months reasonable range)
                if 6 <= new_tenure <= 60:
                    changes_made.append(f"Tenure: {new_tenure} months")
                else:
                    return {
                        'message': f"{greeting}\n❌ Invalid tenure. Please use a value between 6 and 60 months.",
                        'awaiting_plan_modification': True,
                        'modifying_plan_id': plan_id,
                        'show_greeting': True
                    }
            except ValueError:
                pass

        # Parse rate changes
        rate_match = re.search(r'change\s+rate\s+to\s*(\d+(?:\.\d+)?)\s*%', message_lower)
        if rate_match:
            try:
                new_rate = float(rate_match.group(1))
                # Validate interest rate (reasonable range 8-25%)
                if 8.0 <= new_rate <= 25.0:
                    changes_made.append(f"Interest Rate: {new_rate}%")
                else:
                    return {
                        'message': f"{greeting}\n❌ Invalid interest rate. Please use a value between 8% and 25%.",
                        'awaiting_plan_modification': True,
                        'modifying_plan_id': plan_id,
                        'show_greeting': True
                    }
            except ValueError:
                pass

        # If no changes detected, show error and keep awaiting
        if not changes_made:
            return {
                'message': f"{greeting}\n❌ I couldn't understand your modification. Please use one of these formats:\n• change downpayment to 25%\n• change tenure to 36 months\n• change rate to 12.5%",
                'awaiting_plan_modification': True,
                'modifying_plan_id': plan_id,
                'show_greeting': True
            }

        # Recalculate EMI with new parameters
        product_price = float(plan.price)

        # Calculate new loan amount based on downpayment percentage
        downpayment_amount = product_price * (new_downpayment_pct / 100)
        new_loan_amount = product_price - downpayment_amount

        # Calculate new EMI
        new_emi = self.calculate_emi(new_loan_amount, new_rate, new_tenure)

        # Calculate new total paid
        new_total_paid = downpayment_amount + (new_emi * new_tenure)

        # Update the plan in database
        plan.downpayment = Decimal(str(new_downpayment_pct))
        plan.loan_amount = Decimal(str(new_loan_amount))
        plan.interest_rate = Decimal(str(new_rate))
        plan.tenure = new_tenure
        plan.emi = Decimal(str(new_emi))
        plan.total_paid = Decimal(str(new_total_paid))
        plan.save()

        # Create response showing changes
        response = f"{greeting}\n\n✅ **Plan Modified Successfully!**\n\n"
        response += f"**Updated Plan #{plan_id} - {plan.product}**\n\n"
        response += "**Changes Made:**\n"
        for change in changes_made:
            response += f"• {change}\n"
        response += "\n"

        response += "**Updated Plan Details:**\n"
        response += f"• Product Price: ₹{product_price:,.0f}\n"
        response += f"• Downpayment: {new_downpayment_pct}% (₹{downpayment_amount:,.0f})\n"
        response += f"• Loan Amount: ₹{new_loan_amount:,.0f}\n"
        response += f"• Interest Rate: {new_rate}% p.a.\n"
        response += f"• Tenure: {new_tenure} months\n"
        response += f"• New EMI: ₹{new_emi:,.0f}\n"
        response += f"• Total Payable: ₹{new_total_paid:,.0f}\n\n"

        # Show savings/benefits if applicable
        original_emi = float(plan.emi) - new_emi  # Difference (simplified)
        if abs(original_emi) > 100:  # Significant change
            if original_emi > 0:
                response += f"🎉 **Great! Your EMI decreased by ₹{original_emi:,.0f} per month!**\n\n"
            else:
                response += f"⚠️ **Note: Your EMI increased by ₹{-original_emi:,.0f} per month.**\n\n"

        response += "**Say 'show my saved plans' to view all plans or 'modify another plan' to continue.**"

        # Clear modification context
        user_context.pop('awaiting_plan_modification', None)
        user_context.pop('modifying_plan_id', None)
        user_context.pop('current_plan_data', None)

        return {
            'message': response,
            'plan_modified': plan_id,
            'changes': changes_made,
            'new_emi': new_emi,
            'new_total_paid': new_total_paid,
            'show_greeting': True
        }

# Global instance
_chatbot = None

def get_chatbot() -> SpecializedFinancialChatbot:
    """Get the chatbot instance"""
    global _chatbot
    if _chatbot is None:
        _chatbot = SpecializedFinancialChatbot()
    return _chatbot

def answer_financial_question(question: str, user_income: float = 0, item_price: float = 0, emi: float = 0, user_context: Dict = None) -> Dict:
    """
    Entry point for the specialized chatbot
    """
    chatbot = get_chatbot()

    # Build user context
    context = user_context or {}
    if user_income:
        context['average_income'] = user_income
    if item_price:
        context['product_price'] = item_price
    if emi:
        context['emi'] = emi

    return chatbot.process_message(question, context)

if __name__ == "__main__":
    # Test the chatbot
    chatbot = SpecializedFinancialChatbot()

    test_messages = [
        "I want to buy a car for 8 lakhs",
        "How much should I save per month?",
        "Can I afford an EMI of 5000?",
        "I want to go on vacation",
    ]

    for msg in test_messages:
        print(f"\nUser: {msg}")
        response = chatbot.process_message(msg, {'average_income': 50000})
        print(f"Bot: {response['message']}")
        print("-" * 80)
