# filepath: procurement/forms/tracking.py
from django import forms

from procurement.models import Kind, OrderStatus
from procurement.stages import STAGE_LABELS


class TrackingFilterForm(forms.Form):
    q = forms.CharField(label='Cari Nomor Atau Judul',required=False,max_length=200)
    kind = forms.ChoiceField(label='Jenis Pengadaan',required=False,choices=[('','Semua Jenis'),*Kind.choices])
    stage = forms.ChoiceField(label='Tahap Pengadaan',required=False)

    def __init__(self,*args,orders_only=False,**kwargs):
        super().__init__(*args,**kwargs)
        codes = OrderStatus.values if orders_only else STAGE_LABELS
        self.fields['stage'].choices = [('', 'Semua Tahap'),*((code,STAGE_LABELS[code]) for code in codes)]
