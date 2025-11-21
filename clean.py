import os
files = ['complete_loan_product_dataset.xlsx', 'create_users_direct.py', 'simple_user_creator.py', 'run_command.py', 'update_passwords.py', 'history.py', 'remove_files.py', 'cleanup.bat']
for f in files:
    try:
        if os.path.exists(f):
            os.remove(f)
            print('Removed:', f)
    except: pass
print('Done')
