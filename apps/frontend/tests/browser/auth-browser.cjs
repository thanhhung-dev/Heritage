// Test the actual form -> fetch -> auth API flow on isolated loopback services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.AUTH_BROWSER_FRONTEND || 'http://127.0.0.1:3006';
const api = process.env.AUTH_BROWSER_API || 'http://127.0.0.1:18928';
const cdp = process.env.AUTH_BROWSER_CDP || 'http://127.0.0.1:9225';
for (const url of [base, api, cdp]) assert.equal(new URL(url).hostname, '127.0.0.1');
const output = path.resolve(process.env.AUTH_BROWSER_ARTIFACTS || '.next/auth-browser-review');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  fs.mkdirSync(output, { recursive: true });
  assert.equal((await (await fetch(api + '/__reset', { method: 'POST' })).json()).reset, true);
  const info = await (await fetch(cdp + '/json/version')).json();
  const ws = new WebSocket(info.webSocketDebuggerUrl);
  await new Promise(resolve => ws.addEventListener('open', resolve, { once: true }));
  let sequence = 0, targetId, sessionId;
  const pending = new Map(), exceptions = [];
  const send = (method, params = {}, session = sessionId) => new Promise((resolve, reject) => {
    const id = ++sequence; pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params, ...(session ? { sessionId: session } : {}) }));
  });
  ws.addEventListener('message', async event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const call = pending.get(message.id); pending.delete(message.id);
      if (message.error) call.reject(new Error(JSON.stringify(message.error))); else call.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
    else if (message.method === 'Fetch.requestPaused') {
      const { requestId, request } = message.params;
      const target = new URL(request.url);
      if (target.origin !== api) {
        await send('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' });
        exceptions.push('Blocked auth request to unexpected API origin: ' + target.origin);
      } else await send('Fetch.continueRequest', { requestId });
    }
  });
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  async function wait(expression) {
    const until = Date.now() + 60000;
    while (Date.now() < until) { if (await evaluate(expression)) return; await pause(150); }
    throw new Error('Browser readiness deadline: ' + expression);
  }
  async function page(route) {
    await send('Page.navigate', { url: base + route });
    // SSR markup can be visible before React has installed form handlers.
    await wait(`(()=>{const form=document.querySelector('form');return !!form&&Object.keys(form).some(key=>key.startsWith('__reactProps$')&&typeof form[key]?.onSubmit==='function')})()`);
    assert.equal(await evaluate(`document.querySelector('form').method`), 'post');
  }
  async function fill(values) {
    await evaluate(`(()=>{for(const[name,value]of Object.entries(${JSON.stringify(values)})){const input=document.querySelector('input[name='+name+']');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}));}})()`);
    await pause(50);
  }
  const submit = (twice = false) => evaluate(`document.querySelector('form').requestSubmit();${twice ? "document.querySelector('form').requestSubmit();" : ''}`);
  const mode = name => fetch(api + '/__mode/' + name, { method: 'POST' });
  const stats = async () => (await fetch(api + '/__stats')).json();
  async function shot(name) {
    await pause(200);
    const result = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    fs.writeFileSync(path.join(output, name + '.png'), Buffer.from(result.data, 'base64'));
  }
  const hasError = text => wait(`document.querySelector('[role=alert]')?.textContent.includes(${JSON.stringify(text)}) && document.querySelector('form').getAttribute('aria-busy')==='false'`);
  try {
    ({ targetId } = await send('Target.createTarget', { url: 'about:blank' }));
    ({ sessionId } = await send('Target.attachToTarget', { targetId, flatten: true }));
    await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/auth/*', requestStage: 'Request' }] });
    await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
    await mode('normal');
    await page('/sign-up?next=%2Ffaq');
    await evaluate(`localStorage.removeItem('heritage_access_token');localStorage.removeItem('heritage_user')`);
    await fill({ email: 'browser@example.com', username: 'browser_test', password: '1234567' });
    const initial = await stats();
    await submit(); await wait(`document.querySelector('input[name=password]').getAttribute('aria-invalid')==='true'`);
    assert.ok(await evaluate(`document.body.innerText.includes('at least 8 characters')`));
    assert.equal((await stats()).register, initial.register);
    await shot('signup-seven-character-password');
    console.log('PASS: seven-character password has an inline error and sends no request');

    await fill({ password: 'BrowserPass123' });
    await mode('validation'); await submit(); await hasError('Password rejected by server validation');
    assert.equal(await evaluate(`document.activeElement?.name`), 'password');
    assert.equal(await evaluate(`document.body.innerText.includes('[object Object]')`), false);
    assert.equal(await evaluate(`document.querySelectorAll('.ant-message-notice').length`), 0);
    await shot('signup-server-validation');
    await mode('unavailable'); await submit(); await hasError('temporarily unavailable');
    await mode('normal');
    const before = await stats(); await submit(true);
    await wait(`location.pathname==='/sign-in' && !!document.querySelector('[role=status]')`);
    assert.equal((await stats()).register, before.register + 1);
    assert.ok(await evaluate(`document.querySelector('[role=status]').textContent.includes('Account created successfully')`));
    assert.equal(await evaluate(`!!localStorage.getItem('heritage_access_token')`), false);
    await shot('registration-success');
    console.log('PASS: server field errors, service error, one submission and registration success');

    await fill({ email: 'browser@example.com', password: 'wrong' });
    await submit(); await hasError('Incorrect email or password');
    await shot('signin-bad-credentials');
    await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await submit(); await hasError('Cannot connect');
    await send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await fill({ password: 'BrowserPass123' }); await submit(true);
    await wait(`location.pathname==='/faq'`);
    assert.equal(await evaluate(`JSON.parse(localStorage.getItem('heritage_user')).role`), 'user');
    assert.equal(await evaluate(`!!localStorage.getItem('heritage_access_token')`), true);
    console.log('PASS: bad credentials, network failure, real login and safe return destination');

    await page('/sign-up');
    await fill({ email: 'BROWSER@example.com', username: 'other_browser', password: 'BrowserPass123' });
    await submit(); await hasError('email is already in use'); await shot('signup-duplicate-email');
    await evaluate(`localStorage.removeItem('heritage_access_token');localStorage.removeItem('heritage_user')`);
    await page('/sign-in?next=https%3A%2F%2Fevil.invalid');
    await fill({ email: 'browser@example.com', password: 'BrowserPass123' });
    await mode('malformed'); await submit(); await hasError('invalid sign-in response');
    assert.equal(await evaluate(`!!localStorage.getItem('heritage_access_token')`), false);
    await mode('normal');

    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await page('/sign-up'); await fill({ email: 'mobile@example.com', username: 'mobile_user', password: '1234567' }); await submit();
    await wait(`document.querySelector('input[name=password]').getAttribute('aria-invalid')==='true'`);
    assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'));
    await shot('signup-mobile-error');
    await page('/sign-in'); await fill({ email: 'browser@example.com', password: 'bad' }); await submit(); await hasError('Incorrect email or password');
    assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'));
    await shot('signin-mobile-error');
    assert.deepEqual(exceptions, []);
    console.log('PASS: duplicate identity, malformed response, mobile forms and no JavaScript exceptions');
    console.log('Screenshots: ' + output);
  } catch (error) { await shot('failure'); throw error; }
  finally {
    await mode('normal');
    if (targetId) await send('Target.closeTarget', { targetId });
    ws.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; setTimeout(() => process.exit(1), 500); });
