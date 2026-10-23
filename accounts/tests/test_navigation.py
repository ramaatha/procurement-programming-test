from django.contrib.auth import SESSION_KEY
from django.test import TestCase

from accounts.models import Role
from procurement.tests.factories import user


class NavigationTests(TestCase):
    def setUp(self):
        self.actor = user(Role.ADMIN)
        self.client.force_login(self.actor)

    def test_navigation_uses_title_case(self):
        response = self.client.get('/')
        for label in ('Pengadaan Internal', 'Antrean Kerja', 'Permintaan Pengadaan',
                      'Purchase Order', 'Kelola Vendor', 'Kelola Akun'):
            self.assertIn(label, ' '.join(response.content.decode().split()))

    def test_logout_confirmation_does_not_end_session(self):
        response = self.client.get('/logout/confirm/')
        self.assertContains(response, 'Keluar Dari Akun?')
        self.assertContains(response, 'Isian yang belum disimpan')
        self.assertContains(response, 'Ya, Keluar')
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.client.post('/logout/').status_code, 303)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_confirmation_requires_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get('/logout/confirm/'), '/login/?next=/logout/confirm/')
