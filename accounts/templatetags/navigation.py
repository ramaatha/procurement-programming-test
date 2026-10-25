# filepath: accounts/templatetags/navigation.py
from typing import NamedTuple

from django import template
from django.urls import reverse

register = template.Library()


class Breadcrumb(NamedTuple):
    label: str
    url: str | None


def link(label: str, view: str, *args) -> Breadcrumb:
    return Breadcrumb(label, reverse(view, args=args))


def trail(context) -> list[Breadcrumb]:
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    if not match or not request.user.is_authenticated or context.get("error_title"):
        return []
    name = context.get("breadcrumb_page", match.url_name)
    namespace, params = match.namespace, match.kwargs
    items = [link("Beranda", "accounts:home")]
    if namespace == "accounts":
        if name == "home":
            return items
        if name == "logout_confirm":
            return items + [Breadcrumb("Konfirmasi Keluar", None)]
        labels = {"user_list": "Kelola Akun", "user_create": "Buat Akun",
                  "user_edit": "Ubah Akun", "user_password": "Reset Password"}
        if name not in labels:
            return []
        if name != "user_list":
            items.append(link("Kelola Akun", "accounts:user_list"))
        if name == "user_password":
            items.append(link("Ubah Akun", "accounts:user_edit", params["user_id"]))
        return items + [Breadcrumb(labels[name], None)]
    if namespace != "procurement":
        return []
    if name in {"vendor_list", "vendor_create", "vendor_edit"}:
        if name != "vendor_list":
            items.append(link("Kelola Vendor", "procurement:vendor_list"))
        label = {"vendor_list": "Kelola Vendor", "vendor_create": "Tambah Vendor",
                 "vendor_edit": "Ubah Vendor"}[name]
        return items + [Breadcrumb(label, None)]
    if name == "approval_list":
        return items + [Breadcrumb("Antrean Persetujuan", None)]
    request_pages = {
        "request_list", "request_create", "request_detail", "request_edit",
        "request_submit", "request_cancel", "request_review", "request_return_revision",
        "request_revision", "quotation_list", "quotation_select", "quotation_create",
        "quotation_edit", "order_issue",
    }
    if name in request_pages:
        items.append(link("Daftar Permintaan", "procurement:request_list"))
        if name == "request_list":
            return items
        if name == "request_create":
            return items + [Breadcrumb("Buat Permintaan", None)]
        request_id = params["request_id"]
        items.append(link("Detail Permintaan", "procurement:request_detail", request_id))
        if name == "request_edit":
            return items + [Breadcrumb("Ubah Draf", None)]
        if name == "request_revision":
            return items + [Breadcrumb("Revisi Pengajuan", None)]
        if name in {"quotation_list", "quotation_select", "quotation_create", "quotation_edit"}:
            items.append(link("Penawaran", "procurement:quotation_list", request_id))
            if name in {"quotation_create", "quotation_edit"}:
                label = "Tambah Penawaran" if name == "quotation_create" else "Ubah Penawaran"
                items.append(Breadcrumb(label, None))
        return items
    if name in {"order_list", "order_detail", "order_close", "receipt_create", "receipt_detail"}:
        items.append(link("Daftar PO", "procurement:order_list"))
        if name == "order_list":
            return items
        order_id = context["receipt"].order_id if name == "receipt_detail" else params["order_id"]
        items.append(link("Detail PO", "procurement:order_detail", order_id))
        if name in {"receipt_create", "receipt_detail"}:
            label = "Catat Penerimaan" if name == "receipt_create" else "Detail Penerimaan"
            items.append(Breadcrumb(label, None))
        return items
    return []


@register.inclusion_tag("includes/breadcrumbs.html", takes_context=True)
def breadcrumbs(context):
    items = trail(context)
    if items:
        items[-1] = Breadcrumb(items[-1].label, None)
    return {"breadcrumbs": items}
