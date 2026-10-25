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

async function verifyBreadcrumbs(page, request) {
  const deep = request + 'quotations/new/';
  assert.equal((await page.goto(base + deep)).status(), 200);
  const trail = () => page.getByRole('navigation', { name: 'Jejak navigasi', exact: true });
  const labels = await trail().locator('li').allTextContents();
  assert.deepEqual(labels.map(label => label.replace(/\u2192/g, '').replace(/\s+/g, ' ').trim()),
    ['Beranda', 'Daftar Permintaan', 'Detail Permintaan', 'Penawaran', 'Tambah Penawaran']);
  assert.equal(await trail().locator('[aria-current=page]').innerText(), 'Tambah Penawaran');
  assert.equal(await trail().locator('[aria-current=page] a').count(), 0);
  assert.deepEqual((await trail().locator('.breadcrumb-separator').allTextContents()).map(s => s.trim()),
    ['\u2192', '\u2192', '\u2192', '\u2192']);
  const destinations = await trail().locator('a').evaluateAll(links => links.map(link => link.getAttribute('href')));
  for (const width of [320, 390, 640, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert(await trail().evaluate(nav => parseFloat(getComputedStyle(nav).fontSize) >= 16));
    assert(await trail().locator('a').evaluateAll(links => links.every(link => link.getBoundingClientRect().height >= 44)));
    if ([390, 1440].includes(width))
      await page.screenshot({ path: path.join(output, 'breadcrumbs-' + width + '.png'), fullPage: false });
  }
  evidence('breadcrumb font, arrow semantics and responsive wrapping', { widths: [320,390,640,768,1024,1440], fontMinPx: 16 });
  for (let i = 0; i < destinations.length; i++) {
    await page.goto(base + deep);
    const anchor = trail().locator('a').nth(i);
    if (i === 0) {
      await anchor.focus();
      await page.keyboard.press('Tab');
      await page.keyboard.press('Shift+Tab');
      assert(await anchor.evaluate(link => document.activeElement === link && parseFloat(getComputedStyle(link).outlineWidth) >= 3));
    }
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === base + destinations[i] && r.request().isNavigationRequest()),
      i === 0 ? anchor.press('Enter') : anchor.click(),
    ]);
    assert.equal(response.status(), 200);
    await page.waitForLoadState('domcontentloaded');
    assert.equal(new URL(page.url()).pathname, destinations[i]);
  }
  evidence('breadcrumb ancestor links work with keyboard and pointer', { destinations });
  await page.goto(base + request + 'quotations/');
  assert.equal(await page.getByLabel(/^Alasan hanya satu vendor:?$/).count(), 1);
  assert.equal(await page.getByText('Wajib jika hanya satu vendor memiliki penawaran yang memenuhi syarat.', { exact: true }).count(), 1);
  evidence('single eligible vendor explanation is visible beside its field');
}


async function verifyStatusNotice(page) {
  const notice = page.locator('.messages[role="status"]');
  await notice.waitFor({ state: 'visible' });
  assert((await notice.innerText()).includes('PO berhasil diterbitkan.'));
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const layout = await notice.evaluate(element => {
      const style = getComputedStyle(element);
      const range = document.createRange();
      range.selectNodeContents(element.querySelector('li'));
      const textWidth = range.getBoundingClientRect().width;
      const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)
        + parseFloat(style.borderLeftWidth) + parseFloat(style.borderRightWidth);
      return {
        width: element.getBoundingClientRect().width,
        textWidth, padding,
        noMarkers: [...element.children].every(item => getComputedStyle(item).listStyleType === 'none'),
      };
    });
    assert(layout.noMarkers, 'Status messages must have no bullet markers');
    assert(layout.width <= layout.textWidth + layout.padding + 2, 'Short status must fit its text');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    if ([390, 1440].includes(width))
      await page.screenshot({ path: path.join(output, 'status-notice-' + width + '.png'), fullPage: false });
  }
  const original = await notice.innerHTML();
  try {
    await page.setViewportSize({ width: 320, height: 900 });
    await notice.evaluate(element => {
      element.firstElementChild.textContent = 'Pesan status sintetis untuk memeriksa pembungkusan teks. '.repeat(12) + 'REFERENSI'.repeat(20);
      const extra = document.createElement('li');
      extra.textContent = 'Pesan sintetis kedua.';
      element.append(extra);
    });
    assert(await notice.evaluate(element => {
      const parent = element.parentElement;
      const parentStyle = getComputedStyle(parent);
      const available = parent.clientWidth - parseFloat(parentStyle.paddingLeft) - parseFloat(parentStyle.paddingRight);
      return element.getBoundingClientRect().width <= available + 1
        && [...element.children].every(item => getComputedStyle(item).listStyleType === 'none');
    }));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  } finally {
    await notice.evaluate((element, original) => { element.innerHTML = original; }, original);
    await page.setViewportSize({ width: 1440, height: 900 });
  }
  evidence('status notice fits text without bullets; long and multiple messages wrap', { widths: [320,390,768,1440], role: 'status' });
}


async function followAction(page, label, expectedHref) {
  const control = page.getByRole('link', { name: label, exact: true });
  await control.waitFor({ state: 'visible' });
  assert.equal(await control.getAttribute('href'), expectedHref);
  assert(await control.evaluate(link => {
    const style = getComputedStyle(link), box = link.getBoundingClientRect();
    return box.height >= 44 && parseFloat(style.fontSize) >= 16
      && parseFloat(style.borderTopWidth) >= 1 && style.backgroundColor !== 'rgba(0, 0, 0, 0)';
  }), label + ': action must look like a readable button');
  const destination = new URL(expectedHref, page.url()).href;
  await control.focus();
  await control.press('Enter');
  await page.waitForURL(destination);
  await page.waitForLoadState('domcontentloaded');
}
let receiptActionCaptured = false;
async function verifyReceiptEntry(page) {
  const control = page.getByRole('link', { name: 'Catat Penerimaan', exact: true });
  assert(await control.evaluate(link => {
    const details = document.querySelector('main dl');
    return Boolean(link.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING);
  }));
  if (receiptActionCaptured) return;
  for (const width of [320,390,640,768,1024,1440]) {
    await page.setViewportSize({ width, height: 900 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert(await control.evaluate(link => link.getBoundingClientRect().height >= 44));
    if ([390,1440].includes(width))
      await page.screenshot({ path: path.join(output, 'receipt-action-' + width + '.png'), fullPage: false });
  }
  receiptActionCaptured = true;
}
async function verifyActionLayouts(cases) {
  let checks = 0;
  for (const [page, route] of cases) {
    assert.equal((await page.goto(base + route)).status(), 200);
    assert(await page.locator('.page-actions a').count() > 0);
    for (const width of [320,390,640,768,1024,1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      assert(await page.locator('main a.button').evaluateAll(links => links.every(link => {
        const box = link.getBoundingClientRect();
        return box.height >= 44 && box.right <= innerWidth + 1 && box.left >= -1;
      })));
      checks++;
    }
  }
  evidence('workflow action buttons reflow across requester, PO, accounts and vendors', { checks, widths: [320,390,640,768,1024,1440] });
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
  await page.goto(base + '/requests/');
  await followAction(page, 'Buat Permintaan', '/requests/new/');
  await page.locator('[name=kind]').selectOption(kind);
  await fill(page, {
    title, reason: incomplete ? '' : 'Pengujian sintetis panduan',
    destination: incomplete ? '' : 'Kantor Demo', needed_on: today,
    'items-0-name': kind === 'GOODS' ? 'Monitor Uji' : 'Pemeriksaan Jaringan',
    'items-0-unit': kind === 'GOODS' ? 'unit' : 'kunjungan',
    'items-0-quantity': kind === 'GOODS' ? '10' : '2', 'items-0-unit_price': kind === 'GOODS' ? '100.000' : '100.000,00'
  });
  assert.equal(await click(page, 'Simpan Draf'), 303);
  await page.waitForURL(/\/requests\/[0-9a-f-]+\/$/);
  return new URL(page.url()).pathname;
}
async function submit(page, request) {
  await page.goto(base + request);
  await followAction(page, 'Lanjutkan Pengajuan', '#submit-heading');
  assert.equal(await click(form(page, 'submit-heading'), 'Ajukan Permintaan'), 303);
  assert.equal(state(request).request[0].status, 'SUBMITTED');
}
async function review(page, request, decision = 'APPROVE', reason = 'Sesuai kebutuhan uji') {
  await page.goto(base + request);
  await followAction(page, 'Tinjau Pengajuan', '#review-heading');
  const target = form(page, 'review-heading');
  await target.locator('[name=decision]').selectOption(decision);
  await fill(target, { reason });
  assert.equal(await click(target, 'Simpan Keputusan'), 303);
}
async function quote(page, request, suffix) {
  await page.goto(base + request);
  await followAction(page, 'Penawaran dan Pemilihan Vendor', request + 'quotations/');
  await followAction(page, 'Tambah Penawaran', request + 'quotations/new/');
  await page.locator('[name=vendor]').selectOption({ label: 'DEMO Vendor Peralatan' });
  await fill(page, {
    reference: prefix + suffix, quoted_on: today, valid_until: tomorrow, fulfillment_days: '1',
    'items-0-unit_price': '90.000,00'
  });
  assert.equal(await click(page, 'Simpan Penawaran'), 303);
  await page.waitForURL(base + request + 'quotations/');
  await followAction(page, 'Pilih Penawaran', '#selection-heading');
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
  await followAction(page, 'Lanjutkan Penerbitan PO', '#issue-heading');
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
  assert.equal((await page.goto(base + order)).status(), 200);
  await verifyReceiptEntry(page);
  await followAction(page, 'Catat Penerimaan', order + 'receipts/new/');
  for (const name of ['service_started_on', 'service_ended_on']) {
    const input = page.locator('[name="' + name + '"]');
    assert.equal(await input.count(), evidenceType === 'GOODS_DELIVERY' ? 0 : 1);
    if (evidenceType !== 'GOODS_DELIVERY') assert.notEqual(await input.getAttribute('required'), null);
  }
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
      ['G-01', false, 'Draf'], ['J-01', false, 'Disetujui'],
      ['G-02', true, 'Terbit'], ['G-03', true, 'Diterima sebagian'], ['J-02', true, 'Diterima lengkap']
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
        for (const [label, quantity] of [['Dipesan', '10'], ['Diterima', '6'], ['Ditolak', '2'], ['Sisa', '4']]) {
          assert(new RegExp(label + ': ' + quantity + '(?: \u00b7|$)').test(normalized.trim()), code + ': ' + label + ' balance');
        }
      }
      if (code === 'J-02') {
        await admin.locator('main a[href^="/receipts/"]').first().click();
        assert((await text(admin)).includes('Laporan pekerjaan'));
        assert((await text(admin)).includes('Periode jasa'));
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
    await invalid(owner, edit, 'Simpan Draf', incomplete,
      'Gunakan angka biasa', 'negative quantity');
    await owner.locator('[name="items-0-quantity"]').fill('10');
    await owner.locator('[name="items-0-unit_price"]').fill('not-a-price');
    await invalid(owner, owner.locator('main form'), 'Simpan Draf', incomplete,
      'Format harga tidak valid', 'invalid price');

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
    assert.equal(await click(owner, 'Simpan Draf'), 303);
    await submit(owner, request);
    await review(approver, request);
    assert.equal(state(request).requestrevision.length, 2);
    await owner.goto(base + request + 'revisions/1/');
    assert((await text(owner)).includes('Kantor Demo'));
    assert(!(await text(owner)).includes('Kantor Demo Revisi'));
    evidence('procurement return clears selection; revision1 immutable; resubmit revision2');
    await quote(buyer, request, ' goods-new');
    await verifyBreadcrumbs(buyer, request);
    const order = await issue(buyer, request);
    await verifyStatusNotice(buyer);
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
    await followAction(receiver, 'Catat Penerimaan Berikutnya', order + 'receipts/new/');
    assert.equal(await receiver.locator('[name=service_started_on]').count(), 0);
    await receiver.goto(base + order);
    assert((await text(receiver)).includes('Diterima sebagian'));
    assert.match((await receiver.locator('#balances-heading').locator('..').innerText()).replace(/\s+/g, ' '), /Sisa: 4(?: \u00b7|$)/);
    await receiptForm(receiver, order, '4', '0');
    await saveReceipt(receiver);
    assert.match((await text(receiver)).replace(/\s+/g, ' '), /Diterima: 4 unit \u00b7 Ditolak: 0 unit/);
    assert.equal(await receiver.getByRole('link', { name: 'Catat Penerimaan Berikutnya', exact: true }).count(), 0);
    await followAction(receiver, 'Buka Detail PO', order);
    assert((await text(receiver)).includes('Diterima lengkap'));
    assert.match((await receiver.locator('#balances-heading').locator('..').innerText()).replace(/\s+/g, ' '), /Dipesan: 10 \u00b7 Diterima: 10 \u00b7 Ditolak: 2 \u00b7 Sisa: 0/);
    assert.equal(state(request).receipt.length, 2);
    assert.equal(state(request).receiptitem.reduce((n, r) => n + r.accepted_milli, 0), 10000);
    assert.equal(state(request).receiptitem.reduce((n, r) => n + r.rejected_milli, 0), 2000);
    evidence('goods partial then complete; rejection history preserved', { nextReceiptActionMatchesRemaining: true });

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
      const label = evidenceType === 'SERVICE_REPORT' ? 'Laporan pekerjaan' : 'Berita acara jasa';
      const detail = await text(receiver);
      assert(detail.includes(label) && detail.includes('Periode jasa') && detail.includes('Pemeriksaan sintetis'));
      assert.equal(state(service.request).purchaseorder[0].total_minor, 18000000);
      const receipt = state(service.request).receipt[0];
      assert.equal(receipt.evidence_type, evidenceType);
      assert.equal(receipt.service_started_on, today);
      assert.equal(receipt.service_ended_on, today);
      assert.equal(state(service.request).purchaseorder[0].status, 'RECEIVED');
      evidence(evidenceType + ' final receipt detail', { period: today, total: 'IDR 180.000,00' });
    }

    evidence('goods omit service dates; both service evidence types require and save periods');
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
      if (partial) assert.match((await approver.locator('#balances-heading').locator('..').innerText()).replace(/\s+/g, ' '), /Sisa: 4(?: \u00b7|$)/);
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
    assert.equal(await click(a, 'Simpan Draf'), 303);
    await fill(b, { title: prefix + ' stale B' });
    await invalid(b, b.locator('main form'), 'Simpan Draf', stale, 'Data sudah berubah', 'two tabs stale draft', 409);
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
    await noBuyer.goto(base + noJs.request + 'quotations/');
    assert.equal(await noBuyer.getByRole('navigation', { name: 'Jejak navigasi', exact: true }).locator('[aria-current=page]').innerText(), 'Penawaran');
    evidence('JavaScript disabled: draft to approval, PO and final receipt', { breadcrumbRendered: true });

    const localized = await draft(owner, prefix + ' localized money');
    await owner.goto(base + localized + 'edit/');
    await fill(owner, { 'items-0-unit_price': '25.00.000' });
    await invalid(owner, owner.locator('main form'), 'Simpan Draf', localized,
      'Format harga tidak valid', 'malformed price grouping rejected without writes');
    await fill(owner, { 'items-0-unit_price': '1.250,50' });
    assert.equal(await click(owner, 'Simpan Draf'), 303);
    assert.equal(state(localized).requestitem[0].estimated_unit_price_minor, 125050);
    assert((await text(owner)).includes('12.505,00'));
    for (const value of ['1250.50', '1.250,50']) {
      await owner.goto(base + localized + 'edit/');
      await fill(owner, { 'items-0-unit_price': value });
      assert.equal(await click(owner, 'Simpan Draf'), 303);
      assert.equal(state(localized).requestitem[0].estimated_unit_price_minor, 125050);
    }
    evidence('Indonesian and legacy fractional price input stores exact minor units', { priceMinor: 125050, quantity: 10 });
    await verifyActionLayouts([[owner, '/requests/'], [owner, request], [receiver, order], [admin, '/users/'], [admin, '/vendors/']]);
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
