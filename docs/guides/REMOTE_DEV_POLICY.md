# Remote Dev/Deploy Validation Policy (Amazon Linux, Web Apps)

This guide describes how the Best‑First Search Agent (BFS) and Validator jointly assess “remote development / deployment” tasks (e.g., spinning up a web app on an Amazon Linux server).

The validator is intentionally strict for Dev/Ops tasks. High‑level summaries are not enough. Completion requires concrete commands and verifiable checks.

## Required Artifacts (what the validator looks for)

- Commands: Concrete shell commands for
  - Package install/update (e.g., `yum`/`dnf`/`apt`)
  - Service control/config (`systemctl`, `pm2`, `nginx`, `apachectl`)
  - Networking/firewall changes (`firewall-cmd`, `ufw`, or AWS Security Group notes)
  - File placement/permissions (`cp`, `chown`, `chmod`)
- Verification steps (Operational Checks):
  - `curl http://localhost:80` (or public IP/DNS) with expected output or HTTP 200
  - `systemctl status <service>` is `active (running)`
  - `ss -ltnp` shows the expected port bound
  - Optional: `journalctl -u <service> -n 50` for recent logs
- Rollback notes:
  - How to stop/disable a service
  - How to revert config changes safely (backup/restore)
- Idempotency and safety:
  - Commands should be safe to re‑run (e.g., use `-y`, check file/service existence)
  - Minimal required privileges (use `sudo` only where needed)

## Evidence in the Draft

The composer includes an “Operational Checks” section for Dev/Ops tasks. The agent extracts a short snippet for the validator, which requires:

- At least one install/config/start sequence
- At least one verification command with expected output
- A brief rollback note

If these are missing, the validator rejects completion.

## Agent Behavior (BFS + Validator)

- Validation as action: The agent injects `synthesize_answer → validate` once its plan value crosses a threshold.
- Evidence gating: For Dev/Ops tasks, the agent prefers an “Operational Checks” section before re‑validating.
- Test/Checks gating: When the validator asks for tests/checks, the agent injects `test_example` instead of `validate` until checks are present.
- Logs:
  - `[BFS] draft:` prints a summary: code/tests presence and ops checks snippet
  - `[BFS][validator]` shows completion/confidence and rationale

## Environment Variables

- `BFS_VALIDATOR_MODE` (default `action`): `action` | `periodic` | `both`
- `BFS_VALUE_TRIGGER` (default `0.8`): Value threshold to schedule synthesize/validate
- `BFS_VALIDATION_COOLDOWN` (default `2`): Minimum iterations between validations
- `BFS_VALIDATOR_CONF` (default `0.7`): Minimum validator confidence to accept completion
- `BFS_HINT_BOOST` (default `0.35`): Boost for plans matching validator suggestions
- `BFS_SPECIAL_HINT_BOOST` (default `0.1`): Extra boost for `implement_code` / `test_example`

## Example: Static Site on Amazon Linux with Apache

- Install & start Apache
```
sudo yum update -y
sudo yum install -y httpd
sudo systemctl enable httpd
sudo systemctl start httpd
```
- Deploy content and permissions
```
echo "<h1>Hello from Amazon Linux</h1>" | sudo tee /var/www/html/index.html
sudo chown -R apache:apache /var/www/html
```
- Open firewall / Security Group
```
# If using firewalld
sudo firewall-cmd --add-service=http --permanent || true
sudo firewall-cmd --reload || true
# If on AWS, ensure Security Group allows inbound TCP/80 from your IP
```
- Verification checks
```
# Local check
curl -sS http://localhost:80 | head -n 2
# Service status
systemctl status httpd --no-pager | head -n 5
# Port listening
ss -ltnp | grep ":80"
```
- Rollback
```
sudo systemctl stop httpd
sudo systemctl disable httpd
# Optional: remove Apache if desired
# sudo yum remove -y httpd
```

## Acceptance Checklist (used by validator)

- [ ] Installation/configuration commands provided
- [ ] Service start/enable commands included
- [ ] Verification commands included with expected outputs
- [ ] Port/status checks included
- [ ] Rollback guidance provided
- [ ] Networking/firewall/Security Group considerations addressed
- [ ] Steps are idempotent and safe to re‑run

If any box is unchecked, the validator will suggest next actions and not pass the task.

