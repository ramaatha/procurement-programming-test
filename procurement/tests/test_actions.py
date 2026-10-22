# filepath: procurement/tests/test_actions.py
import importlib
from unittest.mock import patch
from uuid import uuid4

from django.apps import apps
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import SimpleTestCase, TransactionTestCase

from accounts.models import User


class ActionTokenTests(SimpleTestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('common.actions'), 'Protokol aksi belum tersedia.')
        self.actions=importlib.import_module('common.actions')
        self.scope=dict(actor_id=1,target_type='REQUEST',target_key=str(uuid4()),action='request.submit')

    def test_TC18_token_matches_exact_actor_target_and_action(self):
        token=self.actions.make_action_token(**self.scope)
        nonce=self.actions.load_action_token(token,**self.scope)
        self.assertEqual(self.actions.load_action_token(token,**self.scope),nonce)
        for change in [dict(actor_id=2),dict(target_type='ORDER'),dict(target_key=str(uuid4())),dict(action='request.cancel')]:
            with self.subTest(change=change),self.assertRaises(ValidationError):
                self.actions.load_action_token(token,**(self.scope|change))

    def test_TC18_token_rejects_tampering_and_expiry(self):
        with patch('django.core.signing.time.time',return_value=1000000):
            token=self.actions.make_action_token(**self.scope)
        for altered in [token+'x', '', 'not-a-token', None]:
            with self.subTest(token=altered),self.assertRaises(ValidationError):
                self.actions.load_action_token(altered,**self.scope)
        with patch('django.core.signing.time.time',return_value=1086401),self.assertRaises(ValidationError):
            self.actions.load_action_token(token,**self.scope)
        with patch('django.core.signing.time.time',return_value=1086399):
            self.assertIsNotNone(self.actions.load_action_token(token,**self.scope))

    def test_TC18_payload_hash_is_canonical_and_rejects_sensitive_or_ambiguous_data(self):
        a=self.actions
        self.assertEqual(a.payload_hash({'b':'0.050','a':[1,{'x':'kursi'}]}),a.payload_hash({'a':[1,{'x':'kursi'}],'b':'0.050'}))
        self.assertNotEqual(a.payload_hash({'quantity':'1.000'}),a.payload_hash({'quantity':'2.000'}))
        self.assertNotEqual(a.payload_hash({'rows':['1','2']}),a.payload_hash({'rows':['2','1']}))
        for payload in [{'password':'secret'},{'user':{'new_password':'secret'}},{'initial_password':'secret'},{'value':0.1},{'value':float('nan')},{1:'key'},['not-a-dict']]:
            with self.subTest(payload=payload),self.assertRaises(ValidationError):
                a.payload_hash(payload)


class ActionTransactionTests(TransactionTestCase):
    def setUp(self):
        self.assertTrue(apps.is_installed('procurement'), 'Schema Procurement belum terdaftar.')
        self.actions=importlib.import_module('common.actions')
        self.ConflictError=importlib.import_module('common.errors').ConflictError
        from procurement.tests.factories import context, draft, user
        self.actor=user('REQUESTER')
        self.request=draft(self.actor)
        self.audit=apps.get_model('procurement','AuditEvent')
        self.receipts=apps.get_model('procurement','ActionReceipt')
        self.ctx=context(self.actor,self.request)
        self.scope=dict(action='request.edit',target_type='REQUEST',target_key=str(self.request.pk))
        self.digest=self.actions.payload_hash({'title':'Kursi','expected_version':1})

    def fixture_action(self, *, fail=False):
        a=self.actions
        with transaction.atomic():
            replay=a.find_replay(self.ctx,**self.scope,digest=self.digest)
            if replay is not None:
                return a.resolve_result(replay)
            obj=type(self.request).objects.get(pk=self.request.pk)
            a.check_version(obj,self.ctx.expected_version)
            obj.title='Kursi';obj.version+=1;obj.save()
            self.audit.objects.create(request=obj,actor=self.actor,actor_name=self.actor.username,actor_role=self.actor.role,action=self.scope['action'],target_type='REQUEST',target_id=str(obj.pk),changes={'title':'Kursi'})
            a.record_action(self.ctx,**self.scope,digest=self.digest,result=obj)
            if fail:raise ValidationError('Gagal setelah audit.')
            return obj

    def test_TC18_same_nonce_replays_once_before_stale_version(self):
        first=self.fixture_action();second=self.fixture_action()
        self.assertEqual(first.pk,second.pk)
        self.request.refresh_from_db()
        self.assertEqual(self.request.version,2)
        self.assertEqual(self.audit.objects.count(),1)
        self.assertEqual(self.receipts.objects.count(),1)

    def test_TC18_same_nonce_with_changed_payload_or_scope_conflicts(self):
        self.fixture_action()
        for changes in [dict(digest='b'*64),dict(action='request.cancel'),dict(target_key='other')]:
            args=self.scope|dict(digest=self.digest)|changes
            with self.subTest(changes=changes),transaction.atomic(),self.assertRaises(self.ConflictError):
                self.actions.find_replay(self.ctx,**args)

    def test_TC18_non_replayable_password_action_rejects_nonce_reuse(self):
        with transaction.atomic():
            self.actions.record_action(self.ctx,action='account.password',target_type='USER',target_key=str(self.actor.pk),digest='',result=self.actor)
        with transaction.atomic(),self.assertRaises(self.ConflictError):
            self.actions.find_replay(self.ctx,action='account.password',target_type='USER',target_key=str(self.actor.pk),digest='',replayable=False)

    def test_TC06_new_nonce_with_stale_version_does_not_write(self):
        self.fixture_action()
        self.ctx=self.actions.ActionContext(actor_id=self.actor.pk,nonce=uuid4(),expected_version=1)
        with self.assertRaises(self.ConflictError):self.fixture_action()
        self.assertEqual(self.audit.objects.count(),1)
        self.assertEqual(self.receipts.objects.count(),1)

    def test_TC13_failure_rolls_back_document_audit_and_action_receipt(self):
        with self.assertRaises(ValidationError):self.fixture_action(fail=True)
        self.request.refresh_from_db()
        self.assertEqual(self.request.title,'')
        self.assertEqual(self.request.version,1)
        self.assertFalse(self.audit.objects.exists())
        self.assertFalse(self.receipts.objects.exists())
        self.fixture_action()
        self.assertEqual(self.receipts.objects.count(),1)

    def test_TC18_result_resolver_rejects_unknown_model_types(self):
        self.fixture_action()
        receipt=self.receipts.objects.get()
        receipt.result_type='os.system'
        with self.assertRaises(self.ConflictError):self.actions.resolve_result(receipt)

    def test_TC18_protocol_helpers_require_transaction(self):
        with self.assertRaises(RuntimeError):
            self.actions.find_replay(self.ctx,**self.scope,digest=self.digest)
        with self.assertRaises(RuntimeError):
            self.actions.record_action(self.ctx,**self.scope,digest=self.digest,result=self.request)
