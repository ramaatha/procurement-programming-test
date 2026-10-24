# filepath: procurement/models/demo.py
from django.db import models


class DemoSetup(models.Model):
    key = models.CharField(max_length=40, primary_key=True)
    manifest = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
