from django.shortcuts import redirect
from django.urls import Resolver404, resolve
from .models import UserProfile


class RequirePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            try:
                must_change_password = user.userprofile.must_change_password
            except UserProfile.DoesNotExist:
                must_change_password = False

            if must_change_password:
                try:
                    route_name = resolve(request.path_info).url_name
                except Resolver404:
                    route_name = None
                if route_name not in {'password_change_required', 'logout'}:
                    return redirect('password_change_required')

        return self.get_response(request)