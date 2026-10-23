# filepath: accounts/tests/test_auth.py
from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase


class AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "Synthetic-passphrase-48!"
        cls.user = get_user_model().objects.create_user(
            username="requester.example", password=cls.password
        )
        cls.inactive = get_user_model().objects.create_user(
            username="inactive.example", password=cls.password, is_active=False
        )

    def test_TC01_login_logout(self):
        response = self.client.post(
            "/login/", {"username": self.user.username, "password": self.password}
        )
        self.assertRedirects(response, "/", status_code=303)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/login/", status_code=303)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertRedirects(self.client.get("/"), "/login/?next=/")

    def test_TC01_login_page(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'autocomplete="off"', count=3)

    def test_TC01_invalid_credentials_preserve_username_not_password(self):
        response = self.client.post(
            "/login/", {"username": self.user.username, "password": "invalid-password"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(response, self.user.username, status_code=400)
        self.assertNotContains(response, 'value="invalid-password"', status_code=400)

    def test_TC01_inactive_account(self):
        response = self.client.post(
            "/login/", {"username": self.inactive.username, "password": self.password}
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_invalid_login_shows_one_error_inside_login_form(self):
        response = self.client.post('/login/', {'username': self.user.username, 'password': 'invalid-password'})
        message = 'Tidak dapat masuk. Periksa username dan password, atau hubungi admin.'
        self.assertContains(response, message, count=1, status_code=400)
        self.assertNotContains(response, 'id="error-summary"', status_code=400)
        self.assertContains(response, 'id="login-errors"', status_code=400)
        self.assertNotContains(response, 'data-error-focus', status_code=400)
        self.assertNotIn('value=', str(response.context['form']['password']))

    def test_TC01_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_TC02_anonymous_redirect(self):
        self.assertRedirects(self.client.get("/"), "/login/?next=/")

    def test_TC01_safe_redirect(self):
        for target in ["https://example.invalid", "//example.invalid", "javascript:alert(1)"]:
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post("/login/", {
                    "username": self.user.username, "password": self.password, "next": target,
                })
                self.assertRedirects(response, "/", status_code=303)

    def test_TC01_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        credentials = {"username": self.user.username, "password": self.password}
        self.assertEqual(client.post("/login/", credentials).status_code, 403)
        response = client.get("/login/")
        self.assertEqual(response.status_code, 200)
        token = client.cookies["csrftoken"].value
        response = client.post("/login/", {**credentials, "csrfmiddlewaretoken": token})
        self.assertRedirects(response, "/", status_code=303)
        self.assertEqual(client.post("/logout/").status_code, 403)
        self.assertIn(SESSION_KEY, client.session)
        response = client.post("/logout/", {
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, "/login/", status_code=303)

    def test_TC02_deactivation_revokes_existing_session(self):
        self.client.force_login(self.user)
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertRedirects(self.client.get("/"), "/login/?next=/")

    def test_TC02_no_public_registration_or_admin(self):
        self.assertEqual(self.client.get("/register/").status_code, 404)
        self.assertEqual(self.client.get("/admin/").status_code, 404)
