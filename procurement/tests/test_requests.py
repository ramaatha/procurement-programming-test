# filepath: procurement/tests/test_requests.py
import importlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.http import Http404
from django.test import Client, TestCase, TransactionTestCase
from django.test import RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser
from django.urls import resolve
from django.views.debug import SafeExceptionReporterFilter
from django.utils import timezone

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.inputs import DraftInput, RequestLineInput
from procurement.models import ActionReceipt, AuditEvent, PurchaseRequest, RequestStatus
from procurement.tests.factories import issued, user


def data(*, items=None, **changes):
    values=dict(kind='GOODS',title='Kebutuhan kantor',reason='Penggantian',destination='Kantor',needed_on=timezone.localdate()+timedelta(days=2),items=(RequestLineInput('Kursi','unit','10','100.00'),) if items is None else items)
    return DraftInput(**(values|changes))


class RequestServiceTests(TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('procurement.services'), 'Service permintaan belum tersedia.')
        self.service=importlib.import_module('procurement.services.requests')
        self.owner=user(Role.REQUESTER)
        self.create_ctx=ActionContext(self.owner.pk,uuid4(),None)

    def create(self, value=None):
        return self.service.save_draft(self.create_ctx,request_id=None,data=value or data())

    def ctx(self, request, actor=None):
        return ActionContext((actor or self.owner).pk,uuid4(),request.version)

    def test_TC03_incomplete_draft_and_no_items_are_allowed(self):
        request=self.create(data(items=(),title='',reason='',destination='',needed_on=None))
        self.assertEqual(request.requester_id,self.owner.pk)
        self.assertEqual(request.status,'DRAFT')
        self.assertEqual(request.version,1)
        self.assertFalse(request.items.exists())
        with self.assertRaises(ValidationError):self.service.submit_request(self.ctx(request),request_id=request.pk)
        self.assertFalse(request.revisions.exists())

    def test_TC03_each_saved_item_must_be_complete_and_positive(self):
        for line in [RequestLineInput('','unit','1','1'),RequestLineInput('Kursi','','1','1'),RequestLineInput('Kursi','unit','0','1'),RequestLineInput('Kursi','unit','1','0'),RequestLineInput('Kursi','unit','1.0001','1'),RequestLineInput('Kursi','unit',1.0,'1')]:
            with self.subTest(line='invalid'),self.assertRaises(ValidationError):self.create(data(items=(line,)))
        self.assertFalse(PurchaseRequest.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC03_submit_requires_future_or_today_date_and_complete_header(self):
        for changes in [dict(title=''),dict(reason=''),dict(destination=''),dict(needed_on=None),dict(needed_on=timezone.localdate()-timedelta(days=1)),dict(items=())]:
            self.create_ctx=ActionContext(self.owner.pk,uuid4(),None)
            request=self.create(data(**changes))
            with self.subTest(changes=list(changes)),self.assertRaises(ValidationError):self.service.submit_request(self.ctx(request),request_id=request.pk)
            request.refresh_from_db()
            self.assertEqual(request.status,'DRAFT')
            self.assertFalse(request.revisions.exists())
        self.create_ctx=ActionContext(self.owner.pk,uuid4(),None)
        request=self.create(data(needed_on=timezone.localdate()))
        self.assertEqual(self.service.submit_request(self.ctx(request),request_id=request.pk).status,'SUBMITTED')

    def test_TC04_submit_freezes_half_up_line_totals_and_header(self):
        lines=(RequestLineInput('A','unit','0.5','0.01'),RequestLineInput('B','unit','0.5','0.01'))
        request=self.create(data(items=lines))
        result=self.service.submit_request(self.ctx(request),request_id=request.pk)
        revision=result.revisions.get(number=1)
        self.assertEqual(revision.estimated_total_minor,2)
        self.assertEqual(list(revision.items.values_list('line_total_minor',flat=True)),[1,1])
        self.assertEqual(revision.title,'Kebutuhan kantor')
        self.assertEqual(revision.submitted_by_id,self.owner.pk)
        self.assertEqual(result.version,2)

    def test_TC04_revision_snapshot_is_not_overwritten_by_working_copy_edit(self):
        request=self.create()
        request=self.service.submit_request(self.ctx(request),request_id=request.pk)
        old=request.revisions.get(number=1)
        PurchaseRequest.objects.filter(pk=request.pk).update(status='CHANGES_REQUESTED')
        request.refresh_from_db()
        request=self.service.save_draft(self.ctx(request),request_id=request.pk,data=data(title='Revisi',items=(RequestLineInput('Meja','unit','2','200'),)))
        request=self.service.submit_request(self.ctx(request),request_id=request.pk)
        old.refresh_from_db()
        self.assertEqual(old.title,'Kebutuhan kantor')
        self.assertEqual(old.items.get().name,'Kursi')
        self.assertEqual(request.current_revision_number,2)
        self.assertEqual(request.revisions.get(number=2).items.get().name,'Meja')

    def test_TC18_create_edit_submit_cancel_replays_are_idempotent(self):
        request=self.create()
        self.assertEqual(self.create().pk,request.pk)
        edit_ctx=self.ctx(request)
        request=self.service.save_draft(edit_ctx,request_id=request.pk,data=data(title='Baru'))
        self.service.save_draft(edit_ctx,request_id=request.pk,data=data(title='Baru'))
        submit_ctx=self.ctx(request)
        request=self.service.submit_request(submit_ctx,request_id=request.pk)
        self.service.submit_request(submit_ctx,request_id=request.pk)
        cancel_ctx=self.ctx(request)
        request=self.service.cancel_request(cancel_ctx,request_id=request.pk,reason='Tidak diperlukan')
        self.service.cancel_request(cancel_ctx,request_id=request.pk,reason='Tidak diperlukan')
        self.assertEqual(PurchaseRequest.objects.count(),1)
        self.assertEqual(request.revisions.count(),1)
        self.assertEqual(AuditEvent.objects.filter(request=request).count(),4)
        self.assertEqual(ActionReceipt.objects.filter(actor=self.owner).count(),4)

    def test_TC18_changed_payload_and_stale_version_conflict_without_writes(self):
        request=self.create()
        with self.assertRaises(ConflictError):self.create(data(title='Berbeda'))
        stale=self.ctx(request)
        self.service.save_draft(self.ctx(request),request_id=request.pk,data=data(title='Baru'))
        with self.assertRaises(ConflictError):self.service.save_draft(stale,request_id=request.pk,data=data())
        request.refresh_from_db()
        self.assertEqual(request.title,'Baru')
        self.assertEqual(request.version,2)

    def test_TC18_equivalent_numeric_text_replays_same_canonical_payload(self):
        first=self.create(data(items=(RequestLineInput('A','unit','1.0','02.0'),)))
        second=self.create(data(items=(RequestLineInput('A','unit','1.000','2.00'),)))
        self.assertEqual(first.pk,second.pk)
        self.assertEqual(AuditEvent.objects.filter(request=first).count(),1)

    def test_TC02_owner_and_current_role_are_checked_before_replay(self):
        request=self.create()
        other=user(Role.REQUESTER)
        with self.assertRaises(Http404):self.service.save_draft(self.ctx(request,other),request_id=request.pk,data=data())
        User.objects.filter(pk=self.owner.pk).update(role=Role.APPROVER)
        with self.assertRaises(PermissionDenied):self.create()
        with self.assertRaises(PermissionDenied):self.service.submit_request(self.ctx(request),request_id=request.pk)
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):self.service.cancel_request(self.ctx(request),request_id=request.pk,reason='Batal')

    def test_TC15_cancel_permitted_states_requires_reason_and_clears_selection(self):
        for state in ['DRAFT','CHANGES_REQUESTED','SUBMITTED','APPROVED']:
            self.create_ctx=ActionContext(self.owner.pk,uuid4(),None)
            request=self.create()
            PurchaseRequest.objects.filter(pk=request.pk).update(status=state,selection_reason='Lama',single_source_reason='Lama')
            request.refresh_from_db()
            with self.subTest(state=state),self.assertRaises(ValidationError):self.service.cancel_request(self.ctx(request),request_id=request.pk,reason='  ')
            request=self.service.cancel_request(self.ctx(request),request_id=request.pk,reason='Tidak diperlukan')
            self.assertEqual(request.status,'CANCELLED')
            self.assertEqual(request.selection_reason,'')
            self.assertEqual(request.single_source_reason,'')
            self.assertEqual(AuditEvent.objects.get(request=request,action='request.cancel').reason,'Tidak diperlukan')

    def test_TC15_existing_po_blocks_edit_submit_and_cancel_even_if_terminal(self):
        order=issued()
        order.status='CANCELLED';order.closed_by=order.issued_by;order.closed_at=timezone.now();order.closed_reason='Tidak dilanjutkan';order.save()
        request=order.request
        self.owner=request.requester
        for operation in [lambda:self.service.save_draft(self.ctx(request),request_id=request.pk,data=data()),lambda:self.service.submit_request(self.ctx(request),request_id=request.pk),lambda:self.service.cancel_request(self.ctx(request),request_id=request.pk,reason='Batal')]:
            with self.assertRaises(ConflictError):operation()

    def test_TC03_terminal_or_submitted_request_cannot_be_edited_or_resubmitted(self):
        request=self.create()
        for state in ['SUBMITTED','APPROVED','REJECTED','CANCELLED']:
            PurchaseRequest.objects.filter(pk=request.pk).update(status=state)
            request.refresh_from_db()
            with self.subTest(state=state),self.assertRaises(ConflictError):self.service.save_draft(self.ctx(request),request_id=request.pk,data=data())
            with self.assertRaises(ConflictError):self.service.submit_request(self.ctx(request),request_id=request.pk)

    def test_TC13_snapshot_audit_failure_rolls_back_revision_and_status(self):
        request=self.create()
        with patch('procurement.services.requests.AuditEvent.objects.create',side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):self.service.submit_request(self.ctx(request),request_id=request.pk)
        request.refresh_from_db()
        self.assertEqual(request.status,'DRAFT')
        self.assertEqual(request.current_revision_number,0)
        self.assertFalse(request.revisions.exists())
        self.assertEqual(ActionReceipt.objects.filter(actor=self.owner).count(),1)

    def test_TC04_overflow_in_line_or_document_total_is_rejected_atomically(self):
        for lines in [(RequestLineInput('A','unit','9223372036854775.807','10.01'),),(RequestLineInput('A','unit','1','92233720368547758.07'),RequestLineInput('B','unit','1','0.01'))]:
            with self.subTest(lines=len(lines)),self.assertRaises(ValidationError):self.create(data(items=lines))
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_TC18_version_and_revision_limit_do_not_overflow_storage(self):
        request=self.create()
        PurchaseRequest.objects.filter(pk=request.pk).update(version=9223372036854775807)
        request.refresh_from_db()
        with self.assertRaises(ValidationError):self.service.save_draft(self.ctx(request),request_id=request.pk,data=data())
        PurchaseRequest.objects.filter(pk=request.pk).update(version=1,current_revision_number=9223372036854775807)
        request.refresh_from_db()
        with self.assertRaises(ValidationError):self.service.submit_request(self.ctx(request),request_id=request.pk)


class RequestHttpTests(TestCase):
    def setUp(self):
        self.owner=user(Role.REQUESTER)
        self.client.force_login(self.owner)

    def form_payload(self, **changes):
        response=self.client.get('/requests/new/')
        self.assertEqual(response.status_code,200)
        values={'kind':'GOODS','title':'Kursi','reason':'Kebutuhan','destination':'Kantor','needed_on':str(timezone.localdate()+timedelta(days=1)),'action_token':response.context['form'].initial['action_token'],'items-TOTAL_FORMS':'1','items-INITIAL_FORMS':'0','items-0-name':'Kursi','items-0-unit':'unit','items-0-quantity':'0.333','items-0-unit_price':'0.05'}
        return values|changes

    def create(self):
        response=self.client.post('/requests/new/',self.form_payload())
        self.assertEqual(response.status_code,303)
        return PurchaseRequest.objects.get(requester=self.owner)

    def test_TC18_initial_form_does_not_show_a_validation_alert(self):
        response=self.client.get('/requests/new/')
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,'role="alert"')

    def test_TC03_delete_checkbox_removes_working_item_without_snapshot_change(self):
        request=self.create()
        form=self.client.get(f'/requests/{request.pk}/edit/').context['form']
        payload=self.form_payload(**{'items-INITIAL_FORMS':'1','items-0-DELETE':'on'})
        payload.update(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])
        self.assertEqual(self.client.post(f'/requests/{request.pk}/edit/',payload).status_code,303)
        self.assertFalse(request.items.exists())
        self.assertFalse(request.revisions.exists())

    @override_settings(DEBUG=False)
    def test_TC18_request_action_tokens_are_redacted_in_exception_reports(self):
        for path in ['/requests/new/',f'/requests/{uuid4()}/edit/',f'/requests/{uuid4()}/submit/',f'/requests/{uuid4()}/cancel/']:
            request=RequestFactory().post(path,dict(action_token='synthetic-action-token',csrfmiddlewaretoken='synthetic-csrf-token'))
            request.user=AnonymousUser()
            match=resolve(path);match.func(request,**match.kwargs)
            filtered=SafeExceptionReporterFilter().get_post_parameters(request)
            for field in ['action_token','csrfmiddlewaretoken']:
                with self.subTest(path=path,field=field):self.assertNotEqual(filtered[field],request.POST[field])

    def test_TC03_create_ignores_owner_total_and_status_from_browser(self):
        response=self.client.post('/requests/new/',self.form_payload(requester=str(user(Role.REQUESTER).pk),status='APPROVED',total_minor='1'))
        self.assertEqual(response.status_code,303)
        request=PurchaseRequest.objects.get()
        self.assertEqual(request.requester_id,self.owner.pk)
        self.assertEqual(request.status,'DRAFT')
        self.assertContains(self.client.get(response['Location']),'0,02')

    def test_TC03_blank_extra_rows_are_ignored_partial_rows_are_invalid(self):
        payload=self.form_payload(**{'items-TOTAL_FORMS':'2'})
        self.assertEqual(self.client.post('/requests/new/',payload).status_code,303)
        self.assertEqual(PurchaseRequest.objects.get().items.count(),1)
        payload=self.form_payload(**{'items-TOTAL_FORMS':'2','items-1-name':'Tidak lengkap'})
        response=self.client.post('/requests/new/',payload)
        self.assertEqual(response.status_code,400)
        self.assertContains(response,'Tidak lengkap',status_code=400)
        self.assertEqual(PurchaseRequest.objects.count(),1)

    def test_TC03_add_row_preserves_data_without_persisting_draft(self):
        response=self.client.post('/requests/new/',self.form_payload(intent='add_row'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.context['formset'].forms),2)
        self.assertContains(response,'Kursi')
        self.assertNotContains(response,'role="alert"')
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_TC03_missing_management_data_is_rejected(self):
        payload=self.form_payload()
        del payload['items-TOTAL_FORMS']
        self.assertEqual(self.client.post('/requests/new/',payload).status_code,400)
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_TC02_unrelated_requester_cannot_read_edit_or_post_to_request(self):
        request=self.create()
        self.client.force_login(user(Role.REQUESTER))
        for suffix in ['', 'edit/', 'submit/', 'cancel/', 'revisions/1/']:
            path=f'/requests/{request.pk}/{suffix}'
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,404 if suffix not in ['submit/','cancel/'] else 405)
        self.assertEqual(self.client.post(f'/requests/{request.pk}/cancel/',{}).status_code,404)
        self.assertNotContains(self.client.get('/requests/'),request.number)

    def test_TC02_read_visibility_matches_role_matrix(self):
        request=self.create()
        for role in [Role.ADMIN,Role.APPROVER,Role.PROCUREMENT]:
            self.client.force_login(user(role))
            self.assertContains(self.client.get('/requests/'),request.number)
            self.assertEqual(self.client.get(f'/requests/{request.pk}/').status_code,200)
            self.assertEqual(self.client.get(f'/requests/{request.pk}/edit/').status_code,403)
            self.assertEqual(self.client.get('/requests/new/').status_code,403)
        receiver=user(Role.RECEIVER);self.client.force_login(receiver)
        self.assertNotContains(self.client.get('/requests/'),request.number)
        self.assertEqual(self.client.get(f'/requests/{request.pk}/').status_code,404)
        order=issued()
        self.assertEqual(self.client.get(f'/requests/{order.request_id}/').status_code,200)

    def test_TC18_submit_snapshot_view_and_cancel_are_post_only_and_replay_safe(self):
        request=self.create()
        detail=self.client.get(f'/requests/{request.pk}/')
        form=detail.context['submit_form']
        payload=dict(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])
        path=f'/requests/{request.pk}/submit/'
        self.assertEqual(self.client.get(path).status_code,405)
        self.assertEqual(self.client.post(path,payload).status_code,303)
        self.assertEqual(self.client.post(path,payload).status_code,303)
        self.assertContains(self.client.get(f'/requests/{request.pk}/revisions/1/'),'0,02')
        detail=self.client.get(f'/requests/{request.pk}/');form=detail.context['cancel_form']
        self.assertEqual(self.client.post(f'/requests/{request.pk}/cancel/',dict(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'],reason='Tidak diperlukan')).status_code,303)
        self.assertContains(self.client.get(f'/requests/{request.pk}/'),'Dibatalkan')
        self.assertEqual(request.revisions.count(),1)

    def test_TC18_another_actors_token_and_stale_edit_are_rejected(self):
        payload=self.form_payload()
        self.client.force_login(user(Role.REQUESTER))
        self.assertEqual(self.client.post('/requests/new/',payload).status_code,400)
        self.client.force_login(self.owner)
        request=self.create()
        form=self.client.get(f'/requests/{request.pk}/edit/').context['form']
        payload.update(action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])
        payload['items-INITIAL_FORMS']='1'
        self.assertEqual(self.client.post(f'/requests/{request.pk}/edit/',payload).status_code,303)
        payload['action_token']=self.client.get(f'/requests/{request.pk}/edit/').context['form'].initial['action_token']
        self.assertEqual(self.client.post(f'/requests/{request.pk}/edit/',payload).status_code,409)

    def test_TC02_csrf_is_required_and_user_text_is_escaped(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.owner)
        response=client.get('/requests/new/')
        self.assertEqual(response.status_code,200)
        payload=self.form_payload(title='<script>alert(1)</script>')
        self.assertEqual(client.post('/requests/new/',payload).status_code,403)
        payload['csrfmiddlewaretoken']=client.cookies['csrftoken'].value
        # Token belongs to the same actor, not a browser session.
        response=client.post('/requests/new/',payload)
        self.assertEqual(response.status_code,303)
        detail=client.get(response['Location'])
        self.assertNotContains(detail,'<script>alert(1)</script>')
        self.assertContains(detail,'&lt;script&gt;')


class RequestConcurrencyTests(TransactionTestCase):
    def test_TC18_two_submitters_produce_one_snapshot_for_same_or_different_nonce(self):
        self.assertIsNotNone(importlib.util.find_spec('procurement.services'),'Request service missing.')
        service=importlib.import_module('procurement.services.requests')
        owner=user(Role.REQUESTER)
        for same_nonce in [True,False]:
            request=service.save_draft(ActionContext(owner.pk,uuid4(),None),request_id=None,data=data())
            nonce=uuid4();gate=Barrier(2)
            contexts=[ActionContext(owner.pk,nonce,request.version),ActionContext(owner.pk,nonce if same_nonce else uuid4(),request.version)]
            def submit(ctx):
                close_old_connections()
                try:
                    gate.wait(timeout=5)
                    service.submit_request(ctx,request_id=request.pk)
                    return 'ok'
                except ConflictError:return 'conflict'
                finally:close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,contexts))
            self.assertEqual(results.count('ok'),2 if same_nonce else 1)
            self.assertEqual(request.revisions.count(),1)
            self.assertEqual(AuditEvent.objects.filter(request=request,action='request.submit').count(),1)
