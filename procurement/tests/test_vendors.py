# filepath: procurement/tests/test_vendors.py
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase

from accounts.models import Role, User
from common.actions import ActionContext
from common.errors import ConflictError
from procurement.models import ActionReceipt, AuditEvent, Vendor
from procurement.services import requests
from procurement.tests.factories import context, user


class VendorTests(TestCase):
    def setUp(self):
        from importlib import import_module, util
        self.assertIsNotNone(util.find_spec('procurement.services.sourcing'), 'Sourcing service missing')
        self.service = import_module('procurement.services.sourcing')
        self.actor = user(Role.PROCUREMENT)
        self.client.force_login(self.actor)

    def save(self, target=None, **changes):
        values = dict(name='Vendor Nusantara', contact='vendor@example.invalid', is_active=True)
        values.update(changes)
        ctx = context(self.actor, target) if target else ActionContext(self.actor.pk, uuid4(), None)
        return self.service.save_vendor(ctx, vendor_id=target.pk if target else None, **values)

    def test_TC07_create_update_deactivate_and_preserve_creator(self):
        target = self.save(name='  Vendor Nusantara  ')
        creator = target.created_by_id
        self.assertEqual((target.name, target.version), ('Vendor Nusantara', 1))
        self.actor = user(Role.ADMIN)
        result = self.save(target, is_active=False)
        self.assertEqual((result.is_active, result.version, result.created_by_id), (False, 2, creator))
        self.assertEqual(AuditEvent.objects.filter(target_type='VENDOR').count(), 2)

    def test_TC07_invalid_fields_and_privilege_are_rejected_without_writes(self):
        for changes in [dict(name=' '), dict(contact=''), dict(is_active='true'), dict(name='x'*201)]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.save(**changes)
        for role in [Role.REQUESTER, Role.APPROVER, Role.RECEIVER]:
            self.actor = user(role)
            self.actor.is_superuser = True
            self.actor.save()
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                self.save()
        self.assertFalse(Vendor.objects.exists())

    def test_TC18_vendor_replay_stale_payload_and_role_change(self):
        ctx = ActionContext(self.actor.pk, uuid4(), None)
        values = dict(vendor_id=None, name='Vendor', contact='Kontak', is_active=True)
        target = self.service.save_vendor(ctx, **values)
        self.assertEqual(self.service.save_vendor(ctx, **values).pk, target.pk)
        with self.assertRaises(ConflictError):
            self.service.save_vendor(ctx, **(values | dict(contact='Berbeda')))
        stale = context(self.actor, target)
        self.save(target, is_active=False)
        with self.assertRaises(ConflictError):
            self.service.save_vendor(stale, **(values | dict(vendor_id=target.pk)))
        User.objects.filter(pk=self.actor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.service.save_vendor(ctx, **values)
        self.assertEqual(Vendor.objects.count(), 1)

    def test_TC18_vendor_audit_failure_rolls_back_and_version_overflow_is_rejected(self):
        with patch('procurement.services.sourcing.AuditEvent.objects.create', side_effect=RuntimeError('Synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.save()
        self.assertFalse(Vendor.objects.exists())
        self.assertFalse(ActionReceipt.objects.exists())
        target = self.save()
        Vendor.objects.filter(pk=target.pk).update(version=9223372036854775807)
        target.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.save(target)

    def test_TC07_vendor_form_create_edit_and_non_manager_denial(self):
        response = self.client.get('/vendors/new/')
        self.assertEqual(response.status_code, 200)
        payload = dict(response.context['form'].initial) | dict(name='Vendor baru', contact='Kontak', is_active='on')
        payload['expected_version'] = ''
        self.assertEqual(self.client.post('/vendors/new/', payload).status_code, 303)
        target = Vendor.objects.get()
        self.assertContains(self.client.get('/vendors/'), 'Vendor baru')
        path = f'/vendors/{target.pk}/edit/'
        response = self.client.get(path)
        payload = dict(response.context['form'].initial) | dict(name='Vendor baru', contact='Kontak')
        payload.pop('is_active', None)
        self.assertEqual(self.client.post(path, payload).status_code, 303)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.client.force_login(user(Role.REQUESTER))
        for url in ['/vendors/', '/vendors/new/', path]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_TC18_vendor_csrf_invalid_input_token_and_stale_edit(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.actor)
        response = client.get('/vendors/new/')
        self.assertEqual(response.status_code, 200)
        payload = dict(response.context['form'].initial) | dict(name='Vendor', contact='')
        payload['expected_version'] = ''
        self.assertEqual(client.post('/vendors/new/', payload).status_code, 403)
        payload['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/vendors/new/', payload).status_code, 400)
        self.assertFalse(Vendor.objects.exists())
        payload['contact'] = '<script>kontak</script>'
        self.assertEqual(client.post('/vendors/new/', payload).status_code, 303)
        self.assertContains(client.get('/vendors/'), '&lt;script&gt;')
        target = Vendor.objects.get()
        path = f'/vendors/{target.pk}/edit/'
        response = self.client.get(path)
        stale = dict(response.context['form'].initial) | dict(name='Vendor', contact='Kontak')
        self.save(target)
        self.assertEqual(self.client.post(path, stale).status_code, 409)
        self.assertEqual(self.client.post('/vendors/', {}).status_code, 405)
