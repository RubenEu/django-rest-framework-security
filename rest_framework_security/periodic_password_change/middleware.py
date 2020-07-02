from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.shortcuts import redirect

from rest_framework_security.authentication.middleware import get_admin_base_url, is_path_allowed
from rest_framework_security.periodic_password_change.utils import password_is_expired


class PeriodicPasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.default_allowed_urls = [
            get_admin_base_url('password_change'),
            get_admin_base_url('password_change_done'),
            get_admin_base_url('jsi18n'),
            get_admin_base_url('login'),
            get_admin_base_url('logout'),
        ]
        # One-time configuration and initialization.

    def __call__(self, request):
        session: SessionBase = request.session
        admin_base_url = get_admin_base_url('index')
        require_change = session.get('periodic_password_change')
        if require_change and not password_is_expired(request.user):
            session['periodic_password_change'] = False
            require_change = False
        if request.path in self.default_allowed_urls or (require_change and is_path_allowed(request.path)):
            pass
        elif require_change and admin_base_url and request.path.startswith(admin_base_url):
            return redirect('admin:password_change')
        elif require_change:
            request.user = AnonymousUser()
        response = self.get_response(request)
        return response
