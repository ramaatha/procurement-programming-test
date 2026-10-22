# filepath: procurement/tests/test_approvals.py
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError, close_old_connections
from django.http import Http404
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from django.views.debug import SafeExceptionReporterFilter

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.inputs import DraftInput, RequestLineInput
from procurement.models import ActionReceipt, ApprovalDecision, AuditEvent, PurchaseRequest
from procurement.services import requests as service
from procurement.tests.factories import context, issued, user


def request_data(title='Kursi operasional'):
    return DraftInput('GOODS', title, 'Kebutuhan kantor', 'Kantor',
                      timezone.localdate() + timedelta(days=3),
                      (RequestLineInput('Kursi', 'unit', '2', '100.00'),))


def submitted(owner):
    target = service.save_draft(ActionContext(owner.pk, uuid4(), None), request_id=None, data=request_data())
    return service.submit_request(context(owner, target), request_id=target.pk)


class ApprovalServiceTests(TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(service, 'review_request', None)), 'Approval service missing')
        self.assertTrue(callable(getattr(service, 'request_revision', None)), 'Revision service missing')
        self.owner = user(Role.REQUESTER)
        self.approver = user(Role.APPROVER)
        self.buyer = user(Role.PROCUREMENT)
        self.target = submitted(self.owner)

    def review(self, decision='APPROVE', reason='', ctx=None):
        return service.review_request(ctx or context(self.approver, self.target),
                                      request_id=self.target.pk, decision=decision, reason=reason)

    def test_TC05_each_decision_records_current_snapshot_and_matching_status(self):
        for decision, status, reason in [('APPROVE', 'APPROVED', ''),
                                         ('REQUEST_CHANGES', 'CHANGES_REQUESTED', 'Rinci kebutuhan'),
                                         ('REJECT', 'REJECTED', 'Belum diperlukan')]:
            with self.subTest(decision=decision):
                self.target = submitted(self.owner)
                version = self.target.version
                result = self.review(decision, reason)
                row = ApprovalDecision.objects.get(revision__request=self.target)
                self.assertEqual((row.actor_id, row.requester_at_decision_id, row.revision.number),
                                 (self.approver.pk, self.owner.pk, 1))
                self.assertEqual((row.decision, row.reason, result.status, result.version),
                                 (decision, reason, status, version + 1))
                event = AuditEvent.objects.get(request=result, action='request.review')
                self.assertEqual((event.reason, event.changes['decision']), (reason, decision))

    def test_TC05_invalid_decision_or_required_reason_does_not_write(self):
        for decision, reason in [('REQUEST_CHANGES', '  '), ('REJECT', ''), ('OTHER', 'x'),
                                 ('APPROVE', 'x' * 4001), ('APPROVE', None)]:
            with self.subTest(decision=decision), self.assertRaises(ValidationError):
                self.review(decision, reason)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, 'SUBMITTED')
        self.assertFalse(ApprovalDecision.objects.exists())
        self.assertFalse(AuditEvent.objects.filter(action='request.review').exists())

    def test_TC06_self_review_remains_forbidden_after_role_change_and_superuser(self):
        User.objects.filter(pk=self.owner.pk).update(role=Role.APPROVER, is_superuser=True)
        with self.assertRaises(PermissionDenied):
            self.review(ctx=context(self.owner, self.target))
        self.assertFalse(ApprovalDecision.objects.exists())

    def test_TC06_wrong_role_and_inactive_actor_are_denied_before_replay(self):
        ctx = context(self.approver, self.target)
        self.review(ctx=ctx)
        for changes in [dict(role=Role.ADMIN), dict(role=Role.PROCUREMENT),
                        dict(role=Role.REQUESTER), dict(role=Role.RECEIVER),
                        dict(role=Role.APPROVER, is_active=False)]:
            User.objects.filter(pk=self.approver.pk).update(**changes)
            expected = Http404 if changes.get('role') in (Role.REQUESTER, Role.RECEIVER) else PermissionDenied
            with self.subTest(changes=changes), self.assertRaises(expected):
                self.review(ctx=ctx)
        self.assertEqual(ApprovalDecision.objects.count(), 1)

    def test_TC06_replay_is_idempotent_but_changed_payload_and_new_nonce_conflict(self):
        ctx = context(self.approver, self.target)
        first = self.review('REQUEST_CHANGES', '  Perjelas ukuran  ', ctx)
        self.assertEqual(self.review('REQUEST_CHANGES', 'Perjelas ukuran', ctx).pk, first.pk)
        for decision, reason, replay_ctx in [('APPROVE', '', ctx),
                                             ('REQUEST_CHANGES', 'Alasan lain', ctx),
                                             ('REQUEST_CHANGES', 'Perjelas ukuran', context(self.approver, first))]:
            with self.subTest(decision=decision), self.assertRaises(ConflictError):
                self.review(decision, reason, replay_ctx)
        self.assertEqual(ApprovalDecision.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action='request.review').count(), 1)
        self.assertEqual(ActionReceipt.objects.filter(actor=self.approver).count(), 1)

    def test_TC06_stale_version_and_non_submitted_states_cannot_be_reviewed(self):
        stale = context(self.approver, self.target)
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=self.target.version + 1)
        with self.assertRaises(ConflictError):
            self.review(ctx=stale)
        for status in ['DRAFT', 'CHANGES_REQUESTED', 'APPROVED', 'REJECTED', 'CANCELLED']:
            PurchaseRequest.objects.filter(pk=self.target.pk).update(status=status)
            self.target.refresh_from_db()
            with self.subTest(status=status), self.assertRaises(ConflictError):
                self.review()
        self.assertFalse(ApprovalDecision.objects.exists())

    def test_TC06_missing_current_snapshot_and_existing_decision_are_conflicts(self):
        PurchaseRequest.objects.filter(pk=self.target.pk).update(current_revision_number=2)
        with self.assertRaises(ConflictError):
            self.review()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(current_revision_number=1)
        self.review()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(status='SUBMITTED')
        self.target.refresh_from_db()
        with self.assertRaises(ConflictError):
            self.review()
        self.assertEqual(ApprovalDecision.objects.count(), 1)

    def test_TC18_review_audit_failure_rolls_back_decision_status_and_receipt(self):
        with patch('procurement.services.requests.AuditEvent.objects.create', side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.review()
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, 'SUBMITTED')
        self.assertFalse(ApprovalDecision.objects.exists())
        self.assertFalse(ActionReceipt.objects.filter(actor=self.approver).exists())

    def test_TC10_procurement_revision_clears_candidate_preserves_history_and_resubmits(self):
        self.target = self.review()
        # Existing order fixture supplies a valid historical quotation for the same request.
        from procurement.models import Quotation, Vendor
        vendor = Vendor.objects.create(name='Vendor sintetis', contact='x@example.invalid', created_by=self.buyer)
        revision = self.target.revisions.get(number=1)
        quote = Quotation.objects.create(revision=revision, vendor=vendor, reference='Q-1',
                                        quoted_on=timezone.localdate(), valid_until=timezone.localdate(),
                                        fulfillment_days=1, total_minor=20000, created_by=self.buyer)
        self.target.selected_quotation = quote
        self.target.selection_reason = 'Sesuai kebutuhan'
        self.target.single_source_reason = 'Satu sumber'
        self.target.save()
        decision_id = revision.approval.pk
        self.target = service.request_revision(context(self.buyer, self.target), request_id=self.target.pk, reason='Ubah jumlah')
        self.assertEqual((self.target.status, self.target.selected_quotation_id,
                          self.target.selection_reason, self.target.single_source_reason),
                         ('CHANGES_REQUESTED', None, '', ''))
        self.target = service.save_draft(context(self.owner, self.target), request_id=self.target.pk,
                                         data=request_data('Judul diperbarui'))
        self.target = service.submit_request(context(self.owner, self.target), request_id=self.target.pk)
        self.assertEqual((self.target.current_revision_number, self.target.status), (2, 'SUBMITTED'))
        revision.refresh_from_db()
        self.assertEqual((revision.title, revision.estimated_total_minor, revision.approval.pk),
                         ('Kursi operasional', 20000, decision_id))
        self.assertEqual(quote.revision_id, revision.pk)
        self.review('APPROVE')
        self.assertEqual(ApprovalDecision.objects.filter(revision__request=self.target).count(), 2)

    def test_TC10_procurement_return_requires_reason_current_approval_and_no_po(self):
        with self.assertRaises(ConflictError):
            service.request_revision(context(self.buyer, self.target), request_id=self.target.pk, reason='Ubah')
        self.target = self.review()
        for reason in ['', '  ', 'x' * 4001]:
            with self.subTest(reason=reason[:5]), self.assertRaises(ValidationError):
                service.request_revision(context(self.buyer, self.target), request_id=self.target.pk, reason=reason)
        order = issued()
        for status in ['ISSUED', 'RECEIVED']:
            type(order).objects.filter(pk=order.pk).update(status=status)
            with self.subTest(status=status), self.assertRaises(ConflictError):
                service.request_revision(context(self.buyer, order.request), request_id=order.request_id, reason='Ubah')
        ApprovalDecision.objects.filter(revision__request=self.target).delete()
        with self.assertRaises(ConflictError):
            service.request_revision(context(self.buyer, self.target), request_id=self.target.pk, reason='Ubah')

    def test_TC10_procurement_return_replay_conflicts_and_current_permission(self):
        self.target = self.review()
        ctx = context(self.buyer, self.target)
        first = service.request_revision(ctx, request_id=self.target.pk, reason='Ubah')
        self.assertEqual(service.request_revision(ctx, request_id=self.target.pk, reason='Ubah').pk, first.pk)
        with self.assertRaises(ConflictError):
            service.request_revision(ctx, request_id=self.target.pk, reason='Berbeda')
        User.objects.filter(pk=self.buyer.pk).update(role=Role.ADMIN)
        with self.assertRaises(PermissionDenied):
            service.request_revision(ctx, request_id=self.target.pk, reason='Ubah')
        self.assertEqual(AuditEvent.objects.filter(request=self.target, action='request.revision').count(), 1)
        self.assertEqual(ApprovalDecision.objects.count(), 1)

    def test_TC18_return_audit_failure_rolls_back_status_selection_and_receipt(self):
        self.target = self.review()
        before = self.target.version
        with patch('procurement.services.requests.AuditEvent.objects.create', side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                service.request_revision(context(self.buyer, self.target), request_id=self.target.pk, reason='Ubah')
        self.target.refresh_from_db()
        self.assertEqual((self.target.status, self.target.version), ('APPROVED', before))
        self.assertFalse(ActionReceipt.objects.filter(actor=self.buyer).exists())

    def test_TC18_version_limit_rejects_review_and_return_atomically(self):
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=9223372036854775807)
        self.target.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.review()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=2)
        self.target.refresh_from_db()
        self.target = self.review()
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=9223372036854775807)
        self.target.refresh_from_db()
        with self.assertRaises(ValidationError):
            service.request_revision(context(self.buyer, self.target), request_id=self.target.pk, reason='Ubah')


class ApprovalHttpTests(TestCase):
    def setUp(self):
        self.owner = user(Role.REQUESTER)
        self.approver = user(Role.APPROVER)
        self.buyer = user(Role.PROCUREMENT)
        self.target = submitted(self.owner)
        self.path = f'/requests/{self.target.pk}/'
        self.client.force_login(self.approver)

    def payload(self, field='review_form', actor=None):
        if actor:
            self.client.force_login(actor)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get(field), f'{field} missing')
        form = response.context[field]
        return dict(form.initial)

    def test_TC05_queue_only_shows_pending_not_own_and_is_paginated(self):
        User.objects.filter(pk=self.approver.pk).update(role=Role.REQUESTER)
        own = submitted(self.approver)
        User.objects.filter(pk=self.approver.pk).update(role=Role.APPROVER)
        response = self.client.get('/approvals/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.target.number)
        self.assertNotContains(response, own.number)
        self.assertEqual(self.client.post('/approvals/', {}).status_code, 405)
        self.assertEqual(response.context['page_obj'].paginator.per_page, 25)
        for role in [Role.REQUESTER, Role.PROCUREMENT, Role.ADMIN, Role.RECEIVER]:
            self.client.force_login(user(role))
            self.assertEqual(self.client.get('/approvals/').status_code, 403)

    def test_TC05_review_post_creates_decision_replays_and_hides_terminal_controls(self):
        payload = self.payload() | dict(decision='APPROVE', reason='', status='REJECTED', actor=str(self.owner.pk))
        self.assertEqual(self.client.get(self.path + 'review/').status_code, 405)
        for _ in range(2):
            self.assertEqual(self.client.post(self.path + 'review/', payload).status_code, 303)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, 'APPROVED')
        self.assertEqual(ApprovalDecision.objects.get().actor_id, self.approver.pk)
        detail = self.client.get(self.path)
        self.assertIsNone(detail.context['review_form'])
        self.assertContains(self.client.get(self.path + 'revisions/1/'), self.approver.username)
        self.assertNotContains(self.client.get('/approvals/'), self.target.number)

    def test_TC05_invalid_reason_preserves_choice_and_does_not_write(self):
        payload = self.payload() | dict(decision='REJECT', reason=' ')
        response = self.client.post(self.path + 'review/', payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context['review_form']['decision'].value(), 'REJECT')
        self.assertTrue(response.context['review_form'].errors)
        self.assertFalse(ApprovalDecision.objects.exists())

    def test_TC06_stale_review_and_wrong_actor_token_do_not_write(self):
        payload = self.payload() | dict(decision='APPROVE', reason='')
        self.client.force_login(user(Role.APPROVER))
        self.assertEqual(self.client.post(self.path + 'review/', payload).status_code, 400)
        self.client.force_login(self.approver)
        PurchaseRequest.objects.filter(pk=self.target.pk).update(version=self.target.version + 1)
        self.assertEqual(self.client.post(self.path + 'review/', payload).status_code, 409)
        self.assertFalse(ApprovalDecision.objects.exists())

    def test_TC06_role_change_and_self_review_are_forbidden_without_superuser_bypass(self):
        payload = self.payload() | dict(decision='APPROVE', reason='')
        User.objects.filter(pk=self.approver.pk).update(role=Role.ADMIN, is_superuser=True)
        self.assertEqual(self.client.post(self.path + 'review/', payload).status_code, 403)
        User.objects.filter(pk=self.owner.pk).update(role=Role.APPROVER, is_superuser=True)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.path + 'review/', payload).status_code, 403)

    def test_TC10_procurement_return_form_posts_reason_and_hides_after_success(self):
        payload = self.payload() | dict(decision='APPROVE', reason='')
        self.assertEqual(self.client.post(self.path + 'review/', payload).status_code, 303)
        payload = self.payload('revision_form', self.buyer) | dict(reason='<script>ubah</script>')
        self.assertEqual(self.client.get(self.path + 'request-revision/').status_code, 405)
        self.assertEqual(self.client.post(self.path + 'request-revision/', payload).status_code, 303)
        self.assertEqual(self.client.post(self.path + 'request-revision/', payload).status_code, 303)
        detail = self.client.get(self.path)
        self.assertIsNone(detail.context['revision_form'])
        self.assertContains(detail, '&lt;script&gt;ubah&lt;/script&gt;')
        self.assertNotContains(detail, '<script>ubah</script>')
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.path + 'edit/').status_code, 200)

    def test_TC18_csrf_rejection_keeps_decision_empty(self):
        payload = self.payload() | dict(decision='APPROVE', reason='')
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.approver)
        self.assertEqual(client.post(self.path + 'review/', payload).status_code, 403)
        client.get(self.path)
        payload['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertEqual(client.post(self.path + 'review/', payload).status_code, 303)

    def test_TC18_known_busy_error_is_503_but_unexpected_database_error_is_not_swallowed(self):
        payload = self.payload() | dict(decision='APPROVE', reason='')
        with patch('procurement.views.requests.review_request', side_effect=OperationalError('database is locked')):
            response = self.client.post(self.path + 'review/', payload)
        self.assertEqual((response.status_code, response['Retry-After']), (503, '1'))
        with patch('procurement.views.requests.review_request', side_effect=OperationalError('unknown table')):
            with self.assertRaises(OperationalError):
                self.client.post(self.path + 'review/', payload)
        self.assertFalse(ApprovalDecision.objects.exists())

    @override_settings(DEBUG=False)
    def test_TC18_review_and_return_tokens_are_redacted_in_exception_reports(self):
        for suffix in ['review/', 'request-revision/']:
            path = self.path + suffix
            self.assertEqual(self.client.get(path).status_code, 405)
            request = RequestFactory().post(path, dict(action_token='synthetic-token', csrfmiddlewaretoken='synthetic-csrf'))
            request.user = AnonymousUser()
            match = resolve(path)
            match.func(request, **match.kwargs)
            filtered = SafeExceptionReporterFilter().get_post_parameters(request)
            for key in ['action_token', 'csrfmiddlewaretoken']:
                self.assertNotEqual(filtered[key], request.POST[key])


class ApprovalConcurrencyTests(TransactionTestCase):
    def test_TC06_two_reviewers_cannot_record_two_decisions_for_one_revision(self):
        self.assertTrue(callable(getattr(service, 'review_request', None)), 'Approval service missing')
        owner = user(Role.REQUESTER)
        for same_nonce in [False, True]:
            target = submitted(owner)
            actors = [user(Role.APPROVER), user(Role.APPROVER)]
            if same_nonce:
                actors[1] = actors[0]
            nonce = uuid4()
            contexts = [ActionContext(actor.pk, nonce if same_nonce else uuid4(), target.version) for actor in actors]
            gate = Barrier(2)

            def decide(ctx):
                close_old_connections()
                try:
                    gate.wait(timeout=5)
                    service.review_request(ctx, request_id=target.pk, decision='APPROVE', reason='')
                    return 'ok'
                except ConflictError:
                    return 'conflict'
                finally:
                    close_old_connections()

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(decide, contexts, timeout=15))
            self.assertCountEqual(results, ['ok', 'ok'] if same_nonce else ['ok', 'conflict'])
            self.assertEqual(ApprovalDecision.objects.filter(revision__request=target).count(), 1)
            self.assertEqual(AuditEvent.objects.filter(request=target, action='request.review').count(), 1)
            target.refresh_from_db()
            self.assertEqual(target.status, 'APPROVED')
