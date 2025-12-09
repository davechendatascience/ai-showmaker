# Plan-Execute Agent (BFS-Free)

This patch replaces the BFS frontier loop with a simpler **plan → execute → replan** strategy.

## What changed
- Added `src/agents/plan-execute-agent.ts`
  - Generates a compact, ordered tool plan up front (JSON steps with tool + inputs).
  - Executes steps sequentially.
  - On failure: retries up to `PLAN_MAX_ATTEMPTS`, then replans the remaining steps using the completed step history and failure reason.
  - Uses rich memory for logging, file tracking, and lightweight goal checks.
  - Provides `getState()` for CLI status and a stub `getScenarioCache()` (scenario prediction disabled).
- Swapped the app entry point to the new agent in `src/main.ts`.
  - Startup copy now references the Plan-Execute Agent and no longer prints BFS/validator tunables.
  - The `state` command shows plan progress (done/pending/failed/replans), and `scenarios` notes that prediction is disabled.

## New environment knobs
- `PLAN_MAX_STEPS` (default 8) — cap on planned steps returned by the LLM.
- `PLAN_MAX_REPLANS` (default 3) — how many times we allow replanning after failures.
- `PLAN_MAX_ATTEMPTS` (default 2) — retries per step before triggering a replan.
- `PLAN_LLM_TEMPERATURE` (default 0.1) — planning prompt temperature.

## Execution flow
1. Start task + rich memory context.
2. LLM produces an ordered plan (<= `PLAN_MAX_STEPS`).
3. Execute each step in order.
4. If a step fails:
   - Retry (up to `PLAN_MAX_ATTEMPTS`).
   - Otherwise replan remaining steps with completed-step history (up to `PLAN_MAX_REPLANS`).
5. Stop when plan is complete or goal evidence is detected via the memory manager.

## Files touched
- `src/agents/plan-execute-agent.ts` — new agent implementation.
- `src/main.ts` — wiring to use the new agent and refresh CLI status displays.

## Notes
- Scenario prediction/validator logic from BFS is intentionally omitted.
- Goal detection relies on memory evidence (implementation + synthesis or file creation + synthesis).
- The previous BFS agent remains in the repo for reference but is no longer used by the CLI entrypoint.
