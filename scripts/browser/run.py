# filepath: scripts/browser/run.py
"""Run browser regressions against a fresh source copy and synthetic SQLite database."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

source = Path(__file__).resolve().parents[2]
node = os.environ.get("E2E_NODE") or shutil.which("node")
if not node or not os.environ.get("PLAYWRIGHT_MODULE"):
    raise SystemExit("Require existing Node and PLAYWRIGHT_MODULE; this runner installs nothing.")
scratch_parent = Path(os.environ.get("E2E_SCRATCH_ROOT", str(Path.home() / ".codex" / "tmp"))).resolve()
if scratch_parent.is_relative_to(source):
    raise SystemExit("E2E_SCRATCH_ROOT must be outside the repository.")
scratch_parent.mkdir(parents=True, exist_ok=True)
work = scratch_parent / ("procurement-browser-" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3))
app = work / "app"
app.mkdir(parents=True)
files = subprocess.check_output(
    ["git", "-C", str(source), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
).decode("utf-8").split("\0")
hashes = {}
for name in filter(None, files):
    relative = Path(name)
    if any(part in {".git", ".venv", "node_modules", "var", "tmp", "__pycache__"} for part in relative.parts):
        continue
    if relative.name == ".env" or relative.suffix in {".pyc", ".sqlite3"}:
        continue
    original = source / relative
    if original.is_file():
        destination = app / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
        hashes[name] = hashlib.sha256(original.read_bytes()).hexdigest()
(work / "source-hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
data = app / "var" / "demo"
data.mkdir(parents=True)
(data / ".e2e-isolated").write_text("Synthetic E2E database only\n", encoding="utf-8")
env = dict(os.environ)
env.update(
    DJANGO_SECRET_KEY=secrets.token_urlsafe(64),
    DJANGO_DEBUG="true",
    DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost",
    DJANGO_DATA_DIR=str(data),
    E2E_APP_DIR=str(app),
    E2E_DATA_DIR=str(data),
    E2E_DATABASE=str(data / "db.sqlite3"),
    E2E_PYTHON=sys.executable,
    E2E_ALLOW_MUTATIONS="isolated-synthetic",
    E2E_ALLOW_SYNTHETIC_FIXTURE="1",
    E2E_PASSWORD=secrets.token_urlsafe(24) + "!aA7",
    E2E_FIXTURE_MANIFEST=str(work / "fixture.json"),
)
env.pop("DJANGO_SETTINGS_MODULE", None)

def run(name, command, extra_env=None):
    child_env = env | (extra_env or {})
    with (work / (name + ".log")).open("w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=app, env=child_env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{name} failed (exit {result.returncode}); inspect {work / (name + '.log')}")
    print(f"PASS {name}", flush=True)

server = None
server_log = None
try:
    run("migrate", [sys.executable, "manage.py", "migrate", "--noinput"])
    run("seed", [sys.executable, "manage.py", "seed_demo"], {"DEMO_PASSWORD": env["E2E_PASSWORD"]})
    run("fixture", [sys.executable, str(app / "scripts/browser/pagination_fixture.py")])
    fixture = json.loads((work / "fixture.json").read_text(encoding="utf-8"))
    env["E2E_FOREIGN_REQUEST"] = fixture["foreignRequestPath"]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env["E2E_BASE_URL"] = f"http://127.0.0.1:{port}"
    server_log = (work / "server.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=app, env=env, stdout=server_log, stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 20
    while True:
        if server.poll() is not None:
            raise RuntimeError(f"Server exited early; inspect {work / 'server.log'}")
        try:
            with urlopen(env["E2E_BASE_URL"] + "/login/", timeout=1) as response:
                if response.status == 200:
                    break
        except (OSError, URLError):
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Server startup timed out; inspect {work / 'server.log'}")
            time.sleep(0.2)
    for suite in ("accounts", "pagination", "business"):
        folder = work / (suite + "-evidence")
        run(suite, [node, str(app / f"scripts/browser/{suite}.cjs")], {"E2E_OUTPUT_DIR": str(folder)})
    summary = {
        "status": "PASS",
        "accounts": json.loads((work / "accounts-evidence/accounts-results.json").read_text(encoding="utf-8")),
        "pagination": json.loads((work / "pagination-evidence/pagination-results.json").read_text(encoding="utf-8")),
        "business": json.loads((work / "business-evidence/business-summary.json").read_text(encoding="utf-8")),
    }
    (work / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"PASS browser suites. Evidence: {work}", flush=True)
finally:
    if server is not None and server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
    if server_log is not None:
        server_log.close()
