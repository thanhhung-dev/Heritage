// Run against knowledge-fixture.cjs and a local Next server; no real R2 writes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.KNOWLEDGE_FRONTEND_URL || 'http://127.0.0.1:3006';
const fixture = process.env.KNOWLEDGE_FIXTURE_URL || 'http://127.0.0.1:18926';
const debug = process.env.KNOWLEDGE_CDP_URL || 'http://127.0.0.1:9225';
// Optional proxy for an already running local frontend compiled with another
// loopback fixture port. Never redirect a production API into test data.
const apiProxy = process.env.KNOWLEDGE_BROWSER_API_PROXY;
if (apiProxy) assert.equal(new URL(apiProxy).hostname, '127.0.0.1');
for (const url of [base, fixture, debug]) assert.equal(new URL(url).hostname, '127.0.0.1', 'Browser tests require loopback services');
const output = path.resolve(process.env.KNOWLEDGE_BROWSER_ARTIFACTS || '.next/knowledge-browser-review');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  fs.mkdirSync(output, { recursive: true });
  assert.equal((await (await fetch(fixture + '/__reset')).json()).reset, true, 'Wrong fixture server');
  const version = await (await fetch(debug + '/json/version')).json();
  const ws = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise(resolve => ws.addEventListener('open', resolve, { once: true }));
  let sequence = 0, targetId, sessionId, cancelledInterceptions = 0;
  const pending = new Map(), transfers = [], errors = [];
  function send(method, params = {}, session) {
    return new Promise((resolve, reject) => {
      const id = ++sequence; pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params, ...(session ? { sessionId: session } : {}) }));
    });
  }
  ws.addEventListener('message', async event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const call = pending.get(message.id); pending.delete(message.id);
      if (message.error) call.reject(new Error(JSON.stringify(message.error))); else call.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    else if (message.method === 'Fetch.requestPaused') {
      try {
        const { requestId, request } = message.params;
        if (apiProxy && request.url.startsWith(apiProxy + '/')) {
          const local = new URL(request.url);
          const response = await fetch(fixture + local.pathname + local.search, {
            method: request.method, headers: { 'Content-Type': 'application/json' },
            ...(request.postData ? { body: request.postData } : {}),
          });
          await send('Fetch.fulfillRequest', { requestId, responseCode: response.status,
            body: Buffer.from(await response.arrayBuffer()).toString('base64'), responseHeaders: [
              { name: 'Content-Type', value: 'application/json' },
              { name: 'Access-Control-Allow-Origin', value: base },
              { name: 'Access-Control-Allow-Methods', value: 'GET,POST,DELETE,OPTIONS' },
              { name: 'Access-Control-Allow-Headers', value: 'Content-Type,Authorization,X-Correlation-ID' },
            ] }, sessionId);
          return;
        }
        const headers = Object.fromEntries(Object.entries(request.headers).map(([key, value]) => [key.toLowerCase(), value]));
        assert.equal(new URL(request.url).hostname, 'r2.example.invalid');
        assert.equal(headers.authorization, undefined);
        if (request.method === 'PUT') {
          assert.equal(headers['if-none-match'], '*');
          assert.equal(headers['content-type'], 'text/plain');
          assert.ok(headers['x-amz-meta-upload-id']);
          transfers.push(request);
          await fetch(fixture + '/__received/' + headers['x-amz-meta-upload-id']);
        }
        await send('Fetch.fulfillRequest', { requestId, responseCode: 200, body: '', responseHeaders: [
          { name: 'Access-Control-Allow-Origin', value: base },
          { name: 'Access-Control-Allow-Methods', value: 'PUT,OPTIONS,GET' },
          { name: 'Access-Control-Allow-Headers', value: 'Content-Type,If-None-Match,x-amz-meta-upload-id' },
        ] }, sessionId);
      } catch (error) {
        // Full navigation can cancel a paused folder request before its local
        // fixture response arrives. CDP then invalidates that interception ID.
        if (error.message.includes('"code":-32602') && error.message.includes('Invalid InterceptionId')) cancelledInterceptions++;
        else errors.push(error.message);
      }
    }
  });
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, sessionId);
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  async function wait(expression) {
    const deadline = Date.now() + 45000;
    while (Date.now() < deadline) { if (await evaluate(expression)) return; await pause(150); }
    throw new Error('Timed out: ' + expression + '\n' + await evaluate('document.body.innerText.slice(0,1000)'));
  }
  const click = label => evaluate(`[...document.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(label)})?.click()`);
  async function navigate(route, ready) {
    await send('Page.navigate', { url: base + route }, sessionId);
    await wait(ready);
  }
  async function screenshot(name) {
    await pause(250);
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, sessionId);
    fs.writeFileSync(path.join(output, name + '.png'), Buffer.from(shot.data, 'base64'));
  }
  try {
    ({ targetId } = await send('Target.createTarget', { url: 'about:blank' }));
    ({ sessionId } = await send('Target.attachToTarget', { targetId, flatten: true }));
    await send('Page.enable', {}, sessionId); await send('Runtime.enable', {}, sessionId);
    await send('Fetch.enable', { patterns: [{ urlPattern: 'https://r2.example.invalid/*', requestStage: 'Request' },
      ...(apiProxy ? [{ urlPattern: apiProxy + '/api/admin/knowledge/*', requestStage: 'Request' }] : [])] }, sessionId);
    await send('Page.addScriptToEvaluateOnNewDocument', { source: `localStorage.setItem('heritage_access_token','synthetic-review-token');localStorage.setItem('heritage_user',JSON.stringify({account_id:'1',username:'Review Admin',role:'ADMIN'}));` }, sessionId);
    await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1200, deviceScaleFactor: 1, mobile: false }, sessionId);
    await navigate('/admin/documents?prefix=archives/', `document.body.innerText.includes('Monument reference.md')`);
    assert.deepEqual(await evaluate(`(()=>{const r=document.querySelector('section').getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()`), [284, 28, 1612, 1144]);
    await screenshot('library-desktop');
    await click('Upload documents'); await wait(`!!document.querySelector('[role=dialog]')`);
    assert.equal(await evaluate(`getComputedStyle(document.querySelector('.ant-modal-container')).backgroundColor`), 'rgb(255, 255, 255)');
    await click('Change folder');
    await evaluate(`[...document.querySelectorAll('[role=dialog] button')].find(e=>e.textContent.trim()==='research').click()`);
    await evaluate(`(()=>{const input=document.querySelector('[role=dialog] input[type=file]'),data=new DataTransfer();data.items.add(new File(['hello from browser'],'browser-upload.txt',{type:'text/plain'}));input.files=data.files;input.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await wait(`document.querySelector('[role=dialog]')?.innerText.includes('browser-upload.txt')`);
    await screenshot('upload-modal-selected'); await click('Upload 1 file');
    await wait(`document.querySelector('[role=dialog]')?.innerText.includes('Stored key:')`);
    assert.equal(transfers.length, 1);
    await screenshot('upload-modal-stored');
    await evaluate(`document.querySelector('.ant-modal-close').click()`);
    console.log('PASS: real browser XHR, signed headers, selected destination and verified completion');

    await click('Create folder'); await wait(`!!document.querySelector('#knowledge-folder-name')`);
    await evaluate(`(()=>{const input=document.querySelector('#knowledge-folder-name');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'Browser acceptance');input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    await evaluate(`document.querySelector('[role=dialog] form').requestSubmit()`);
    await wait(`!document.querySelector('[role=dialog]') && document.body.innerText.includes('Browser acceptance')`);
    console.log('PASS: create folder refreshes actual listing');
    await navigate('/admin/documents/details?key=archives%2FMonument%20reference.md', `!!document.querySelector('pre')`);
    assert.equal(await evaluate('!!window.previewExecuted'), false);
    assert.ok(await evaluate(`document.querySelector('pre').textContent.includes('<script>')`));
    await screenshot('details-desktop');
    await click('Delete file'); await wait(`!!document.querySelector('[role=dialog]')`);
    assert.ok(await evaluate(`document.querySelector('[role=dialog]').textContent.includes('archives/Monument reference.md')`));
    await evaluate(`[...document.querySelectorAll('[role=dialog] button')].find(e=>e.textContent.trim()==='Delete file').click()`);
    await wait(`location.pathname==='/admin/documents' && !document.querySelector('[role=dialog]') && !!document.querySelector('[role=table]')`);
    assert.equal(await evaluate(`document.querySelector('[role=table]').textContent.includes('Monument reference.md')`), false);
    console.log('PASS: preview renders hostile markup as text; exact-key deletion refreshes parent');

    const cases = [['library', '/admin/documents?prefix=archives/', 'Field observations.txt'],
      ['upload', '/admin/documents/upload?prefix=archives/', 'Upload queue'],
      ['details', '/admin/documents/details?key=archives%2FField%20observations.txt', 'Metadata and original file'],
      ['metadata', '/admin/documents/metadata?key=archives%2FField%20observations.txt', 'Document metadata'],
      ['review', '/admin/documents/review', 'Pending review'], ['ingestion', '/admin/documents/ingestion', 'Ingestion']];
    for (const [width, height, label] of [[1920, 1200, 'desktop'], [390, 844, 'mobile']]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600 }, sessionId);
      for (const [name, route, text] of cases) {
        await navigate(route, `!!document.querySelector('h1') && document.body.innerText.includes(${JSON.stringify(text)})`);
        assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'), name + ' overflows viewport');
        await screenshot(name + '-' + label);
        if (name === 'library' && label === 'mobile') {
          await click('Upload documents'); await wait(`!!document.querySelector('[role=dialog]')`);
          assert.ok(await evaluate(`(()=>{const modal=document.querySelector('[role=dialog]'),r=modal.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&modal.scrollWidth<=modal.clientWidth})()`), 'Mobile upload modal overflows');
          await screenshot('upload-modal-mobile');
          await evaluate(`document.querySelector('.ant-modal-close').click()`);
          await wait(`!document.querySelector('[role=dialog]')`);
        }
      }
    }
    for (const [mode, text] of [['empty', 'No files in this folder'], ['error', 'Try again'], ['unauthorized', 'Sign in to continue'], ['forbidden', 'Administrator access required']]) {
      await fetch(fixture + '/__mode/' + mode);
      await navigate('/admin/documents', `document.body.innerText.includes(${JSON.stringify(text)})`);
      await screenshot('state-' + mode);
    }
    await fetch(fixture + '/__mode/normal');
    assert.deepEqual(errors, []);
    console.log('PASS: desktop/mobile routes, empty/error/401/403 states; no JavaScript exceptions');
    console.log('Navigation-cancelled CDP requests: ' + cancelledInterceptions);
    console.log('Screenshots: ' + output);
  } catch (error) {
    await screenshot('failure');
    throw error;
  } finally {
    await fetch(fixture + '/__mode/normal');
    if (targetId) await send('Target.closeTarget', { targetId });
    ws.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; setTimeout(() => process.exit(1), 500); });
