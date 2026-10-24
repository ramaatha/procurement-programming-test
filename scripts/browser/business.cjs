// filepath: scripts/browser/business.cjs
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = new URL(process.env.E2E_BASE_URL);
assert(origin.protocol === 'http:' && origin.port && !['80','443'].includes(origin.port)
  && origin.pathname === '/' && !origin.search && !origin.hash && !origin.username && !origin.password,
  'Explicit loopback HTTP test origin on a nonstandard port required');
const base = origin.origin;
const password = process.env.E2E_PASSWORD;
const output = process.env.E2E_OUTPUT_DIR;
const database = process.env.E2E_DATABASE;
const runtimeErrors = [];
const python = process.env.E2E_PYTHON;
assert(base && ['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname), 'Loopback test URL required');
assert(password && output && database && python, 'E2E_PASSWORD/OUTPUT_DIR/DATABASE/PYTHON required');
assert.equal(process.env.E2E_ALLOW_MUTATIONS, 'isolated-synthetic', 'Explicit synthetic mutation opt-in required');
assert(fs.existsSync(path.join(path.dirname(database), '.e2e-isolated')), 'Isolated database marker required');
fs.mkdirSync(output, { recursive: true });
const report = [], prefix = 'E2E B ' + Date.now();
const date = offset => {
  const now = new Date(Date.now() + offset * 86400000);
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Jakarta' }).format(now);
};
const today = date(0), tomorrow = date(1);
let browser;
function evidence(name, details = {}) {
  report.push({ name, ...details });
  fs.writeFileSync(path.join(output, 'business-results.json'), JSON.stringify(report, null, 2));
  console.log('PASS', name);
}
function state(request) {
  const id = request.split('/').filter(Boolean)[1];
  return JSON.parse(execFileSync(python, [path.join(__dirname, 'observe.py'), database, id], { encoding: 'utf8' }));
}
async function text(page) { return (await page.locator('main').innerText()).replace(/\s+/g, ' '); }
async function fill(scope, values) {
  for (const [name, value] of Object.entries(values)) await scope.locator('[name="' + name + '"]').fill(value);
}
function form(page, heading) { return page.locator('section[aria-labelledby="' + heading + '"] form'); }
async function click(scope, name) {
  const page = typeof scope.page === 'function' ? scope.page() : scope;
  const response = page.waitForResponse(r => r.request().isNavigationRequest() && r.request().method() === 'POST');
  await scope.getByRole('button', { name, exact: true }).click();
  const result = await response;
  await page.waitForLoadState('domcontentloaded');
  return result.status();
}
async function freshPage(javaScriptEnabled = true) {
  const context = await browser.newContext({ javaScriptEnabled, viewport: { width: 1280, height: 900 } });
  await context.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.abort('blockedbyclient'));
  context.on('page', page => page.on('pageerror', error => runtimeErrors.push(String(error))));
  return context.newPage();
}
async function login(username, javaScriptEnabled = true) {
  const page = await freshPage(javaScriptEnabled);
  await page.goto(base + '/login/');
  await fill(page, { username, password });
  await click(page, 'Masuk');
  await page.waitForURL(base + '/');
  assert((await page.locator('.account-name').innerText()).includes(username));
  return page;
}
async function draft(page, title, kind = 'GOODS', incomplete = false) {
  await page.goto(base + '/requests/new/');
  await page.locator('[name=kind]').selectOption(kind);
  await fill(page, {
    title, reason: incomplete ? '' : 'Pengujian sintetis panduan',
    destination: incomplete ? '' : 'Kantor Demo', needed_on: today,
    'items-0-name': kind === 'GOODS' ? 'Monitor Uji' : 'Pemeriksaan Jaringan',
    'items-0-unit': kind === 'GOODS' ? 'unit' : 'kunjungan',
    'items-0-quantity': kind === 'GOODS' ? '10' : '2', 'items-0-unit_price': '100000'
  });
  assert.equal(await click(page, 'Simpan Draft'), 303);
  await page.waitForURL(/\/requests\/[0-9a-f-]+\/$/);
  return new URL(page.url()).pathname;
}
async function submit(page, request) {
  await page.goto(base + request);
  assert.equal(await click(form(page, 'submit-heading'), 'Ajukan Permintaan'), 303);
  assert.equal(state(request).request[0].status, 'SUBMITTED');
}
async function review(page, request, decision = 'APPROVE', reason = 'Sesuai kebutuhan uji') {
  await page.goto(base + request);
  const target = form(page, 'review-heading');
  await target.locator('[name=decision]').selectOption(decision);
  await fill(target, { reason });
  assert.equal(await click(target, 'Simpan Keputusan'), 303);
}
async function quote(page, request, suffix) {
  await page.goto(base + request + 'quotations/new/');
  await page.locator('[name=vendor]').selectOption({ label: 'DEMO Vendor Peralatan' });
  await fill(page, {
    reference: prefix + suffix, quoted_on: today, valid_until: tomorrow, fulfillment_days: '1',
    'items-0-unit_price': '90000'
  });
  assert.equal(await click(page, 'Simpan Penawaran'), 303);
  await page.waitForURL(base + request + 'quotations/');
  await page.locator('[name=quotation]').selectOption({ index: 1 });
  await fill(page, { reason: 'Harga sesuai plafon uji', single_source_reason: 'Satu vendor sintetis layak' });
  assert.equal(await click(page, 'Simpan Pilihan Vendor'), 303);
  const snapshot = state(request);
  assert(snapshot.request[0].selected_quotation_id);
  assert(snapshot.quotation.some(row => row.id === snapshot.request[0].selected_quotation_id));
  assert.equal(snapshot.quotationitem.length, snapshot.quotation.length);
}
async function issue(page, request) {
  await page.goto(base + request);
  assert.equal(await click(form(page, 'issue-heading'), 'Terbitkan PO'), 303);
  await page.waitForURL(/\/orders\/[0-9a-f-]+\/$/);
  return new URL(page.url()).pathname;
}
async function ready(owner, approver, buyer, suffix, kind = 'GOODS') {
  const request = await draft(owner, prefix + suffix, kind);
  await submit(owner, request);
  await review(approver, request);
  await quote(buyer, request, suffix);
  const order = await issue(buyer, request);
  return { request, order };
}
async function receiptForm(page, order, accepted, rejected, evidenceType = 'GOODS_DELIVERY', period = true) {
  const response = await page.goto(base + order + 'receipts/new/');
  assert.equal(response.status(), 200);
  await fill(page, {
    reference: prefix + '-R-' + report.length + '-' + Date.now(),
    notes: 'Pemeriksaan sintetis sesuai panduan', 'items-0-accepted': accepted,
    'items-0-rejected': rejected
  });
  await page.locator('[name=evidence_type]').selectOption(evidenceType);
  if (evidenceType !== 'GOODS_DELIVERY' && period) {
    await fill(page, { service_started_on: today, service_ended_on: today });
  }
}
async function saveReceipt(page) {
  assert.equal(await click(page, 'Simpan Penerimaan Final'), 303);
  await page.waitForURL(/\/receipts\/[0-9a-f-]+\/$/);
}
async function invalid(page, scope, button, request, expectedText, name, status = 400) {
  const before = state(request);
  await scope.evaluate(node => { if (node.tagName === 'FORM') node.noValidate = true; });
  const actual = await click(scope, button);
  assert.equal(actual, status, name + ': HTTP');
  assert((await text(page)).includes(expectedText), name + ': specific error: ' + await text(page));
  const errors = page.locator('main .errorlist');
  assert(await errors.count() > 0);
  assert.equal(await page.locator('main .errorlist').evaluateAll(nodes => nodes.filter(n => !n.closest('form')).length), 0);
  assert.deepEqual(state(request), before, name + ': business state unchanged');
  evidence(name, { http: status, businessStateUnchanged: true, errorInsideForm: true });
}
(async () => {
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const admin = await login('demo_admin'), owner = await login('demo_pemohon');
    const approver = await login('demo_approver'), buyer = await login('demo_procurement');
    const receiver = await login('demo_penerima');

    for (const [code, orders, expected] of [
      ['G-01', false, 'Draft'], ['J-01', false, 'Disetujui'],
      ['G-02', true, 'Terbit'], ['G-03', true, 'Diterima Sebagian'], ['J-02', true, 'Diterima Lengkap']
    ]) {
      await admin.goto(base + (orders ? '/orders/' : '/requests/') + '?q=' + encodeURIComponent('[DEMO ' + code + ']'));
      const link = admin.locator('main li h2 a').first();
      assert.equal(await link.count(), 1, code + ': demo link');
      await link.click();
      assert((await text(admin)).includes(expected), code + ': status');
      if (code === 'G-03') {
        const balances = admin.locator('#balances-heading').locator('..');
        const values = await balances.innerText();
        const normalized = values.replace(/\s+/g, ' ');
        for (const [label, quantity] of [['Dipesan', '10.000'], ['Diterima', '6.000'], ['Ditolak', '2.000'], ['Sisa', '4.000']]) {
          assert(normalized.includes(label + ': ' + quantity), code + ': ' + label + ' balance');
        }
      }
      if (code === 'J-02') {
        await admin.locator('main a[href^="/receipts/"]').first().click();
        assert((await text(admin)).includes('Laporan Pekerjaan'));
        assert((await text(admin)).includes('Periode Jasa'));
      }
      evidence('demo ' + code + ' readback', { expected });
    }

    const wrong = await freshPage();
    await wrong.goto(base + '/login/');
    await fill(wrong, { username: 'demo_pemohon', password: 'Wrong-synthetic-81274!' });
    assert.equal(await click(wrong, 'Masuk'), 400);
    assert.equal(await wrong.locator('main .errorlist').count(), 1);
    assert.equal(await wrong.locator('[name=password]').inputValue(), '');
    assert.notEqual(await wrong.evaluate(() => document.activeElement.closest('.errorlist') !== null), true);
    evidence('bad login: one inline error, no server-rendered password, no error focus');

    const incomplete = await draft(owner, prefix + ' incomplete', 'GOODS', true);
    await invalid(owner, form(owner, 'submit-heading'), 'Ajukan Permintaan', incomplete,
      'Alasan wajib diisi sebelum pengajuan.', 'submit missing header');
    await owner.goto(base + incomplete + 'edit/');
    const edit = owner.locator('main form');
    await owner.locator('[name="items-0-quantity"]').fill('-1');
    await invalid(owner, edit, 'Simpan Draft', incomplete,
      'Gunakan angka biasa', 'negative quantity');
    await owner.locator('[name="items-0-quantity"]').fill('10');
    await owner.locator('[name="items-0-unit_price"]').fill('not-a-price');
    await invalid(owner, owner.locator('main form'), 'Simpan Draft', incomplete,
      'angka', 'invalid price');

    const request = await draft(owner, prefix + ' goods');
    assert((await text(owner)).includes('1.000.000,00'));
    evidence('goods estimate displayed', { expected: 'IDR 1.000.000,00' });
    await submit(owner, request);
    for (const decision of ['REQUEST_CHANGES', 'REJECT']) {
      await approver.goto(base + request);
      await form(approver, 'review-heading').locator('[name=decision]').selectOption(decision);
      await fill(form(approver, 'review-heading'), { reason: '' });
      await invalid(approver, form(approver, 'review-heading'), 'Simpan Keputusan', request,
        'Isi alasan untuk keputusan ini.', decision + ' missing reason');
    }
    await review(approver, request);
    await quote(buyer, request, ' goods-old');
    const selected = state(request);
    const revisionSnapshot = selected.requestrevision;
    await buyer.goto(base + request);
    await fill(form(buyer, 'revision-heading'), { reason: 'Sesuaikan lokasi sebelum PO' });
    assert.equal(await click(form(buyer, 'revision-heading'), 'Minta Revisi Kebutuhan'), 303);
    const returned = state(request);
    assert.equal(returned.request[0].status, 'CHANGES_REQUESTED');
    assert.equal(returned.request[0].selected_quotation_id, null);
    assert.equal(returned.request[0].selection_reason, '');
    assert.equal(returned.request[0].single_source_reason, '');
    assert.deepEqual(returned.requestrevision, revisionSnapshot);
    assert.equal(returned.approvaldecision.length, 1);
    await owner.goto(base + request + 'edit/');
    await fill(owner, { destination: 'Kantor Demo Revisi' });
    assert.equal(await click(owner, 'Simpan Draft'), 303);
    await submit(owner, request);
    await review(approver, request);
    assert.equal(state(request).requestrevision.length, 2);
    await owner.goto(base + request + 'revisions/1/');
    assert((await text(owner)).includes('Kantor Demo'));
    assert(!(await text(owner)).includes('Kantor Demo Revisi'));
    evidence('procurement return clears selection; revision1 immutable; resubmit revision2');
    await quote(buyer, request, ' goods-new');
    const order = await issue(buyer, request);
    const issued = state(request);
    assert.equal(issued.purchaseorder[0].total_minor, 90000000);
    for (const item of ['900.000,00', 'DEMO Vendor Peralatan', 'Monitor Uji', 'Kantor Demo Revisi', 'Harga sesuai plafon uji', 'Satu vendor sintetis layak'])
      assert((await text(buyer)).includes(item), 'order snapshot ' + item);
    evidence('PO total and snapshot readback', { total: 'IDR 900.000,00', snapshotFields: ['vendor', 'item', 'destination', 'reasons'] });
    await receiptForm(receiver, order, '6', '2');
    await invalid(receiver, receiver.locator('main form'), 'Simpan Penerimaan Final', request,
      'Alasan penolakan', 'rejected quantity missing reason');
    await fill(receiver, { 'items-0-rejection_reason': 'Dua unit rusak' });
    await saveReceipt(receiver);
    assert((await text(receiver)).includes('Dua unit rusak'));
    await receiver.goto(base + order);
    assert((await text(receiver)).includes('Diterima Sebagian'));
    assert((await text(receiver)).includes('4.000'));
    await receiptForm(receiver, order, '4', '0');
    await saveReceipt(receiver);
    await receiver.goto(base + order);
    assert((await text(receiver)).includes('Diterima Lengkap'));
    assert.equal(state(request).receipt.length, 2);
    assert.equal(state(request).receiptitem.reduce((n, r) => n + r.accepted_milli, 0), 10000);
    assert.equal(state(request).receiptitem.reduce((n, r) => n + r.rejected_milli, 0), 2000);
    evidence('goods partial then complete; rejection history preserved');

    for (const evidenceType of ['SERVICE_REPORT', 'SERVICE_ACCEPTANCE']) {
      const service = await ready(owner, approver, buyer, ' ' + evidenceType, 'SERVICES');
      await receiptForm(receiver, service.order, '2', '0', evidenceType, false);
      await invalid(receiver, receiver.locator('main form'), 'Simpan Penerimaan Final', service.request,
        'Bidang ini tidak boleh kosong.', evidenceType + ' missing period');
      await fill(receiver, { service_started_on: tomorrow, service_ended_on: tomorrow });
      await invalid(receiver, receiver.locator('main form'), 'Simpan Penerimaan Final', service.request,
        'periode', evidenceType + ' future period');
      await fill(receiver, { service_started_on: today, service_ended_on: today });
      await saveReceipt(receiver);
      const label = evidenceType === 'SERVICE_REPORT' ? 'Laporan Pekerjaan' : 'Berita Acara Jasa';
      const detail = await text(receiver);
      assert(detail.includes(label) && detail.includes('Periode Jasa') && detail.includes('Pemeriksaan sintetis'));
      assert.equal(state(service.request).purchaseorder[0].total_minor, 18000000);
      const receipt = state(service.request).receipt[0];
      assert.equal(receipt.evidence_type, evidenceType);
      assert.equal(receipt.service_started_on, today);
      assert.equal(receipt.service_ended_on, today);
      assert.equal(state(service.request).purchaseorder[0].status, 'RECEIVED');
      evidence(evidenceType + ' final receipt detail', { period: today, total: 'IDR 180.000,00' });
    }

    const cancelled = await draft(owner, prefix + ' cancel request');
    await fill(form(owner, 'cancel-heading'), { reason: 'Kebutuhan uji dibatalkan' });
    assert.equal(await click(form(owner, 'cancel-heading'), 'Batalkan Permintaan'), 303);
    assert.equal(state(cancelled).request[0].status, 'CANCELLED');
    assert.equal(state(cancelled).purchaseorder.length, 0);
    evidence('owner cancels before PO with reason');

    for (const partial of [false, true]) {
      const closing = await ready(owner, approver, buyer, partial ? ' close short' : ' cancel PO');
      if (partial) {
        await receiptForm(receiver, closing.order, '6', '2');
        await fill(receiver, { 'items-0-rejection_reason': 'Dua unit rusak' });
        await saveReceipt(receiver);
      }
      const staleReceipt = await receiver.context().newPage();
      await receiptForm(staleReceipt, closing.order, '1', '0');
      await approver.goto(base + closing.order);
      const staleClose = await approver.context().newPage();
      await staleClose.goto(base + closing.order);
      await fill(approver, { reason: 'Sisa tidak akan dipenuhi dalam uji' });
      assert.equal(await click(approver, 'Konfirmasi Akhiri PO'), 303);
      const status = partial ? 'CLOSED_SHORT' : 'CANCELLED';
      assert.equal(state(closing.request).purchaseorder[0].status, status);
      if (partial) assert((await text(approver)).includes('4.000'));
      await fill(staleClose, { reason: 'Percobaan penutupan kedua' });
      await invalid(staleClose, staleClose.locator('main form').filter({ has: staleClose.locator('[name=reason]') }),
        'Konfirmasi Akhiri PO', closing.request, 'sudah berubah', status + ' second closure', 409);
      await invalid(staleReceipt, staleReceipt.locator('main form'), 'Simpan Penerimaan Final',
        closing.request, 'sudah berubah', status + ' stale receipt rejected', 409);
      await staleReceipt.close();
      const before = state(closing.request);
      assert.equal((await receiver.goto(base + closing.order + 'receipts/new/')).status(), 409);
      assert.deepEqual(state(closing.request), before);
      evidence(status + ': terminal receipt unavailable', { http: 409, businessStateUnchanged: true });
      await staleClose.close();
    }

    const stale = await draft(owner, prefix + ' stale draft');
    const a = await owner.context().newPage(), b = await owner.context().newPage();
    await a.goto(base + stale + 'edit/'); await b.goto(base + stale + 'edit/');
    await fill(a, { title: prefix + ' winner A' });
    assert.equal(await click(a, 'Simpan Draft'), 303);
    await fill(b, { title: prefix + ' stale B' });
    await invalid(b, b.locator('main form'), 'Simpan Draft', stale, 'Data sudah berubah', 'two tabs stale draft', 409);
    assert.equal(state(stale).request[0].title, prefix + ' winner A');
    await a.close(); await b.close();

    assert.equal((await admin.goto(base + '/requests/new/')).status(), 403);
    const other = await login('demo_pemohon');
    const foreign = process.env.E2E_FOREIGN_REQUEST;
    assert(foreign && /^\/requests\/[0-9a-f-]+\/$/.test(foreign), 'Foreign-owner fixture path required');
    if (foreign) {
      const before = state(foreign);
      assert.equal((await other.goto(base + foreign)).status(), 404);
      assert.deepEqual(state(foreign), before);
      evidence('foreign requester detail hidden', { http: 404 });
    }
    evidence('admin cannot create request', { http: 403 });

    const noOwner = await login('demo_pemohon', false), noApprover = await login('demo_approver', false);
    const noBuyer = await login('demo_procurement', false), noReceiver = await login('demo_penerima', false);
    const noJs = await ready(noOwner, noApprover, noBuyer, ' noJS');
    await receiptForm(noReceiver, noJs.order, '10', '0');
    await saveReceipt(noReceiver);
    assert.equal(state(noJs.request).purchaseorder[0].status, 'RECEIVED');
    evidence('JavaScript disabled: draft to approval, PO and final receipt');

    await receiver.goto(base + order);
    await receiver.screenshot({ path: path.join(output, 'goods-complete.png'), fullPage: true });
    await buyer.goto(base + order + 'print/');
    assert((await text(buyer)).includes('900.000,00'));
    await buyer.pdf({ path: path.join(output, 'goods-po.pdf'), format: 'A4' });
    let widths = 0;
    for (const page of [owner, buyer, receiver, noOwner]) {
      for (const width of [320, 390, 640, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        widths++;
      }
    }
    evidence('responsive states', { checks: widths, widths: [320, 390, 640, 768, 1024, 1440], businessFlows: false });
    assert.deepEqual(runtimeErrors, []);
    fs.writeFileSync(path.join(output, 'business-summary.json'), JSON.stringify({
      passed: report.length, completed: true, origin: base, prefix, javascriptDisabledFullFlow: true, runtimeErrors,
      bounds: ['Real password manager not exercised', 'No remote deployment, TLS, proxy, load or live CVE audit']
    }, null, 2));
  } finally { await browser.close(); }
})().catch(error => {
  fs.writeFileSync(path.join(output, 'business-failure.txt'), String(error.stack).split(password).join('[REDACTED]'));
  console.error(String(error.stack).split(password).join('[REDACTED]'));
  process.exitCode = 1;
});
