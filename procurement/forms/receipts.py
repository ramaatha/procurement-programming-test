# filepath: procurement/forms/receipts.py
from django import forms
from django.forms import BaseFormSet, formset_factory

from common.forms import ActionForm
from common.numbers import format_quantity, parse_quantity
from procurement.inputs import ReceiptInput, ReceiptLineInput
from procurement.models import EvidenceType, Kind


class ReceiptForm(ActionForm):
    reference = forms.CharField(label='Referensi bukti',max_length=100)
    notes = forms.CharField(label='Catatan pemeriksaan',max_length=4000,widget=forms.Textarea)
    evidence_type = forms.ChoiceField(label='Jenis bukti',choices=EvidenceType.choices)
    service_started_on = forms.DateField(label='Awal pelaksanaan jasa',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),input_formats=['%Y-%m-%d'])
    service_ended_on = forms.DateField(label='Akhir pelaksanaan jasa',required=False,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),input_formats=['%Y-%m-%d'])

    def __init__(self,*args,kind,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['expected_version'].required = True
        if kind == Kind.GOODS:
            self.fields['evidence_type'].choices = [(EvidenceType.GOODS_DELIVERY,'Surat jalan')]
        else:
            self.fields['evidence_type'].choices = EvidenceType.choices[1:]
            self.fields['service_started_on'].required = True
            self.fields['service_ended_on'].required = True

    def to_input(self,formset):
        data = self.cleaned_data
        return ReceiptInput(data['reference'],data['notes'],data['evidence_type'],data.get('service_started_on'),
                            data.get('service_ended_on'),tuple(ReceiptLineInput(row['order_item_id'],row['accepted'],row['rejected'],row['rejection_reason']) for row in formset.cleaned_data))


class ReceiptLineForm(forms.Form):
    order_item_id = forms.UUIDField(widget=forms.HiddenInput)
    accepted = forms.CharField(label='Diterima sekarang',max_length=24,strip=False,help_text='Gunakan titik desimal, maksimal tiga angka desimal. Isi 0 bila tidak ada.')
    rejected = forms.CharField(label='Ditolak sekarang',max_length=24,strip=False)
    rejection_reason = forms.CharField(label='Alasan penolakan',max_length=4000,required=False,widget=forms.Textarea(attrs={'rows':2}))

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.empty_permitted = False

    def clean_accepted(self):
        return format_quantity(parse_quantity(self.cleaned_data['accepted'],allow_zero=True))

    def clean_rejected(self):
        return format_quantity(parse_quantity(self.cleaned_data['rejected'],allow_zero=True))


class BaseReceiptFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        data = self.management_form.cleaned_data
        total,initial = data.get('TOTAL_FORMS',0),data.get('INITIAL_FORMS',0)
        if total < 1 or initial < 0 or initial > total:
            raise forms.ValidationError('Rincian penerimaan tidak lengkap. Muat ulang halaman.')


ReceiptLineFormSet = formset_factory(ReceiptLineForm,formset=BaseReceiptFormSet,extra=0,min_num=1,
                                      validate_min=True,max_num=1000,absolute_max=1000,validate_max=True)


class CloseOrderForm(ActionForm):
    reason = forms.CharField(label='Alasan pembatalan atau penutupan sisa',max_length=4000,widget=forms.Textarea(attrs={'rows':3}))

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['expected_version'].required = True
