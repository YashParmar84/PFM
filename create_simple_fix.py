#!/usr/bin/env python3

# This script will create the corrected version of the problematic section in user/views.py

corrected_code = '''

                # Handle API response
                if response.status_code == 200:
                    ai_message = response.json()["choices"][0]["message"]["content"]
                    print(f"DEBUG: Successfully got response from Groq API")
                else:
                    # For any non-200 status, use fallback immediately
                    return generate_fallback_response(
                        user_message, average_monthly_income, selected_item,
                        affordability_score, f"API error ({response.status_code})"
                    )
                '''

print("Corrected API response handling code:")
print(corrected_code)
