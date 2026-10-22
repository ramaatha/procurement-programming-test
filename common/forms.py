# filepath: common/forms.py
from django import forms


class ActionForm(forms.Form):
    action_token=forms.CharField(label='Token aksi',max_length=2048,widget=forms.HiddenInput)
    expected_version=forms.IntegerField(label='Versi data',min_value=1,required=False,widget=forms.HiddenInput)
