# filepath: accounts/tests/test_breadcrumbs.py
from html.parser import HTMLParser
from uuid import uuid4

from django.test import TestCase

from accounts.models import Role
from common.actions import ActionContext
from procurement.forms.sourcing import SelectionForm
from procurement.inputs import ReceiptInput, ReceiptLineInput
from procurement.models import Quotation
from procurement.services.receipts import post_receipt
from procurement.services.sourcing import save_vendor
from procurement.tests.factories import approved, context, draft, issued, user


class TrailParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.hidden = False
        self.item = None
        self.items = []
        self.separators = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "nav" and attrs.get("aria-label") == "Jejak navigasi":
            self.active = True
        if not self.active:
            return
        if tag == "li":
            self.item = {"text": [], "href": None, "current": False}
        elif tag == "a" and self.item is not None:
            self.item["href"] = attrs.get("href")
        elif tag == "span":
            self.hidden = attrs.get("aria-hidden") == "true"
            if self.item is not None and attrs.get("aria-current") == "page":
                self.item["current"] = True

    def handle_data(self, data):
        if self.active and self.hidden and data.strip():
            self.separators.append(data.strip())
        if self.active and self.item is not None and not self.hidden:
            self.item["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "span":
            self.hidden = False
        elif tag == "li" and self.active and self.item is not None:
            self.item["label"] = " ".join("".join(self.item.pop("text")).split())
            self.items.append(self.item)
            self.item = None
        elif tag == "nav":
            self.active = False


class BreadcrumbTests(TestCase):
    def trail(self, response, expected, status=200):
        self.assertEqual(response.status_code, status)
        parser = TrailParser()
        parser.feed(response.content.decode())
        self.assertEqual([(item["label"], item["href"]) for item in parser.items], expected)
        self.assertEqual([item["label"] for item in parser.items if item["current"]], [expected[-1][0]])
        self.assertEqual(parser.separators, ["\u2192"] * (len(expected) - 1))

    def test_quotation_path_and_short_vendor_reason(self):
        owner, reviewer, buyer = user(Role.REQUESTER), user(Role.APPROVER), user(Role.PROCUREMENT)
        target = approved(owner, reviewer)
        self.client.force_login(buyer)
        parent = [("Beranda", "/"), ("Daftar Permintaan", "/requests/"),
                  ("Detail Permintaan", f"/requests/{target.pk}/")]
        self.trail(self.client.get(f"/requests/{target.pk}/quotations/"), parent + [("Penawaran", None)])
        self.trail(self.client.get(f"/requests/{target.pk}/quotations/new/"),
                   parent + [("Penawaran", f"/requests/{target.pk}/quotations/"), ("Tambah Penawaran", None)])
        field = SelectionForm(quotations=Quotation.objects.none()).fields["single_source_reason"]
        self.assertEqual(field.label, "Alasan hanya satu vendor")
        self.assertEqual(field.help_text, "Wajib jika hanya satu vendor memiliki penawaran yang memenuhi syarat.")
        self.assertFalse(field.required)

    def test_request_pages_keep_canonical_parents(self):
        owner = user(Role.REQUESTER)
        target = draft(owner)
        self.client.force_login(owner)
        root = [("Beranda", "/"), ("Daftar Permintaan", "/requests/")]
        self.trail(self.client.get("/requests/new/"), root + [("Buat Permintaan", None)])
        self.trail(self.client.get(f"/requests/{target.pk}/"), root + [("Detail Permintaan", None)])
        self.trail(self.client.get(f"/requests/{target.pk}/edit/"),
                   root + [("Detail Permintaan", f"/requests/{target.pk}/"), ("Ubah Draf", None)])
        target = approved(owner, user(Role.APPROVER))
        self.trail(self.client.get(f"/requests/{target.pk}/revisions/1/"),
                   root + [("Detail Permintaan", f"/requests/{target.pk}/"), ("Revisi Pengajuan", None)])

    def test_account_vendor_and_list_pages(self):
        admin = user(Role.ADMIN)
        vendor = save_vendor(ActionContext(admin.pk, uuid4(), None), vendor_id=None,
                             name="Vendor navigasi", contact="demo@example.invalid", is_active=True)
        self.client.force_login(admin)
        cases = [
            ("/", [("Beranda", None)]),
            ("/requests/", [("Beranda", "/"), ("Daftar Permintaan", None)]),
            ("/orders/", [("Beranda", "/"), ("Daftar PO", None)]),
            ("/users/", [("Beranda", "/"), ("Kelola Akun", None)]),
            ("/users/new/", [("Beranda", "/"), ("Kelola Akun", "/users/"), ("Buat Akun", None)]),
            (f"/users/{admin.pk}/password/", [("Beranda", "/"), ("Kelola Akun", "/users/"),
                ("Ubah Akun", f"/users/{admin.pk}/edit/"), ("Reset Password", None)]),
            ("/vendors/new/", [("Beranda", "/"), ("Kelola Vendor", "/vendors/"), ("Tambah Vendor", None)]),
            (f"/vendors/{vendor.pk}/edit/", [("Beranda", "/"), ("Kelola Vendor", "/vendors/"), ("Ubah Vendor", None)]),
        ]
        for path, expected in cases:
            with self.subTest(path=path):
                self.trail(self.client.get(path), expected)

    def test_order_receipt_and_print_link_are_preserved(self):
        order = issued()
        receiver = user(Role.RECEIVER)
        self.client.force_login(receiver)
        root = [("Beranda", "/"), ("Daftar PO", "/orders/")]
        detail = self.client.get(f"/orders/{order.pk}/")
        self.trail(detail, root + [("Detail PO", None)])
        self.assertContains(detail, f'href="/orders/{order.pk}/print/"')
        self.assertContains(detail, f'href="/requests/{order.request_id}/"')
        self.trail(self.client.get(f"/orders/{order.pk}/receipts/new/"),
                   root + [("Detail PO", f"/orders/{order.pk}/"), ("Catat Penerimaan", None)])
        post_receipt(context(receiver, order), order_id=order.pk, data=ReceiptInput(
            "NAV-RECEIPT", "Pemeriksaan navigasi", "GOODS_DELIVERY", None, None,
            tuple(ReceiptLineInput(item.pk, "10", "0", "") for item in order.items.all())))
        receipt = order.receipts.get()
        self.trail(self.client.get(f"/receipts/{receipt.pk}/"),
                   root + [("Detail PO", f"/orders/{order.pk}/"), ("Detail Penerimaan", None)])
        self.assertNotContains(self.client.get(f"/orders/{order.pk}/print/"), 'aria-label="Jejak navigasi"')

    def test_invalid_selection_keeps_quotation_path(self):
        owner, reviewer, buyer = user(Role.REQUESTER), user(Role.APPROVER), user(Role.PROCUREMENT)
        target = approved(owner, reviewer)
        self.client.force_login(buyer)
        response = self.client.post(f"/requests/{target.pk}/quotations/select/", {})
        self.trail(response, [("Beranda", "/"), ("Daftar Permintaan", "/requests/"),
                            ("Detail Permintaan", f"/requests/{target.pk}/"), ("Penawaran", None)], status=400)

    def test_login_and_error_do_not_invent_breadcrumbs(self):
        self.assertNotContains(self.client.get("/login/"), 'aria-label="Jejak navigasi"')
        self.client.force_login(user(Role.ADMIN))
        self.assertNotContains(self.client.get("/missing/"), 'aria-label="Jejak navigasi"', status_code=404)

    def test_locked_edit_uses_the_page_actually_rendered(self):
        order = issued()
        target = order.request
        self.client.force_login(order.issued_by)
        parent = [("Beranda", "/"), ("Daftar Permintaan", "/requests/"),
                  ("Detail Permintaan", f"/requests/{target.pk}/")]
        for path in (f"/requests/{target.pk}/quotations/new/",
                     f"/requests/{target.pk}/quotations/{order.quotation_id}/edit/"):
            with self.subTest(path=path):
                self.trail(self.client.get(path), parent + [("Penawaran", None)], status=409)
        self.client.force_login(target.requester)
        self.trail(self.client.get(f"/requests/{target.pk}/edit/"),
                   [("Beranda", "/"), ("Daftar Permintaan", "/requests/"),
                    ("Detail Permintaan", None)], status=409)
