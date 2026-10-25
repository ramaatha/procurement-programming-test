# filepath: accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import password_validators_help_text_html

from accounts.models import Role
from common.forms import ActionForm


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Tidak dapat masuk. Periksa username dan password, atau hubungi admin.',
        'inactive': 'Tidak dapat masuk. Periksa username dan password, atau hubungi admin.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username'
        self.fields['username'].widget.attrs.update(autocomplete='off', autocapitalize='none')
        self.fields['password'].label = 'Password'
        self.fields['password'].widget.attrs['autocomplete'] = 'off'


class UserForm(ActionForm):
    username = forms.CharField(label='Username', max_length=150, widget=forms.TextInput(attrs={'autocomplete':'off','autocapitalize':'none'}))
    role = forms.ChoiceField(label='Peran', choices=Role.choices)
    is_active = forms.BooleanField(label='Akun aktif', required=False)
    initial_password = forms.CharField(label='Password awal', max_length=4096, strip=False, required=False, widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}), help_text=password_validators_help_text_html())
    confirm_password = forms.CharField(label='Ulangi password awal', max_length=4096, strip=False, required=False, widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))

    def __init__(self, *args, creating: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.creating = creating
        if creating:
            self.fields['initial_password'].required = True
            self.fields['confirm_password'].required = True
        else:
            del self.fields['initial_password']
            del self.fields['confirm_password']
            self.fields['expected_version'].required = True

    def clean(self):
        cleaned = super().clean()
        if self.creating and cleaned.get('initial_password') != cleaned.get('confirm_password'):
            self.add_error('confirm_password', 'Konfirmasi password belum sama.')
        return cleaned


class PasswordForm(ActionForm):
    new_password = forms.CharField(label='Password baru', max_length=4096, strip=False, widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}), help_text=password_validators_help_text_html())
    confirm_password = forms.CharField(label='Ulangi password baru', max_length=4096, strip=False, widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_version'].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            self.add_error('confirm_password', 'Konfirmasi password belum sama.')
        return cleaned
