# filepath: config/tests/test_pythonanywhere.py
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
HOST = "ramaatha.pythonanywhere.com"
SECRET = "Synthetic-deployment-only-" + "x" * 60


class PythonAnywhereTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = Path(self.directory.name) / "private.json"

    def run_python(self, *arguments, profile=False):
        env = os.environ.copy()
        env["PROCUREMENT_HOST_CONFIG"] = str(self.config)
        env["DJANGO_DEBUG"] = "true"
        env["DJANGO_ALLOWED_HOSTS"] = "wrong.example.invalid"
        env["DJANGO_SECRET_KEY"] = "ambient-value-must-not-be-used"
        env["DJANGO_SETTINGS_MODULE"] = (
            "config.settings_pythonanywhere" if profile else "config.settings"
        )
        return subprocess.run(
            [sys.executable, *arguments], cwd=ROOT, env=env,
            capture_output=True, text=True, timeout=20,
        )

    def private_config(self, data=None):
        self.config.write_text(json.dumps(data if data is not None else {
            "hostname": HOST, "secret_key": SECRET,
        }), encoding="utf-8")
        self.config.chmod(0o600)

    def test_configure_generates_private_secret_without_printing_it(self):
        result = self.run_python(
            "-m", "deploy.pythonanywhere", "configure",
            "--hostname", HOST, "--config", str(self.config),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.config.read_text())
        self.assertEqual(data["hostname"], HOST)
        self.assertGreaterEqual(len(data["secret_key"]), 50)
        self.assertNotIn(data["secret_key"], result.stdout + result.stderr)
        if os.name == "posix":
            self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)

    def test_configure_does_not_replace_existing_secret(self):
        self.private_config()
        before = self.config.read_bytes()
        result = self.run_python(
            "-m", "deploy.pythonanywhere", "configure",
            "--hostname", HOST, "--config", str(self.config),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sudah ada", result.stderr)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertNotIn(SECRET, result.stdout + result.stderr)

    def test_configure_rejects_non_pythonanywhere_or_ambiguous_host(self):
        for hostname in (
            "https://ramaatha.pythonanywhere.com", "*.pythonanywhere.com",
            "ramaatha.pythonanywhere.com/other", "example.invalid",
            "ramaatha.pythonanywhere.com.evil.invalid", "../ramaatha.pythonanywhere.com",
        ):
            with self.subTest(hostname=hostname):
                result = self.run_python(
                    "-m", "deploy.pythonanywhere", "configure",
                    "--hostname", hostname, "--config", str(self.config),
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Hostname", result.stderr)
                self.assertFalse(self.config.exists())

    def test_profile_forces_host_private_secret_and_secure_settings(self):
        self.private_config()
        program = (
            "import json;from django.conf import settings as s;"
            "print(json.dumps(dict(debug=s.DEBUG,host=s.ALLOWED_HOSTS,"
            "secret=s.SECRET_KEY,session=s.SESSION_COOKIE_SECURE,"
            "csrf=s.CSRF_COOKIE_SECURE,redirect=s.SECURE_SSL_REDIRECT,"
            "db=str(s.DATABASES['default']['NAME']),"
            "mode=s.DATABASES['default']['OPTIONS']['transaction_mode'],"
            "static=s.STATIC_URL,root=str(s.STATIC_ROOT))))"
        )
        result = self.run_python("-c", program, profile=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["debug"])
        self.assertEqual(data["host"], [HOST])
        self.assertEqual(data["secret"], SECRET)
        self.assertTrue(data["session"] and data["csrf"] and data["redirect"])
        self.assertEqual(Path(data["db"]), ROOT / "var" / "pythonanywhere" / "db.sqlite3")
        self.assertEqual(data["mode"], "IMMEDIATE")
        self.assertEqual(data["static"], "/static/")
        self.assertEqual(Path(data["root"]), ROOT / "var" / "pythonanywhere" / "static")

    def test_profile_missing_configuration_fails_closed(self):
        result = self.run_python("-c", "from django.conf import settings;print(settings.DEBUG)", profile=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Konfigurasi hosting", result.stderr)

    def test_profile_invalid_private_data_fails_without_echoing_values(self):
        for data in (
            [], {"hostname": HOST}, {"hostname": HOST, "secret_key": "short"},
            {"hostname": "evil.invalid", "secret_key": SECRET},
            {"hostname": HOST, "secret_key": SECRET, "DJANGO_DEBUG": True},
        ):
            with self.subTest(keys=list(data) if isinstance(data, dict) else "array"):
                self.private_config(data)
                result = self.run_python("-c", "from django.conf import settings;print(settings.DEBUG)", profile=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Konfigurasi hosting", result.stderr)
                self.assertNotIn(SECRET, result.stdout + result.stderr)

    def test_wsgi_https_http_and_spoofed_header_boundaries(self):
        self.private_config()
        program = """
import json,runpy
from io import BytesIO
from wsgiref.util import setup_testing_defaults
app=runpy.run_path('deploy/pythonanywhere_wsgi.py')['application']
results=[]
for scheme,host,extra,method in [
 ('https','ramaatha.pythonanywhere.com',{},'GET'),
 ('http','ramaatha.pythonanywhere.com',{},'GET'),
 ('http','ramaatha.pythonanywhere.com',{'HTTP_X_FORWARDED_PROTO':'https'},'GET'),
 ('https','foreign.example.invalid',{},'GET'),
 ('https','ramaatha.pythonanywhere.com',{},'POST'),
]:
 env={};setup_testing_defaults(env)
 env.update(REQUEST_METHOD=method,PATH_INFO='/login/',HTTP_HOST=host,
            SERVER_NAME=host,CONTENT_LENGTH='0')
 env['wsgi.url_scheme']=scheme;env['wsgi.input']=BytesIO(b'')
 env.update(extra)
 captured={}
 def start(status,headers,exc_info=None):
  captured.update(status=int(status.split()[0]),headers=headers)
 response=app(env,start)
 body=b''.join(response).decode()
 if hasattr(response,'close'):response.close()
 captured['login_form']='name="username"' in body
 results.append(captured)
print(json.dumps(results))
"""
        result = self.run_python("-c", program, profile=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertEqual([r["status"] for r in values], [200, 301, 301, 400, 403])
        self.assertTrue(values[0]["login_form"])
        self.assertIn("Secure", next(value for name, value in values[0]["headers"] if name.lower() == "set-cookie"))
        self.assertEqual(dict(values[1]["headers"])["Location"], "https://ramaatha.pythonanywhere.com/login/")
