from django.core.exceptions import PermissionDenied
from functools import wraps


def role_required(allowed_role_names):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            user_role = request.user.role.name
            if user_role not in allowed_role_names:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_user_role(user):
    return user.role.name if user.is_authenticated else None