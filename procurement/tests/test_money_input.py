# filepath: procurement/tests/test_money_input.py
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import Role
from procurement.forms.requests import RequestLineForm
from procurement.forms.sourcing import QuotationLineForm
from procurement.models import PurchaseRequest, Quotation, Vendor
from procurement.tests.factories import approved, user


class MoneyInputTests(SimpleTestCase):
    def forms_for(self, value):
        return (
            RequestLineForm(dict(name='Pemeriksaan jaringan',unit='paket',quantity='1',unit_price=value)),
            QuotationLineForm(dict(revision_item_id=str(uuid4()),unit_price=value)),
        )

    def test_prices_accept_indonesian_and_legacy_formats_without_value_changes(self):
        for value, expected in (
            ('250.000','250000.00'),('1.250,50','1250.50'),('1250,50','1250.50'),
            ('250000','250000.00'),('1250.50','1250.50'),('1.000','1000.00'),
            ('1.23','1.23'),('0,01','0.01'),('0.01','0.01'),(' 250.000 ','250000.00'),
            ('92.233.720.368.547.758,07','92233720368547758.07'),
        ):
            for form in self.forms_for(value):
                with self.subTest(value=value, form=type(form).__name__):
                    self.assertTrue(form.is_valid(),form.errors)
                    self.assertEqual(form.cleaned_data['unit_price'],expected)

    def test_prices_reject_malformed_grouping_precision_zero_and_overflow(self):
        for value in ('25.00.000','1.23,50','1,250.50','1,234','1.2345','1.000,001',
                      'Rp250.000','250 000','-1','+1','1e3','NaN','0','0,00','0.000',
                      '92.233.720.368.547.758,08','9'*100):
            for form in self.forms_for(value):
                with self.subTest(value=value,form=type(form).__name__):
                    self.assertFalse(form.is_valid())
                    self.assertIn('unit_price',form.errors)

    def test_quantity_keeps_its_existing_decimal_semantics(self):
        form=RequestLineForm(dict(name='A',unit='unit',quantity='1.000',unit_price='1.000'))
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.cleaned_data['quantity'],'1.000')
        self.assertEqual(form.cleaned_data['unit_price'],'1000.00')


class MoneyInputHTTPTests(TestCase):
    def setUp(self):
        self.client.force_login(user(Role.REQUESTER))

    def payload(self,value):
        form=self.client.get('/requests/new/').context['form']
        return {'kind':'SERVICES','title':'Uji harga Indonesia','reason':'Pengujian',
                'destination':'Kantor Demo','needed_on':str(timezone.localdate()),
                'action_token':form.initial['action_token'],
                'items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'0',
                'items-0-name':'Pemeriksaan jaringan','items-0-unit':'paket',
                'items-0-quantity':'1','items-0-unit_price':value}

    def test_indonesian_price_survives_save_edit_and_equivalent_replay(self):
        payload=self.payload('250.000')
        response=self.client.post('/requests/new/',payload)
        self.assertEqual(response.status_code,303)
        request=PurchaseRequest.objects.get()
        self.assertEqual(request.items.get().estimated_unit_price_minor,25000000)
        payload['items-0-unit_price']='250000.00'
        self.assertEqual(self.client.post('/requests/new/',payload).status_code,303)
        self.assertEqual(PurchaseRequest.objects.count(),1)
        path=f'/requests/{request.pk}/edit/'
        page=self.client.get(path)
        form=page.context['form']
        payload.update(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])
        payload['items-0-unit_price']='1.250,50'
        self.assertEqual(self.client.post(path,payload).status_code,303)
        self.assertEqual(request.items.get().estimated_unit_price_minor,125050)
        self.assertContains(self.client.get(f'/requests/{request.pk}/'),'1.250,50')

    def test_invalid_grouping_does_not_create_request(self):
        response=self.client.post('/requests/new/',self.payload('25.00.000'))
        self.assertEqual(response.status_code,400)
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_quotation_create_and_edit_store_exact_prices_without_javascript(self):
        target=approved(user(Role.REQUESTER),user(Role.APPROVER))
        actor=user(Role.PROCUREMENT)
        self.client.force_login(actor)
        vendor=Vendor.objects.create(name='Vendor uji',contact='uji@example.invalid',is_active=True,created_by=actor)
        item=target.revisions.get(number=1).items.get()
        path=f'/requests/{target.pk}/quotations/'
        form=self.client.get(path+'new/').context['form']
        payload=dict(form.initial)|dict(vendor=str(vendor.pk),reference='UJI-FORMAT',
            quoted_on=str(timezone.localdate()),valid_until=str(timezone.localdate()),fulfillment_days='0')|{
            'items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'1',
            'items-0-revision_item_id':str(item.pk),'items-0-unit_price':'250.000'}
        self.assertEqual(self.client.post(path+'new/',payload).status_code,303)
        quote=Quotation.objects.get()
        self.assertEqual(quote.items.get().unit_price_minor,25000000)
        self.assertEqual(quote.total_minor,250000000)
        edit=path+f'{quote.pk}/edit/'
        form=self.client.get(edit).context['form']
        payload.update(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])
        payload['items-0-unit_price']='1.250,50'
        self.assertEqual(self.client.post(edit,payload).status_code,303)
        quote.refresh_from_db()
        self.assertEqual(quote.items.get().unit_price_minor,125050)
        self.assertEqual(quote.total_minor,1250500)
        form=self.client.get(edit).context['form']
        payload.update(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])
        payload['items-0-unit_price']='1,250.50'
        self.assertEqual(self.client.post(edit,payload).status_code,400)
        quote.refresh_from_db()
        self.assertEqual(quote.total_minor,1250500)
