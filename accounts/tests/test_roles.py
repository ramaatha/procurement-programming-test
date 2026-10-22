# filepath: accounts/tests/test_roles.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


class AccountRoleTests(TestCase):
    def test_TC02_each_role_can_access_its_account(self):
        examples = [
            ("REQUESTER", "Pemohon"), ("APPROVER", "Approver"),
            ("PROCUREMENT", "Procurement"), ("RECEIVER", "Penerima"), ("ADMIN", "Admin"),
        ]
        for role, label in examples:
            with self.subTest(role=role):
                user = get_user_model().objects.create_user(
                    username=f"example.{role.lower()}", role=role,
                    password="Synthetic-role-passphrase-57!",
                )
                self.client.logout()
                response = self.client.post("/login/", {
                    "username": user.username, "password": "Synthetic-role-passphrase-57!",
                })
                self.assertRedirects(response, "/", status_code=303)
                response = self.client.get("/")
                self.assertContains(response, label)

    def test_TC02_browser_cannot_assign_role_during_login(self):
        user = get_user_model().objects.create_user(
            username="example.requester", password="Synthetic-role-passphrase-57!"
        )
        self.client.post("/login/", {
            "username": user.username, "password": "Synthetic-role-passphrase-57!",
            "role": "ADMIN", "is_superuser": True,
        })
        user.refresh_from_db()
        self.assertEqual(user.role, "REQUESTER")
        self.assertFalse(user.is_superuser)
        self.assertContains(self.client.get("/"), "Pemohon")

    def test_TC02_unknown_role_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create(username="bad.role", role="UNKNOWN")

    def test_TC02_zero_version_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create(username="bad.version", version=0)

    def test_TC02_current_role_display_reflects_database(self):
        user = get_user_model().objects.create_user(username="changing.role")
        self.client.force_login(user)
        self.assertContains(self.client.get("/"), "Pemohon")
        get_user_model().objects.filter(pk=user.pk).update(role="RECEIVER")
        self.assertContains(self.client.get("/"), "Penerima")

    def test_TC02_home_does_not_accept_post(self):
        user = get_user_model().objects.create_user(username="read.only")
        self.client.force_login(user)
        self.assertEqual(self.client.post("/").status_code, 405)
