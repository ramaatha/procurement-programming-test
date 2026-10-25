// filepath: scripts/browser/accounts.cjs
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const base = new URL(process.env.E2E_BASE_URL);
if (base.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname) || !base.port || ['80', '443'].includes(base.port) || base.username || base.password || base.pathname !== '/' || base.search || base.hash) {
  throw new Error('E2E_BASE_URL must be an explicit loopback HTTP test origin on a nonstandard port.');
}
if (!process.env.E2E_PASSWORD) throw new Error('E2E_PASSWORD is required.');
if (!process.env.E2E_OUTPUT_DIR) throw new Error('E2E_OUTPUT_DIR is required.');
assert.equal(process.env.E2E_ALLOW_MUTATIONS, 'isolated-synthetic', 'Explicit synthetic mutation opt-in required');
if (!process.env.E2E_DATABASE || !fs.existsSync(path.join(path.dirname(process.env.E2E_DATABASE), '.e2e-isolated'))) {
  throw new Error('Isolated database marker required');
}
const output = path.resolve(process.env.E2E_OUTPUT_DIR);
fs.mkdirSync(output, { recursive: true });
const suffix = Date.now().toString(36) + crypto.randomBytes(3).toString('hex');
const member = `e2e_member_${suffix}`;
const secondary = `e2e_admin_${suffix}`;
const vendor = `E2E Accounts Vendor ${suffix}`;
const passwordA = crypto.randomBytes(20).toString('base64url') + '!aA7';
const passwordB = crypto.randomBytes(20).toString('base64url') + '!bB8';
const passwordC = crypto.randomBytes(20).toString('base64url') + '!cC9';
const secrets = [process.env.E2E_PASSWORD, passwordA, passwordB, passwordC];
const safeError = error => secrets.reduce((text, secret) => text.split(secret).join('[REDACTED]'), String(error.stack || error));
const evidence = { suite: 'accounts-vendor-session', baseUrl: base.origin, startedAt: new Date().toISOString(), synthetic: { member, secondary, vendor }, steps: [], runtimeErrors: [], screenshots: [] };
let browser;
let currentPage;
const contexts = [];

async function newPage() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  contexts.push(context);
  await context.route('**/*', route => new URL(route.request().url()).origin === base.origin ? route.continue() : route.abort('blockedbyclient'));
  const page = await context.newPage();
  page.on('pageerror', error => evidence.runtimeErrors.push(safeError(error)));
  return page;
}
async function go(page, route) {
  currentPage = page;
  const response = await page.goto(new URL(route, base).href);
  assert(response && response.status() < 500, `Navigation failed: ${route}`);
  return response;
}
async function submit(page, button, expected = 303) {
  const responsePromise = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).origin === base.origin);
  await page.getByRole('button', { name: button, exact: true }).click();
  const response = await responsePromise;
  assert.equal(response.status(), expected, `Unexpected form POST status for ${button}`);
  await page.waitForLoadState('networkidle');
  return response;
}
const checkedPasswordNames = new Set();
async function checkPasswordToggle(page, inputName, description) {
  if (checkedPasswordNames.has(inputName)) return;
  const input = page.locator('input[name="' + inputName + '"]');
  const button = page.locator('button.password-toggle[aria-controls="' + await input.getAttribute('id') + '"]');
  assert.equal(await button.getAttribute('aria-label'), 'Tampilkan ' + description);
  assert.equal(await input.getAttribute('type'), 'password');
  assert.equal(await button.getAttribute('aria-controls'), await input.getAttribute('id'));
  assert.equal(await button.getAttribute('title'), 'Tampilkan ' + description);
  await button.focus();
  await button.press('Enter');
  assert.equal(await input.getAttribute('type'), 'text');
  assert.equal(await button.getAttribute('aria-label'), 'Sembunyikan ' + description);
  assert.equal(await button.getAttribute('title'), 'Sembunyikan ' + description);
  await button.press('Enter');
  assert.equal(await input.getAttribute('type'), 'password');
  checkedPasswordNames.add(inputName);
}
async function login(page, username, password, success = true) {
  await go(page, '/login/');
  await page.getByLabel(/^Username:?$/).fill(username);
  await page.getByLabel(/^Password:?$/).fill(password);
  await checkPasswordToggle(page, 'password', 'password');
  await submit(page, 'Masuk', success ? 303 : 400);
  if (success) {
    assert.equal(new URL(page.url()).pathname, '/');
    assert.equal(await page.locator('.account-name').innerText(), username);
  } else {
    assert.equal(new URL(page.url()).pathname, '/login/');
    assert.match(await page.locator('main').innerText(), /Tidak dapat masuk/);
    assert.equal(await page.locator('.account-name').count(), 0);
  }
}
async function logout(page, cancelFirst = false) {
  await page.getByRole('link', { name: 'Keluar', exact: true }).click();
  const dialog = page.locator('#logout-dialog');
  await dialog.waitFor({ state: 'visible' });
  if (cancelFirst) {
    await dialog.getByRole('button', { name: 'Batal', exact: true }).click();
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(await page.locator('.account-name').count(), 1);
    await page.getByRole('link', { name: 'Keluar', exact: true }).click();
    await dialog.waitFor({ state: 'visible' });
  }
  await submit(page, 'Ya, Keluar');
  assert.equal(new URL(page.url()).pathname, '/login/');
  await go(page, '/');
  assert.equal(new URL(page.url()).pathname, '/login/');
}
async function shot(page, name) {
  const file = `${name}.png`;
  await page.screenshot({ path: path.join(output, file), fullPage: true });
  evidence.screenshots.push(file);
}
async function step(name, action) {
  const started = Date.now();
  try {
    await action();
    evidence.steps.push({ name, status: 'passed', durationMs: Date.now() - started });
    console.log(`PASS ${name}`);
  } catch (error) {
    evidence.steps.push({ name, status: 'failed', durationMs: Date.now() - started, error: safeError(error) });
    throw error;
  } finally {
    fs.writeFileSync(path.join(output, 'accounts-results.json'), JSON.stringify(evidence, null, 2));
  }
}
async function createUser(page, username, role, active) {
  await go(page, '/users/');
  await page.getByRole('link', { name: 'Buat Akun', exact: true }).click();
  await page.getByLabel(/^Username:?$/).fill(username);
  await page.getByLabel(/^Peran:?$/).selectOption(role);
  await page.getByLabel(/^Akun aktif:?$/).setChecked(active);
  await page.getByLabel(/^Password awal:?$/).fill(passwordA);
  await page.getByLabel(/^Ulangi password awal:?$/).fill(passwordA);
  await checkPasswordToggle(page, 'initial_password', 'password awal');
  await checkPasswordToggle(page, 'confirm_password', 'konfirmasi password');
  await submit(page, 'Buat Akun');
  assert.match(new URL(page.url()).pathname, /^\/users\/\d+\/edit\/$/);
  assert.equal(await page.getByLabel(/^Username:?$/).inputValue(), username);
  assert.equal(await page.getByLabel(/^Peran:?$/).inputValue(), role);
  assert.equal(await page.getByLabel(/^Akun aktif:?$/).isChecked(), active);
  return new URL(page.url()).pathname;
}
async function resetPassword(page, editRoute, password, self = false) {
  await go(page, editRoute);
  await page.getByRole('link', { name: 'Reset Password', exact: true }).click();
  await page.getByLabel(/^Password baru:?$/).fill(password);
  await page.getByLabel(/^Ulangi password baru:?$/).fill(password);
  await checkPasswordToggle(page, 'new_password', 'password baru');
  await submit(page, 'Reset Password');
  assert.equal(new URL(page.url()).pathname, self ? '/login/' : editRoute);
}

(async () => {
  try {
    browser = await chromium.launch({ channel: 'chrome', headless: true });
    const adminPage = await newPage();
    const memberPage = await newPage();
    const loginProbe = await newPage();
    const selfPage = await newPage();
    let memberRoute;
    let secondaryRoute;
    let vendorRoute;
    await step('Admin login; cancel logout then confirm logout; protected home redirects', async () => {
      await login(adminPage, 'demo_admin', process.env.E2E_PASSWORD);
      await logout(adminPage, true);
    });
    await step('Same browser context logs into requester role after logout, then returns to admin', async () => {
      await login(adminPage, 'demo_pemohon', process.env.E2E_PASSWORD);
      assert.equal((await adminPage.locator('.topbar span').innerText()).trim(), 'Pemohon');
      assert.equal(await adminPage.getByRole('link', { name: 'Kelola Akun', exact: true }).count(), 0);
      await logout(adminPage);
      await login(adminPage, 'demo_admin', process.env.E2E_PASSWORD);
    });
    await step('Create own inactive requester and read back account fields', async () => {
      memberRoute = await createUser(adminPage, member, 'REQUESTER', false);
      await go(adminPage, memberRoute);
      assert.equal(await adminPage.getByLabel(/^Akun aktif:?$/).isChecked(), false);
      await shot(adminPage, '01-member-inactive');
    });
    await step('Inactive account login is rejected', async () => {
      await login(loginProbe, member, passwordA, false);
      await shot(loginProbe, '02-inactive-login-rejected');
    });
    await step('Reactivate account, read back state, and login successfully', async () => {
      await go(adminPage, memberRoute);
      await adminPage.getByLabel(/^Akun aktif:?$/).check();
      await submit(adminPage, 'Simpan Perubahan');
      await go(adminPage, memberRoute);
      assert.equal(await adminPage.getByLabel(/^Akun aktif:?$/).isChecked(), true);
      await login(memberPage, member, passwordA);
      assert.equal((await memberPage.locator('.topbar span').innerText()).trim(), 'Pemohon');
    });
    await step('Change own requester to procurement and verify existing-session role access', async () => {
      await go(adminPage, memberRoute);
      await adminPage.getByLabel(/^Peran:?$/).selectOption('PROCUREMENT');
      await submit(adminPage, 'Simpan Perubahan');
      await go(adminPage, memberRoute);
      assert.equal(await adminPage.getByLabel(/^Peran:?$/).inputValue(), 'PROCUREMENT');
      await go(memberPage, '/');
      assert.equal((await memberPage.locator('.topbar span').innerText()).trim(), 'Procurement');
      await memberPage.getByRole('link', { name: 'Kelola Vendor', exact: true }).click();
      assert.equal(new URL(memberPage.url()).pathname, '/vendors/');
      await shot(memberPage, '03-role-change-current-session');
    });
    await step('Admin resets member password; active old session is revoked', async () => {
      await resetPassword(adminPage, memberRoute, passwordB);
      await go(memberPage, '/');
      assert.equal(new URL(memberPage.url()).pathname, '/login/');
      assert.equal(await memberPage.locator('.account-name').count(), 0);
      await shot(memberPage, '04-old-session-revoked');
    });
    await step('Old member password fails and new password succeeds', async () => {
      await login(loginProbe, member, passwordA, false);
      await login(memberPage, member, passwordB);
      assert.equal((await memberPage.locator('.topbar span').innerText()).trim(), 'Procurement');
      await shot(memberPage, '05-new-password-login');
    });
    await step('Create own secondary admin and login', async () => {
      secondaryRoute = await createUser(adminPage, secondary, 'ADMIN', true);
      await login(selfPage, secondary, passwordA);
      assert.equal((await selfPage.locator('.topbar span').innerText()).trim(), 'Admin');
    });
    await step('Secondary admin self-reset logs current session out', async () => {
      await resetPassword(selfPage, secondaryRoute, passwordC, true);
      await go(selfPage, '/users/');
      assert.equal(new URL(selfPage.url()).pathname, '/login/');
      await shot(selfPage, '06-self-reset-logout');
    });
    await step('Self-reset old password fails; new password login succeeds', async () => {
      await login(loginProbe, secondary, passwordA, false);
      await login(selfPage, secondary, passwordC);
      assert.equal((await selfPage.locator('.topbar span').innerText()).trim(), 'Admin');
    });
    await step('Create own vendor and read back persisted active fields', async () => {
      await go(adminPage, '/vendors/');
      await adminPage.getByRole('link', { name: 'Tambah Vendor', exact: true }).click();
      await adminPage.getByLabel(/^Nama vendor:?$/).fill(vendor);
      await adminPage.getByLabel(/^Kontak:?$/).fill(`synthetic-${suffix}@example.invalid`);
      await adminPage.getByLabel(/^Vendor aktif:?$/).check();
      await submit(adminPage, 'Simpan Vendor');
      await adminPage.getByRole('link', { name: vendor, exact: true }).click();
      vendorRoute = new URL(adminPage.url()).pathname;
      assert.equal(await adminPage.getByLabel(/^Nama vendor:?$/).inputValue(), vendor);
      assert.equal(await adminPage.getByLabel(/^Kontak:?$/).inputValue(), `synthetic-${suffix}@example.invalid`);
      assert.equal(await adminPage.getByLabel(/^Vendor aktif:?$/).isChecked(), true);
    });
    await step('Edit own vendor name/contact and read back list plus form', async () => {
      await adminPage.getByLabel(/^Nama vendor:?$/).fill(`${vendor} Edited`);
      await adminPage.getByLabel(/^Kontak:?$/).fill(`edited-${suffix}@example.invalid`);
      await submit(adminPage, 'Simpan Vendor');
      const row = adminPage.locator('main li').filter({ has: adminPage.getByRole('link', { name: `${vendor} Edited`, exact: true }) });
      assert.match(await row.innerText(), /Aktif/);
      await adminPage.getByRole('link', { name: `${vendor} Edited`, exact: true }).click();
      assert.equal(new URL(adminPage.url()).pathname, vendorRoute);
      assert.equal(await adminPage.getByLabel(/^Kontak:?$/).inputValue(), `edited-${suffix}@example.invalid`);
    });
    await step('Deactivate own vendor and read back nonactive state in list and fresh form', async () => {
      await adminPage.getByLabel(/^Vendor aktif:?$/).uncheck();
      await submit(adminPage, 'Simpan Vendor');
      const row = adminPage.locator('main li').filter({ has: adminPage.getByRole('link', { name: `${vendor} Edited`, exact: true }) });
      assert.match(await row.innerText(), /Nonaktif/);
      await shot(adminPage, '07-vendor-list-nonactive');
      await adminPage.getByRole('link', { name: `${vendor} Edited`, exact: true }).click();
      await go(adminPage, vendorRoute);
      assert.equal(await adminPage.getByLabel(/^Vendor aktif:?$/).isChecked(), false);
      assert.equal(await adminPage.getByLabel(/^Nama vendor:?$/).inputValue(), `${vendor} Edited`);
      assert.equal(await adminPage.getByLabel(/^Kontak:?$/).inputValue(), `edited-${suffix}@example.invalid`);
      await shot(adminPage, '08-vendor-persisted-nonactive');
    });
    await step('No browser JavaScript runtime errors across tested contexts', async () => assert.deepEqual(evidence.runtimeErrors, []));
    evidence.status = 'passed';
  } catch (error) {
    evidence.status = 'failed';
    evidence.error = safeError(error);
    console.error(safeError(error));
    if (currentPage && !currentPage.isClosed()) {
      await currentPage.locator('input[type=password]').fill('').catch(() => {});
      await shot(currentPage, 'failure').catch(() => {});
    }
    process.exitCode = 1;
  } finally {
    evidence.finishedAt = new Date().toISOString();
    fs.writeFileSync(path.join(output, 'accounts-results.json'), JSON.stringify(evidence, null, 2));
    for (const context of contexts) await context.close().catch(() => {});
    if (browser) await browser.close();
    console.log(JSON.stringify({ status: evidence.status, passed: evidence.steps.filter(step => step.status === 'passed').length, failed: evidence.steps.filter(step => step.status === 'failed').length, output }));
  }
})();


