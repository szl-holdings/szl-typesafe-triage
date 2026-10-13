/* Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
 * Local rendered fixtures of the actual source-bound local/public Python apps.
 * Real deterministic decisions use synthetic inputs only after explicit clicks.
 * Recovery cases are labelled intercepted fixtures. No provider or model runs.
 * These unsigned observations do not qualify publication or live readiness. */
const assert = require('node:assert/strict');
const { spawn, execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const out = path.resolve(process.env.TRIAGE_QA_OUT || path.join(root, 'reports/native-frontend'));
const python = process.env.PYTHON || 'python3';
const pythonEnv = { PATH: process.env.PATH, PYTHONPATH: path.join(root, 'src'), PYTHONDONTWRITEBYTECODE: '1' };
const hash = data => createHash('sha256').update(data).digest('hex');
const sourceRevision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8', timeout: 5000 }).trim();
if (process.env.SOURCE_REVISION) assert.equal(process.env.SOURCE_REVISION, sourceRevision, 'Declared source is the exact checkout');
const native = JSON.parse(execFileSync(python, ['-B', '-c', 'import json;from szl_triage.native_assets import TOKEN_CSS,ORBIT_SVG;print(json.dumps({"tokens":TOKEN_CSS,"orbit":ORBIT_SVG}))'], { cwd: root, env: pythonEnv, encoding: 'utf8', timeout: 5000 }));
const checks = [], observations = [];
const check = (name, pass, detail = null) => checks.push({ name, pass: Boolean(pass), detail });

async function inspect(page, forced = false) {
  return page.evaluate(({ forced }) => {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    function rgba(value) {
      if (!CSS.supports('color', value)) throw new Error('Invalid computed color');
      ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = value; ctx.fillRect(0, 0, 1, 1);
      const c = [...ctx.getImageData(0, 0, 1, 1).data]; c[3] /= 255; return c;
    }
    function over(a, b) { const alpha = a[3] + b[3] * (1 - a[3]); return alpha ? [0, 1, 2].map(i => (a[i] * a[3] + b[i] * b[3] * (1 - a[3])) / alpha).concat(alpha) : [0, 0, 0, 0]; }
    function luminance(c) { return c.slice(0, 3).map(x => x / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4).reduce((n, x, i) => n + x * [.2126, .7152, .0722][i], 0); }
    function ratio(a, b) { const x = luminance(a), y = luminance(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); }
    const cache = new WeakMap();
    function backdrop(el) {
      if (!el) return [[255, 255, 255, 1]];
      if (cache.has(el)) return cache.get(el);
      const s = getComputedStyle(el); let values = backdrop(el.parentElement).map(c => over(rgba(s.backgroundColor), c));
      // This source-owned card has an opaque surface layer over a border-only
      // foil gradient. Include the full atmosphere range behind its text; the
      // outer border gradient cannot be used as the text's background.
      if (el.classList.contains('method')) {
        const ground = rgba(s.getPropertyValue('--surface'));
        values = [ground, over(rgba(s.getPropertyValue('--hero-atmosphere')), ground)];
      }
      cache.set(el, values); return values;
    }
    const visible = el => el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) && el.getBoundingClientRect().height > 0;
    const failures = [], overflow = [], targets = [], unlabeled = []; let pairs = 0;
    function textContrast(el, label) {
      if (forced || el.closest('[disabled]')) return;
      const s = getComputedStyle(el), foreground = rgba(s.color);
      const measured = Math.min(...backdrop(el).map(c => ratio(over(foreground, c), c)));
      const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.6667 && parseFloat(s.fontWeight) >= 700);
      const minimum = large ? 3 : 4.5; pairs++;
      if (measured < minimum || Number(s.opacity) !== 1) failures.push({ text: label.slice(0, 90), ratio: +measured.toFixed(3), minimum, opacity: s.opacity });
    }
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let item; (item = walker.nextNode());) {
      const label = item.textContent.trim(), el = item.parentElement;
      if (!label || !el || el.closest('script,style,svg') || !visible(el)) continue;
      const range = document.createRange(); range.selectNodeContents(item); const r = range.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if ((r.left < -1 || r.right > innerWidth + 1) && !el.closest('.skip')) overflow.push({ text: label.slice(0, 90), left: r.left, right: r.right });
      textContrast(el, label);
    }
    for (const el of document.querySelectorAll('button,textarea,summary,nav a')) {
      if (!visible(el) || el.disabled) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 43.9 || r.height < 43.9) targets.push({ text: (el.textContent || el.getAttribute('aria-label') || el.id).trim().slice(0, 70), width: r.width, height: r.height });
      if (!el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby') && !el.labels?.length && !el.textContent.trim()) unlabeled.push(el.tagName);
      if (el.matches('textarea')) textContrast(el, el.value);
    }
    return { viewport: innerWidth, documentWidth: document.documentElement.scrollWidth, h1: document.querySelectorAll('h1').length, pairs, failures, overflow, targets, unlabeled, animations: document.getAnimations().filter(a => a.playState === 'running').length };
  }, { forced });
}

(async () => {
  fs.mkdirSync(out, { recursive: true });
  let browser, child, origins, fixtureExit;
  const fixtureErrors = [];
  function record(name, data) {
    observations.push({ name, ...data });
    check(name + ': reflow, contrast, targets, labels and motion', data.documentWidth <= data.viewport + 1 && data.h1 === 1 && !data.failures.length && !data.overflow.length && !data.targets.length && !data.unlabeled.length && !data.animations, data);
  }
  async function open(index, options = {}, scenario = 'actual-source') {
    const origin = origins[index];
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: 'dark', reducedMotion: 'reduce', ...options });
    const page = await context.newPage(), errors = [], requests = [], denied = [], violations = [];
    let permittedPosts = 0;
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => { window.__nativeCspViolations = []; document.addEventListener('securitypolicyviolation', e => window.__nativeCspViolations.push(e.violatedDirective)); });
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      requests.push({ method: request.method(), path: url.pathname });
      if (url.origin !== origin || !['/', '/readyz', '/healthz', '/v1/decide', '/favicon.ico'].includes(url.pathname)) { denied.push(request.method() + ' ' + url.origin + url.pathname); return route.abort(); }
      if (request.method() === 'POST') {
        if (url.pathname !== '/v1/decide' || permittedPosts < 1) { denied.push('Unrequested POST ' + url.pathname); return route.abort(); }
        permittedPosts--;
      } else if (request.method() !== 'GET') { denied.push(request.method() + ' ' + url.pathname); return route.abort(); }
      if (url.pathname === '/readyz' && scenario === 'missing-identity') return route.fulfill({ status: 503, contentType: 'application/json', body: '{"status":"UNAVAILABLE"}' });
      if (url.pathname === '/readyz' && scenario === 'invalid-identity') { const response = await route.fetch(); const body = await response.json(); body.model_loaded = true; return route.fulfill({ response, json: body }); }
      if (url.pathname === '/v1/decide') {
        if (scenario === 'rejected') return route.fulfill({ status: 403, contentType: 'application/json', body: '{"error":"EXPLICIT_REJECTION_FIXTURE"}' });
        if (scenario === 'malformed') return route.fulfill({ status: 200, contentType: 'application/json', body: 'Not a JSON response' });
        if (scenario === 'oversize') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ fixture: 'x'.repeat(270000) }) });
        if (scenario === 'timeout') { await new Promise(resolve => setTimeout(resolve, 8500)); try { return await route.abort(); } catch { return; } }
        if (['unknown-state', 'untrusted-text', 'zero'].includes(scenario)) {
          const response = await route.fetch(); const body = await response.json();
          if (scenario === 'unknown-state') body.decision.state = 'UNKNOWN_FIXTURE';
          if (scenario === 'untrusted-text') { body.decision.rationale = ['<img src=x onerror="window.__unexpectedMarkup=true">']; body.decision.evidence = ['<script>window.__unexpectedMarkup=true</script>']; }
          if (scenario === 'zero') body.decision.lambda = 0;
          return route.fulfill({ response, json: body });
        }
      }
      return route.continue();
    });
    const response = await page.goto(origin + '/', { waitUntil: 'networkidle', timeout: 15000 });
    const raw = await response.text(), csp = response.headers()['content-security-policy'];
    check((index ? 'public' : 'local') + ': exact inlined native bytes and nonce CSP', response.status() === 200 && raw.includes(native.orbit) && raw.includes(native.tokens) && /script-src 'nonce-[A-Za-z0-9_-]+'/.test(csp) && !/unsafe-inline|unsafe-eval|img-src|https:/.test(csp) && !raw.includes('__NONCE__'));
    if (options.javaScriptEnabled !== false) await page.locator('#submit').isEnabled();
    return { context, page, errors, requests, denied, violations, scenario, allowPosts: n => { permittedPosts += n; }, remainingPosts: () => permittedPosts };
  }
  async function traffic(name, current, posts = 0) {
    const csp = await current.page.evaluate(() => window.__nativeCspViolations || []);
    check(name + ': no page/CSP errors, external traffic or unrequested operations', !current.errors.length && !current.denied.length && !csp.length && current.remainingPosts() === 0 && current.requests.filter(r => r.method === 'POST').length === posts, { errors: current.errors, denied: current.denied, csp, posts: current.requests.filter(r => r.method === 'POST'), scenario: current.scenario });
  }
  async function run(current, input) {
    if (input !== undefined) await current.page.locator('#text').fill(input);
    current.allowPosts(1);
    await current.page.locator('#submit').click();
    await current.page.waitForFunction(() => document.querySelector('#triage-form').getAttribute('aria-busy') === 'false' && document.querySelector('#status').textContent !== 'Ready for your input.', { timeout: 12000 });
  }
  try {
    child = spawn(python, ['-B', path.join(root, 'scripts/native_frontend_fixture.py'), '--out', out], { cwd: root, env: pythonEnv, stdio: ['pipe', 'pipe', 'pipe'] });
    fixtureExit = new Promise(resolve => child.on('exit', (code, signal) => resolve({ code, signal })));
    child.stderr.on('data', data => fixtureErrors.push(data.toString()));
    origins = await new Promise((resolve, reject) => {
      let buffer = ''; const timer = setTimeout(() => reject(new Error('Local fixture startup timed out')), 10000);
      child.on('error', reject); child.on('exit', () => { clearTimeout(timer); if (!buffer.includes('\n')) reject(new Error('Fixture stopped before startup')); });
      child.stdout.on('data', data => { buffer += data.toString(); if (buffer.includes('\n')) { clearTimeout(timer); try { resolve(JSON.parse(buffer.split('\n')[0]).origins); } catch (error) { reject(error); } } });
    });
    assert.equal(origins.length, 2); assert.ok(origins.every(origin => /^http:\/\/127\.0\.0\.1:\d+$/.test(origin)));
    browser = await chromium.launch({ headless: true, ...(process.env.TRIAGE_BROWSER ? { executablePath: process.env.TRIAGE_BROWSER } : {}), args: ['--no-sandbox', '--disable-dev-shm-usage'] });
    const widths = process.env.TRIAGE_QA_QUICK ? [1440, 320] : [2560, 1920, 1440, 1024, 768, 375, 320];
    for (const [index, name] of ['local', 'public'].entries()) {
      for (const width of widths) {
        const current = await open(index, { viewport: { width, height: 1000 } });
        for (const theme of ['dark', 'light']) {
          if (theme === 'light') await current.page.locator('#theme').click();
          await current.page.waitForFunction(() => !document.querySelector('#identity').textContent.startsWith('Loading'));
          check(name + ' source distinction ' + theme, await current.page.locator('#identity').innerText() === 'Source response received' && (index ? await current.page.locator('#source-commit').isVisible() : await current.page.locator('#source-commit').count() === 0));
          record(`${name} ${width}px ${theme}`, await inspect(current.page));
          if ([1440, 320].includes(width)) {
            await current.page.screenshot({ path: path.join(out, `${name}-${width}-${theme}.png`), fullPage: true });
            await current.page.screenshot({ path: path.join(out, `${name}-${width}-${theme}-viewport.png`) });
          }
        }
        await traffic(name + ' ' + width, current); await current.context.close();
      }
      for (const mode of [{ label: 'forced', forcedColors: 'active' }, { label: 'contrast', contrast: 'more' }, { label: 'no-js', javaScriptEnabled: false }, { label: 'print' }, { label: 'landscape', viewport: { width: 844, height: 390 } }, { label: 'initial-light', colorScheme: 'light' }]) {
        const { label, ...options } = mode;
        const current = await open(index, options);
        if (label === 'print') await current.page.emulateMedia({ media: 'print' });
        if (label === 'no-js') check(name + ': useful no-JavaScript state', await current.page.locator('noscript').isVisible() && await current.page.locator('#submit').isDisabled() && await current.page.locator('#theme').isHidden());
        record(name + ' ' + label, await inspect(current.page, label === 'forced'));
        await traffic(name + ' ' + label, current); await current.context.close();
      }
      const keyboard = await open(index, { viewport: { width: 320, height: 900 } });
      await keyboard.page.keyboard.press('Tab');
      check(name + ': skip link is first keyboard stop', await keyboard.page.locator('.skip').evaluate(el => el === document.activeElement));
      await keyboard.page.keyboard.press('Enter');
      check(name + ': skip enters the actual workspace', await keyboard.page.locator('#workspace').evaluate(el => el === document.activeElement));
      for (const [example, state, tier, label] of [['billing', 'MEASURED', 'ENGINE', 'BILLING'], ['guard', 'REVIEW', 'GUARD', 'REVIEW'], ['doctrine', 'REVIEW', 'DOCTRINE', 'REVIEW']]) {
        const before = keyboard.requests.filter(r => r.method === 'POST').length;
        await keyboard.page.locator(`[data-example="${example}"]`).focus(); await keyboard.page.keyboard.press('Enter');
        check(name + ': ' + example + ' example stays local until submit', keyboard.requests.filter(r => r.method === 'POST').length === before && await keyboard.page.locator('#text').evaluate(el => el === document.activeElement));
        await run(keyboard);
        check(name + ': real deterministic ' + example + ' response', await keyboard.page.locator('#returned-state').innerText() === state && await keyboard.page.locator('#decision-tier').innerText() === tier && await keyboard.page.locator('#decision-label').innerText() === label);
        await keyboard.page.locator('.raw-response summary').click();
        const envelope = JSON.parse(await keyboard.page.locator('#result').innerText());
        check(name + ': raw ' + example + ' state retained and unsigned', envelope.decision.state === state && envelope.authenticity === 'UNSIGNED_CONTENT_INTEGRITY_ONLY' && (!index || (envelope.model_loaded === false && envelope.disposition === 'HOLD')));
        record(name + ' ' + example + ' decision at 320px', await inspect(keyboard.page));
        if (index === 1 && example === 'guard') await keyboard.page.locator('#workspace').screenshot({ path: path.join(out, 'public-320-guard-response.png') });
        await keyboard.page.locator('.raw-response summary').click();
        const submitted = keyboard.requests.filter(r => r.method === 'POST').length;
        await keyboard.page.locator('#text').fill('A newly edited report');
        check(name + ': editing after ' + example + ' clears the previous response without submitting',
          await keyboard.page.locator('#decision').isHidden() && await keyboard.page.locator('#returned-state').isHidden()
          && await keyboard.page.locator('#empty').isVisible()
          && await keyboard.page.locator('#result').innerText() === 'Report changed. No request has been sent.'
          && await keyboard.page.locator('#status').innerText() === 'Report changed. Run triage to submit.'
          && keyboard.requests.filter(r => r.method === 'POST').length === submitted);
      }
      await keyboard.page.locator('#text').fill('   ');
      await keyboard.page.locator('#submit').click();
      check(name + ': empty input is not submitted', await keyboard.page.locator('#status').innerText() === 'Enter a report of 1–8,192 characters.');
      await traffic(name + ' keyboard and real local decisions', keyboard, 3); await keyboard.context.close();
      for (const scenario of ['missing-identity', 'invalid-identity', 'rejected', 'malformed', 'oversize', 'unknown-state', 'untrusted-text', 'zero', 'timeout']) {
        if (process.env.TRIAGE_QA_QUICK && scenario === 'timeout') continue;
        const current = await open(index, {}, scenario);
        const identityCase = scenario.endsWith('identity');
        if (identityCase) {
          await current.page.waitForFunction(() => document.querySelector('#identity').textContent.includes('unavailable'));
          check(name + ': ' + scenario + ' never invents identity', await current.page.locator('#policy-hash').innerText() === 'Unavailable' && (!index || await current.page.locator('#source-commit').isHidden()));
        } else {
          await run(current);
          const expected = scenario === 'rejected' ? 'Request rejected.' : scenario === 'unknown-state' ? 'Decision presentation unavailable.' : ['untrusted-text', 'zero'].includes(scenario) ? 'MEASURED · BILLING · ENGINE' : 'Response unavailable.';
          check(name + ': ' + scenario + ' is explicit', await current.page.locator('#status').innerText() === expected);
          if (scenario === 'zero') check(name + ': zero is preserved without truthy fallback', await current.page.locator('#decision-lambda').innerText() === '0');
          if (scenario === 'untrusted-text') check(name + ': returned text cannot become markup', await current.page.locator('#rationale').innerText() === '<img src=x onerror="window.__unexpectedMarkup=true">' && await current.page.locator('#rationale img,#evidence script').count() === 0 && await current.page.evaluate(() => window.__unexpectedMarkup !== true));
        }
        record(name + ' ' + scenario, await inspect(current.page));
        await traffic(name + ' ' + scenario, current, identityCase ? 0 : 1); await current.context.close();
      }
    }
  } catch (error) {
    check('Qualification completes', false, String(error.stack || error));
  } finally {
    if (browser) await browser.close();
    if (child && child.exitCode === null) child.stdin.end('stop\n');
    if (fixtureExit) {
      let timer;
      const ended = await Promise.race([fixtureExit, new Promise(resolve => { timer = setTimeout(() => { child.kill('SIGTERM'); resolve({ timeout: true }); }, 6000); })]);
      clearTimeout(timer); check('Local fixture closes without loading model libraries', ended.code === 0 && !fixtureErrors.length, { ...ended, errors: fixtureErrors });
    }
    const report = { schema: 'szl.triage.native-browser-observation/v1', unsigned: true, sourceRevision, dataClass: 'LOCAL_DETERMINISTIC_SOFTWARE_FIXTURES', providerMutations: 0, liveVerified: false, checks, observations };
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(report, null, 2) + '\n');
    const failed = checks.filter(c => !c.pass);
    console.log(JSON.stringify({ checks: checks.length, passed: checks.length - failed.length, failed: failed.map(c => ({ name: c.name, detail: c.detail })), report: path.join(out, 'results.json') }, null, 2));
    if (failed.length) process.exitCode = 1;
  }
})();
