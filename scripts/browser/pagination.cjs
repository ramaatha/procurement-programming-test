// filepath: scripts/browser/pagination.cjs
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = new URL(process.env.E2E_BASE_URL);
if (base.protocol !== 'http:' || !['127.0.0.1','localhost','[::1]'].includes(base.hostname) || !base.port || ['80','443'].includes(base.port) || base.username || base.password || base.pathname !== '/' || base.search || base.hash) throw new Error('Require explicit loopback HTTP test origin on a nonstandard port.');
for (const key of ['E2E_PASSWORD','E2E_OUTPUT_DIR','E2E_FIXTURE_MANIFEST']) if (!process.env[key]) throw new Error(`${key} is required.`);
const fixture = JSON.parse(fs.readFileSync(process.env.E2E_FIXTURE_MANIFEST,'utf8'));
if (!fixture.prefix.startsWith('E2E PAGE ') || fixture.orders.length !== 26 || fixture.requestIds.length !== 26) throw new Error('Require the synthetic pagination fixture manifest.');
assert.equal(process.env.E2E_ALLOW_MUTATIONS, 'isolated-synthetic', 'Explicit synthetic mutation opt-in required');
if (!process.env.E2E_DATABASE || !fs.existsSync(path.join(path.dirname(process.env.E2E_DATABASE), '.e2e-isolated'))) {
  throw new Error('Isolated database marker required');
}
const output = path.resolve(process.env.E2E_OUTPUT_DIR);
fs.mkdirSync(output,{recursive:true});
const evidence = {suite:'tracking-filter-pagination',startedAt:new Date().toISOString(),baseUrl:base.origin,fixture:{prefix:fixture.prefix,source:fixture.fixture},checks:[],runtimeErrors:[],screenshots:[]};
let browser,page;
const safeError = error => String(error.stack || error).split(process.env.E2E_PASSWORD).join('[REDACTED]');
async function go(route) {
  const response = await page.goto(new URL(route,base).href);
  assert.equal(response.status(),200,`GET failed: ${route}`);
}
async function clickLink(locator) {
  const href = await locator.getAttribute('href');
  const target = new URL(href,page.url());
  assert.equal(target.origin,base.origin);
  await Promise.all([page.waitForURL(target.href),locator.click()]);
  await page.waitForLoadState('networkidle');
  return target;
}
async function applyFilters(route,q,kind,stage) {
  await go(route);
  await page.getByLabel(/^Cari Nomor Atau Judul:?\s*$/).fill(q);
  await page.getByLabel(/^Jenis Pengadaan:?\s*$/).selectOption(kind);
  await page.getByLabel(/^Tahap Pengadaan:?\s*$/).selectOption(stage);
  await Promise.all([page.waitForURL(url => url.searchParams.get('q') === q),page.getByRole('button',{name:'Terapkan Pencarian Dan Filter',exact:true}).click()]);
  await page.waitForLoadState('networkidle');
  for (const [key,value] of Object.entries({q,kind,stage})) assert.equal(new URL(page.url()).searchParams.get(key),value);
}
const rowLinks = () => page.locator('main h2 a');
const hrefs = async () => rowLinks().evaluateAll(nodes => nodes.map(node=>node.getAttribute('href')));
async function screenshot(name) {
  const file = `${name}.png`;
  await page.screenshot({path:path.join(output,file),fullPage:true});
  evidence.screenshots.push(file);
}
async function tracking(route,ids) {
  await applyFilters(route,fixture.trackingQuery,'GOODS','ISSUED');
  const first = await hrefs();
  assert.equal(first.length,25);
  const nav = page.getByRole('navigation',{name:'Halaman Daftar',exact:true});
  const nextUrl = await clickLink(nav.getByRole('link',{name:'Berikutnya',exact:true}));
  for (const [key,value] of Object.entries({q:fixture.trackingQuery,kind:'GOODS',stage:'ISSUED',page:'2'})) assert.equal(nextUrl.searchParams.get(key),value);
  const second = await hrefs();
  assert.equal(second.length,1);
  assert(first.every(href=>!second.includes(href)));
  const actual = [...first,...second].map(href=>href.split('/').filter(Boolean).at(-1)).sort();
  assert.deepEqual(actual,[...ids].sort());
  await screenshot(route === '/requests/' ? 'requests-page2' : 'orders-page2');
  await clickLink(page.getByRole('navigation',{name:'Halaman Daftar',exact:true}).getByRole('link',{name:'Sebelumnya',exact:true}));
  assert.deepEqual(await hrefs(),first);
  await clickLink(page.getByRole('link',{name:'Hapus Filter',exact:true}));
  assert.equal(new URL(page.url()).pathname,route);
  assert.equal(new URL(page.url()).search,'');
  for (const name of ['q','kind','stage']) assert.equal(await page.locator(`[name="${name}"]`).inputValue(),'');
  evidence.checks.push({case:`${route} combined filters, next, previous, reset`,result:'PASS',pageCounts:[25,1],uniqueRows:26,query:fixture.trackingQuery});
}
function quoteRefs(all,marker) { return all.map(text=>text.slice(text.indexOf(marker)).trim()).filter(text=>text.startsWith(marker)); }
async function quotePages() {
  await go(fixture.quotationPath+'?page=1&history_page=1');
  const first = await page.locator('main h3').allTextContents();
  assert.equal(quoteRefs(first,fixture.prefix+' ACTIVE').length,25);
  assert.equal(quoteRefs(first,fixture.prefix+' HIST').length,25);
  const active = () => page.getByRole('navigation',{name:'Halaman Penawaran',exact:true});
  const history = () => page.getByRole('navigation',{name:'Halaman Riwayat Penawaran',exact:true});
  let url = await clickLink(active().getByRole('link',{name:'Berikutnya',exact:true}));
  assert.equal(url.searchParams.get('page'),'2'); assert.equal(url.searchParams.get('history_page'),'1');
  let current = await page.locator('main h3').allTextContents();
  assert.equal(quoteRefs(current,fixture.prefix+' ACTIVE').length,1);
  assert.equal(quoteRefs(current,fixture.prefix+' HIST').length,25);
  const activeLast = quoteRefs(current,fixture.prefix+' ACTIVE');
  url = await clickLink(history().getByRole('link',{name:'Riwayat Berikutnya',exact:true}));
  assert.equal(url.searchParams.get('page'),'2'); assert.equal(url.searchParams.get('history_page'),'2');
  current = await page.locator('main h3').allTextContents();
  assert.deepEqual(quoteRefs(current,fixture.prefix+' ACTIVE'),activeLast);
  assert.equal(quoteRefs(current,fixture.prefix+' HIST').length,1);
  await screenshot('quotes-both-page2');
  url = await clickLink(active().getByRole('link',{name:'Sebelumnya',exact:true}));
  assert.equal(url.searchParams.get('page'),'1'); assert.equal(url.searchParams.get('history_page'),'2');
  current = await page.locator('main h3').allTextContents();
  assert.equal(quoteRefs(current,fixture.prefix+' ACTIVE').length,25);
  assert.equal(quoteRefs(current,fixture.prefix+' HIST').length,1);
  await clickLink(history().getByRole('link',{name:'Riwayat Sebelumnya',exact:true}));
  assert.equal(new URL(page.url()).searchParams.get('page'),'1');
  assert.equal(new URL(page.url()).searchParams.get('history_page'),'1');
  evidence.checks.push({case:'dual quotation pagination preserves the other page parameter',result:'PASS',path:fixture.quotationPath,activeCount:26,historicalCount:26});
}
(async()=>{
  try {
    browser = await chromium.launch({channel:process.env.E2E_BROWSER_CHANNEL || 'chrome',headless:true});
    const context = await browser.newContext({viewport:{width:1440,height:1000}});
    await context.route('**/*',route=>new URL(route.request().url()).origin === base.origin ? route.continue() : route.abort('blockedbyclient'));
    page = await context.newPage();
    page.on('pageerror',error=>evidence.runtimeErrors.push(safeError(error)));
    await go('/login/');
    await page.getByLabel(/^Username:?\s*$/).fill(process.env.E2E_USERNAME || 'demo_procurement');
    await page.getByLabel(/^Password:?\s*$/).fill(process.env.E2E_PASSWORD);
    const loginResponse = page.waitForResponse(response=>response.request().method()==='POST' && new URL(response.url()).pathname==='/login/');
    await page.getByRole('button',{name:'Masuk',exact:true}).click();
    assert.equal((await loginResponse).status(),303);
    await page.waitForURL(base.origin+'/');
    await tracking('/requests/',fixture.requestIds);
    await tracking('/orders/',fixture.orders.map(order=>order.id));
    for (const query of [fixture.orders[0].number,fixture.orders[0].requestNumber]) {
      await applyFilters('/orders/',query,'GOODS','ISSUED');
      assert.deepEqual(await hrefs(),[`/orders/${fixture.orders[0].id}/`]);
      evidence.checks.push({case:'PO search by PO or source PR number',result:'PASS',query});
    }
    await quotePages();
    assert.deepEqual(evidence.runtimeErrors,[]);
    evidence.result='PASS';
  } catch(error) {
    evidence.result='FAIL'; evidence.error=safeError(error);
    if(page) await screenshot('failure').catch(()=>{});
    process.exitCode=1;
  } finally {
    evidence.completedAt=new Date().toISOString();
    fs.writeFileSync(path.join(output,'pagination-results.json'),JSON.stringify(evidence,null,2));
    if(browser) await browser.close();
    console.log(JSON.stringify({result:evidence.result,checks:evidence.checks.length,output,error:evidence.error}));
  }
})();