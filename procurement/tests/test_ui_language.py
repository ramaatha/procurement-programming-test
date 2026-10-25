# filepath: procurement/tests/test_ui_language.py
from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from common.actions import ActionContext
from procurement.inputs import (
    DraftInput, QuotationInput, QuoteLineInput, ReceiptInput, ReceiptLineInput, RequestLineInput,
)
from procurement.services.receipts import post_receipt
from procurement.services.requests import save_draft
from procurement.services.sourcing import save_quotation, save_vendor
from procurement.tests.factories import approved, context, issued, user


class InterfaceLanguageTests(TestCase):
    def test_request_copy_preserves_user_text_and_uses_sentence_case_history(self):
        owner = user(Role.REQUESTER)
        target = save_draft(
            ActionContext(owner.pk, uuid4(), None),
            request_id=None,
            data=DraftInput(
                "GOODS", "Riset dan UJI MixedCase", "Kebutuhan untuk tim iOS", "Lab A",
                timezone.localdate() + timedelta(days=1),
                (RequestLineInput("iPhone 15 Pro", "unit", "10", "100000"),),
            ),
        )
        self.client.force_login(owner)
        page = self.client.get(f"/requests/{target.pk}/")
        self.assertContains(page, "Draf dibuat")
        self.assertContains(page, "Penawaran dan Pemilihan Vendor")
        self.assertContains(page, "Riset dan UJI MixedCase")
        self.assertContains(page, "iPhone 15 Pro")
        self.assertNotContains(page, "Riset Dan Uji Mixedcase")
        edit = self.client.get(f"/requests/{target.pk}/edit/")
        self.assertContains(edit, "Alasan kebutuhan:")
        self.assertContains(edit, "Estimasi harga per unit (IDR):")
        self.assertEqual(target.status, "DRAFT")

    def test_quotation_heading_and_date_caption_use_their_own_case(self):
        owner, reviewer, buyer = user(Role.REQUESTER), user(Role.APPROVER), user(Role.PROCUREMENT)
        target = approved(owner, reviewer)
        vendor = save_vendor(ActionContext(buyer.pk, uuid4(), None),
                             vendor_id=None, name="Vendor iOS UJI", contact="demo@example.invalid", is_active=True)
        item = target.revisions.get(number=1).items.get()
        save_quotation(
            context(buyer, target), request_id=target.pk, quotation_id=None,
            data=QuotationInput(vendor.pk, "Ref-iPhone-ABC", timezone.localdate(),
                                timezone.localdate() + timedelta(days=1), 1,
                                (QuoteLineInput(item.pk, "9.00"),)),
        )
        self.client.force_login(buyer)
        form = self.client.get(f"/requests/{target.pk}/quotations/new/")
        self.assertContains(form, "Berlaku sampai:")
        self.assertContains(form, "Harga per unit (IDR):")
        page = self.client.get(f"/requests/{target.pk}/quotations/")
        self.assertContains(page, "Pilih Penawaran")
        self.assertContains(page, "Berlaku sampai")
        self.assertContains(page, "Vendor iOS UJI")
        self.assertContains(page, "Ref-iPhone-ABC")
        self.assertNotContains(page, "Berlaku Sampai")

    def test_status_filter_and_receipt_history_do_not_title_case_sentences(self):
        order = issued()
        receiver = user(Role.RECEIVER)
        post_receipt(context(receiver, order), order_id=order.pk, data=ReceiptInput(
            "UJI-BAHASA", "Pemeriksaan selesai.", "GOODS_DELIVERY", None, None,
            tuple(ReceiptLineInput(item.pk, "10", "0", "") for item in order.items.all()),
        ))
        self.client.force_login(order.issued_by)
        detail = self.client.get(f"/orders/{order.pk}/")
        self.assertContains(detail, "Diterima lengkap")
        self.assertContains(detail, "Penerimaan dicatat")
        self.assertNotContains(detail, "Diterima Lengkap")
        filtered = self.client.get("/orders/", {"stage": "RECEIVED"})
        self.assertEqual(filtered.status_code, 200)
        self.assertContains(filtered, '<option value="RECEIVED" selected>Diterima lengkap</option>', html=True)
