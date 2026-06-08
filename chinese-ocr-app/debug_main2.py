import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
print('Start2')
from main import REIGN_DATABASE, ensure_credits_column, ensure_admin_columns, create_admin_account
print('Done importing main parts')

