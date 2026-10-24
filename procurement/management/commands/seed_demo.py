# filepath: procurement/management/commands/seed_demo.py
import os
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from accounts.models import Role, User
from accounts.services import save_user
from common.actions import ActionContext
from procurement.inputs import DraftInput, RequestLineInput, QuotationInput, QuoteLineInput, ReceiptInput, ReceiptLineInput
from procurement.models import PurchaseRequest, Vendor, PurchaseOrder
from procurement.models.demo import DemoSetup
from procurement.services.requests import save_draft, submit_request, review_request
from procurement.services.sourcing import save_vendor, save_quotation, select_quotation
from procurement.services.orders import issue_order
from procurement.services.receipts import post_receipt


ACCOUNTS = {
    'demo_admin': Role.ADMIN, 'demo_pemohon': Role.REQUESTER,
    'demo_approver': Role.APPROVER, 'demo_procurement': Role.PROCUREMENT,
    'demo_penerima': Role.RECEIVER,
}
SCENARIOS = {
    'G-01': ('GOODS', 'Peralatan Kantor Draft'),
    'J-01': ('SERVICES', 'Pemeliharaan Jaringan Siap Penawaran'),
    'G-02': ('GOODS', 'Monitor Siap Diterima'),
    'G-03': ('GOODS', 'Peralatan Diterima Sebagian'),
    'J-02': ('SERVICES', 'Pemeriksaan Jaringan Selesai'),
}
VENDOR_NAME = 'DEMO Vendor Peralatan'


def context(actor: User, target=None) -> ActionContext:
    return ActionContext(actor.pk, uuid4(), target.version if target else None)


@sensitive_variables('password')
def create_demo(password: str) -> dict:
    if not password or len(password) > 4096:
        raise CommandError('Isi DEMO_PASSWORD dengan password demo yang valid.')
    try:
        for username in ACCOUNTS:
            validate_password(password, User(username=username))
    except ValidationError:
        raise CommandError('DEMO_PASSWORD tidak memenuhi validator aplikasi. Gunakan minimal 6 karakter, bukan angka saja, bukan password umum atau mirip username.') from None
    # The manifest and every service mutation commit together; failed setup leaves no partial demo.
    with transaction.atomic():
        setup = DemoSetup.objects.filter(key='procurement-demo-v1').first()
        if setup:
            manifest = setup.manifest
            if any(not User.objects.filter(pk=pk, username=name).exists() for name, pk in manifest['accounts'].items()) or any(
                not PurchaseRequest.objects.filter(pk=pk).exists() for pk in manifest['requests'].values()
            ) or not Vendor.objects.filter(pk=manifest['vendor']).exists():
                raise CommandError('Identitas demo berubah atau hilang. Data tidak ditimpa; gunakan database demo baru untuk mengulang dari awal.')
            return manifest
        if User.objects.filter(username__in=ACCOUNTS).exists() or Vendor.objects.filter(name=VENDOR_NAME).exists() or PurchaseRequest.objects.filter(title__startswith='[DEMO ').exists():
            raise CommandError('Identitas demo berbenturan dengan data existing. Tidak ada data yang diambil alih; gunakan database demo terpisah.')
        admin = User(username='demo_admin', role=Role.ADMIN, is_active=True)
        admin.set_password(password)
        admin.full_clean()
        admin.save()
        actors = {'demo_admin': admin}
        for username, role in ACCOUNTS.items():
            if username != 'demo_admin':
                actors[username] = save_user(context(admin), user_id=None, username=username, role=role, is_active=True, initial_password=password)
        buyer = actors['demo_procurement']
        vendor = save_vendor(context(admin), vendor_id=None, name=VENDOR_NAME, contact='demo@example.invalid', is_active=True)
        today = timezone.localdate()
        requests = {}
        for code, (kind, title) in SCENARIOS.items():
            target = save_draft(context(actors['demo_pemohon']), request_id=None, data=DraftInput(
                kind, f'[DEMO {code}] {title}', 'Data sintetis untuk pengujian alur pengadaan.', 'Kantor Demo', today + timedelta(days=7),
                (RequestLineInput('Monitor Demo' if kind == 'GOODS' else 'Pemeriksaan Jaringan Demo', 'unit' if kind == 'GOODS' else 'kunjungan', '10', '100000'),)))
            requests[code] = str(target.pk)
            if code == 'G-01':
                continue
            target = submit_request(context(actors['demo_pemohon'], target), request_id=target.pk)
            target = review_request(context(actors['demo_approver'], target), request_id=target.pk, decision='APPROVE', reason='Kebutuhan demo disetujui.')
            if code == 'J-01':
                continue
            revision = target.revisions.get(number=target.current_revision_number)
            quote = save_quotation(context(buyer, target), request_id=target.pk, quotation_id=None, data=QuotationInput(
                vendor.pk, f'DEMO-Q-{code}', today, today + timedelta(days=7), 1,
                tuple(QuoteLineInput(item.pk, '90000') for item in revision.items.all())))
            target.refresh_from_db()
            target = select_quotation(context(buyer, target), request_id=target.pk, quotation_id=quote.pk,
                                      reason='Harga sesuai plafon dan kebutuhan.', single_source_reason='Satu vendor sintetis untuk demonstrasi.')
            order = issue_order(context(buyer, target), request_id=target.pk)
            if code in ('G-03', 'J-02'):
                service = kind == 'SERVICES'
                post_receipt(context(actors['demo_penerima'], order), order_id=order.pk, data=ReceiptInput(
                    f'DEMO-BUKTI-{code}', 'Pemeriksaan contoh selesai.', 'SERVICE_REPORT' if service else 'GOODS_DELIVERY',
                    today if service else None, today if service else None,
                    tuple(ReceiptLineInput(item.pk, '10' if service else '6', '0' if service else '2', '' if service else 'Dua unit rusak.') for item in order.items.all())))
        manifest = dict(accounts={name: actor.pk for name, actor in actors.items()}, requests=requests, vendor=str(vendor.pk))
        DemoSetup.objects.create(key='procurement-demo-v1', manifest=manifest)
        return manifest


class Command(BaseCommand):
    help = 'Buat lima akun dan lima skenario demo tanpa menimpa data existing.'

    @sensitive_variables('password')
    def handle(self, *args, **options):
        password = os.environ.get('DEMO_PASSWORD', '')
        manifest = create_demo(password)
        for username, pk in manifest['accounts'].items():
            actor = User.objects.get(pk=pk)
            self.stdout.write(f'{username}: {actor.role}; aktif={actor.is_active}')
        for code, pk in manifest['requests'].items():
            target = PurchaseRequest.objects.get(pk=pk)
            order = PurchaseOrder.objects.filter(request=target).first()
            self.stdout.write(f'{code}: {target.number}; {target.status}' + (f'; {order.number}; {order.status}' if order else ''))
        self.stdout.write('Data existing dipertahankan, termasuk password, peran dan kemajuan transaksi. Contoh mungkin sudah dilanjutkan atau penawaran kedaluwarsa; ulangi dari awal pada database demo baru.')
