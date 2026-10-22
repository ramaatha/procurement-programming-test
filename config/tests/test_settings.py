# filepath: config/tests/test_settings.py
import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def probe(self, **changes):
        env = os.environ.copy()
        env.update(DJANGO_DEBUG="true", DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1")
        for key, value in changes.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        program = (
            "import json; from django.conf import settings as s; "
            "print(json.dumps({'session_secure':s.SESSION_COOKIE_SECURE,"
            "'csrf_secure':s.CSRF_COOKIE_SECURE,'redirect':s.SECURE_SSL_REDIRECT,"
            "'database':str(s.DATABASES['default']['NAME']),"
            "'test_database':str(s.DATABASES['default']['TEST']['NAME'])}))"
        )
        return subprocess.run(
            [sys.executable, "-c", program], env=env,
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True,
            timeout=15,
        )

    def test_TC19_missing_secret_rejected(self):
        result = self.probe(DJANGO_SECRET_KEY=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_TC19_short_secret_rejected(self):
        self.assertNotEqual(self.probe(DJANGO_SECRET_KEY="too-short").returncode, 0)

    def test_TC19_invalid_debug_rejected(self):
        self.assertNotEqual(self.probe(DJANGO_DEBUG="typo").returncode, 0)

    def test_TC19_production_requires_hosts(self):
        for hosts in [None, ", ,"]:
            with self.subTest(hosts=hosts):
                self.assertNotEqual(
                    self.probe(DJANGO_DEBUG="false", DJANGO_ALLOWED_HOSTS=hosts).returncode, 0
                )

    def test_TC19_wildcard_hosts_rejected(self):
        self.assertNotEqual(
            self.probe(DJANGO_DEBUG="false", DJANGO_ALLOWED_HOSTS="*").returncode, 0
        )

    def test_TC19_production_uses_secure_cookies_and_https(self):
        result = self.probe(DJANGO_DEBUG="false", DJANGO_ALLOWED_HOSTS="app.example.invalid")
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertTrue(values["session_secure"])
        self.assertTrue(values["csrf_secure"])
        self.assertTrue(values["redirect"])

    def test_TC19_test_database_is_separate(self):
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertNotEqual(values["database"], values["test_database"])
