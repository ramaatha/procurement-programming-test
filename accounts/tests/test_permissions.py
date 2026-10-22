# filepath: accounts/tests/test_permissions.py
import importlib
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.db import OperationalError
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import resolve
from django.views.debug import SafeExceptionReporterFilter

from accounts.models import Role, User
from common.actions import ActionContext
from procurement.models import ActionReceipt, AuditEvent


class AccountPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=User.objects.create_user(username='admin.example',password='Synthetic-admin-start-2026!',role=Role.ADMIN)
        cls.member=User.objects.create_user(username='member.example',password='Synthetic-member-start-2026!')

    def get_form(self,path):
        response=self.client.get(path)
        self.assertEqual(response.status_code,200)
        return response.context['form']

    def edit_payload(self):
        form=self.get_form(f'/users/{self.member.pk}/edit/')
        return dict(username=self.member.username,role=Role.RECEIVER,is_active='on',action_token=form.initial['action_token'],expected_version=form.initial['expected_version'])

    def test_TC02_anonymous_is_redirected_and_non_admin_roles_are_forbidden(self):
        paths=['/users/','/users/new/',f'/users/{self.member.pk}/edit/',f'/users/{self.member.pk}/password/']
        for path in paths:
            self.assertEqual(self.client.get(path).status_code,302)
        for role in [Role.REQUESTER,Role.APPROVER,Role.PROCUREMENT,Role.RECEIVER]:
            actor=User.objects.create_user(username=f'role-{role}',role=role,is_superuser=True)
            self.client.force_login(actor)
            for path in paths:
                with self.subTest(role=role,path=path):
                    self.assertEqual(self.client.get(path).status_code,403)
                    self.assertIn(self.client.post(path,{}).status_code,[403,405])
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC02_admin_list_form_and_navigation_are_available(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/'),'Kelola akun')
        self.assertContains(self.client.get('/users/'),self.member.username)
        form=self.get_form('/users/new/')
        self.assertNotIn('is_superuser',form.fields)
        self.assertNotIn('is_staff',form.fields)
        self.assertNotIn('password',form.fields)
        self.assertEqual(self.client.get('/users/999999/edit/').status_code,404)
        self.assertEqual(self.client.delete('/users/').status_code,405)

    def test_TC02_create_post_ignores_privilege_injection_and_redirects(self):
        self.client.force_login(self.admin)
        form=self.get_form('/users/new/')
        data=dict(username='created.example',role=Role.REQUESTER,is_active='on',initial_password='Synthetic-created-start-2026!',confirm_password='Synthetic-created-start-2026!',action_token=form.initial['action_token'],is_superuser='on',is_staff='on')
        response=self.client.post('/users/new/',data)
        self.assertEqual(response.status_code,303)
        created=User.objects.get(username='created.example')
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.is_staff)
        self.assertTrue(created.check_password(data['initial_password']))
        self.assertEqual(self.client.post('/users/new/',data).status_code,409)
        self.assertEqual(ActionReceipt.objects.get().payload_hash,'')

    def test_TC18_invalid_form_preserves_safe_fields_not_password(self):
        self.client.force_login(self.admin)
        form=self.get_form('/users/new/')
        data=dict(username='keep.example',role=Role.REQUESTER,initial_password='short',confirm_password='short',action_token=form.initial['action_token'])
        response=self.client.post('/users/new/',data)
        self.assertEqual(response.status_code,400)
        self.assertContains(response,'keep.example',status_code=400)
        self.assertNotContains(response,'value="short"',status_code=400)
        self.assertNotContains(response,'Synthetic-',status_code=400)
        self.assertFalse(User.objects.filter(username='keep.example').exists())
        self.assertEqual(response.context['form'].data['action_token'],data['action_token'])

    def test_TC18_password_confirmation_mismatch_is_not_saved(self):
        self.client.force_login(self.admin)
        form=self.get_form(f'/users/{self.member.pk}/password/')
        response=self.client.post(f'/users/{self.member.pk}/password/',dict(new_password='Synthetic-first-2026!',confirm_password='Synthetic-second-2026!',action_token=form.initial['action_token'],expected_version=self.member.version))
        self.assertEqual(response.status_code,400)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password('Synthetic-member-start-2026!'))

    def test_TC18_edit_replay_stale_version_and_token_scope(self):
        self.client.force_login(self.admin)
        data=self.edit_payload()
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',data).status_code,303)
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',data).status_code,303)
        self.assertEqual(AuditEvent.objects.count(),1)
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',data|dict(role=Role.APPROVER)).status_code,409)
        fresh=self.edit_payload()
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',fresh|dict(expected_version=1)).status_code,409)
        self.assertEqual(self.client.post(f'/users/{self.admin.pk}/edit/',fresh).status_code,400)

    def test_TC18_other_admin_cannot_use_action_token(self):
        self.client.force_login(self.admin)
        data=self.edit_payload()
        other=User.objects.create_user(username='other.admin',role=Role.ADMIN)
        self.client.force_login(other)
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',data).status_code,400)
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC02_role_change_or_deactivation_after_get_prevents_post(self):
        self.client.force_login(self.admin)
        data=self.edit_payload()
        User.objects.filter(pk=self.admin.pk).update(role=Role.RECEIVER)
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',data).status_code,403)
        User.objects.filter(pk=self.admin.pk).update(role=Role.ADMIN,is_active=False)
        self.assertEqual(self.client.post(f'/users/{self.member.pk}/edit/',data).status_code,302)
        self.assertFalse(AuditEvent.objects.exists())

    def test_TC02_user_management_posts_require_csrf(self):
        self.client=Client(enforce_csrf_checks=True)
        self.client.force_login(self.admin)
        form=self.get_form('/users/new/')
        self.assertEqual(self.client.post('/users/new/',{'action_token':form.initial['action_token']}).status_code,403)

    def test_TC02_password_reset_revokes_existing_target_session(self):
        member_client=Client();member_client.force_login(self.member)
        self.client.force_login(self.admin)
        path=f'/users/{self.member.pk}/password/'
        form=self.get_form(path)
        data=dict(new_password='Synthetic-reset-start-2026!',confirm_password='Synthetic-reset-start-2026!',action_token=form.initial['action_token'],expected_version=self.member.version)
        self.assertEqual(self.client.post(path,data).status_code,303)
        self.assertEqual(self.client.post(path,data).status_code,409)
        self.assertEqual(member_client.get('/').status_code,302)
        self.assertNotIn(SESSION_KEY,member_client.session)

    def test_TC02_self_password_reset_logs_out_current_admin(self):
        self.client.force_login(self.admin)
        path=f'/users/{self.admin.pk}/password/'
        form=self.get_form(path)
        response=self.client.post(path,dict(new_password='Synthetic-self-reset-2026!',confirm_password='Synthetic-self-reset-2026!',action_token=form.initial['action_token'],expected_version=self.admin.version))
        self.assertEqual(response.status_code,303)
        self.assertEqual(response['Location'],'/login/')
        self.assertNotIn(SESSION_KEY,self.client.session)

    def test_TC18_sqlite_busy_returns_retryable_response_without_writing(self):
        self.client.force_login(self.admin)
        data=self.edit_payload()
        with patch('accounts.views.save_user',side_effect=OperationalError('database is locked')):
            response=self.client.post(f'/users/{self.member.pk}/edit/',data)
        self.assertEqual(response.status_code,503)
        self.assertEqual(response['Retry-After'],'1')
        self.assertFalse(AuditEvent.objects.exists())

    @override_settings(DEBUG=False)
    def test_TC18_exception_report_redacts_passwords_and_post_tokens(self):
        for path in ['/users/new/',f'/users/{self.member.pk}/edit/',f'/users/{self.member.pk}/password/']:
            data=dict(username='safe.example',action_token='synthetic-action-token',csrfmiddlewaretoken='synthetic-csrf-token',initial_password='synthetic-initial-password',new_password='synthetic-new-password',confirm_password='synthetic-confirmation')
            request=RequestFactory().post(path,data)
            request.user=AnonymousUser()
            match=resolve(path)
            match.func(request,**match.kwargs)
            filtered=SafeExceptionReporterFilter().get_post_parameters(request)
            for name in ['action_token','csrfmiddlewaretoken','confirm_password']:
                with self.subTest(path=path,field=name):self.assertNotEqual(filtered[name],data[name])
            password='new_password' if path.endswith('/password/') else 'initial_password'
            self.assertNotEqual(filtered[password],data[password])
            self.assertEqual(filtered['username'],'safe.example')

    @override_settings(DEBUG=False)
    def test_TC18_exception_report_redacts_generated_token_in_form_locals(self):
        request=RequestFactory().get('/users/new/')
        request.user=self.admin
        match=resolve('/users/new/')
        with patch('accounts.views.render',side_effect=RuntimeError('Synthetic render failure')):
            try:match.func(request,**match.kwargs)
            except RuntimeError as error:
                traceback=error.__traceback__
                while traceback is not None:
                    frame=traceback.tb_frame
                    if frame.f_code.co_name=='_account_form':
                        token=frame.f_locals['initial']['action_token']
                        filtered=SafeExceptionReporterFilter().get_traceback_frame_variables(request,frame)
                        self.assertFalse(token in repr(filtered),'Generated token appears in exception-report locals.')
                        break
                    traceback=traceback.tb_next
                else:self.fail('Account form was not exercised.')
            else:self.fail('Synthetic render failure did not reach the form.')


class LastAdminTransactionTests(TransactionTestCase):
    def test_TC02_concurrent_self_demotions_keep_one_active_admin(self):
        self.assertIsNotNone(importlib.util.find_spec('accounts.services'), 'Service akun belum tersedia.')
        save_user=importlib.import_module('accounts.services').save_user
        admins=[User.objects.create_user(username=f'admin-{i}',role=Role.ADMIN) for i in range(2)]
        gate=Barrier(2)

        def demote(actor):
            close_old_connections()
            try:
                gate.wait(timeout=5)
                save_user(ActionContext(actor.pk,uuid4(),1),user_id=actor.pk,username=actor.username,role=Role.REQUESTER,is_active=True)
                return 'changed'
            except ValidationError:
                return 'blocked'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes=list(workers.map(demote,admins))
        self.assertCountEqual(outcomes,['changed','blocked'])
        self.assertEqual(User.objects.filter(role=Role.ADMIN,is_active=True).count(),1)
        self.assertEqual(AuditEvent.objects.count(),1)
        self.assertEqual(ActionReceipt.objects.count(),1)
