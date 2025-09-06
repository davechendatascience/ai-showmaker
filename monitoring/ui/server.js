// Minimal monitoring UI server to manage bridge and app and stream logs
// Usage: node monitoring/ui/server.js

const http = require('http');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
// Load env so children inherit any .env values when launched from UI
try { require('dotenv').config(); } catch (_) {}

const PORT = process.env.PORT ? Number(process.env.PORT) : 3300;

function detectVenvPython() {
  const candidates = process.platform === 'win32'
    ? [
        path.resolve(process.cwd(), '.venv', 'Scripts', 'python.exe'),
        path.resolve(process.cwd(), 'venv', 'Scripts', 'python.exe'),
      ]
    : [
        path.resolve(process.cwd(), '.venv', 'bin', 'python'),
        path.resolve(process.cwd(), 'venv', 'bin', 'python'),
      ];
  for (const p of candidates) {
    try { if (fs.existsSync(p)) return p; } catch (_) {}
  }
  return null;
}

let bridgeProcess = null;
let appProcess = null;

// SSE subscribers
const bridgeSubscribers = new Set();
const appSubscribers = new Set();

function writeSSE(res, line) {
  try {
    res.write(`data: ${line.replace(/\r?\n/g, '\\n')}\n\n`);
  } catch (_) {
    // ignore broken pipe
  }
}

function broadcast(set, line) {
  for (const res of Array.from(set)) {
    writeSSE(res, line);
  }
}

function spawnBridge() {
  if (bridgeProcess && !bridgeProcess.killed) {
    return { ok: true, message: 'Bridge already running', pid: bridgeProcess.pid };
  }
  const pythonCmd = process.env.PYTHON || detectVenvPython() || 'python';
  const script = path.resolve(process.cwd(), 'full_mcp_bridge.py');
  const env = {
    ...process.env,
    PYTHONIOENCODING: process.env.PYTHONIOENCODING || 'utf-8',
    PYTHONUTF8: process.env.PYTHONUTF8 || '1',
    PYTHONUNBUFFERED: process.env.PYTHONUNBUFFERED || '1',
  };
  const child = spawn(pythonCmd, [script], { cwd: process.cwd(), env, shell: process.platform === 'win32' });
  bridgeProcess = child;

  child.stdout.on('data', (data) => {
    const text = data.toString();
    broadcast(bridgeSubscribers, text);
  });
  child.stderr.on('data', (data) => {
    const text = data.toString();
    broadcast(bridgeSubscribers, text);
  });
  child.on('error', (err) => {
    broadcast(bridgeSubscribers, `\n[bridge:error] ${String(err)}\n`);
  });
  child.on('exit', (code, signal) => {
    broadcast(bridgeSubscribers, `\n[bridge] exited code=${code} signal=${signal}\n`);
    bridgeProcess = null;
  });
  return { ok: true, message: 'Bridge started', pid: child.pid };
}

function stopBridge() {
  if (bridgeProcess && !bridgeProcess.killed) {
    bridgeProcess.kill();
    return { ok: true, message: 'Bridge stopping' };
  }
  return { ok: true, message: 'Bridge not running' };
}

function spawnApp() {
  if (appProcess && !appProcess.killed) {
    return { ok: true, message: 'App already running', pid: appProcess.pid };
  }
  // Prefer ts-node if available; otherwise compiled dist if present
  const appTs = path.resolve(process.cwd(), 'src', 'main.ts');
  const appJs = path.resolve(process.cwd(), 'dist', 'main.js');
  const useTs = fs.existsSync(appTs);
  let cmd, args;
  if (useTs) {
    // Try local ts-node binary first for reliability
    const binDir = path.resolve(process.cwd(), 'node_modules', '.bin');
    const tsNodeBin = process.platform === 'win32'
      ? path.join(binDir, 'ts-node.cmd')
      : path.join(binDir, 'ts-node');
    if (fs.existsSync(tsNodeBin)) {
      cmd = tsNodeBin;
      args = [appTs];
    } else {
      // Fallback to runtime require hook
      cmd = 'node';
      args = ['-r', 'ts-node/register', appTs];
    }
  } else if (fs.existsSync(appJs)) {
    cmd = 'node';
    args = [appJs];
  } else {
    return { ok: false, message: 'Cannot find src/main.ts or dist/main.js' };
  }
  const child = spawn(cmd, args, { cwd: process.cwd(), env: process.env, shell: process.platform === 'win32' });
  appProcess = child;
  child.stdout.on('data', (data) => {
    broadcast(appSubscribers, data.toString());
  });
  child.stderr.on('data', (data) => {
    broadcast(appSubscribers, data.toString());
  });
  child.on('error', (err) => {
    broadcast(appSubscribers, `\n[app:error] ${String(err)}\n`);
  });
  child.on('exit', (code, signal) => {
    broadcast(appSubscribers, `\n[app] exited code=${code} signal=${signal}\n`);
    appProcess = null;
  });
  return { ok: true, message: 'App started', pid: child.pid };
}

function stopApp() {
  if (appProcess && !appProcess.killed) {
    // Try sending Ctrl+C on Windows not simple; use kill
    appProcess.kill();
    return { ok: true, message: 'App stopping' };
  }
  return { ok: true, message: 'App not running' };
}

function sendToApp(line) {
  if (!appProcess || appProcess.killed || !appProcess.stdin) {
    return { ok: false, message: 'App is not running' };
  }
  try {
    appProcess.stdin.write(line.endsWith('\n') ? line : line + '\n');
    return { ok: true, message: 'Sent' };
  } catch (e) {
    return { ok: false, message: String(e) };
  }
}

function serveStatic(req, res) {
  let filePath = req.url === '/' ? '/index.html' : req.url;
  const resolved = path.join(__dirname, 'public', path.normalize(filePath).replace(/^\\+|^\/+/, ''));
  if (!resolved.startsWith(path.join(__dirname, 'public'))) {
    res.writeHead(403); res.end('Forbidden'); return;
  }
  fs.readFile(resolved, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    const ext = path.extname(resolved).toLowerCase();
    const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css' };
    res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream' });
    res.end(data);
  });
}

function json(res, code, obj) {
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(obj));
}

function sseHandler(set, req, res, name) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });
  res.write('\n');
  set.add(res);
  writeSSE(res, `[${name}] connected`);
  req.on('close', () => set.delete(res));
}

async function proxyBridge(pathname, res) {
  // Simple proxy to the local Python bridge for info endpoints
  const httpModule = require('http');
  const options = { hostname: 'localhost', port: 8000, path: pathname, method: 'GET' };
  const req = httpModule.request(options, (pres) => {
    let body = '';
    pres.on('data', (chunk) => (body += chunk));
    pres.on('end', () => {
      res.writeHead(pres.statusCode || 500, { 'Content-Type': 'application/json' });
      res.end(body);
    });
  });
  req.on('error', (err) => json(res, 502, { error: String(err) }));
  req.end();
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const { pathname } = url;

  // API routes
  if (pathname === '/api/bridge/start' && req.method === 'POST') return json(res, 200, spawnBridge());
  if (pathname === '/api/bridge/stop' && req.method === 'POST') return json(res, 200, stopBridge());
  if (pathname === '/api/app/start' && req.method === 'POST') return json(res, 200, spawnApp());
  if (pathname === '/api/app/stop' && req.method === 'POST') return json(res, 200, stopApp());
  if (pathname === '/api/app/send' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      try {
        const { query } = JSON.parse(body || '{}');
        return json(res, 200, sendToApp(String(query || '').trim()));
      } catch (e) {
        return json(res, 400, { ok: false, message: 'Invalid JSON' });
      }
    });
    return;
  }
  if (pathname === '/api/bridge/status') return json(res, 200, { running: !!bridgeProcess, pid: bridgeProcess?.pid || null });
  if (pathname === '/api/app/status') return json(res, 200, { running: !!appProcess, pid: appProcess?.pid || null });
  if (pathname === '/api/logs/bridge') return sseHandler(bridgeSubscribers, req, res, 'bridge');
  if (pathname === '/api/logs/app') return sseHandler(appSubscribers, req, res, 'app');
  if (pathname === '/api/bridge/tools') return proxyBridge('/tools', res);
  if (pathname === '/api/bridge/servers') return proxyBridge('/servers', res);
  if (pathname === '/api/bridge/health') return proxyBridge('/health', res);
  if (pathname === '/api/bridge/execute' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const httpModule = require('http');
      const buf = Buffer.from(body || '{}');
      const req2 = httpModule.request({ hostname: '127.0.0.1', port: 8000, path: '/execute', method: 'POST', agent: new httpModule.Agent({ keepAlive: false }), headers: { 'Content-Type': 'application/json', 'Content-Length': buf.length, 'Connection': 'close' } }, (pres) => {
        let chunks = '';
        pres.on('data', (ch) => (chunks += ch));
        pres.on('end', () => { try { json(res, pres.statusCode || 500, chunks ? JSON.parse(chunks) : {}); } catch { json(res, 500, { error: 'Invalid JSON from bridge' }); } });
      });
      req2.on('error', (err) => json(res, 502, { error: String(err) }));
      req2.write(buf); req2.end();
    });
    return;
  }
  // GET variant for execute (used by app fallback)
  if (pathname.startsWith('/api/bridge/execute_get') && req.method === 'GET') {
    const httpModule = require('http');
    const upstream = httpModule.request(
      {
        hostname: '127.0.0.1',
        port: 8000,
        path: '/execute_get' + (url.search || ''),
        method: 'GET',
        agent: new httpModule.Agent({ keepAlive: false }),
        headers: { 'Connection': 'close' },
      },
      (pres) => {
        let chunks = '';
        pres.on('data', (ch) => (chunks += ch));
        pres.on('end', () => {
          try {
            json(res, pres.statusCode || 500, chunks ? JSON.parse(chunks) : {});
          } catch {
            json(res, 500, { error: 'Invalid JSON from bridge' });
          }
        });
      }
    );
    upstream.on('error', (err) => json(res, 502, { error: String(err) }));
    upstream.end();
    return;
  }
  if (pathname === '/api/bridge/execute_get' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      try {
        const { tool_name, params } = JSON.parse(body || '{}');
        const qs = new URLSearchParams({
          tool_name: String(tool_name || ''),
          params: JSON.stringify(params || {}),
        }).toString();
        const httpModule = require('http');
        const req2 = httpModule.request({ hostname: '127.0.0.1', port: 8000, path: '/execute_get?' + qs, method: 'GET', agent: new httpModule.Agent({ keepAlive: false }) }, (pres) => {
          let chunks = '';
          pres.on('data', (ch) => (chunks += ch));
          pres.on('end', () => { try { json(res, pres.statusCode || 500, chunks ? JSON.parse(chunks) : {}); } catch { json(res, 500, { error: 'Invalid JSON from bridge' }); } });
        });
        req2.on('error', (err) => json(res, 502, { error: String(err) }));
        req2.end();
      } catch (e) {
        json(res, 400, { error: 'Invalid JSON' });
      }
    });
    return;
  }
  if (pathname === '/api/bridge/remote-logs') {
    // Proxy SSE stream from bridge
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    });
    const httpModule = require('http');
    const req2 = httpModule.request({ hostname: 'localhost', port: 8000, path: '/remote-logs', method: 'GET' }, (pres) => {
      pres.on('data', (chunk) => {
        try { res.write(chunk); } catch (_) {}
      });
      pres.on('end', () => { try { res.end(); } catch (_) {} });
    });
    req2.on('error', () => { try { res.end(); } catch (_) {} });
    req2.end();
    return;
  }

  // Remote interactive session proxies
  if (pathname === '/api/remote/session/start' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const httpModule = require('http');
      const buf = Buffer.from(body || '{}');
      const req2 = httpModule.request({ hostname: 'localhost', port: 8000, path: '/remote/session/start', method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': buf.length } }, (pres) => {
        let chunks = '';
        pres.on('data', (ch) => (chunks += ch));
        pres.on('end', () => { json(res, pres.statusCode || 500, chunks ? JSON.parse(chunks) : {}); });
      });
      req2.on('error', (err) => json(res, 502, { error: String(err) }));
      req2.write(buf); req2.end();
    });
    return;
  }
  if (pathname === '/api/remote/session/send' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const httpModule = require('http');
      const buf = Buffer.from(body || '{}');
      const req2 = httpModule.request({ hostname: 'localhost', port: 8000, path: '/remote/session/send', method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': buf.length } }, (pres) => {
        let chunks = '';
        pres.on('data', (ch) => (chunks += ch));
        pres.on('end', () => { json(res, pres.statusCode || 500, chunks ? JSON.parse(chunks) : {}); });
      });
      req2.on('error', (err) => json(res, 502, { error: String(err) }));
      req2.write(buf); req2.end();
    });
    return;
  }
  if (pathname === '/api/remote/session/close' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      const httpModule = require('http');
      const buf = Buffer.from(body || '{}');
      const req2 = httpModule.request({ hostname: 'localhost', port: 8000, path: '/remote/session/close', method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': buf.length } }, (pres) => {
        let chunks = '';
        pres.on('data', (ch) => (chunks += ch));
        pres.on('end', () => { json(res, pres.statusCode || 500, chunks ? JSON.parse(chunks) : {}); });
      });
      req2.on('error', (err) => json(res, 502, { error: String(err) }));
      req2.write(buf); req2.end();
    });
    return;
  }
  if (pathname.startsWith('/api/remote/session/stream')) {
    // Proxy SSE by forwarding query string as-is
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
    const httpModule = require('http');
    const req2 = httpModule.request({ hostname: 'localhost', port: 8000, path: '/remote/session/stream' + (url.search || ''), method: 'GET' }, (pres) => {
      pres.on('data', (chunk) => { try { res.write(chunk); } catch(_){} });
      pres.on('end', () => { try { res.end(); } catch(_){} });
    });
    req2.on('error', () => { try { res.end(); } catch(_){} });
    req2.end();
    return;
  }

  // Static files
  return serveStatic(req, res);
});

server.listen(PORT, () => {
  console.log(`Monitoring UI running at http://localhost:${PORT}`);
  console.log('Open this URL in your browser.');
});
