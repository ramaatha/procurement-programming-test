# filepath: procurement/forms/sourcing.py
from django import forms
from django.forms import BaseFormSet, formset_factory

from common.forms import ActionForm
from common.numbers import MAX_INT64, format_money, parse_money
from procurement.inputs import QuotationInput, QuoteLineInput
from procurement.models import Quotation, Vendor


class VendorForm(ActionForm):
    name = forms.CharField(label='Nama Vendor', max_length=200)
    contact = forms.CharField(label='Kontak', max_length=500)
    is_active = forms.BooleanField(label='Vendor Aktif', required=False, initial=True)

    def __init__(self, *args, creating=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_version'].required = not creating


class VendorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name + ('' if obj.is_active else ' (Nonaktif)')


class QuotationForm(ActionForm):
    vendor = VendorChoiceField(label='Vendor', queryset=Vendor.objects.none())
    reference = forms.CharField(label='Referensi Penawaran', max_length=100)
    quoted_on = forms.DateField(label='Tanggal Penawaran', input_formats=['%Y-%m-%d'],
                                widget=forms.DateInput(format='%Y-%m-%d', attrs={'type':'date'}))
    valid_until = forms.DateField(label='Berlaku Sampai', input_formats=['%Y-%m-%d'],
                                  widget=forms.DateInput(format='%Y-%m-%d', attrs={'type':'date'}))
    fulfillment_days = forms.IntegerField(label='Estimasi Pemenuhan (Hari)', min_value=0, max_value=MAX_INT64)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_version'].required = True
        self.fields['vendor'].queryset = Vendor.objects.order_by('name','pk')

    def to_input(self, formset):
        data = self.cleaned_data
        return QuotationInput(data['vendor'].pk, data['reference'], data['quoted_on'], data['valid_until'],
                              data['fulfillment_days'], tuple(QuoteLineInput(row['revision_item_id'], row['unit_price'])
                                                             for row in formset.cleaned_data))


class QuotationLineForm(forms.Form):
    revision_item_id = forms.UUIDField(widget=forms.HiddenInput)
    unit_price = forms.CharField(label='Harga Per Unit (IDR)', max_length=24, strip=False,
                                 help_text='Gunakan titik desimal, maksimal dua angka desimal.')

    def clean_unit_price(self):
        return format_money(parse_money(self.cleaned_data['unit_price']))


class BaseQuotationFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        management = self.management_form.cleaned_data
        total, initial = management.get('TOTAL_FORMS', 0), management.get('INITIAL_FORMS', 0)
        if total < 1 or initial < 0 or initial > total:
            raise forms.ValidationError('Rincian item tidak lengkap. Muat ulang penawaran.')
        if any(self.errors):
            return
        if any(not row or 'revision_item_id' not in row or 'unit_price' not in row for row in self.cleaned_data):
            raise forms.ValidationError('Isi harga untuk seluruh item revisi.')


QuotationLineFormSet = formset_factory(QuotationLineForm, formset=BaseQuotationFormSet, extra=0,
                                       max_num=1000, absolute_max=1000, validate_max=True)


class QuotationChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        total = format_money(obj.total_minor).replace('.', ',')
        return f'{obj.reference} · {obj.vendor.name} · IDR {total} · {obj.fulfillment_days} hari · sampai {obj.valid_until:%d-%m-%Y}'


class SelectionForm(ActionForm):
    quotation = QuotationChoiceField(label='Penawaran Yang Dipilih', queryset=Quotation.objects.none())
    reason = forms.CharField(label='Alasan Pemilihan', max_length=4000, widget=forms.Textarea(attrs={'rows':3}))
    single_source_reason = forms.CharField(label='Alasan Sumber Tunggal', max_length=4000, required=False,
                                           widget=forms.Textarea(attrs={'rows':3}),
                                           help_text='Wajib jika hanya satu vendor mempunyai penawaran yang layak.')

    def __init__(self, *args, quotations, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_version'].required = True
        self.fields['quotation'].queryset = quotations
