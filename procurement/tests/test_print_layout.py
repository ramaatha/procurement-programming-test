from html.parser import HTMLParser
from django.test import TestCase
from procurement.models import Vendor
from procurement.tests.factories import issued


class PrintTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row = []
        if tag in ('th','td') and self.row is not None: self.cell = []

    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('th','td') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


class PrintLayoutTests(TestCase):
    def test_printed_goods_have_explicit_columns_and_exact_totals(self):
        order = issued(quantity='4')
        self.client.force_login(order.request.requester)
        response = self.client.get(f'/orders/{order.pk}/print/')
        parser = PrintTableParser()
        parser.feed(response.content.decode())
        self.assertGreaterEqual(len(parser.rows),3,'Printed order needs a readable item table and total row.')
        self.assertEqual(parser.rows[0], ['No.','Uraian','Jumlah','Satuan','Harga satuan (IDR)','Total (IDR)'])
        self.assertEqual(parser.rows[1], ['1','Item contoh','4','unit','10,00','40,00'])
        self.assertEqual(parser.rows[-1], ['Total pesanan (IDR)','40,00'])
        self.assertContains(response, 'Purchase Order (PO)')
        self.assertContains(response, 'Cetak PO')
        self.assertNotContains(response, 'Catat Penerimaan')

    def test_print_keeps_vendor_snapshot_and_supports_services(self):
        order = issued(quantity='0.333',kind='SERVICES')
        Vendor.objects.filter(pk=order.vendor_id).update(name='Nama vendor sesudah PO')
        self.client.force_login(order.request.requester)
        response = self.client.get(f'/orders/{order.pk}/print/')
        self.assertContains(response, 'Vendor contoh')
        self.assertNotContains(response, 'Nama vendor sesudah PO')
        self.assertContains(response, 'Rincian Jasa')
        self.assertContains(response, 'Lokasi Layanan')
        parser = PrintTableParser()
        parser.feed(response.content.decode())
        self.assertEqual(parser.rows[1][2:], ['0,333','unit','10,00','3,33'])
