print('Start')
from reference_matcher import match_image
print('Imported reference_matcher')
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
print('Reconfigured')
from db import fetch_all_marks
print('Imported db')
from passlib.context import CryptContext
print('Importing passlib done')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print('Created CryptContext')

