from unittest.mock import patch
from uuid import uuid4

from django.test import Client, TestCase, override_settings

from accounts.models import Role
from common.actions import ActionContext
from procurement.inputs import DraftInput, RequestLineInput
from procurement.models import PurchaseRequest
from procurement.services.requests import save_draft
from procurement.tests.factories import approved, user


class InterfaceTests(TestCase):
    def setUp(self):
        self.actor = user(Role.REQUESTER)
        self.client.force_login(self.actor)

    def test_invalid_form_retains_values_and_shows_field_errors_inside_form(self):
        get = self.client.get('/requests/new/')
        token = get.context['form'].initial['action_token']
        post = dict(action_token=token,kind='GOODS',title='Kebutuhan tetap tersimpan',reason='Alasan',destination='Lokasi',
                    **{'items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'0','items-0-name':'Monitor','items-0-unit':'unit',
                       'items-0-quantity':'-1','items-0-unit_price':'10','intent':'save'})
        response = self.client.post('/requests/new/',post)
        self.assertContains(response,'Kebutuhan tetap tersimpan',status_code=400)
        self.assertNotContains(response,'id="error-summary"',status_code=400)
        self.assertContains(response,'id="id_items-0-quantity_error"',status_code=400)

    @override_settings(DEBUG=False,SECURE_SSL_REDIRECT=False)
    def test_404_and_csrf_errors_have_recovery_and_no_internal_payload(self):
        self.assertContains(self.client.get('/missing/'),'Kembali ke Beranda',status_code=404)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.actor)
        response = csrf.post('/requests/new/',dict(action_token='not-a-secret'))
        self.assertContains(response,'Sesi Form Perlu Diperbarui',status_code=403)
        self.assertNotContains(response,'not-a-secret',status_code=403)

    def test_navigation_is_role_scoped_and_has_skip_link(self):
        response = self.client.get('/')
        self.assertContains(response,'href="#content"')
        self.assertNotContains(response,'Kelola Akun')
        self.assertContains(response,'Antrean Kerja')

    @override_settings(DEBUG=False,SECURE_SSL_REDIRECT=False)
    def test_unexpected_failure_returns_safe_500_without_token_or_traceback(self):
        get = self.client.get('/requests/new/')
        payload = dict(action_token=get.context['form'].initial['action_token'],kind='GOODS',
                       title='Draft gagal',**{'items-TOTAL_FORMS':'0','items-INITIAL_FORMS':'0','intent':'save'})
        self.client.raise_request_exception = False
        with patch('procurement.views.requests.save_draft',side_effect=RuntimeError('private-internal-failure')):
            response = self.client.post('/requests/new/',payload)
        self.assertContains(response,'Permintaan Belum Dapat Diselesaikan',status_code=500)
        for secret in ('private-internal-failure',payload['action_token'],'Traceback'):
            self.assertNotContains(response,secret,status_code=500)

    def test_home_approver_does_not_offer_own_request(self):
        target = approved(self.actor,user(Role.APPROVER))
        PurchaseRequest.objects.filter(pk=target.pk).update(status='SUBMITTED')
        self.actor.role = Role.APPROVER
        self.actor.save(update_fields=['role'])
        response = self.client.get('/')
        self.assertNotContains(response,target.number)

    def test_negative_formset_management_cannot_clear_draft(self):
        target = save_draft(ActionContext(self.actor.pk,uuid4(),None),request_id=None,
            data=DraftInput('GOODS','Tetap','Alasan','Kantor',None,(RequestLineInput('Barang','unit','1','10'),)))
        get = self.client.get(f'/requests/{target.pk}/edit/')
        payload = {key: value if value is not None else '' for key,value in get.context['form'].initial.items()}
        payload.update({'items-TOTAL_FORMS':'-1','items-INITIAL_FORMS':'0','intent':'save'})
        self.assertEqual(self.client.post(f'/requests/{target.pk}/edit/',payload).status_code,400)
        self.assertEqual(target.items.count(),1)
