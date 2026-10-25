# filepath: deploy/ai.py
"""Configure the optional provider key separately from application/hosting secrets."""
import argparse
import getpass
import json
import os
from pathlib import Path


def create_configuration(path: Path, key: str) -> None:
    if not isinstance(key,str) or not 10<=len(key)<=4096 or any(c.isspace() for c in key):
        raise ValueError('API key tidak valid.')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as handle:
        json.dump({'api_key':key},handle)
        handle.write('\n')


def main() -> None:
    parser=argparse.ArgumentParser(description='Aktifkan bantuan AI opsional; key tidak ditampilkan.')
    parser.add_argument('action',choices=['configure'])
    parser.add_argument('--config',type=Path,default=Path.home()/'.config/procurement-demo/ai.json')
    args=parser.parse_args()
    try:
        key=getpass.getpass('Groq API key (input disembunyikan): ').strip()
        if key!=getpass.getpass('Ulangi API key: ').strip():
            raise ValueError('API key tidak cocok.')
        create_configuration(args.config,key)
    except FileExistsError:
        parser.error('Konfigurasi AI sudah ada; file tidak ditimpa.')
    except (OSError,ValueError,EOFError):
        parser.error('Konfigurasi gagal. Periksa key dan izin file; key tidak disimpan ulang.')
    print('Konfigurasi AI tersimpan secara privat. Reload aplikasi, lalu uji satu contoh singkat.')


if __name__=='__main__':
    main()
