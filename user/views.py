from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta
from django.db.models import Sum
from user.models import Transaction, LoanProduct, AIConsultation, Budget, UserProfile
from django.conf import settings
from financial_chatbot import answer_financial_question, get_chatbot


def is_user_profile_ready(user):
    """Check if user has at least 6 months of transaction history"""
    from datetime import date
    from django.db.models import Min
    
    first_txn = Transaction.objects.filter(user=user).aggregate(first_date=Min('date'))['first_date']
    if first_txn:
        days_active = (date.today() - first_txn).days
        return days_active >= 180
    return False

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
    # Get available loan products and deduplicate
    all_products = LoanProduct.objects.all()
    seen_products = set()
    loan_products = []

    for product in all_products:
        # Create a unique key for the product to identify duplicates
        product_key = (
            product.model_name,
            product.bank_name,
            product.interest_rate,
            product.price,
            product.emi,
            product.tenure_months
        )

        if product_key not in seen_products:
            seen_products.add(product_key)
            loan_products.append(product)
    
    # Get consultation history
    consultations = AIConsultation.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Check financial profile readiness
    profile_ready = is_user_profile_ready(request.user)
    
    context = {
        'average_monthly_income': average_monthly_income,
        'loan_products': loan_products,
        'consultations': consultations,
        'monthly_income_data': json.dumps(monthly_income),
        'profile_ready': profile_ready
    }
    
    return render(request, 'user/ai_financial_insights.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def ai_chat_api(request):
    """API endpoint for AI chat with financial insights"""
    try:
        data = json.loads(request.body)
        
        # Check profile readiness
        if not is_user_profile_ready(request.user):
            return JsonResponse({
                'error': 'Financial profile not ready.',
                'reply': 'I cannot provide insights until you have at least 6 months of financial history. Please add more transaction data.'
            }, status=403)
            
        user_message = data.get('message', '').strip()
        selected_item_id = data.get('selected_item_id')

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        # Always include the latest consultation_id for this user if it exists
        current_consultation = None
        consultation_id = None

        try:
            # Get the most recent consultation for this user (regardless of completion status)
            current_consultation = AIConsultation.objects.filter(
                user=request.user
            ).order_by('-created_at').first()

            if current_consultation:
                consultation_id = current_consultation.id
                print(f"DEBUG: Found current_consultation ID: {consultation_id}")
            else:
                print("DEBUG: No existing consultation found for user")

        except Exception as e:
            print(f"DEBUG: Error getting consultation: {e}")

        # Get selected loan product if provided
        selected_item = None

        if selected_item_id:
            # Handle fallback IDs that don't exist in database
            if str(selected_item_id) in ['9991', '9992', '9993', '9994', '9995', '9996', '9997', '9998']:
                # Create a temporary LoanProduct object based on fallback data
                fallback = {
                    '9991': {'category': 'home_loan', 'model_name': 'Home Loan', 'price': 5000000, 'emi': 45000, 'bank_name': 'State Bank of India (SBI)', 'interest_rate': 10.5, 'tenure_months': 240},
                    '9992': {'category': 'home_loan', 'model_name': 'Home Loan', 'price': 3000000, 'emi': 28000, 'bank_name': 'HDFC Bank', 'interest_rate': 11.3, 'tenure_months': 240},
                    '9993': {'category': 'personal_loan', 'model_name': 'Personal Loan', 'price': 200000, 'emi': 8500, 'bank_name': 'HDFC Bank', 'interest_rate': 12.5, 'tenure_months': 60},
                    '9994': {'category': 'personal_loan', 'model_name': 'Personal Loan', 'price': 150000, 'emi': 6250, 'bank_name': 'ICICI Bank', 'interest_rate': 13.2, 'tenure_months': 48},
                    '9995': {'category': 'gold_loan', 'model_name': 'Gold Loan', 'price': 100000, 'emi': 2250, 'bank_name': 'HDFC Bank', 'interest_rate': 9.5, 'tenure_months': 60},
                    '9996': {'category': 'two_wheeler', 'model_name': 'Two Wheeler Loan', 'price': 100000, 'emi': 3500, 'bank_name': 'HDFC Bank', 'interest_rate': 11.8, 'tenure_months': 60},
                    '9997': {'category': 'four_wheeler', 'model_name': 'Car Loan', 'price': 800000, 'emi': 22000, 'bank_name': 'ICICI Bank', 'interest_rate': 13.5, 'tenure_months': 84},
                    '9998': {'category': 'electronics', 'model_name': 'Electronic Device Loan', 'price': 80000, 'emi': 2800, 'bank_name': 'Bajaj Finance (NBFC)', 'interest_rate': 14.5, 'tenure_months': 48}
                }.get(str(selected_item_id))

                if fallback:
                    category_display_map = {
                        'home_loan': 'Home Loan',
                        'personal_loan': 'Personal Loan',
                        'gold_loan': 'Gold Loan',
                        'two_wheeler': 'Two Wheeler',
                        'four_wheeler': 'Four Wheeler',
                        'electronics': 'Electronics'
                    }
                    # Create a temporary object-like structure - no import needed inside scope
                    selected_item = type('TempLoanProduct', (), {
                        'id': int(selected_item_id),
                        'category': fallback['category'],
                        'model_name': fallback['model_name'],
                        'price': fallback['price'],
                        'emi': fallback['emi'],
                        'bank_name': fallback['bank_name'],
                        'interest_rate': fallback['interest_rate'],
                        'tenure_months': fallback['tenure_months'],
                        'item_id': int(selected_item_id),  # Add missing item_id
                        'get_category_display': lambda fallback=fallback: category_display_map.get(
                            fallback['category'], fallback['category']
                        )
                    })()
            else:
                selected_item = get_object_or_404(LoanProduct, id=selected_item_id)

        # Calculate last 6 months income data (automatically, never ask user)
        six_months_ago = datetime.now() - timedelta(days=180)
        income_transactions_agg = Transaction.objects.filter(
            user=request.user,
            transaction_type='income',
            date__gte=six_months_ago
        ).values('amount')

        # Build income history for last 6 months (list of monthly incomes)
        income_history = []
        monthly_income_totals = {}

        for transaction in income_transactions_agg:
            # Group by month (simplified - assuming we want monthly totals)
            # In production, you'd want more precise monthly aggregation
            income_history.append(float(transaction['amount']))

        # Calculate average monthly income safely
        average_monthly_income = 0.0
        if income_history:
            average_monthly_income = sum(income_history) / len(income_history)

        # Build user context for the new chatbot (pass actual last 6 months income data)
        user_context = {
            'user_id': request.user.id,
            'average_income': average_monthly_income,
            'income_history': []  # Start empty
        }

        user_context['income_history'] = [float(t['amount']) for t in income_transactions_agg]  # Actual last 6 months income amounts

        if selected_item:
            user_context['product_price'] = selected_item.price
            user_context['selected_item'] = selected_item

        # Load conversation context from the most recent AIConsultation
        recent_consultation = AIConsultation.objects.filter(user=request.user).order_by('-created_at').first()
        if recent_consultation and recent_consultation.conversation_context:
            # Restore the conversation context (will be empty dict if not set)
            user_context.update(recent_consultation.conversation_context)
            print(f"DEBUG: Loaded conversation context from consultation {recent_consultation.id}")

            # Generate AI response using the specialized chatbot
        chatbot = get_chatbot()

        # For save/show commands, get the user object from the imports
        from django.contrib.auth.models import User as DjangoUser
        current_user = request.user

        # Check message type and pass user if needed
        try:
            if 'save this plan' in user_message.lower():
                ai_response = chatbot._handle_save_plan(user_message, user_context, current_user)
            elif 'show my saved plans' in user_message.lower():
                ai_response = chatbot._handle_show_saved_plans(user_message, user_context, current_user)
            else:
                # Process the message
                ai_response = chatbot.process_message(user_message, user_context)

                # Store the current response for "piche chalo" functionality (going back to last chat)
                # Only store if it's not a "piche chalo" replacement response
                if not (ai_response and ai_response.get('replace_current_chat')):
                    user_context['last_response'] = ai_response

            # After processing, save the updated context back to the consultation
            # Prepare context data to save (exclude temporary or non-serializable items)
            context_to_save = {}
            persist_keys = [
                'affordable', 'awaiting_affordability_response', 'awaiting_monthly_savings_response',
                'selected_product', 'product_selected', 'total_savings_needed', 'saving_plan_target_product',
                'saving_plan_target_price', 'saving_plan_income', 'temp_savings', 'temp_savings_type',
                'available_suggestions', 'product_selected', 'last_message', 'average_income',
                'income_history', 'user_id', 'last_response'  # Add last_response for piche chalo functionality
            ]

            for key in persist_keys:
                if key in user_context:
                    value = user_context[key]
                    # Skip non-serializable objects (convert selected_product to dict if needed)
                    if key == 'selected_product' and value:
                        if isinstance(value, dict):
                            context_to_save[key] = value
                        elif hasattr(value, '__dict__'):
                            # Convert to dict for storage (exclude methods)
                            context_to_save[key] = {k: v for k, v in value.__dict__.items() if not k.startswith('_')}
                        else:
                            context_to_save[key] = str(value)  # Fallback to string
                    else:
                        context_to_save[key] = value

            # Save back to the same consultation
            if recent_consultation:
                recent_consultation.conversation_context = context_to_save
                recent_consultation.save()
                print(f"DEBUG: Saved conversation context to consultation {recent_consultation.id}")
            else:
                # Create a new consultation to store context
                AIConsultation.objects.create(
                    user=request.user,
                    user_income=average_monthly_income,
                    ai_recommendation="Conversation context stored",
                    affordability_score=5.0,
                    recommended_banks=[],
                    risk_assessment="Context preservation",
                    conversation_context=context_to_save
                )
                print("DEBUG: Created new consultation to store conversation context")
        except Exception as chatbot_error:
            print(f"Chatbot processing error: {chatbot_error}")
            import traceback
            traceback.print_exc()

            # Always return a valid response even if chatbot fails
            ai_response = {
                'reply': f"Hello! How can I help you today?\n\nSorry, there was an error processing your request: {str(chatbot_error)}\n\nPlease try again with a different question.",
                'has_item_selected': False,
                'risk_assessment': 'Error occurred',
                'recommended_banks': [],
                'affordability_analysis': []
            }

        # Build response data compatible with frontend
        response_data = {
            'reply': ai_response.get('message', 'I understand your question. Let me analyze your financial situation and provide personalized recommendations.'),
            'has_item_selected': selected_item is not None,
            'affordability_analysis': ai_response.get('financial_analysis', []),
            'affordability_score': ai_response.get('recommended_emi', 5.0) if ai_response.get('product_category') else 5.0,
            'risk_assessment': 'Analysis completed',
            'recommended_banks': ai_response.get('rates', []),
        }

        # Add replace_current_chat flag if present in ai_response (for piche chalo functionality)
        if ai_response.get('replace_current_chat'):
            response_data['replace_current_chat'] = ai_response.get('replace_current_chat')

        # Add product-specific data if available
        if 'product_category' in ai_response:
            response_data.update({
                'product_analysis': {
                    'category': ai_response.get('product_category'),
                    'price': ai_response.get('price'),
                    'emi_options': ai_response.get('emi_options', []),
                    'downpayment_options': ai_response.get('downpayment_options', []),
                    'affordable_options': ai_response.get('affordable_options', []),
                    'recommended_emi': ai_response.get('recommended_emi')
                }
            })

        # Add saving plan data if available
        if 'saving_plans' in ai_response:
            response_data['saving_plans'] = ai_response['saving_plans']

        # Add affordability data if available
        if 'affordability' in ai_response:
            response_data['affordability'] = ai_response['affordability']

        # Always include consultation_id if it exists
        if consultation_id:
            response_data['consultation_id'] = consultation_id
            print(f"DEBUG: Including consultation_id {consultation_id} in AI response")
        else:
            print("DEBUG: No consultation_id to include in AI response")

        if selected_item:
            response_data['item_details'] = {
                'name': selected_item.model_name,
                'price': float(selected_item.price),
                'emi': float(selected_item.emi),
                'bank': selected_item.bank_name
            }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def create_consultation(request):
    """API endpoint to create a new consultation record"""
    try:
        data = json.loads(request.body)
        
        # Check profile readiness
        if not is_user_profile_ready(request.user):
            return JsonResponse({'error': 'Financial profile not ready. At least 6 months of history required.'}, status=403)

        selected_item_id = data.get('selected_item_id')
        
        if not selected_item_id:
            print(f"DEBUG: Missing selected_item_id in request data: {data}")
            return JsonResponse({'error': 'Selected item ID is required'}, status=400)
            
        print(f"DEBUG: Creating consultation for selected_item_id: {selected_item_id}")

        # Get or create the loan product
        selected_item = None
        fallback_data = None

        try:
            # First try to get real product from database
            selected_item = LoanProduct.objects.get(id=selected_item_id)
            print(f"DATA: Using real database product: {selected_item.model_name}")
        except (LoanProduct.DoesNotExist, ValueError):
            # For fallback products, create a temporary entry in the database
            print(f"FALLBACK: Fallback product ID: {selected_item_id}")

            # Define fallback product data
            fallback_products = {
                '9991': {'category': 'home_loan', 'model_name': 'Home Loan', 'price': 5000000, 'emi': 45000, 'bank_name': 'State Bank of India (SBI)', 'interest_rate': 10.5, 'tenure_months': 240, 'item_id': '9991'},
                '9992': {'category': 'home_loan', 'model_name': 'Home Loan', 'price': 3000000, 'emi': 28000, 'bank_name': 'HDFC Bank', 'interest_rate': 11.3, 'tenure_months': 240, 'item_id': '9992'},
                '9993': {'category': 'personal_loan', 'model_name': 'Personal Loan', 'price': 200000, 'emi': 8500, 'bank_name': 'HDFC Bank', 'interest_rate': 12.5, 'tenure_months': 60, 'item_id': '9993'},
                '9994': {'category': 'personal_loan', 'model_name': 'Personal Loan', 'price': 150000, 'emi': 6250, 'bank_name': 'ICICI Bank', 'interest_rate': 13.2, 'tenure_months': 48, 'item_id': '9994'},
                '9995': {'category': 'gold_loan', 'model_name': 'Gold Loan', 'price': 100000, 'emi': 2250, 'bank_name': 'HDFC Bank', 'interest_rate': 9.5, 'tenure_months': 60, 'item_id': '9995'},
                '9996': {'category': 'two_wheeler', 'model_name': 'Two Wheeler Loan', 'price': 100000, 'emi': 3500, 'bank_name': 'HDFC Bank', 'interest_rate': 11.8, 'tenure_months': 60, 'item_id': '9996'},
                '9997': {'category': 'four_wheeler', 'model_name': 'Car Loan', 'price': 800000, 'emi': 22000, 'bank_name': 'ICICI Bank', 'interest_rate': 13.5, 'tenure_months': 84, 'item_id': '9997'},
                '9998': {'category': 'electronics', 'model_name': 'Electronic Device Loan', 'price': 80000, 'emi': 2800, 'bank_name': 'Bajaj Finance (NBFC)', 'interest_rate': 14.5, 'tenure_months': 48, 'item_id': '9998'}
            }

            fb_data = fallback_products.get(str(selected_item_id))
            if fb_data:
                print(f"SWITCH: Creating fallback product in database for ID: {selected_item_id}")
                # Create a temporary LoanProduct entry for this fallback
                selected_item = LoanProduct.objects.create(**fb_data)
                fallback_data = fb_data
                print(f"✅ Created fallback product: {selected_item.model_name} (ID: {selected_item.id})")
            else:
                return JsonResponse({'error': f'Invalid product ID: {selected_item_id}'}, status=400)

        # Get user's income data for last 6 months
        six_months_ago = datetime.now() - timedelta(days=180)

        income_transactions = Transaction.objects.filter(
            user=request.user,
            transaction_type='income',
            date__gte=six_months_ago
        )

        # Calculate average monthly income - safer calculation
        monthly_income = {}
        for transaction in income_transactions:
            month_key = f"{transaction.date.year}-{transaction.date.month}"
            if month_key not in monthly_income:
                monthly_income[month_key] = 0
            monthly_income[month_key] += float(transaction.amount)

        # Calculate average monthly income safely
        average_monthly_income = 0.0
        if monthly_income:
            total_income = sum(monthly_income.values())
            average_monthly_income = total_income / len(monthly_income)

            print(f"MONEY: Calculated average income: {average_monthly_income}")

        # Capture custom product data from frontend overrides
        custom_data = {
            'emi': data.get('custom_emi'),
            'bank': data.get('custom_bank'),
            'rate': data.get('custom_rate'),
            'tenure': data.get('custom_tenure')
        }
        
        # Create consultation data
        consultation_data = {
            'user': request.user,
            'selected_item': selected_item,
            'user_income': average_monthly_income,
            'ai_recommendation': f'Consultation started for product ID {selected_item_id} - Ready for plan generation',
            'recommended_banks': [],
            'risk_assessment': 'Analysis in progress',
            'affordability_score': 5.0,
        }

        # Store fallback data if this is a fallback product OR if we have custom overrides
        if fallback_data:
            # Merge custom overrides into fallback data if present
            if any(custom_data.values()):
                fallback_data.update({k: v for k, v in custom_data.items() if v is not None})
            consultation_data['fallback_item_data'] = fallback_data
        elif any(custom_data.values()):
            # Store custom overrides even for real products
            consultation_data['fallback_item_data'] = {k: v for k, v in custom_data.items() if v is not None}

        try:
            print(f"SEARCH: Creating consultation with selected_item ID: {selected_item.id}")
            # Create consultation
            consultation = AIConsultation.objects.create(**consultation_data)
            print(f"SUCCESS: Consultation CREATED with ID: {consultation.id}")

            # Verify the consultation was created successfully
            created_consultation = AIConsultation.objects.get(id=consultation.id, user=request.user)
            print(f"SUCCESS: Consultation verified: {created_consultation.id}")

        except Exception as db_error:
            print(f"❌ Database error creating consultation: {db_error}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Database error: {str(db_error)}'}, status=500)

        return JsonResponse({
            'success': True,
            'consultation_id': consultation.id,
            'message': f'Consultation created successfully for product ID {selected_item_id}',
            'user_income': float(average_monthly_income)
        })

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"❌ Unexpected error in create_consultation: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def generate_financial_plans_api(request):
    """API endpoint to generate financial plans for an existing consultation"""
    try:
        # Check profile readiness
        if not is_user_profile_ready(request.user):
            return JsonResponse({'error': 'Financial profile not ready. At least 6 months of history required.'}, status=403)

        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')

        print(f"DEBUG: generate_financial_plans_api called with data: {data}")

        if not consultation_id:
            print("ERROR: DEBUG: No consultation_id provided")
            return JsonResponse({'error': 'Consultation ID is required'}, status=400)

        # Get the consultation
        try:
            consultation = AIConsultation.objects.get(id=consultation_id, user=request.user)
            print(f"DEBUG: Found consultation: {consultation.id}")
            print(f"DEBUG: Consultation selected_item: {consultation.selected_item}")
            print(f"DEBUG: Consultation ai_recommendation: {consultation.ai_recommendation}")
            print(f"DEBUG: Consultation fallback_item_data: {getattr(consultation, 'fallback_item_data', 'Not available')}")
            print(f"DEBUG: Consultation user_income: {consultation.user_income}")
        except AIConsultation.DoesNotExist:
            print(f"❌ DEBUG: Consultation not found: {consultation_id}")
            return JsonResponse({'error': 'Consultation not found'}, status=404)

        # Get selected item from consultation
        selected_item = consultation.selected_item
        print(f"DEBUG: selected_item initially: {selected_item}")

        # If no selected item but we have fallback data, create a temporary object
        if not selected_item:
            print("🔄 DEBUG: No selected_item, checking for fallback data")

            # First try fallback_item_data field if available
            if hasattr(consultation, 'fallback_item_data') and consultation.fallback_item_data:
                print(f"✅ DEBUG: Using fallback_item_data: {consultation.fallback_item_data}")
                fb_data = consultation.fallback_item_data

                # Validate required fields
                required_fields = ['category', 'model_name', 'price', 'emi', 'bank_name', 'interest_rate', 'tenure_months']
                missing_fields = [field for field in required_fields if field not in fb_data]
                if missing_fields:
                    print(f"❌ DEBUG: Missing fields in fallback data: {missing_fields}")
                    return JsonResponse({'error': f'Missing required fields in fallback data: {missing_fields}'}, status=400)

                category_display_map = {
                    'home_loan': 'Home Loan',
                    'personal_loan': 'Personal Loan',
                    'gold_loan': 'Gold Loan',
                    'two_wheeler': 'Two Wheeler',
                    'four_wheeler': 'Four Wheeler',
                    'electronics': 'Electronics'
                }

                try:
                    selected_item = type('TempLoanProduct', (), {
                        'id': fb_data.get('id', 0),
                        'category': fb_data['category'],
                        'model_name': fb_data['model_name'],
                        'price': float(fb_data['price']),
                        'emi': float(fb_data['emi']),
                        'bank_name': fb_data['bank_name'],
                        'interest_rate': float(fb_data['interest_rate']),
                        'tenure_months': int(fb_data['tenure_months']),
                        'item_id': fb_data.get('item_id', fb_data.get('id', 0)),
                        'get_category_display': lambda: category_display_map.get(fb_data['category'], fb_data['category'])
                    })()
                    print(f"✅ DEBUG: Created temporary object from fallback_item_data: {selected_item.model_name}")
                except (ValueError, TypeError) as e:
                    print(f"❌ DEBUG: Error creating temporary object: {e}")
                    return JsonResponse({'error': f'Invalid fallback data format: {str(e)}'}, status=400)

            # Fallback: Try to extract fallback ID from recommendation (legacy)
            elif consultation.ai_recommendation:
                print(f"🔄 DEBUG: Checking ai_recommendation for fallback ID: {consultation.ai_recommendation}")
                import re
                match = re.search(r'ID (\d+)', consultation.ai_recommendation)
                if match:
                    fallback_id = match.group(1)
                    print(f"🔍 DEBUG: Extracted fallback ID from recommendation: {fallback_id}")

                    fallback_products = {
                        '9991': {'category': 'home_loan', 'model_name': 'Home Loan', 'price': 5000000, 'emi': 45000, 'bank_name': 'State Bank of India (SBI)', 'interest_rate': 10.5, 'tenure_months': 240},
                        '9992': {'category': 'home_loan', 'model_name': 'Home Loan', 'price': 3000000, 'emi': 28000, 'bank_name': 'HDFC Bank', 'interest_rate': 11.3, 'tenure_months': 240},
                        '9993': {'category': 'personal_loan', 'model_name': 'Personal Loan', 'price': 200000, 'emi': 8500, 'bank_name': 'HDFC Bank', 'interest_rate': 12.5, 'tenure_months': 60},
                        '9994': {'category': 'personal_loan', 'model_name': 'Personal Loan', 'price': 150000, 'emi': 6250, 'bank_name': 'ICICI Bank', 'interest_rate': 13.2, 'tenure_months': 48},
                        '9995': {'category': 'gold_loan', 'model_name': 'Gold Loan', 'price': 100000, 'emi': 2250, 'bank_name': 'HDFC Bank', 'interest_rate': 9.5, 'tenure_months': 60},
                        '9996': {'category': 'two_wheeler', 'model_name': 'Two Wheeler Loan', 'price': 100000, 'emi': 3500, 'bank_name': 'HDFC Bank', 'interest_rate': 11.8, 'tenure_months': 60},
                        '9997': {'category': 'four_wheeler', 'model_name': 'Car Loan', 'price': 800000, 'emi': 22000, 'bank_name': 'ICICI Bank', 'interest_rate': 13.5, 'tenure_months': 84},
                        '9998': {'category': 'electronics', 'model_name': 'Electronic Device Loan', 'price': 80000, 'emi': 2800, 'bank_name': 'Bajaj Finance (NBFC)', 'interest_rate': 14.5, 'tenure_months': 48}
                    }

                    if fallback_id in fallback_products:
                        fb_data = fallback_products[fallback_id]
                        print(f"✅ DEBUG: Using fallback product data for ID {fallback_id}: {fb_data}")
                        category_display_map = {
                            'home_loan': 'Home Loan',
                            'personal_loan': 'Personal Loan',
                            'gold_loan': 'Gold Loan',
                            'two_wheeler': 'Two Wheeler',
                            'four_wheeler': 'Four Wheeler',
                            'electronics': 'Electronics'
                        }

                        selected_item = type('TempLoanProduct', (), {
                            'id': int(fallback_id),
                            'category': fb_data['category'],
                            'model_name': fb_data['model_name'],
                            'price': fb_data['price'],
                            'emi': fb_data['emi'],
                            'bank_name': fb_data['bank_name'],
                            'interest_rate': fb_data['interest_rate'],
                            'tenure_months': fb_data['tenure_months'],
                            'item_id': int(fallback_id),
                            'get_category_display': lambda fb_data=fb_data: category_display_map.get(fb_data['category'], fb_data['category'])
                        })()
                    else:
                        print(f"❌ DEBUG: Fallback ID {fallback_id} not found in fallback_products")
                else:
                    print("❌ DEBUG: No fallback ID found in ai_recommendation")
            else:
                print("❌ DEBUG: No fallback data available")

        if not selected_item:
            print("❌ DEBUG: No valid item found after all attempts")
            return JsonResponse({'error': 'No valid item found for this consultation. Please ensure the consultation has item data.'}, status=400)

        print(f"✅ DEBUG: Final selected_item: {selected_item.model_name}, Price: {selected_item.price}, Income: {consultation.user_income}")

        # Validate that user_income exists
        if not consultation.user_income or consultation.user_income <= 0:
            print(f"❌ DEBUG: Invalid user income: {consultation.user_income}")
            return JsonResponse({'error': 'Invalid user income data'}, status=400)

        # Generate financial plans
        try:
            print("🚀 DEBUG: Calling generate_financial_plans function")
            # Pass custom overrides stored in consultation (e.g. from frontend calculation)
            custom_overrides = consultation.fallback_item_data
            financial_plans = generate_financial_plans(consultation.user_income, selected_item, custom_overrides)
            print(f"✅ DEBUG: Generated {len(financial_plans)} plans")

            if not financial_plans or len(financial_plans) == 0:
                print("❌ DEBUG: No financial plans generated")
                return JsonResponse({'error': 'Failed to generate financial plans - no plans created'}, status=500)

            return JsonResponse({
                'success': True,
                'financial_plans': financial_plans,
                'consultation_id': consultation.id,
                'user_income': float(consultation.user_income)
            })

        except Exception as plan_error:
            print(f"❌ DEBUG: Error in generate_financial_plans function: {plan_error}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Plan generation failed: {str(plan_error)}'}, status=500)

    except json.JSONDecodeError as e:
        print(f"❌ DEBUG: JSON decode error: {e}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"❌ DEBUG: Unexpected error in generate_financial_plans_api: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)

def generate_financial_plans(average_monthly_income, selected_item, custom_overrides=None):
    """Generate multiple financial plans for the selected item with different banks and rates"""
    try:
        print("🔧 DEBUG: Starting generate_financial_plans")
        print(f"🔧 DEBUG: average_monthly_income type: {type(average_monthly_income)}, value: {average_monthly_income}")

        if not selected_item:
            print("❌ DEBUG: No selected_item provided")
            return None

        # Ensure consistent float conversion for all numeric values
        try:
            product_price = float(selected_item.price)
            print(f"🔧 DEBUG: product_price converted to float: {product_price} (from {type(selected_item.price)})")
        except Exception as e:
            print(f"❌ DEBUG: Error converting product_price: {e}")
            return None

        plans = []
        plan_counter = 1
        
        # Calculate affordability limit
        max_affordable_emi = float(average_monthly_income) * 0.20
        print(f"🔧 DEBUG: Affordability Limit (20% of {average_monthly_income}): {max_affordable_emi}")

        # --- PLAN 1: EXACT MATCH PLAN ---
        # Use custom overrides if available (from frontend product card), otherwise DB values
        p1_bank = selected_item.bank_name
        p1_rate = float(selected_item.interest_rate)
        p1_tenure = int(selected_item.tenure_months)
        p1_emi = float(selected_item.emi)
        
        if custom_overrides:
            print(f"🔧 DEBUG: Using custom overrides for Plan 1: {custom_overrides}")
            p1_bank = custom_overrides.get('bank') or p1_bank
            p1_rate = float(custom_overrides.get('rate') or p1_rate)
            p1_tenure = int(custom_overrides.get('tenure') or p1_tenure)
            p1_emi = float(custom_overrides.get('emi') or p1_emi)
            
        # Re-verify/calculate Plan 1 details to ensure consistency
        # Assuming 20% down payment as standard unless override exists (we don't pass dp override yet)
        down_payment_percent = 20.0
        down_payment = product_price * (down_payment_percent / 100.0)
        loan_amount = product_price - down_payment
        
        # Recalculate EMI to be precise or trust the override?
        # User requested "exact same EMI value". If we trust frontend, we use p1_emi.
        # However, for the plan description we need totals.
        # Let's use the override EMI directly if valid.
        
        total_repayment = p1_emi * p1_tenure
        remaining_salary = float(average_monthly_income) - p1_emi
        total_interest = total_repayment - loan_amount
        
        affordability_score = 9.0 if p1_emi <= max_affordable_emi else 5.0 # Basic check
        
        plan1_description = f"""Downpayment ₹{down_payment:,.0f}
Loan Amount ₹{loan_amount:,.0f}
Tenure {p1_tenure} months
EMI ₹{p1_emi:.0f}
Interest Rate {p1_rate}%
Total Payable ₹{total_repayment:,.0f}"""

        plan_data_1 = {
            "plan_id": f"plan_{plan_counter}",
            "name": f"Plan {plan_counter}: {p1_bank} (Selected)",
            "bank": p1_bank,
            "tenure_months": int(p1_tenure),
            "interest_rate": float(p1_rate),
            "product_cost": float(product_price),
            "down_payment": float(down_payment),
            "down_payment_percent": float(down_payment_percent),
            "loan_amount": float(loan_amount),
            "emi": float(p1_emi),
            "total_repayment": float(total_repayment),
            "remaining_salary": float(remaining_salary),
            "total_interest": float(total_interest),
            "affordability_score": float(affordability_score),
            "plan_description": plan1_description
        }
        
        plans.append(plan_data_1)
        plan_counter += 1
        print(f"✅ DEBUG: Plan 1 (Selected) created: {p1_bank} {p1_tenure}m @ {p1_rate}%")


        # --- ADDITIONAL 10 PLANS ---
        # Bank configurations with different interest rates
        plan_requirements = [
            (12, 3),  # 3 plans for 12 months
            (24, 3),  # 3 plans for 24 months
            (48, 4)   # 4 plans for 48 months
        ]
        
        bank_pool = [
            {"bank": "State Bank of India (SBI)", "rate": 8.5},
            {"bank": "HDFC Bank", "rate": 9.0},
            {"bank": "ICICI Bank", "rate": 9.5},
            {"bank": "Axis Bank", "rate": 8.75},
            {"bank": "Kotak Mahindra Bank", "rate": 9.25},
            {"bank": "Bajaj Finance", "rate": 11.0},
            {"bank": "IDFC First Bank", "rate": 9.75},
            {"bank": "Bank of Baroda", "rate": 8.90}
        ]

        for tenure, count in plan_requirements:
            plans_for_tenure = 0
            
            # Rotate through banks to generate required number of plans for this tenure
            for i in range(len(bank_pool)):
                if plans_for_tenure >= count:
                    break
                    
                bank_config = bank_pool[i % len(bank_pool)] # Cycle through banks
                
                # Slightly vary rate based on tenure for realism
                base_rate = bank_config['rate']
                adjusted_rate = base_rate + (0.5 if tenure > 24 else 0)
                
                try:
                    # Calculate down payment (20% down payment)
                    down_payment = product_price * (down_payment_percent / 100.0)
                    loan_amount = product_price - down_payment

                    # Calculate EMI
                    monthly_rate = adjusted_rate / (12.0 * 100.0)
                    emi_numerator = loan_amount * monthly_rate * (1.0 + monthly_rate)**tenure
                    emi_denominator = (1.0 + monthly_rate)**tenure - 1.0

                    if emi_denominator == 0:
                        continue

                    emi = emi_numerator / emi_denominator
                    
                    # STRICT AFFORDABILITY FILTER: EMI must be <= 20% of income
                    if emi > max_affordable_emi:
                        # Skip this plan if unaffordable
                        continue

                    # Calculate totals
                    total_repayment = emi * tenure
                    remaining_salary = float(average_monthly_income) - emi
                    total_interest = total_repayment - loan_amount
                    
                    affordability_score = 9.0

                    plan_description = f"""Downpayment ₹{down_payment:,.0f}
Loan Amount ₹{loan_amount:,.0f}
Tenure {tenure} months
EMI ₹{emi:.0f}
Interest Rate {adjusted_rate}%
Total Payable ₹{total_repayment:,.0f}"""

                    plan_data = {
                        "plan_id": f"plan_{plan_counter}",
                        "name": f"Plan {plan_counter}: {bank_config['bank']} ({tenure}m)",
                        "bank": bank_config['bank'],
                        "tenure_months": int(tenure),
                        "interest_rate": float(adjusted_rate),
                        "product_cost": float(product_price),
                        "down_payment": float(down_payment),
                        "down_payment_percent": float(down_payment_percent),
                        "loan_amount": float(loan_amount),
                        "emi": float(emi),
                        "total_repayment": float(total_repayment),
                        "remaining_salary": float(remaining_salary),
                        "total_interest": float(total_interest),
                        "affordability_score": float(affordability_score),
                        "plan_description": plan_description
                    }

                    plans.append(plan_data)
                    plans_for_tenure += 1
                    plan_counter += 1
                    
                except Exception as plan_error:
                    print(f"❌ DEBUG: Error creating plan: {plan_error}")
                    continue

        print(f"✅ DEBUG: Generated {len(plans)} plans successfully")
        return plans

    except Exception as e:
        print(f"❌ DEBUG: Unexpected error in generate_financial_plans: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_ai_response(user_message, average_monthly_income, selected_item, monthly_income, financial_plans=None, selected_item_id=None):
    """Generate AI response using Groq API"""
    try:
        import requests

        # ========= Build the financial context =========
        context = f"""
        You are a helpful financial planning AI assistant.
        The user's average monthly income: ₹{average_monthly_income:.2f}
        """

        # Add item details if selected
        if selected_item:
            context += f"""
            User is asking about the item: {selected_item.model_name}
            Item Price: ₹{float(selected_item.price):,.2f}
            Monthly EMI: ₹{float(selected_item.emi):,.2f}
            Bank: {selected_item.bank_name}
            Interest Rate: {float(selected_item.interest_rate)}% per annum
            Tenure: {selected_item.tenure_months} months
            """

        # If plans are provided, use them directly instead of asking Groq for plans
        if financial_plans:
            return {
                "message": f"I've generated personalized financial plans for the {selected_item.model_name if selected_item else 'selected item'} based on your income of ₹{average_monthly_income:.2f}/month. Please select the plan that works best for you.",
                "recommendation": f"Based on your income of ₹{average_monthly_income:.2f}/month, here are suitable financial plans.",
                "affordability_score": 8.0,
                "recommended_banks": [],
                "risk_assessment": "Plans calculated based on your financial profile.",
                "affordability_analysis": {}
            }

        # ========= Affordability Calculation =========
        affordability_score = 0
        recommended_banks = []
        risk_assessment = ""

        if selected_item:
            emi = float(selected_item.emi)
            income = average_monthly_income

            emi_ratio = (emi / income) * 100 if income > 0 else 999
            
            # STRICT RULE: Max EMI is 20% of income
            if emi_ratio <= 20:
                affordability_score = 9.0
                risk_assessment = "Excellent – This EMI is within the 20% safe limit of your income."
            elif emi_ratio <= 30:
                affordability_score = 5.0
                risk_assessment = "Caution – EMI exceeds the strict 20% limit. Not recommended."
            else:
                affordability_score = 2.0
                risk_assessment = "High Risk – EMI exceeds safe limits. Highly inadvisable."

            # Recommend alternative banks - check if it's a fallback item
            try:
                # Check if this is a fallback item by checking if it has the fallback ID
                if str(selected_item_id) in ['9991', '9992', '9993', '9994', '9995', '9996', '9997', '9998']:
                    # For fallback items, create mock recommendations based on category
                    fallback_recommendations = {
                        'home_loan': [
                            {"bank": "State Bank of India (SBI)", "emi": emi * 1.0, "rate": 10.5},
                            {"bank": "HDFC Bank", "emi": emi * 0.95, "rate": 11.3},
                            {"bank": "ICICI Bank", "emi": emi * 0.98, "rate": 11.7},
                        ],
                        'personal_loan': [
                            {"bank": "HDFC Bank", "emi": emi * 0.95, "rate": 12.5},
                            {"bank": "ICICI Bank", "emi": emi * 0.98, "rate": 13.2},
                            {"bank": "Kotak Mahindra Bank", "emi": emi * 1.02, "rate": 13.5},
                        ],
                        'gold_loan': [
                            {"bank": "HDFC Bank", "emi": emi * 1.0, "rate": 9.5},
                            {"bank": "ICICI Bank", "emi": emi * 0.98, "rate": 10.2},
                        ],
                        'two_wheeler': [
                            {"bank": "HDFC Bank", "emi": emi * 0.95, "rate": 11.8},
                            {"bank": "ICICI Bank", "emi": emi * 0.98, "rate": 12.0},
                        ],
                        'four_wheeler': [
                            {"bank": "ICICI Bank", "emi": emi * 1.0, "rate": 13.5},
                            {"bank": "HDFC Bank", "emi": emi * 0.95, "rate": 13.8},
                        ],
                        'electronics': [
                            {"bank": "Bajaj Finance (NBFC)", "emi": emi * 1.0, "rate": 14.5},
                            {"bank": "HDFC Bank", "emi": emi * 0.98, "rate": 14.0},
                        ]
                    }
                    recommended_banks = fallback_recommendations.get(selected_item.category, [
                        {"bank": "HDFC Bank", "emi": emi * 0.95, "rate": 11.0},
                        {"bank": "ICICI Bank", "emi": emi * 0.98, "rate": 11.5},
                    ])
                else:
                    # For real items, find similar ones in database
                    similar_items = LoanProduct.objects.filter(
                        category=selected_item.category
                    ).order_by('emi')

                    for item in similar_items[:3]:
                        if item.id != int(selected_item_id):  # Don't recommend the same item
                            recommended_banks.append({
                                "bank": item.bank_name,
                                "emi": float(item.emi),
                                "rate": float(item.interest_rate),
                            })
            except Exception as e:
                print(f"Error finding similar items: {e}")
                # Continue without bank recommendations if this fails

        # ========= Groq API Request with better error handling =========

        # Check if API key exists
        groq_api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not groq_api_key:
            print("DEBUG: GROQ_API_KEY not found in settings")
            ai_message = generate_fallback_response(
                user_message, average_monthly_income, selected_item,
                affordability_score if 'affordability_score' in locals() else 5.0,
                "API key not configured"
            )

        else:
            try:
                headers = {
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful financial planning AI assistant. Provide clear, structured, personalized financial recommendations. "
                                "If asked about financial planning or affordability, provide direct advice. If asked about specific products, "
                                "give detailed analysis based on the user's financial situation."
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                f"{context}\n\nUser Question: {user_message}\n\n"
                                "Provide a clear, structured, personalized financial recommendation."
                            )
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                }

                print(f"DEBUG: Making request to Groq API with model: llama-3.1-8b-instant")
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                print(f"DEBUG: Groq API response status: {response.status_code}")
                if response.status_code == 200:
                    ai_message = response.json()["choices"][0]["message"]["content"]
                    print(f"DEBUG: Successfully got response from Groq API")
                elif response.status_code == 401:
                    ai_message = "⚠️ API authentication failed. Please check the API key configuration."
                    print("DEBUG: Groq API authentication failed - invalid API key")
                elif response.status_code == 429:
                    ai_message = "⚠️ Rate limit exceeded. Please try again later."
                    print("DEBUG: Groq API rate limit exceeded")
                elif response.status_code >= 500:
                    ai_message = "⚠️ Groq API server error. Please try again later."
                    print("DEBUG: Groq API server error")
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                        ai_message = f"Groq API Error: {error_msg} (Status: {response.status_code})"
                        print(f"DEBUG: Groq API error: {error_msg}")
                    except:
                        ai_message = f"Groq API Error: Status {response.status_code}"
                        print(f"DEBUG: Groq API error with status {response.status_code}")

            except requests.exceptions.Timeout:
                ai_message = "⚠️ Request to Groq API timed out. Please try again."
                print("DEBUG: Groq API request timed out")
            except requests.exceptions.ConnectionError:
                ai_message = "⚠️ Unable to connect to Groq API. Check your internet connection."
                print("DEBUG: Groq API connection error")
            except requests.exceptions.RequestException as e:
                ai_message = f"⚠️ Network error: {str(e)}"
                print(f"DEBUG: Groq API network error: {str(e)}")
            except Exception as e:
                ai_message = f"⚠️ Unexpected error: {str(e)}"
                print(f"DEBUG: Unexpected error in Groq API call: {str(e)}")
                ai_message = generate_fallback_response(
                    user_message, average_monthly_income, selected_item,
                    affordability_score if 'affordability_score' in locals() else 5.0,
                    "API unavailable - using fallback"
                )

    except Exception as e:
        print("DEBUG: Exception in generate_ai_response:", e)
        ai_message = generate_fallback_response(
            user_message,
            average_monthly_income,
            selected_item,
            affordability_score if 'affordability_score' in locals() else 5.0,
            risk_assessment if 'risk_assessment' in locals() else "Analysis completed"
        )

    # ========= Final Response =========
    return {
        "message": ai_message,
        "recommendation": (
            f"Based on your income of ₹{average_monthly_income:.2f}/month, "
            f"{selected_item.model_name} has an affordability score of {affordability_score}/10."
            if selected_item else "Here is your financial analysis:"
        ),
        "affordability_score": affordability_score if 'affordability_score' in locals() else 5.0,
        "recommended_banks": recommended_banks if 'recommended_banks' in locals() else [],
        "risk_assessment": risk_assessment if 'risk_assessment' in locals() else "Analysis completed",
        "affordability_analysis": (
            {
                "monthly_income": round(average_monthly_income, 2),
                "emi": round(float(selected_item.emi), 2),
                "emi_percentage": round((float(selected_item.emi) / average_monthly_income) * 100, 1)
            }
            if selected_item else {}
        )
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
    from calendar import month_name
    import calendar

    # Get filter parameters
    period = request.GET.get('period', 'current_month')
    selected_month = request.GET.get('month')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Debug: Uncomment to see parameters
    # print(f"DEBUG: period={period}, selected_month={selected_month}, start_date_str={start_date_str}, end_date_str={end_date_str}")

    now = datetime.now()
    start_date = None
    end_date = now.replace(hour=23, minute=59, second=59)

    # Determine date range - priority order: selected_month > custom dates > period buttons > current month
    if selected_month:  # Quick select month - highest priority
        try:
            year_part, month_part = selected_month.split('-')
            start_date = datetime(int(year_part), int(month_part), 1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            period_display = f"{calendar.month_name[int(month_part)]} {year_part}"
        except ValueError as e:
            print(f"Error parsing selected_month {selected_month}: {e}")
            pass
    elif start_date_str and end_date_str:  # Custom date range
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            period_display = f"{start_date_str} to {end_date_str}"
        except ValueError as e:
            print(f"Error parsing custom dates {start_date_str} to {end_date_str}: {e}")
            pass
    elif period == 'last_year':
        start_date = now.replace(year=now.year-1, month=1, day=1, hour=0, minute=0, second=0)
        end_date = now.replace(day=31, month=12, hour=23, minute=59, second=59)
        period_display = f"{now.year-1}"
    elif period == 'custom' and start_date_str and end_date_str:  # Fallback for old logic
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            period_display = f"{start_date_str} to {end_date_str}"
        except ValueError:
            pass
    else:  # Default to current month (includes period == 'current_month')
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        period_display = f"{calendar.month_name[now.month]} {now.year}"

    # Default to current month if no valid dates
    if not start_date:
        period_display = f"{calendar.month_name[now.month]} {now.year}"
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    # Get transactions in the selected period (exclude future dates)
    today = datetime.now().date()
    adjusted_end_date = min(end_date.date(), today) if hasattr(end_date, 'date') else min(end_date, today)

    filtered_transactions = Transaction.objects.filter(
        user=request.user,
        date__range=[start_date, adjusted_end_date]
    ).order_by('-date')

    # Get recent transactions (always the latest 10, excluding future dates)
    today = datetime.now().date()
    recent_transactions = Transaction.objects.filter(
        user=request.user,
        date__lte=today
    ).order_by('-date')[:10]

    # Calculate income and expenses for the period
    total_income = sum(float(t.amount) for t in filtered_transactions if t.transaction_type == 'income')
    total_expense = sum(float(t.amount) for t in filtered_transactions if t.transaction_type == 'expense')
    balance = total_income - total_expense

    # Get available year-month combinations for filter (only where transactions exist)
    available_year_months = Transaction.objects.filter(user=request.user).dates('date', 'month', order='DESC')

    # Create a list of (year, month, month_name) tuples for months that have transactions
    available_months = []
    for year_month in available_year_months:
        year = year_month.year
        month = year_month.month
        month_name = calendar.month_name[month]
        available_months.append({
            'value': f"{year}-{month:02d}",
            'label': f"{month_name} {year}"
        })

    # Sort by year descending, then month descending
    available_months.sort(key=lambda x: (x['value']), reverse=True)

    # Get enriched budget context (withautomatic spending calculations)
    budget_context = get_budget_context(request)

    # Update context with all data
    context = {
        'recent_transactions': filtered_transactions[:10],  # Show filtered transactions as "recent" for the period
        'filtered_transactions': filtered_transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'start_date': start_date,
        'end_date': end_date,
        'period_display': period_display,
        'selected_period': period,
        'selected_month': selected_month,
        'custom_start_date': start_date_str,
        'custom_end_date': end_date_str,
        'available_months': available_months,
    }

    # Add budget context data
    context.update(budget_context)
    context['overall_budget_usage'] = context['overall_percentage']  # Dashboard expects this name

    return render(request, 'user/dashboard.html', context)


@login_required
def add_transaction(request):
    """Add new transaction view"""
    if request.method == 'POST':
        from django.contrib import messages
        from user.models import UserActivity

        amount = request.POST.get('amount').strip()
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        date_str = request.POST.get('date')

        # Validation
        try:
            amount = float(amount)
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero.')
                return render(request, 'user/add_transaction.html', {
                    'amount': request.POST.get('amount'),
                    'transaction_type': transaction_type,
                    'category': category,
                    'description': description,
                    'date': date_str
                })
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid amount.')
            return render(request, 'user/add_transaction.html', {
                'amount': request.POST.get('amount'),
                'transaction_type': transaction_type,
                'category': category,
                'description': description,
                'date': date_str
            })

        if not transaction_type or transaction_type not in ['income', 'expense']:
            messages.error(request, 'Please select a valid transaction type.')
            return render(request, 'user/add_transaction.html', {
                'amount': amount,
                'transaction_type': transaction_type,
                'category': category,
                'description': description,
                'date': date_str
            })

        if not category or category not in [c[0] for c in Transaction.CATEGORIES]:
            messages.error(request, 'Please select a valid category.')
            return render(request, 'user/add_transaction.html', {
                'amount': amount,
                'transaction_type': transaction_type,
                'category': category,
                'description': description,
                'date': date_str
            })

        # Parse date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid date.')
            return render(request, 'user/add_transaction.html', {
                'amount': amount,
                'transaction_type': transaction_type,
                'category': category,
                'description': description,
                'date': date_str
            })

        # Create transaction
        try:
            transaction = Transaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type=transaction_type,
                category=category,
                description=description,
                date=date
            )

            # Log activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='add_transaction',
                description=f"Added {transaction_type} transaction of Rs.{amount:.2f} for {transaction.get_category_display()}",
                metadata={
                    'transaction_id': transaction.id,
                    'amount': str(amount),
                    'type': transaction_type,
                    'category': category
                }
            )

            messages.success(request, f'Transaction added successfully!')
            return redirect('user:dashboard')

        except Exception as e:
            messages.error(request, f'Error adding transaction: {str(e)}')
            return render(request, 'user/add_transaction.html', {
                'amount': amount,
                'transaction_type': transaction_type,
                'category': category,
                'description': description,
                'date': date_str
            })

    return render(request, 'user/add_transaction.html', {
        'transaction_types': Transaction.TRANSACTION_TYPES,
        'categories': Transaction.CATEGORIES,
        'today': datetime.now().date()
    })


@login_required
def transaction_list(request):
    """Transaction list view"""
    today = datetime.now().date()

    filter_month_str = request.GET.get('filter_month')
    if filter_month_str:
        try:
            selected_month = datetime.strptime(filter_month_str, '%Y-%m').date().replace(day=1)
        except (ValueError, TypeError):
            selected_month = today.replace(day=1)
    else:
        selected_month = today.replace(day=1)

    qs = Transaction.objects.filter(user=request.user)

    qs = qs.filter(date__year=selected_month.year, date__month=selected_month.month, date__lte=today)

    tx_type = request.GET.get('type')
    if tx_type in {'income', 'expense'}:
        qs = qs.filter(transaction_type=tx_type)

    category = request.GET.get('category')
    if category:
        qs = qs.filter(category=category)

    transactions = qs.order_by('-date')

    return render(request, 'user/transaction_list.html', {
        'transactions': transactions,
        'selected_month': selected_month,
    })


@login_required
def edit_transaction(request, transaction_id):
    """Edit transaction view"""
    # Transaction editing logic here
    pass


@login_required
def delete_transaction(request, transaction_id):
    """Delete transaction view"""
    from django.contrib import messages
    from user.models import Transaction, UserActivity
    
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    
    if request.method == 'POST' or request.method == 'GET':
        # Create activity record
        try:
            UserActivity.objects.create(
                user=request.user,
                activity_type='delete_transaction',
                description=f"Deleted {transaction.get_category_display()} transaction of Rs.{transaction.amount}",
                metadata={'amount': float(transaction.amount), 'category': transaction.category}
            )
        except Exception as e:
            print(f"Error creating activity: {e}")
            
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully!')
        
    return redirect('user:transaction_list')


@login_required
def budget_management(request):
    """Budget management view"""
    if request.method == 'POST':
        from django.contrib import messages
        from user.models import Budget, UserActivity

        category = request.POST.get('category')
        amount_str = request.POST.get('amount')
        month_str = request.POST.get('month')

        # Validation
        try:
            amount = float(amount_str)
            if amount <= 0:
                messages.error(request, 'Budget amount must be greater than zero.')
                context = get_budget_context(request)
                return render(request, 'user/budget_management.html', context)
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid budget amount.')
            context = get_budget_context(request)
            return render(request, 'user/budget_management.html', context)

        if not category or category not in [c[0] for c in Transaction.CATEGORIES]:
            messages.error(request, 'Please select a valid category.')
            context = get_budget_context(request)
            return render(request, 'user/budget_management.html', context)

        # Parse month
        try:
            month = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid month.')
            context = get_budget_context(request)
            return render(request, 'user/budget_management.html', context)

        # Create or update budget
        try:
            budget, created = Budget.objects.update_or_create(
                user=request.user,
                category=category,
                month=month,
                defaults={'amount': amount}
            )

            # Log activity
            activity_type = 'create_budget' if created else 'update_budget'
            UserActivity.objects.create(
                user=request.user,
                activity_type=activity_type,
                description=f"{'Created' if created else 'Updated'} budget of Rs.{amount:.2f} for {budget.get_category_display()} ({month.strftime('%b %Y')})",
                metadata={
                    'budget_id': budget.id,
                    'amount': str(amount),
                    'category': category,
                    'month': month_str
                }
            )

            messages.success(request, f'Budget {"created" if created else "updated"} successfully!')

            # Stay on the same page to show updated budget overview
            context = get_budget_context(request)
            return render(request, 'user/budget_management.html', context)

        except Exception as e:
            messages.error(request, f'Error saving budget: {str(e)}')
            context = get_budget_context(request)
            return render(request, 'user/budget_management.html', context)

    # GET request - display budget page
    context = get_budget_context(request)
    return render(request, 'user/budget_management.html', context)


def get_budget_context(request):
    """Helper function to get budget context data with enriched budget info for both overview and table"""
    selected_month_str = request.GET.get('filter_month')
    if selected_month_str:
        try:
            selected_month = datetime.strptime(selected_month_str, '%Y-%m').date().replace(day=1)
        except (ValueError, TypeError):
            selected_month = datetime.now().date().replace(day=1)
    else:
        selected_month = datetime.now().date().replace(day=1)

    budgets = Budget.objects.filter(user=request.user, month=selected_month).order_by('-month', '-pk')

    # Create enriched budget data for the overview section (show recent budgets as cards)
    enriched_budgets = []
    total_budgeted = 0.0
    total_spent = 0.0
    total_remaining = 0.0
    over_budget_count = 0

    for budget in budgets:
        current_expenses = 0.0
        budget_amount = 0.0

        try:
            current_expenses_val = budget.get_current_expenses
            current_expenses = float(current_expenses_val or 0)
        except (TypeError, ValueError) as e:
            # print(f"DEBUG: ERROR getting expenses for {budget.category}: {e}")
            current_expenses = 0.0

        try:
            budget_amount = float(budget.amount)
        except (TypeError, ValueError) as e:
            # print(f"DEBUG: ERROR getting budget amount for {budget.category}: {e}")
            budget_amount = 0.0

        # Debug: Show calculation details
        print(f"DEBUG: Budget '{budget.category}' - Spent: Rs.{current_expenses:.2f}, Budget: Rs.{budget_amount:.2f}, Month: {budget.month}")

        is_over_budget = current_expenses > budget_amount
        remaining_amount = budget_amount - current_expenses
        over_budget_amount = current_expenses - budget_amount if is_over_budget else 0

        # Accumulate totals
        total_budgeted += budget_amount
        total_spent += current_expenses
        if not is_over_budget:
            total_remaining += remaining_amount
        else:
            over_budget_count += 1

        enriched_budget = {
            'id': budget.id,
            'category': budget.category,
            'category_display': budget.get_category_display(),
            'amount': budget.amount,
            'month': budget.month,
            'month_display': budget.month.strftime('%b %Y'),
            'current_expenses': current_expenses,
            'remaining_amount': abs(remaining_amount),  # Always positive
            'remaining_budget': abs(remaining_amount),  # Dashboard template uses this name
            'over_budget_amount': over_budget_amount,   # Only positive if over budget
            'is_over_budget': is_over_budget,
            'status': 'over_budget' if is_over_budget else 'remaining',
            'progress_percentage': (current_expenses / budget_amount * 100) if budget_amount > 0 else 0,
            'usage_percentage': (current_expenses / budget_amount * 100) if budget_amount > 0 else 0,  # Alternative name
        }
        enriched_budgets.append(enriched_budget)

    # Calculate overall budget health
    overall_percentage = (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0

    prefill_data = {}
    try:
        category_q = request.GET.get('category')
        amount_q = request.GET.get('amount')
        month_q = request.GET.get('month')
        if category_q and month_q:
            prefill_data = {
                'category': category_q,
                'amount': amount_q or '',
                'month': month_q,
            }
    except Exception:
        prefill_data = {}

    context = {
        'budgets': enriched_budgets,
        'raw_budgets': budgets,
        'prefill_data': prefill_data,
        'categories': Transaction.CATEGORIES,
        'total_budgeted': total_budgeted,
        'total_spent': total_spent,
        'total_remaining': total_remaining,
        'overall_percentage': overall_percentage,
        'over_budget_count': over_budget_count,
        'budget_count': len(enriched_budgets),
        'available_for_budget': (total_budgeted - total_spent) if total_budgeted > 0 else 0,
        'selected_month': selected_month,
    }

    return context


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
        'categories': Transaction.CATEGORIES,
        'today': datetime.now().date(),
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


# New endpoints for financial plan management

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def select_financial_plan(request):
    """API endpoint to select a financial plan"""
    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')
        selected_plan = data.get('selected_plan')

        print(f"📡 select_financial_plan called with consultation_id: {consultation_id}")
        print(f"📦 selected_plan data: {selected_plan}")

        if not consultation_id or not selected_plan:
            print("❌ Missing required data")
            return JsonResponse({'error': 'Consultation ID and selected plan are required'}, status=400)

        try:
            consultation = AIConsultation.objects.get(id=consultation_id, user=request.user)
            print(f"📊 Found consultation: {consultation.id}")
        except AIConsultation.DoesNotExist:
            print(f"❌ Consultation not found: {consultation_id} for user {request.user.username}")
            return JsonResponse({'error': 'Consultation not found or access denied'}, status=404)

        # Update consultation with selected plan
        consultation.selected_plan = selected_plan
        consultation.save()
        print(f"✅ Consultation updated with selected plan")

        return JsonResponse({
            'success': True,
            'message': 'Thank you for selecting a plan! It has been added to your Recent Consultations.',
            'consultation_id': consultation.id
        })

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"❌ Unexpected error in select_financial_plan: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def activate_financial_plan(request):
    """API endpoint to activate a financial plan"""
    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')

        if not consultation_id:
            return JsonResponse({'error': 'Consultation ID is required'}, status=400)

        consultation = get_object_or_404(AIConsultation, id=consultation_id, user=request.user)

        if not consultation.selected_plan:
            return JsonResponse({'error': 'No plan selected for this consultation'}, status=400)

        # Calculate plan dates
        today = datetime.now().date()
        plan_months = consultation.selected_plan.get('tenure_months', 12)
        from dateutil.relativedelta import relativedelta
        end_date = today + relativedelta(months=plan_months)

        # Activate the plan
        consultation.activated_plan = True
        consultation.plan_start_date = today
        consultation.plan_end_date = end_date
        consultation.monthly_tracking_active = True
        consultation.save()

        return JsonResponse({
            'success': True,
            'message': 'Plan activated successfully! Monthly tracking is now enabled.',
            'plan_details': {
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'months': plan_months
            }
        })

    except ImportError:
        # Fallback for dateutil not available
        return JsonResponse({'error': 'Date calculation library not available'}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def delete_financial_plan(request):
    """API endpoint to delete a financial plan/consultation"""
    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')

        if not consultation_id:
            return JsonResponse({'error': 'Consultation ID is required'}, status=400)

        consultation = get_object_or_404(AIConsultation, id=consultation_id, user=request.user)
        consultation.delete()

        return JsonResponse({
            'success': True,
            'message': 'Plan deleted successfully from Recent Consultations.'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_consultation_details(request, consultation_id):
    """API endpoint to get detailed consultation information"""
    try:
        # Validate consultation_id is an integer
        try:
            consultation_id = int(consultation_id)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid consultation ID format'}, status=400)

        # Get consultation with proper exception handling
        try:
            consultation = get_object_or_404(AIConsultation, id=consultation_id, user=request.user)
        except AIConsultation.DoesNotExist:
            return JsonResponse({'error': 'Consultation not found or access denied'}, status=404)

        # Build item data - handle both real items and fallback items
        if consultation.selected_item:
            # Real database item
            item_data = {
                'name': consultation.selected_item.model_name,
                'price': float(consultation.selected_item.price) if consultation.selected_item.price else 0.0,
                'emi': float(consultation.selected_item.emi) if consultation.selected_item.emi else 0.0,
                'bank': consultation.selected_item.bank_name,
                'category': consultation.selected_item.get_category_display(),
            }
        elif hasattr(consultation, 'fallback_item_data') and consultation.fallback_item_data:
            # Fallback item from JSON field
            fallback = consultation.fallback_item_data
            category_display_map = {
                'home_loan': 'Home Loan',
                'personal_loan': 'Personal Loan',
                'gold_loan': 'Gold Loan',
                'two_wheeler': 'Two Wheeler',
                'four_wheeler': 'Four Wheeler',
                'electronics': 'Electronics'
            }

            item_data = {
                'name': fallback.get('model_name', 'Fallback Item'),
                'price': float(fallback.get('price', 0)),
                'emi': float(fallback.get('emi', 0)),
                'bank': fallback.get('bank_name', 'Unknown Bank'),
                'category': category_display_map.get(fallback.get('category'), fallback.get('category', 'Unknown')),
            }
        else:
            # No item data available
            item_data = {
                'name': None,
                'price': 0.0,
                'emi': 0.0,
                'bank': None,
                'category': None,
            }

        # Safely build response data, checking for None values
        response_data = {
            'consultation': {
                'id': consultation.id,
                'created_at': consultation.created_at.strftime('%Y-%m-%d %H:%M:%S') if consultation.created_at else None,
                'user_income': float(consultation.user_income) if consultation.user_income else 0.0,
                'affordability_score': float(consultation.affordability_score) if consultation.affordability_score else 0.0,
                'activated_plan': bool(consultation.activated_plan),
                'plan_start_date': consultation.plan_start_date.strftime('%Y-%m-%d') if consultation.plan_start_date else None,
                'plan_end_date': consultation.plan_end_date.strftime('%Y-%m-%d') if consultation.plan_end_date else None,
                'monthly_tracking_active': bool(consultation.monthly_tracking_active),
                'months_completed': consultation.months_completed,
                'remaining_months': consultation.remaining_months,
            },
            'item': item_data
        }

        # Only include selected_plan if it exists and is not None
        if hasattr(consultation, 'selected_plan') and consultation.selected_plan is not None:
            response_data['selected_plan'] = consultation.selected_plan
        else:
            response_data['selected_plan'] = None

        return JsonResponse(response_data, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request format'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid data format'}, status=400)
    except AIConsultation.DoesNotExist:
        return JsonResponse({'error': 'Consultation not found'}, status=404)
    except Exception as e:
        # Log the actual exception for debugging
        print(f"ERROR in get_consultation_details: {str(e)}")
        return JsonResponse({'error': f'Internal server error: {str(e)}'}, status=500)
