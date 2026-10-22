# filepath: accounts/tests/test_management.py
import importlib
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import SESSION_KEY
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.models import ActionReceipt, AuditEvent


class AccountManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='admin.example', password='Synthetic-admin-start-2026!', role=Role.ADMIN)
        cls.member = User.objects.create_user(username='member.example', password='Synthetic-member-start-2026!')

    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('accounts.services'), 'Service pengelolaan akun belum tersedia.')
        self.service = importlib.import_module('accounts.services')
        self.ctx = ActionContext(self.admin.pk, uuid4(), self.member.version)
        self.password = 'Synthetic-account-created-2026!'

    def save(self, **changes):
        values = dict(user_id=self.member.pk, username=self.member.username, role=Role.REQUESTER, is_active=True)
        return self.service.save_user(self.ctx, **(values | changes))

    def create(self, **changes):
        values = dict(user_id=None, username='new.example', role=Role.RECEIVER, is_active=True, initial_password=self.password)
        return self.service.save_user(ActionContext(self.admin.pk, self.ctx.nonce, None), **(values | changes))

    def test_TC02_admin_creates_account_with_hashed_password_and_no_staff_privileges(self):
        result = self.create()
        self.assertTrue(result.check_password(self.password))
        self.assertNotEqual(result.password, self.password)
        self.assertEqual(result.role, Role.RECEIVER)
        self.assertFalse(result.is_staff)
        self.assertFalse(result.is_superuser)
        self.assertEqual(result.version, 1)
        self.assertEqual(AuditEvent.objects.get().actor_role, Role.ADMIN)
        serialized = str(list(AuditEvent.objects.values())) + str(list(ActionReceipt.objects.values()))
        self.assertNotIn(self.password, serialized)
        self.assertNotIn(result.password, serialized)

    def test_TC02_edit_changes_role_and_activity_without_changing_password(self):
        original_hash = self.member.password
        result = self.save(role=Role.APPROVER, is_active=False)
        self.assertEqual(result.role, Role.APPROVER)
        self.assertFalse(result.is_active)
        self.assertEqual(result.version, 2)
        self.assertEqual(result.password, original_hash)
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_TC02_duplicate_username_bad_role_and_weak_password_do_not_write(self):
        for changes in [dict(username=self.admin.username), dict(role='UNKNOWN'), dict(username=''), dict(username='x'*151), dict(username='bad name'), dict(initial_password='short'), dict(is_active='false')]:
            with self.subTest(changes=list(changes)), self.assertRaises(ValidationError):
                self.create(**changes)
        self.assertEqual(User.objects.count(), 2)
        self.assertFalse(AuditEvent.objects.exists())
        self.assertFalse(ActionReceipt.objects.exists())

    def test_TC02_edit_does_not_accept_password_on_metadata_action(self):
        with self.assertRaises(ValidationError):
            self.save(initial_password=self.password)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password('Synthetic-member-start-2026!'))

    def test_TC02_last_active_admin_cannot_be_demoted_or_disabled(self):
        self.ctx = ActionContext(self.admin.pk, uuid4(), self.admin.version)
        for change in [dict(role=Role.REQUESTER), dict(is_active=False)]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                self.save(**(dict(user_id=self.admin.pk, username=self.admin.username, role=Role.ADMIN) | change))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, Role.ADMIN)

    def test_TC02_admin_can_demote_self_when_another_active_admin_remains(self):
        User.objects.create_user(username='second.admin', role=Role.ADMIN)
        self.ctx = ActionContext(self.admin.pk, uuid4(), self.admin.version)
        result = self.save(user_id=self.admin.pk, username=self.admin.username, role=Role.REQUESTER)
        self.assertEqual(result.role, Role.REQUESTER)
        self.assertEqual(AuditEvent.objects.get().actor_role, Role.ADMIN)

    def test_TC18_metadata_replay_returns_result_without_duplicate_audit(self):
        first = self.save(role=Role.RECEIVER)
        second = self.save(role=Role.RECEIVER)
        self.assertEqual(first.pk, second.pk)
        self.member.refresh_from_db()
        self.assertEqual(self.member.version, 2)
        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(ActionReceipt.objects.count(), 1)
        with self.assertRaises(ConflictError):
            self.save(role=Role.APPROVER)

    def test_TC18_stale_version_and_invalid_create_version_do_not_write(self):
        self.ctx = ActionContext(self.admin.pk, uuid4(), 2)
        with self.assertRaises(ConflictError):
            self.save()
        with self.assertRaises(ConflictError):
            self.service.save_user(self.ctx,user_id=None,username='new.example',role=Role.REQUESTER,is_active=True,initial_password=self.password)
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC18_create_nonce_is_single_use_with_default_replay_option(self):
        self.create()
        for changes in [{}, dict(username='other.example', initial_password='Another-synthetic-secret-2026!')]:
            with self.subTest(changes=list(changes)), self.assertRaises(ConflictError):
                self.create(**changes)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(ActionReceipt.objects.get().payload_hash, '')

    def test_TC18_version_limit_is_rejected_without_partial_changes(self):
        User.objects.filter(pk=self.member.pk).update(version=9223372036854775807)
        self.ctx=ActionContext(self.admin.pk,uuid4(),9223372036854775807)
        for operation in [lambda:self.save(role=Role.RECEIVER),lambda:self.service.reset_password(self.ctx,user_id=self.member.pk,new_password=self.password)]:
            with self.subTest(operation='account mutation'),self.assertRaises(ValidationError):operation()
        self.member.refresh_from_db()
        self.assertEqual(self.member.version,9223372036854775807)
        self.assertEqual(self.member.role,Role.REQUESTER)
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC18_password_reset_nonce_is_single_use_and_contains_no_password_hash(self):
        result = self.service.reset_password(self.ctx,user_id=self.member.pk,new_password=self.password)
        self.assertTrue(result.check_password(self.password))
        self.assertEqual(result.version, 2)
        for password in [self.password, 'Different-synthetic-secret-2026!']:
            with self.subTest(password='redacted'), self.assertRaises(ConflictError):
                self.service.reset_password(self.ctx,user_id=self.member.pk,new_password=password)
        self.assertEqual(ActionReceipt.objects.get().payload_hash, '')
        serialized = str(list(AuditEvent.objects.values())) + str(list(ActionReceipt.objects.values()))
        self.assertNotIn(self.password, serialized)
        self.assertNotIn(result.password, serialized)

    def test_TC02_invalid_password_reset_preserves_hash_and_audit(self):
        for value in ['short', self.member.username, '', None]:
            with self.subTest(value='redacted'), self.assertRaises(ValidationError):
                self.service.reset_password(self.ctx,user_id=self.member.pk,new_password=value)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password('Synthetic-member-start-2026!'))
        self.assertEqual(self.member.version,1)
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC02_role_and_active_status_are_reloaded_inside_service(self):
        for change in [dict(role=Role.REQUESTER), dict(is_active=False)]:
            User.objects.filter(pk=self.admin.pk).update(role=Role.ADMIN,is_active=True)
            User.objects.filter(pk=self.admin.pk).update(**change)
            with self.subTest(change=change), self.assertRaises(PermissionDenied):
                self.save()
            with self.subTest(change=change), self.assertRaises(PermissionDenied):
                self.service.reset_password(self.ctx,user_id=self.member.pk,new_password=self.password)
        self.assertFalse(ActionReceipt.objects.exists())

    def test_TC02_other_roles_cannot_call_service_even_when_superuser(self):
        for role in [Role.REQUESTER,Role.APPROVER,Role.PROCUREMENT,Role.RECEIVER]:
            actor=User.objects.create_user(username=f'direct-{role}',role=role,is_superuser=True)
            self.ctx=ActionContext(actor.pk,uuid4(),self.member.version)
            with self.subTest(role=role),self.assertRaises(PermissionDenied):self.save()
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC02_demoted_actor_cannot_replay_previously_authorized_action(self):
        self.save(role=Role.RECEIVER)
        User.objects.filter(pk=self.admin.pk).update(role=Role.REQUESTER)
        with self.assertRaises(PermissionDenied):
            self.save(role=Role.RECEIVER)
        self.assertEqual(AuditEvent.objects.count(),1)

    def test_TC13_audit_failure_rolls_back_account_change(self):
        with patch('accounts.services.AuditEvent.objects.create',side_effect=RuntimeError('Synthetic audit failure')):
            with self.assertRaises(RuntimeError):self.save(role=Role.RECEIVER)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role,Role.REQUESTER)
        self.assertEqual(self.member.version,1)
        self.assertFalse(ActionReceipt.objects.exists())

    def test_TC13_action_receipt_failure_rolls_back_password_and_audit(self):
        original = self.member.password
        with patch('accounts.services.record_action',side_effect=RuntimeError('Synthetic result failure')):
            with self.assertRaises(RuntimeError):
                self.service.reset_password(self.ctx,user_id=self.member.pk,new_password=self.password)
        self.member.refresh_from_db()
        self.assertEqual(self.member.password,original)
        self.assertEqual(self.member.version,1)
        self.assertFalse(AuditEvent.objects.exists())
