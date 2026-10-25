# filepath: procurement/ai/quota.py
from contextlib import closing
import os
import sqlite3
import time
from uuid import uuid4
from django.conf import settings
from django.utils import timezone
from .config import AIError


def _connect():
    area=settings.DATA_DIR/'ai'
    area.mkdir(mode=0o700,parents=True,exist_ok=True)
    path=area/'usage.sqlite3'
    db=sqlite3.connect(path,timeout=2)
    os.chmod(path,0o600)
    return db


def reserve(actor_id: int) -> str:
    today=timezone.localdate().isoformat()
    token=uuid4().hex
    try:
        with closing(_connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS counts(day TEXT,actor TEXT,count INTEGER NOT NULL,PRIMARY KEY(day,actor))')
            db.execute('CREATE TABLE IF NOT EXISTS lease(id INTEGER PRIMARY KEY CHECK(id=1),token TEXT,expires REAL)')
            db.execute('DELETE FROM counts WHERE day < ?',(today,))
            busy=db.execute('SELECT expires FROM lease WHERE id=1').fetchone()
            if busy and busy[0]>time.time():
                raise AIError('AI sedang memproses permintaan lain. Tunggu sebentar atau lanjutkan manual.',429)
            for actor,limit in (('*',10),(str(actor_id),5)):
                row=db.execute('SELECT count FROM counts WHERE day=? AND actor=?',(today,actor)).fetchone()
                if row and row[0]>=limit:
                    raise AIError('Batas bantuan AI hari ini tercapai. Silakan lanjutkan secara manual.',429)
                db.execute('INSERT INTO counts VALUES(?,?,1) ON CONFLICT(day,actor) DO UPDATE SET count=count+1',(today,actor))
            db.execute('INSERT OR REPLACE INTO lease VALUES(1,?,?)',(token,time.time()+60))
    except (OSError,sqlite3.Error):
        raise AIError('Bantuan AI belum dapat digunakan. Silakan isi form secara manual.',503) from None
    return token


def release(token: str) -> None:
    try:
        with closing(_connect()) as db,db:
            db.execute('DELETE FROM lease WHERE id=1 AND token=?',(token,))
    except (OSError,sqlite3.Error):
        # The bounded lease expires even if a failed cleanup cannot reach the file.
        return
