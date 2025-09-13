# Migration Notes: Best‑First Search Agent + Validator

This document summarizes the transition from a single‑agent orchestration to the new Best‑First Search (BFS) agent paired with a Validator agent.

## What Changed

- Validation as Action: Validation is a first‑class step (`validate`) instead of an implicit end‑state. The main agent injects `synthesize_answer → validate` once its plan value exceeds a threshold, and only finishes when the validator passes with sufficient confidence.
- Evidence Gating: The agent delays validation until fresh evidence exists; when the validator requests tests, it requires self‑tests before re‑validating.
- Self‑Tests for Code Tasks: Composer includes a fenced JSON `cases` block (2–3 minimal cases) and a short walkthrough. The agent detects and surfaces tests to the validator.
- Operational Checks for Dev/Ops Tasks: Composer includes shell commands and verification steps (e.g., curl/systemctl/ss), plus a rollback note. The validator requires these; summaries alone are not accepted.
- Scoring & Guidance: Plans matching validator `suggested_next_actions` are boosted; repeated/early `validate` is downweighted. Special boosts exist for `implement_code` and `test_example`.
- Logging: Draft meta is logged (`[BFS] draft:`) showing code/tests presence and ops checks snippets; full explanations are configurable.

## New/Updated Environment Variables

- `BFS_VALIDATOR_MODE` (default `action`): `action` | `periodic` | `both`
- `BFS_VALUE_TRIGGER` (default `0.8`): Inject synthesize/validate when value ≥ threshold
- `BFS_VALIDATION_COOLDOWN` (default `2`): Minimum iterations between validations
- `BFS_VALIDATOR_CONF` (default `0.7`): Min confidence to accept completion
- `BFS_HINT_BOOST` (default `0.35`): Boost for validator‑aligned plans
- `BFS_SPECIAL_HINT_BOOST` (default `0.1`): Extra boost for `implement_code`/`test_example`
- `BFS_EXPLAIN_MAX` (default `400`): Max chars for inline explanations
- `BFS_EXPLAIN_LOG_MAX` (default `0`): Console truncation for `[BFS] explain:` (0 = no truncation)

## Developer Notes

- Code Location: BFS agent in `src/agents/best-first-search-agent.ts` and Validator in `src/agents/validator-agent.ts`.
- Dev/Ops Policy: See `docs/guides/REMOTE_DEV_POLICY.md` for acceptance criteria on remote/server tasks.
- Backwards Compatibility: Existing LangGraph flows remain, but BFS+Validator is recommended for reliability and better observability.
- Suggested Defaults: `BFS_VALIDATOR_MODE=action`, `BFS_VALUE_TRIGGER=0.8`, `BFS_VALIDATOR_CONF=0.7`.

## FAQ

- Why gate on validator confidence? To avoid early exits on weak evidence and to surface guidance via `suggested_next_actions`.
- Do I need real code execution? Not necessarily. For code tasks, self‑tests (JSON + walkthrough) are sufficient. For Dev/Ops tasks, operational checks stand in for tests.
- How do I debug failures? Check `[BFS] draft:` for code/tests/ops presence, and `[BFS][validator]` rationale and hints. Increase `BFS_HINT_BOOST` if you want stronger adherence to validator guidance.

