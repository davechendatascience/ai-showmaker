AI-Showmaker Monitoring UI

Simple local UI to:
- Spawn the Python MCP bridge (`full_mcp_bridge.py`).
- Start/stop the TypeScript interactive main app (`src/main.ts`).
- Stream live logs from both processes side-by-side.
- Send user task queries into the main app.
- Inspect bridge servers, tools, and health.

How to run
- Prereq: Python available as `python` (or set `PYTHON` env var), Node.js, and local deps installed to run `src/main.ts` (ts-node devDependency).
- Start UI: `npm run monitor:ui`
- Open: http://localhost:3300

Notes
- The UI streams stdout/stderr via Server-Sent Events; refresh keeps connections alive.
- The app input box writes lines to the app process stdin as if you typed in the terminal.
- Bridge info uses the bridge HTTP on `http://localhost:8000`; start the bridge first for server/tool views.
- Start order matters: start the Bridge first, wait until it prints `Starting Full MCP Bridge on http://localhost:8000`, then start the App so it can connect.

Tool Runner
- Use the Tool Runner panel to call any bridge tool directly.
- Select a tool from the dropdown, edit JSON params, and click Run.
- Results from the bridge `/execute` endpoint show on the right. This helps verify schemas (e.g., `filename` vs `file_path`) without going through the agent loop.

Troubleshooting
- Bridge exits with UnicodeEncodeError (cp950) on Windows:
  - Cause: Python stdout encoding defaults to your code page when piped (e.g., cp950), and emoji logs can’t be encoded.
  - Fix: The UI now launches Python with `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`. If you start bridge manually, run `set PYTHONUTF8=1` first or avoid emojis.
- If App fails with `Cannot find module 'ts-node/register'`:
  - Run `npm install` to ensure dev dependencies are present.
  - The UI now prefers `node_modules/.bin/ts-node` when available; otherwise it falls back to `-r ts-node/register`.
- If App complains about missing keys (e.g., `OPENAI_KEY`):
  - Create a `.env` in repo root or export env vars before `npm run monitor:ui`.
  - The UI loads `.env` and passes env to child processes.
- If Bridge fails to import `mcp_servers.*`:
  - Ensure you are launching from the repo root. The UI sets `cwd` to the repo root.
  - Verify Python points to your venv (see section below).

Interactive SSH Session (remote server)
- Start an interactive SSH session under “Interactive SSH Session”:
  - Optional: set a starting directory.
  - Click “Start Session” to open a PTY on the remote host (via `paramiko.invoke_shell`).
  - Type a command in the input and press Enter to send it. Output streams live above.
  - Click “Close Session” to end it.
- Requirements: environment variables for the remote (same as the remote MCP server uses):
  - `AWS_HOST`, `AWS_USER`, `AWS_KEY_PATH` (private key path). The bridge reuses the remote server’s SSH pool logic.
- This panel is independent of the agent’s tool calls; it mirrors a real SSH terminal for visibility and manual debugging.

Using a Python venv
- No, you don’t have to “activate” the venv if you launch the venv’s Python directly. The UI server will try to auto-detect a local venv at `.venv/` or `venv/` and use its Python.
- You can override explicitly with `PYTHON` env var:
  - Windows (PowerShell): `$env:PYTHON = "C:\\path\\to\\repo\\.venv\\Scripts\\python.exe"; npm run monitor:ui`
  - macOS/Linux: `PYTHON=.venv/bin/python npm run monitor:ui`
- Activation is only needed for interactive shells; spawning the interpreter binary (`…/venv/bin/python`) is sufficient for subprocesses and will use the venv’s packages.
