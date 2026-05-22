from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class PhoneAuthBackend(ModelBackend):
    def authenticate(self, request, contacts=None, password=None, **kwargs):
        if contacts is None or password is None:
            return None
        try:
            user = User.objects.get(contacts=contacts)
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
