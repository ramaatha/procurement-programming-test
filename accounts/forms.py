# filepath: accounts/forms.py
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Tidak dapat masuk. Periksa username dan password, atau hubungi admin.",
        "inactive": "Tidak dapat masuk. Periksa username dan password, atau hubungi admin.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["username"].widget.attrs.update(autocomplete="username", autocapitalize="none")
        self.fields["password"].label = "Password"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"
