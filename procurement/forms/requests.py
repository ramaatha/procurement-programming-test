# filepath: procurement/forms/requests.py
from django import forms
from django.forms import BaseFormSet, formset_factory

from common.forms import ActionForm
from common.numbers import format_money,format_quantity,parse_money_input,parse_quantity
from procurement.inputs import DraftInput,RequestLineInput
from procurement.models import Decision, Kind


class DraftForm(ActionForm):
    kind=forms.ChoiceField(label='Jenis pengadaan',choices=Kind.choices)
    title=forms.CharField(label='Judul',max_length=200,required=False)
    reason=forms.CharField(label='Alasan kebutuhan',max_length=4000,required=False,widget=forms.Textarea(attrs={'rows':3}))
    destination=forms.CharField(label='Tujuan penerimaan / layanan',max_length=500,required=False)
    needed_on=forms.DateField(label='Tanggal kebutuhan',required=False,input_formats=['%Y-%m-%d'],widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))

    def __init__(self,*args,creating=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['expected_version'].required=not creating

    def to_input(self,formset) -> DraftInput:
        items=tuple(RequestLineInput(row['name'],row['unit'],row['quantity'],row['unit_price']) for row in formset.cleaned_data if row and not row.get('DELETE'))
        return DraftInput(self.cleaned_data['kind'],self.cleaned_data['title'],self.cleaned_data['reason'],self.cleaned_data['destination'],self.cleaned_data['needed_on'],items)


class RequestLineForm(forms.Form):
    name=forms.CharField(label='Nama item',max_length=200)
    unit=forms.CharField(label='Satuan',max_length=40)
    quantity=forms.CharField(label='Jumlah',max_length=24,strip=False,help_text='Gunakan titik desimal, misalnya 0.333; maksimal 3 desimal.')
    unit_price=forms.CharField(label='Estimasi harga per unit (IDR)',max_length=32,strip=False,
                              help_text='Contoh: 250000 atau 250.000. Untuk pecahan: 1.250,50. Tanpa Rp; maksimal dua angka desimal.',
                              widget=forms.TextInput(attrs={'inputmode':'decimal'}))

    def clean_quantity(self):return format_quantity(parse_quantity(self.cleaned_data['quantity']))

    def clean_unit_price(self):return format_money(parse_money_input(self.cleaned_data['unit_price']))


class BaseRequestFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        values = self.management_form.cleaned_data
        total,initial = values.get('TOTAL_FORMS',0),values.get('INITIAL_FORMS',0)
        if total < 0 or initial < 0 or initial > total:
            raise forms.ValidationError('Rincian item tidak valid. Muat ulang form.')


RequestLineFormSet=formset_factory(RequestLineForm,formset=BaseRequestFormSet,extra=1,can_delete=True,max_num=1000,absolute_max=1000,validate_max=True)


class CancelForm(ActionForm):
    reason=forms.CharField(label='Alasan pembatalan',max_length=4000,widget=forms.Textarea(attrs={'rows':3}))

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['expected_version'].required=True


class ReviewForm(ActionForm):
    decision = forms.ChoiceField(label='Keputusan', choices=[('', 'Pilih keputusan'), *Decision.choices])
    reason = forms.CharField(label='Alasan keputusan', max_length=4000, required=False,
                             widget=forms.Textarea(attrs={'rows': 3}),
                             help_text='Wajib untuk meminta revisi atau menolak permintaan.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_version'].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('decision') in (Decision.REQUEST_CHANGES, Decision.REJECT) and not cleaned.get('reason'):
            self.add_error('reason', 'Isi alasan untuk keputusan ini.')
        return cleaned


class RevisionForm(ActionForm):
    reason = forms.CharField(label='Alasan revisi', max_length=4000,
                             widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_version'].required = True
