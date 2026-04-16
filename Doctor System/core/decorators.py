from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from .models import UserProfile


def get_user_role(user):
    try:
        return user.userprofile.role
    except UserProfile.DoesNotExist:
        return None


def admin_required(view_func):
    def check_role(user):
        return get_user_role(user) == 'admin'
    return user_passes_test(check_role, login_url='login')(login_required(view_func))


def doctor_required(view_func):
    def check_role(user):
        return get_user_role(user) == 'doctor'
    return user_passes_test(check_role, login_url='login')(login_required(view_func))


def billing_required(view_func):
    def check_role(user):
        return get_user_role(user) == 'billing'
    return user_passes_test(check_role, login_url='login')(login_required(view_func))


def accounting_required(view_func):
    def check_role(user):
        return get_user_role(user) == 'accounting'
    return user_passes_test(check_role, login_url='login')(login_required(view_func))

