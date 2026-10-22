# filepath: common/http.py
import sqlite3

from django import forms
from django.core.exceptions import ValidationError
from django.db import OperationalError


def validation_errors(form: forms.Form, error: ValidationError) -> None:
    if hasattr(error,'message_dict'):
        for field,errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None,errors)
    else:form.add_error(None,error.messages)


def database_busy(error: OperationalError) -> bool:
    code=getattr(error.__cause__,'sqlite_errorcode',None)
    if code is not None:return (code & 255) in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED)
    return str(error).lower() in ('database is locked','database table is locked')
