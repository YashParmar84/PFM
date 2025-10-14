#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_finance_management.settings')
django.setup()

from django.contrib.auth.models import User

def update_test_user_passwords():
    """Update passwords for all test users to '123456'"""

    test_users = [
        'high_income_saver',
        'middle_income_balanced',
        'low_income_struggler',
        'freelancer_variable',
        'student_part_time',
        'luxury_spender',
        'family_provider',
        'entrepreneur_risky',
        'retiree_fixed',
        'young_professional'
    ]

    print("Updating passwords for test users...")

    for username in test_users:
        try:
            user = User.objects.get(username=username)
            user.set_password('123456')
            user.save()
            print(f"✓ Updated password for {username}")
        except User.DoesNotExist:
            print(f"✗ User {username} not found")
        except Exception as e:
            print(f"✗ Error updating {username}: {str(e)}")

    print("\n=== PASSWORD UPDATE SUMMARY ===")
    print("All test users now have password: 123456")
    print("You can login with any of these usernames and password '123456'")

if __name__ == "__main__":
    update_test_user_passwords()
