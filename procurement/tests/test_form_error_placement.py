from datetime import timedelta
from html.parser import HTMLParser
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from common.actions import ActionContext
from procurement.inputs import DraftInput, QuotationInput, QuoteLineInput, RequestLineInput
from procurement.services.requests import save_draft, submit_request
from procurement.services.sourcing import save_quotation
from procurement.tests.factories import approved, context, draft, issued, user


class ErrorLocations(HTMLParser):
    def __init__(self):
        super().__init__()
        self.form_depth = 0
        self.error_lists = 0
        self.outside_errors = []
        self.form_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.form_depth += 1
            self.form_text.append([])
        if 'errorlist' in attrs.get('class', '').split():
            self.error_lists += 1
            if not self.form_depth:
                self.outside_errors.append('errorlist')
        if attrs.get('role') == 'alert' and not self.form_depth:
            self.outside_errors.append('alert')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.form_depth -= 1

    def handle_data(self, data):
        if self.form_depth:
            self.form_text[-1].append(data)


class FormErrorPlacementTests(TestCase):
    def setUp(self):
        self.owner = user(Role.REQUESTER)
        self.admin = user(Role.ADMIN)
        self.buyer = user(Role.PROCUREMENT)
        self.approver = user(Role.APPROVER)
        self.receiver = user(Role.RECEIVER)
        self.draft = draft(self.owner)
        self.approved = approved(self.owner, self.approver)
        self.order = issued()
        self.vendor = self.order.quotation.vendor
        revision = self.approved.revisions.get(number=1)
        self.quote = save_quotation(context(self.buyer, self.approved), request_id=self.approved.pk,
            quotation_id=None, data=QuotationInput(self.vendor.pk, 'UI-QUOTE', timezone.localdate(),
                timezone.localdate()+timedelta(days=7), 1,
                tuple(QuoteLineInput(item.pk, '8') for item in revision.items.all())))
        pending = save_draft(ActionContext(self.owner.pk, uuid4(), None), request_id=None,
            data=DraftInput('GOODS', 'Pengujian UI', 'Kebutuhan', 'Kantor', timezone.localdate(),
                            (RequestLineInput('Item', 'unit', '1', '10'),)))
        self.pending = submit_request(context(self.owner, pending), request_id=pending.pk)

    def assert_errors_inside_form(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, 'id="error-summary"', status_code=400)
        parser = ErrorLocations()
        parser.feed(response.content.decode())
        self.assertGreater(parser.error_lists, 0)
        self.assertEqual(parser.outside_errors, [])
        return parser

    def test_invalid_forms_keep_errors_inside_the_affected_form(self):
        cases = [
            (self.admin, '/users/new/'),
            (self.admin, f'/users/{self.owner.pk}/edit/'),
            (self.admin, f'/users/{self.owner.pk}/password/'),
            (self.admin, '/vendors/new/'),
            (self.admin, f'/vendors/{self.vendor.pk}/edit/'),
            (self.owner, '/requests/new/'),
            (self.owner, f'/requests/{self.draft.pk}/edit/'),
            (self.owner, f'/requests/{self.draft.pk}/submit/'),
            (self.owner, f'/requests/{self.draft.pk}/cancel/'),
            (self.approver, f'/requests/{self.pending.pk}/review/'),
            (self.buyer, f'/requests/{self.approved.pk}/request-revision/'),
            (self.buyer, f'/requests/{self.approved.pk}/quotations/new/'),
            (self.buyer, f'/requests/{self.approved.pk}/quotations/{self.quote.pk}/edit/'),
            (self.buyer, f'/requests/{self.approved.pk}/quotations/select/'),
            (self.buyer, f'/requests/{self.approved.pk}/issue-po/'),
            (self.receiver, f'/orders/{self.order.pk}/receipts/new/'),
            (self.approver, f'/orders/{self.order.pk}/close/'),
        ]
        for actor, path in cases:
            with self.subTest(path=path):
                self.client.force_login(actor)
                self.assert_errors_inside_form(self.client.post(path, {}))
        for path in ('/requests/', '/orders/'):
            with self.subTest(path=path):
                self.client.force_login(self.admin)
                response = self.client.get(path, {'kind': 'UNKNOWN'})
                self.assert_errors_inside_form(response)
                self.assertNotContains(response, 'Perbaiki filter untuk menampilkan daftar.', status_code=400)

    def test_last_admin_message_is_shown_once_without_changing_the_account(self):
        self.client.force_login(self.admin)
        path = f'/users/{self.admin.pk}/edit/'
        form = self.client.get(path).context['form']
        response = self.client.post(path, {'username': self.admin.username, 'role': Role.REQUESTER,
            'is_active': 'on', 'action_token': form.initial['action_token'],
            'expected_version': form.initial['expected_version']})
        parser = self.assert_errors_inside_form(response)
        message = 'Admin aktif terakhir tidak dapat dinonaktifkan atau diubah perannya.'
        self.assertContains(response, message, count=1, status_code=400)
        self.assertEqual(sum(message in ' '.join(parts) for parts in parser.form_text), 1)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.role, self.admin.is_active), (Role.ADMIN, True))
