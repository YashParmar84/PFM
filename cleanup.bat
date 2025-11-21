@echo off
echo Removing task-specific files...
del /q complete_loan_product_dataset.xlsx 2>nul
del /q create_users_direct.py 2>nul
del /q simple_user_creator.py 2>nul
del /q run_command.py 2>nul
del /q update_passwords.py 2>nul
del /q history.py 2>nul
del /q remove_files.py 2>nul
if exist __pycache__ rmdir /s /q __pycache__ 2>nul
echo Cleanup complete.
pause
