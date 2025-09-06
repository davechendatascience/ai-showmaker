function $(sel) { return document.querySelector(sel); }

// Basic ANSI-stripping to improve readability of PTY output
function stripAnsi(s) {
  if (!s) return s;
  // OSC sequences: ESC ] ... BEL or ESC \
  s = s.replace(/\u001b\][^\u0007]*(?:\u0007|\u001b\\)/g, '');
  // CSI sequences: ESC [ ... command
  s = s.replace(/\u001b\[[0-9;?]*[ -\/]*[@-~]/g, '');
  // 7-bit C1 escape sequences: ESC followed by a single char
  s = s.replace(/\u001b[@-Z\\-_]/g, '');
  return s;
}

function normalizeCRLF(s) {
  if (!s) return s;
  // Simplify carriage returns; real terminals overwrite line. Here we break lines.
  s = s.replace(/\r\n/g, '\n');
  s = s.replace(/\r/g, '\n');
  return s;
}

function appendLine(el, data) {
  const clean = normalizeCRLF(stripAnsi(String(data || '')));
  el.textContent += clean + '\n';
  el.scrollTop = el.scrollHeight;
}

const bridgeStatusEl = $('#bridge-status');
const appStatusEl = $('#app-status');
const bridgeInfoEl = $('#bridge-info');
const appInfoEl = $('#app-info');
const serversEl = $('#servers');
const bridgeLogEl = $('#bridge-log');
const appLogEl = $('#app-log');
const remoteLogEl = $('#remote-log');
const sshStreamEl = $('#ssh-stream');
const sshInfoEl = $('#ssh-info');
let sshSessionId = null;

async function post(url, body) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  return res.json();
}

async function refreshStatuses() {
  const [bridge, app] = await Promise.all([
    fetch('/api/bridge/status').then(r => r.json()),
    fetch('/api/app/status').then(r => r.json()),
  ]);
  bridgeStatusEl.textContent = `Bridge: ${bridge.running ? 'running' : 'stopped'} ${bridge.pid ? `(pid ${bridge.pid})` : ''}`;
  appStatusEl.textContent = `App: ${app.running ? 'running' : 'stopped'} ${app.pid ? `(pid ${app.pid})` : ''}`;
  bridgeStatusEl.className = 'status ' + (bridge.running ? 'ok' : 'bad');
  appStatusEl.className = 'status ' + (app.running ? 'ok' : 'bad');
}

function attachSSE(endpoint, targetEl) {
  const es = new EventSource(endpoint);
  es.onmessage = (ev) => {
    try {
      const txt = ev.data.replace(/\\n/g, '\n');
      appendLine(targetEl, txt);
    } catch (e) {}
  };
  es.onerror = () => { /* keep retrying */ };
}

async function refreshServers() {
  try {
    const [health, servers, tools] = await Promise.all([
      fetch('/api/bridge/health').then(r => r.json()),
      fetch('/api/bridge/servers').then(r => r.json()),
      fetch('/api/bridge/tools').then(r => r.json()),
    ]);
    serversEl.textContent = JSON.stringify({ health, servers, toolsCount: Array.isArray(tools) ? tools.length : tools }, null, 2);
  } catch (e) {
    serversEl.textContent = 'Unable to reach bridge. Start it first.';
  }
}

window.addEventListener('DOMContentLoaded', () => {
  $('#start-bridge').addEventListener('click', async () => {
    const r = await post('/api/bridge/start');
    bridgeInfoEl.textContent = r.message || JSON.stringify(r);
    refreshStatuses();
  });
  $('#stop-bridge').addEventListener('click', async () => {
    const r = await post('/api/bridge/stop');
    bridgeInfoEl.textContent = r.message || JSON.stringify(r);
    refreshStatuses();
  });
  $('#start-app').addEventListener('click', async () => {
    const r = await post('/api/app/start');
    appInfoEl.textContent = r.message || JSON.stringify(r);
    refreshStatuses();
  });
  $('#stop-app').addEventListener('click', async () => {
    const r = await post('/api/app/stop');
    appInfoEl.textContent = r.message || JSON.stringify(r);
    refreshStatuses();
  });

  $('#send-query').addEventListener('click', async () => {
    const q = $('#user-query').value.trim();
    if (!q) return;
    const r = await post('/api/app/send', { query: q });
    appInfoEl.textContent = r.message || JSON.stringify(r);
    $('#user-query').value = '';
  });

  $('#user-query').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') { $('#send-query').click(); }
  });

  $('#refresh-servers').addEventListener('click', refreshServers);

  attachSSE('/api/logs/bridge', bridgeLogEl);
  attachSSE('/api/logs/app', appLogEl);
  attachSSE('/api/bridge/remote-logs', remoteLogEl);
  refreshStatuses();

  // SSH session handlers
  $('#ssh-start').addEventListener('click', async () => {
    sshStreamEl.textContent = '';
    const cwd = $('#ssh-cwd').value.trim();
    const res = await post('/api/remote/session/start', cwd ? { cwd } : {});
    if (!res.success) { sshInfoEl.textContent = res.error || 'Failed to start session'; return; }
    sshSessionId = res.session_id;
    sshInfoEl.textContent = `Session started: ${sshSessionId}`;
    const es = new EventSource(`/api/remote/session/stream?id=${encodeURIComponent(sshSessionId)}`);
    let last = null;
    es.onmessage = (ev) => {
      try {
        const txt = ev.data.replace(/\\n/g, '\n');
        if (last === txt) return; // collapse duplicates
        last = txt;
        appendLine(sshStreamEl, txt);
      } catch(e){}
    };
    es.onerror = () => {};
  });

  $('#ssh-close').addEventListener('click', async () => {
    if (!sshSessionId) { sshInfoEl.textContent = 'No active session'; return; }
    const res = await post('/api/remote/session/close', { session_id: sshSessionId });
    sshInfoEl.textContent = res.ok ? 'Session closed' : (res.error || 'Failed to close');
    sshSessionId = null;
  });

  $('#ssh-input').addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (!sshSessionId) { sshInfoEl.textContent = 'Start a session first'; return; }
      const cmd = e.target.value;
      e.target.value = '';
      // Do not locally echo; rely on remote shell output to avoid duplicates
      try {
        const res = await post('/api/remote/session/send', { session_id: sshSessionId, data: cmd });
        if (!res.ok) {
          sshInfoEl.textContent = res.error || 'Send failed';
        }
      } catch (err) {
        sshInfoEl.textContent = String(err);
      }
    }
  });

  // Tool Runner wiring
  async function loadToolsToSelect() {
    try {
      const tools = await fetch('/api/bridge/tools').then(r => r.json());
      const sel = $('#tool-select');
      if (!sel) return; // panel may not exist
      sel.innerHTML = '';
      tools.sort((a,b)=>a.name.localeCompare(b.name)).forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.name; opt.textContent = t.name; opt.dataset.schema = JSON.stringify(t.parameters || {});
        sel.appendChild(opt);
      });
      if (tools.length) updateSchemaPreview();
    } catch (e) {
      const schemaEl = $('#tool-schema');
      if (schemaEl) schemaEl.textContent = 'Unable to load tools: ' + e;
    }
  }

  function updateSchemaPreview() {
    const sel = $('#tool-select');
    const schemaEl = $('#tool-schema');
    if (!sel || !schemaEl) return;
    const schema = sel.selectedOptions[0]?.dataset?.schema;
    try {
      const obj = schema ? JSON.parse(schema) : {};
      schemaEl.textContent = JSON.stringify(obj, null, 2);
      if (!$('#tool-params').value.trim()) {
        $('#tool-params').value = '{}';
      }
    } catch { schemaEl.textContent = schema || '{}'; }
  }

  const refreshToolsBtn = $('#refresh-tools');
  if (refreshToolsBtn) refreshToolsBtn.addEventListener('click', loadToolsToSelect);
  const toolSelect = $('#tool-select');
  if (toolSelect) toolSelect.addEventListener('change', updateSchemaPreview);
  const prettyBtn = $('#params-pretty');
  if (prettyBtn) prettyBtn.addEventListener('click', () => {
    try { const obj = JSON.parse($('#tool-params').value || '{}'); $('#tool-params').value = JSON.stringify(obj, null, 2); } catch {}
  });
  const clearBtn = $('#params-clear');
  if (clearBtn) clearBtn.addEventListener('click', () => { $('#tool-params').value = '{}'; });
  const runBtn = $('#run-tool');
  if (runBtn) runBtn.addEventListener('click', async () => {
    const tool = $('#tool-select').value;
    let params = {};
    try { params = JSON.parse($('#tool-params').value || '{}'); } catch(e) { $('#tool-output').textContent = 'Invalid JSON: ' + e; return; }
    $('#tool-output').textContent = 'Running...';
    try {
      let res = await fetch('/api/bridge/execute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tool_name: tool, params }) }).then(r => r.json());
      // Fallback: some environments close POST bodies; try GET variant
      if (res && res.error && String(res.error).toLowerCase().includes('socket')) {
        res = await fetch('/api/bridge/execute_get', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tool_name: tool, params }) }).then(r => r.json());
      }
      $('#tool-output').textContent = JSON.stringify(res, null, 2);
    } catch (e) {
      $('#tool-output').textContent = 'Error: ' + e;
    }
  });

  loadToolsToSelect();
});
