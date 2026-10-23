from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import Role
from procurement.models import AuditEvent, PurchaseOrder, ReceiptItem
from procurement.tests.factories import context, draft, issued, user
from procurement.tests.receipt_fixtures import receipt_data


class TrackingTests(TestCase):
    def setUp(self):
        self.actor = user(Role.APPROVER)
        self.client.force_login(self.actor)

    def test_operational_stage_prioritizes_po_over_approved_request(self):
        from procurement import selectors
        self.assertTrue(hasattr(selectors,'operational_stage'),'Tracking stage missing')
        order = issued()
        for status in ('ISSUED','PARTIALLY_RECEIVED','RECEIVED','CANCELLED','CLOSED_SHORT'):
            terminal = status in ('CANCELLED','CLOSED_SHORT')
            PurchaseOrder.objects.filter(pk=order.pk).update(status=status,closed_by=self.actor if terminal else None,
                         closed_at=timezone.now() if terminal else None,closed_reason='Akhir pesanan' if terminal else '')
            target = selectors.visible_requests(self.actor).get(pk=order.request_id)
            self.assertEqual(selectors.operational_stage(target),status)
        target = draft(user(Role.REQUESTER))
        self.assertEqual(selectors.operational_stage(target),'DRAFT')

    def test_query_number_title_and_combined_kind_stage(self):
        goods = issued()
        service = issued(kind='SERVICES')
        page = self.client.get('/requests/',dict(q=service.request.title,kind='SERVICES',stage='ISSUED'))
        self.assertEqual(page.status_code,200)
        self.assertEqual([row.pk for row in page.context['page_obj']],[service.request_id])
        page = self.client.get('/requests/',dict(q=goods.request.number))
        self.assertEqual([row.pk for row in page.context['page_obj']],[goods.request_id])

    def test_order_search_includes_po_number_and_source_title(self):
        order = issued()
        for query in (order.number,order.request.number,order.request.title):
            page = self.client.get('/orders/',dict(q=query,kind='GOODS',stage='ISSUED'))
            self.assertEqual([row.pk for row in page.context['page_obj']],[order.pk])

    def test_filters_reject_invalid_input_without_broad_results(self):
        issued()
        for url in ('/requests/','/orders/'):
            for data in (dict(kind='ALIEN'),dict(stage='INVALID'),dict(q='a'*201)):
                page = self.client.get(url,data)
                self.assertEqual(page.status_code,400)
                self.assertEqual(list(page.context['page_obj']),[])

    def test_pagination_preserves_search_and_filters(self):
        owner = user(Role.REQUESTER)
        for _ in range(26):
            draft(owner)
        page = self.client.get('/requests/',dict(q='PR-',kind='GOODS',stage='DRAFT'))
        self.assertEqual((len(page.context['page_obj']),page.context['page_obj'].paginator.count),(25,26))
        self.assertContains(page,'stage=DRAFT')
        second = self.client.get('/requests/',dict(q='PR-',kind='GOODS',stage='DRAFT',page=2))
        self.assertEqual(len(second.context['page_obj']),1)
        self.assertTrue(set(row.pk for row in page.context['page_obj']).isdisjoint(row.pk for row in second.context['page_obj']))

    def test_requester_scope_and_receiver_terminal_orders(self):
        first,second = issued(),issued()
        self.client.force_login(first.request.requester)
        page = self.client.get('/requests/',dict(q=second.request.number))
        self.assertEqual(page.context['page_obj'].paginator.count,0)
        self.assertEqual(self.client.get(f'/requests/{second.request_id}/').status_code,404)
        self.client.force_login(user(Role.RECEIVER))
        hidden = draft(user(Role.REQUESTER))
        PurchaseOrder.objects.filter(pk=first.pk).update(status='CLOSED_SHORT',closed_by=self.actor,
                                                        closed_at=timezone.now(),closed_reason='Sisa ditutup')
        self.assertEqual(self.client.get(f'/requests/{hidden.pk}/').status_code,404)
        self.assertEqual(self.client.get('/orders/',dict(stage='CLOSED_SHORT')).context['page_obj'].paginator.count,1)

    def test_closed_short_balances_and_request_detail_agree(self):
        from procurement import selectors
        self.assertTrue(hasattr(selectors,'order_balances'),'Shared balances missing')
        from procurement.services.receipts import post_receipt
        from procurement.services.orders import close_order
        order = issued()
        actor = user(Role.RECEIVER)
        post_receipt(context(actor,order),order_id=order.pk,data=receipt_data(order))
        order.refresh_from_db()
        close_order(context(self.actor,order),order_id=order.pk,reason='Sisa tidak dilanjutkan')
        order.refresh_from_db()
        self.assertEqual(selectors.order_balances(order)[order.items.get().pk],dict(ordered_milli=10000,accepted_milli=6000,rejected_milli=2000,remaining_milli=4000))
        for url in (f'/requests/{order.request_id}/',f'/orders/{order.pk}/'):
            page = self.client.get(url)
            self.assertContains(page,'Selesai Dengan Kekurangan')
            self.assertNotContains(page,'Diterima lengkap')
            self.assertContains(page,'4.000')

    def test_audit_chronology_labels_actor_and_reason_are_historical(self):
        order = issued()
        event = AuditEvent.objects.create(request=order.request,actor=self.actor,actor_name='Nama saat keputusan',actor_role='APPROVER',
                  action='order.close',target_type='ORDER',target_id=str(order.pk),reason='<script>rahasia</script>',changes=dict(status='CLOSED_SHORT'))
        self.actor.username='Nama sekarang'
        self.actor.save(update_fields=['username'])
        page = self.client.get(f'/requests/{order.request_id}/')
        self.assertContains(page,'Nama saat keputusan')
        self.assertContains(page,'Sisa PO Ditutup')
        self.assertNotContains(page,'<script>rahasia</script>')
        times = [item.created_at for item in page.context['audit_page']]
        self.assertEqual(times,sorted(times))

    def test_audit_is_paginated_without_duplicate_events(self):
        order = issued()
        for _ in range(30):
            AuditEvent.objects.create(request=order.request,actor=self.actor,actor_name='Reviewer',actor_role='APPROVER',action='receipt.post',target_type='ORDER',target_id=str(order.pk))
        page = self.client.get(f'/requests/{order.request_id}/')
        next_page = self.client.get(f'/requests/{order.request_id}/',dict(history_page=2))
        self.assertEqual(len(page.context['audit_page']),25)
        self.assertTrue(set(row.pk for row in page.context['audit_page']).isdisjoint(row.pk for row in next_page.context['audit_page']))

    def test_stage_scan_avoids_per_row_order_queries(self):
        from procurement import selectors
        self.assertTrue(hasattr(selectors,'operational_stage'),'Tracking stage missing')
        for _ in range(3):
            issued()
        with CaptureQueriesContext(connection) as queries:
            stages = [selectors.operational_stage(row) for row in selectors.visible_requests(self.actor)]
        self.assertEqual(stages,['ISSUED']*3)
        self.assertLessEqual(len(queries),2)

    def test_read_only_tracking_and_authentication(self):
        order = issued()
        before = (AuditEvent.objects.count(),ReceiptItem.objects.count())
        for url in ('/requests/','/orders/',f'/requests/{order.request_id}/',f'/orders/{order.pk}/'):
            self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual((AuditEvent.objects.count(),ReceiptItem.objects.count()),before)
        self.assertEqual(self.client.post('/requests/',{}).status_code,405)
        self.client.logout()
        self.assertEqual(self.client.get('/orders/').status_code,302)

    def test_order_pagination_keeps_filters_and_stable_order(self):
        # Extra orders use the complete service fixture; each page must stay scoped.
        for _ in range(26):
            issued()
        page = self.client.get('/orders/',dict(q='PO-',kind='GOODS',stage='ISSUED'))
        second = self.client.get('/orders/',dict(q='PO-',kind='GOODS',stage='ISSUED',page=2))
        self.assertEqual((len(page.context['page_obj']),len(second.context['page_obj'])),(25,1))
        self.assertContains(page,'stage=ISSUED')
        self.assertTrue(set(row.pk for row in page.context['page_obj']).isdisjoint(row.pk for row in second.context['page_obj']))

    def test_query_special_characters_are_literal_and_escaped(self):
        issued()
        query = '<script>alert(1)</script>'
        page = self.client.get('/requests/',dict(q=query))
        self.assertEqual(page.context['page_obj'].paginator.count,0)
        self.assertNotContains(page,query)
        self.assertContains(page,'&lt;script&gt;')
        self.assertEqual(self.client.get('/orders/',dict(q="' OR 1=1 --")).context['page_obj'].paginator.count,0)

    def test_no_results_and_invalid_pages_have_predictable_recovery(self):
        page = self.client.get('/requests/',dict(q='missing',page='bad'))
        self.assertEqual((page.status_code,page.context['page_obj'].number),(200,1))
        self.assertContains(page,'Hapus Filter')
        self.assertContains(page,'<li>Tidak ada permintaan yang cocok dengan pencarian dan filter.</li>',html=True)

    def test_all_request_only_stages_are_filterable(self):
        from procurement.models import PurchaseRequest
        owner = user(Role.REQUESTER)
        target = draft(owner)
        for stage in ('DRAFT','SUBMITTED','CHANGES_REQUESTED','APPROVED','REJECTED','CANCELLED'):
            PurchaseRequest.objects.filter(pk=target.pk).update(status=stage)
            page = self.client.get('/requests/',dict(stage=stage))
            self.assertEqual([row.pk for row in page.context['page_obj']],[target.pk])

    def test_query_budget_for_balances_does_not_depend_on_receipt_count(self):
        from procurement.selectors import order_balances
        from procurement.services.receipts import post_receipt
        order,receiver = issued(),user(Role.RECEIVER)
        for _ in range(3):
            post_receipt(context(receiver,order),order_id=order.pk,data=receipt_data(order,'0','1','Ditolak'))
            order.refresh_from_db()
        with CaptureQueriesContext(connection) as queries:
            balances = order_balances(order)
        self.assertEqual(next(iter(balances.values()))['rejected_milli'],3000)
        self.assertLessEqual(len(queries),2)
