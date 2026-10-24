# filepath: procurement/tests/test_stage11_followups.py
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import Role
from procurement.inputs import QuotationInput, QuoteLineInput
from procurement.models import RequestRevision, Vendor
from procurement.selectors import comparison_rows
from procurement.services import orders, requests, sourcing
from procurement.tests.factories import approved, context, user


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class Stage11FollowupTests(TestCase):
    def setUp(self):
        self.owner, self.approver, self.buyer = (
            user(Role.REQUESTER), user(Role.APPROVER), user(Role.PROCUREMENT)
        )
        self.target = approved(self.owner, self.approver)
        self.vendor = Vendor.objects.create(
            name='Vendor Pengujian', contact='test@example.invalid', created_by=self.buyer
        )
        self.client.force_login(self.buyer)
        self.path = f'/requests/{self.target.pk}/quotations/'

    def add_quotes(self, count):
        revision = self.target.revisions.get(number=self.target.current_revision_number)
        item = revision.items.get()
        result = []
        today = timezone.localdate()
        for position in range(count):
            self.target.refresh_from_db()
            result.append(sourcing.save_quotation(
                context(self.buyer, self.target), request_id=self.target.pk, quotation_id=None,
                data=QuotationInput(self.vendor.pk, f'Q-{position}', today,
                                    today + timedelta(days=7), 2,
                                    (QuoteLineInput(item.pk, '8.00'),))
            ))
        self.target.refresh_from_db()
        return result

    def prepare_paginated_history(self):
        self.add_quotes(51)
        self.target = requests.request_revision(
            context(self.buyer, self.target), request_id=self.target.pk, reason='Revisi Kebutuhan'
        )
        self.target = requests.submit_request(context(self.owner, self.target), request_id=self.target.pk)
        self.target = requests.review_request(
            context(self.approver, self.target), request_id=self.target.pk, decision='APPROVE', reason=''
        )
        self.add_quotes(51)

    def test_pagination_links_preserve_the_other_list_page(self):
        self.prepare_paginated_history()
        response = self.client.get(self.path, {'page': 2, 'history_page': 2})
        self.assertEqual(response.status_code, 200)
        links = [attrs['href'] for tag, attrs in Elements(response.content.decode()).elements
                 if tag == 'a' and attrs.get('href', '').startswith('?')]
        values = [parse_qs(urlsplit(link).query) for link in links]
        for expected in (
            {'page': ['1'], 'history_page': ['2']},
            {'page': ['3'], 'history_page': ['2']},
            {'page': ['2'], 'history_page': ['1']},
            {'page': ['2'], 'history_page': ['3']},
        ):
            self.assertIn(expected, values)
        for link in links:
            destination = self.client.get(self.path + link)
            query = parse_qs(urlsplit(link).query)
            self.assertEqual(destination.context['page_obj'].number, int(query['page'][0]))
            self.assertEqual(destination.context['history_page'].number, int(query['history_page'][0]))

    def test_comparison_snapshot_query_count_is_constant_for_more_candidates(self):
        self.add_quotes(1)
        revision = RequestRevision.objects.get(request=self.target, number=1)
        with CaptureQueriesContext(connection) as first:
            initial = comparison_rows(revision)
        self.assertEqual(initial[0]['issues'], [])
        self.assertEqual(initial[0]['lines'][0].revision_item.name, 'Item contoh')
        self.add_quotes(6)
        revision = RequestRevision.objects.get(request=self.target, number=1)
        with CaptureQueriesContext(connection) as expanded:
            rows = comparison_rows(revision)
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row['issues'] == [] for row in rows))
        self.assertEqual(len(expanded), len(first))

    def test_selection_reads_revision_items_once_for_many_candidates(self):
        quote = self.add_quotes(8)[0]
        with CaptureQueriesContext(connection) as captured:
            selected = sourcing.select_quotation(
                context(self.buyer, self.target), request_id=self.target.pk, quotation_id=quote.pk,
                reason='Sesuai Kebutuhan', single_source_reason='Satu Vendor Layak'
            )
        snapshot_queries = [query['sql'] for query in captured
                            if query['sql'].lstrip().startswith('SELECT')
                            and not query['sql'].lstrip().startswith('SELECT 1 ')
                            and 'FROM "procurement_revisionitem"' in query['sql']]
        self.assertEqual(len(snapshot_queries), 1)
        self.target.refresh_from_db()
        self.assertEqual(selected.selected_quotation_id, quote.pk)
        self.assertEqual(self.target.selected_quotation_id, quote.pk)

    def test_issue_order_reads_revision_items_once_for_many_candidates(self):
        quote = self.add_quotes(8)[0]
        self.target = sourcing.select_quotation(
            context(self.buyer, self.target), request_id=self.target.pk, quotation_id=quote.pk,
            reason='Sesuai Kebutuhan', single_source_reason='Satu Vendor Layak'
        )
        with CaptureQueriesContext(connection) as captured:
            order = orders.issue_order(context(self.buyer, self.target), request_id=self.target.pk)
        snapshot_queries = [query['sql'] for query in captured
                            if query['sql'].lstrip().startswith('SELECT')
                            and not query['sql'].lstrip().startswith('SELECT 1 ')
                            and 'FROM "procurement_revisionitem"' in query['sql']]
        self.assertEqual(len(snapshot_queries), 1)
        self.assertEqual(order.items.get().name, 'Item contoh')
        self.assertEqual(order.total_minor, 8000)

    def test_detail_jump_target_accepts_focus_before_actions(self):
        response = self.client.get(f'/requests/{self.target.pk}/')
        elements = Elements(response.content.decode()).elements
        links = [attrs for tag, attrs in elements if tag == 'a' and attrs.get('href') == '#followup']
        targets = [attrs for _, attrs in elements if attrs.get('id') == 'followup']
        self.assertEqual(len(links), 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].get('tabindex'), '-1')
