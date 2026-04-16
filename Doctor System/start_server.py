#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctorsystem.settings')
    
    try:
        django.setup()
        print("=" * 60)
        print("Starting Django Development Server")
        print("=" * 60)
        print("Server running at: http://127.0.0.1:8000/")
        print("Login page: http://127.0.0.1:8000/login/")
        print("Press Ctrl+C to quit")
        print("=" * 60)
        
        execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
