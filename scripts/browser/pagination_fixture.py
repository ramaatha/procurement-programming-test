# filepath: scripts/browser/pagination_fixture.py
"""Synthetic pagination fixtures only; no evidence of user-driven lifecycle creation."""
import json
import os
from datetime import timedelta
from pathlib import Path
import sys
from uuid import uuid4

app = Path(os.environ['E2E_APP_DIR']).resolve()
data = Path(os.environ['E2E_DATA_DIR']).resolve()
output = Path(os.environ['E2E_FIXTURE_MANIFEST']).resolve()
if not (data / '.e2e-isolated').is_file():
    raise SystemExit('Require .e2e-isolated marker')
if os.environ.get('E2E_ALLOW_SYNTHETIC_FIXTURE') != '1':
    raise SystemExit('Set E2E_ALLOW_SYNTHETIC_FIXTURE=1 for synthetic data.')
if not data.is_relative_to(app) or data == app or not (data / 'db.sqlite3').is_file():
    raise SystemExit('Require an existing isolated database in E2E_APP_DIR.')
if (app / '.git').exists() or (app / '.venv').exists() or not (app / 'manage.py').is_file():
    raise SystemExit('Require an isolated source copy without .git or .venv.')
if Path(os.environ.get('DJANGO_DATA_DIR', '')).resolve() != data:
    raise SystemExit('DJANGO_DATA_DIR must match E2E_DATA_DIR.')
sys.path.insert(0, str(app))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from accounts.models import User
from procurement.models import (PurchaseRequest, RequestRevision, RevisionItem,
    Quotation, QuotationItem, PurchaseOrder, PurchaseOrderItem, Vendor)
if Path(settings.DATABASES['default']['NAME']).resolve() != data / 'db.sqlite3':
    raise SystemExit('Configured database does not match the isolated database.')
owner = User.objects.get(username='demo_pemohon')
actor = User.objects.get(username='demo_procurement')
prefix = f'E2E PAGE {uuid4().hex[:10]}'
today = timezone.localdate()
manifest = {'fixture': 'direct-model pagination dataset, not UI lifecycle evidence',
    'prefix': prefix, 'orders': [], 'requestIds': [], 'quotationCurrent': [], 'quotationHistory': []}

def request(title, number=1):
    target = PurchaseRequest.objects.create(requester=owner,kind='GOODS',title=title,
        reason='Synthetic pagination fixture',destination='Fixture only',needed_on=today,
        status='APPROVED',current_revision_number=number)
    rev, item = revision(target, number)
    return target,rev,item

def revision(target, number):
    rev = RequestRevision.objects.create(request=target,number=number,kind='GOODS',
        title=target.title,reason=target.reason,destination=target.destination,needed_on=today,
        estimated_total_minor=10000,submitted_by=owner)
    item = RevisionItem.objects.create(revision=rev,position=1,name=f'{prefix} Item',unit='unit',
        qty_milli=1000,estimated_unit_price_minor=10000,line_total_minor=10000)
    return rev,item

def quote(rev,item,reference):
    target = Quotation.objects.create(revision=rev,vendor=vendor,reference=reference,
        quoted_on=today,valid_until=today+timedelta(days=7),fulfillment_days=1,
        total_minor=9000,created_by=actor)
    QuotationItem.objects.create(quotation=target,revision_item=item,unit_price_minor=9000,line_total_minor=9000)
    return target

with transaction.atomic():
    vendor = Vendor.objects.create(name=f'{prefix} Vendor',contact='fixture@example.invalid',created_by=actor)
    for index in range(26):
        target,rev,item = request(f'{prefix} TRACK {index:02d}')
        quotation = quote(rev,item,f'{prefix} ORDER {index:02d}')
        order = PurchaseOrder.objects.create(request=target,revision=rev,quotation=quotation,
            vendor=vendor,vendor_name=vendor.name,vendor_contact=vendor.contact,kind='GOODS',
            destination=target.destination,total_minor=9000,selection_reason='Synthetic pagination fixture',
            single_source_reason='Fixture only',issued_by=actor)
        PurchaseOrderItem.objects.create(order=order,revision_item=item,position=1,name=item.name,
            unit='unit',qty_milli=1000,unit_price_minor=9000,line_total_minor=9000)
        manifest['requestIds'].append(str(target.pk))
        manifest['orders'].append({'id': str(order.pk),'number':order.number,'requestNumber':target.number})
    target,old_rev,old_item = request(f'{prefix} QUOTES')
    for index in range(26):
        reference = f'{prefix} HIST {index:02d}'
        quote(old_rev,old_item,reference)
        manifest['quotationHistory'].append(reference)
    rev,item = revision(target,2)
    PurchaseRequest.objects.filter(pk=target.pk).update(current_revision_number=2)
    for index in range(26):
        reference = f'{prefix} ACTIVE {index:02d}'
        quote(rev,item,reference)
        manifest['quotationCurrent'].append(reference)
    manifest['quotationPath'] = f'/requests/{target.pk}/quotations/'
    foreign = User.objects.create_user(username=f'e2e_foreign_{uuid4().hex[:12]}',role='REQUESTER')
    hidden = PurchaseRequest.objects.create(requester=foreign,kind='GOODS',title=f'{prefix} FOREIGN')
    manifest['foreignRequestPath'] = f'/requests/{hidden.pk}/'
manifest['trackingQuery'] = f'{prefix} TRACK'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'fixture':manifest['fixture'],'prefix':prefix,'orders':26,'quotesCurrent':26,'quotesHistorical':26,'manifest':str(output)}))