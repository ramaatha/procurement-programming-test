# filepath: deploy/pythonanywhere_wsgi.py
import os
from pathlib import Path
import sys

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_pythonanywhere"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
