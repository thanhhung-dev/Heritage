// Synthetic loopback fixture. This process never contacts an external service.
const http = require('node:http');
const port = Number(process.env.KNOWLEDGE_FIXTURE_PORT || 18926);
const frontend = process.env.KNOWLEDGE_FRONTEND_URL || 'http://127.0.0.1:3006';
const files = new Map(), folders = new Set(), tickets = new Map(), received = new Set();
let mode = 'normal', nextId = 1;
function reset() {
  files.clear(); folders.clear(); tickets.clear(); received.clear(); mode = 'normal'; nextId = 1;
  folders.add('archives/'); folders.add('research/');
  for (const [index, name] of ['Monument reference.md', 'Field observations.txt', 'Archive catalogue.json',
    'Conservation notes.md', 'Oral history.txt', 'Craft research.md', 'Register notes.txt'].entries()) {
    const content = name.endsWith('.json') ? '{"source":"synthetic test fixture"}'
      : `# ${name}\n\nSynthetic browser fixture. <script>window.previewExecuted=true</script>`;
    files.set('archives/' + name, { bucket: 'knowledge-heritage', key: 'archives/' + name, name,
      content, size: Buffer.byteLength(content), contentType: name.endsWith('.json') ? 'application/json'
        : name.endsWith('.md') ? 'text/markdown' : 'text/plain', metadata: {}, etag: '"fixture-' + index + '"',
      lastModified: '2026-11-20T08:00:00Z' });
  }
}
reset();
http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1:' + port);
  res.setHeader('Access-Control-Allow-Origin', frontend);
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Correlation-ID');
  res.setHeader('Cache-Control', 'no-store');
  const send = (code, body) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(code === 204 ? '' : JSON.stringify(body)); };
  if (req.method === 'OPTIONS') return send(204);
  let raw = ''; for await (const chunk of req) raw += chunk;
  const body = raw ? JSON.parse(raw) : {};
  if (url.pathname === '/__reset') { reset(); return send(200, { reset: true }); }
  if (url.pathname.startsWith('/__mode/')) { mode = url.pathname.split('/').pop(); return send(200, { mode }); }
  if (url.pathname.startsWith('/__received/')) { received.add(url.pathname.split('/').pop()); return send(200, {}); }
  if (mode === 'unauthorized') return send(401, { detail: 'Synthetic session expired' });
  if (mode === 'forbidden') return send(403, { detail: 'Synthetic access denied' });
  if (mode === 'error') return send(503, { detail: 'Synthetic storage unavailable' });
  const route = url.pathname.replace('/api/admin/knowledge', '');
  if (route === '/objects' && req.method === 'GET') {
    const prefix = url.searchParams.get('prefix') ?? '';
    return send(200, { bucket: 'knowledge-heritage', prefix, nextContinuationToken: null,
      files: mode === 'empty' ? [] : [...files.values()].filter(f => f.key.startsWith(prefix) && !f.key.slice(prefix.length).includes('/')).map(({ content, ...f }) => f),
      folders: mode === 'empty' ? [] : [...folders].filter(p => p.startsWith(prefix) && p !== prefix && !p.slice(prefix.length, -1).includes('/')).map(p => ({ name: p.slice(prefix.length, -1), prefix: p })) });
  }
  if (route === '/object' || route === '/preview') {
    const f = files.get(url.searchParams.get('key')); if (!f) return send(404, { detail: 'Synthetic file not found' });
    const { content, ...info } = f;
    return send(200, route === '/object' ? info : { key: f.key, content, contentType: 'text/plain; charset=utf-8', size: f.size, etag: f.etag });
  }
  if (route === '/folders') {
    const prefix = body.parentPrefix + body.folderName + '/'; folders.add(prefix);
    return send(201, { name: body.folderName, prefix });
  }
  if (route === '/objects' && req.method === 'DELETE') { files.delete(body.key); return send(204); }
  if (route === '/download-url') return send(200, { key: body.key, downloadUrl: 'https://r2.example.invalid/download', expiresIn: 300 });
  if (route === '/upload-url') {
    const id = 'fixture-' + nextId++;
    const ticket = { uploadId: id, objectKey: body.folder + body.filename, uploadUrl: 'https://r2.example.invalid/staging/' + id,
      method: 'PUT', expiresIn: 300, sessionExpiresAt: '2099-01-01T00:00:00Z', requiredHeaders: {
        'Content-Type': body.contentType, 'If-None-Match': '*', 'x-amz-meta-upload-id': id } };
    tickets.set(id, { ticket, data: body }); return send(201, ticket);
  }
  if (route.endsWith('/complete')) {
    const id = route.split('/').at(-2), pending = tickets.get(id);
    if (!pending || !received.has(id)) return send(404, { detail: 'Synthetic transfer has not completed' });
    const { ticket, data } = pending;
    const object = { bucket: 'knowledge-heritage', key: ticket.objectKey, name: data.filename, size: data.size,
      contentType: data.contentType, metadata: {}, lastModified: '2026-11-20T10:00:00Z', etag: '"uploaded"' };
    files.set(object.key, { ...object, content: 'Synthetic uploaded document' });
    return send(200, { uploadId: id, status: 'stored', object });
  }
  send(404, { detail: 'Synthetic route not found' });
}).listen(port, '127.0.0.1', () => console.log('Knowledge synthetic fixture: 127.0.0.1:' + port));
