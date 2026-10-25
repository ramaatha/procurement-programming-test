from django.test import TestCase
from accounts.models import Role
from procurement.models import Receipt
from procurement.tests.factories import issued, user


class ReceiptHTTPTests(TestCase):
    def setUp(self):
        self.order = issued()
        self.actor = user(Role.RECEIVER)
        self.client.force_login(self.actor)
        self.url = f'/orders/{self.order.pk}/receipts/new/'

    def payload(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code,200)
        form = response.context['form']
        return dict(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'],
                    reference='SJ-HTTP',notes='Pemeriksaan',evidence_type='GOODS_DELIVERY',
                    **{'items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'1',
                       'items-0-order_item_id':str(self.order.items.get().pk),'items-0-accepted':'6',
                       'items-0-rejected':'2','items-0-rejection_reason':'Rusak'})

    def test_post_replay_detail_and_balances(self):
        data = self.payload()
        result = self.client.post(self.url,data)
        self.assertEqual(result.status_code,303)
        self.assertEqual(self.client.post(self.url,data).url,result.url)
        self.assertEqual(Receipt.objects.count(),1)
        detail = self.client.get(result.url)
        self.assertContains(detail, 'SJ-HTTP')
        self.assertEqual(detail.context['lines'][0]['accepted'], '6')
        self.assertEqual(detail.context['lines'][0]['rejected'], '2')
        page = self.client.get(f'/orders/{self.order.pk}/')
        self.assertEqual(page.context['balances'][0]['remaining'], '4')
        self.assertNotContains(page, '4.000')

    def test_invalid_preserves_input_and_negative_management_is_rejected(self):
        data = self.payload()
        data['items-0-accepted'] = '11'
        response = self.client.post(self.url,data)
        self.assertEqual(response.status_code,400)
        self.assertContains(response,'SJ-HTTP',status_code=400)
        data['items-TOTAL_FORMS'] = '-1'
        self.assertEqual(self.client.post(self.url,data).status_code,400)
        self.assertFalse(Receipt.objects.exists())

    def test_permissions_token_and_get_action(self):
        data = self.payload()
        data['action_token'] = 'invalid'
        self.assertEqual(self.client.post(self.url,data).status_code,400)
        self.client.force_login(user(Role.PROCUREMENT))
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.assertEqual(self.client.get(f'/orders/{self.order.pk}/close/').status_code,405)

    def test_closure_confirmation_and_post(self):
        self.client.force_login(user(Role.APPROVER))
        page = self.client.get(f'/orders/{self.order.pk}/')
        self.assertEqual(page.status_code,200)
        form = page.context['close_form']
        response = self.client.post(f'/orders/{self.order.pk}/close/',dict(form.initial,reason='Batal kebutuhan'))
        self.assertEqual(response.status_code,303)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status,'CANCELLED')

    def test_receipt_visibility_follows_order_and_has_no_edit_route(self):
        result = self.client.post(self.url,self.payload())
        self.assertEqual(result.status_code,303)
        self.client.force_login(user(Role.REQUESTER))
        self.assertEqual(self.client.get(result.url).status_code,404)
        self.client.force_login(self.order.request.requester)
        self.assertEqual(self.client.get(result.url).status_code,200)
        self.assertEqual(self.client.post(result.url,{}).status_code,405)
        self.assertEqual(self.client.get(result.url+'edit/').status_code,404)

    def test_csrf_and_terminal_get_guard(self):
        from django.test import Client
        from procurement.models import PurchaseOrder
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.actor)
        self.assertEqual(protected.post(self.url,self.payload()).status_code,403)
        PurchaseOrder.objects.filter(pk=self.order.pk).update(status='RECEIVED')
        self.assertEqual(self.client.get(self.url).status_code,409)

    def test_stale_http_and_busy_response(self):
        from unittest.mock import patch
        from django.db import OperationalError
        data = self.payload()
        self.client.post(self.url,data)
        data = self.payload()
        data['expected_version'] = '1'
        self.assertEqual(self.client.post(self.url,data).status_code,409)
        data = self.payload()
        with patch('procurement.views.receipts.post_receipt',side_effect=OperationalError('database is locked')):
            response = self.client.post(self.url,data)
        self.assertEqual((response.status_code,response['Retry-After']),(503,'5'))

    def test_goods_form_omits_service_dates_and_posts_without_them(self):
        page = self.client.get(self.url)
        self.assertNotContains(page, 'name="service_started_on"')
        self.assertNotContains(page, 'name="service_ended_on"')
        result = self.client.post(self.url, self.payload())
        self.assertEqual(result.status_code, 303)
        receipt = Receipt.objects.get(order=self.order)
        self.assertIsNone(receipt.service_started_on)
        self.assertIsNone(receipt.service_ended_on)

    def test_goods_rejects_forged_service_dates_without_rendering_them(self):
        data = self.payload()
        data.update(service_started_on='2026-01-01', service_ended_on='2026-01-02')
        page = self.client.post(self.url, data)
        self.assertEqual(page.status_code, 400)
        self.assertTrue(page.context['form'].non_field_errors())
        self.assertNotContains(page, 'name="service_started_on"', status_code=400)
        self.assertNotContains(page, 'name="service_ended_on"', status_code=400)
        self.assertFalse(Receipt.objects.exists())

    def test_services_keep_required_dates_and_save_the_period(self):
        from django.utils import timezone
        self.order = issued(kind='SERVICES')
        self.url = f'/orders/{self.order.pk}/receipts/new/'
        page = self.client.get(self.url)
        for name in ('service_started_on', 'service_ended_on'):
            self.assertContains(page, f'name="{name}"')
            self.assertTrue(page.context['form'].fields[name].required)
        data = self.payload()
        data['evidence_type'] = 'SERVICE_REPORT'
        self.assertEqual(self.client.post(self.url, data).status_code, 400)
        today = timezone.localdate()
        data.update(service_started_on=today.isoformat(), service_ended_on=today.isoformat())
        result = self.client.post(self.url, data)
        self.assertEqual(result.status_code, 303)
        receipt = Receipt.objects.get(order=self.order)
        self.assertEqual((receipt.service_started_on, receipt.service_ended_on), (today, today))

    def test_record_receipt_entry_precedes_order_metadata_and_respects_role(self):
        page = self.client.get(f'/orders/{self.order.pk}/')
        entry = f'href="{self.url}"'.encode()
        self.assertLess(page.content.index(entry), page.content.index(b'<dl>'))
        self.client.force_login(user(Role.ADMIN))
        self.assertNotContains(self.client.get(f'/orders/{self.order.pk}/'), entry.decode())

    def test_receipt_next_action_follows_remaining_quantity_and_role(self):
        result = self.client.post(self.url, self.payload())
        page = self.client.get(result.url)
        self.assertContains(page, f'href="{self.url}"')
        self.client.force_login(user(Role.ADMIN))
        self.assertNotContains(self.client.get(result.url), f'href="{self.url}"')
        self.client.force_login(self.actor)
        data = self.payload()
        data.update(reference='SJ-HTTP-2', **{
            'items-0-accepted': '4', 'items-0-rejected': '0',
            'items-0-rejection_reason': '',
        })
        final = self.client.post(self.url, data)
        self.assertEqual(final.status_code, 303)
        self.assertNotContains(self.client.get(final.url), f'href="{self.url}"')
