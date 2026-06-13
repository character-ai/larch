## Proposed Design Outline

### Goals
- Port `check-reviewers.sh` and `run-negotiation-round.sh` to Python in `agents.py` with `agent check-reviewers` and `agent run-negotiation-round` CLI verbs.
- Retarget all callers (session_env.py, agents.py, lib-external-launcher-common.sh, status.sh, external-reviewers.md) to the new CLI verbs.
- Add pytest coverage for probe TTL, auth retry, status KV, and negotiation exit codes; retire bash scripts and their harnesses.

### Non-goals
- Changing the probe mechanics or TTL semantics (stamp-file approach stays identical to bash).
- Porting `sessionstart-health.sh` (it does not call check-reviewers.sh).
- Touching lib-cursor-auth.sh or lib-cursor-launcher-common.sh (their Python equivalents already exist in agents.py).

### Approach sketch
- Add `check_reviewers()` in `agents.py`: stamp-file TTL read/write, binary-found check, auth retry loop (calling existing `cursor_auth_preflight` / `cursor_auth_export_env`), Codex home setup. Emit KV via `emit_kv`.
- Add `check_reviewers_main()` and `run_negotiation_round()` + `run_negotiation_round_main()` in `agents.py`.
- Register `agent check-reviewers` and `agent run-negotiation-round` in cli.py `_REGISTRY`.
- Replace subprocess call in `session_env.py` and direct call in `agents.py _external_health_gate` with the Python function.
- Retarget `lib-external-launcher-common.sh` (6 callsites), `status.sh`, `external-reviewers.md` bash blocks to `python3 cli.py agent check-reviewers / run-negotiation-round`.
- Update `test_agents.py` stubs to mock Python function directly.
- Retire 8 bash files; append to `migrated-scripts.tsv`; run `make lint-retired-scripts`.

### Surfaces in scope
- `python/agents.py` (new functions)
- `python/cli.py` (two new registry entries)
- `python/test_agents.py` (new tests, updated stubs)
- `python/session_env.py` (subprocess → direct call)
- `scripts/lib-external-launcher-common.sh` (6 callsites retargeted)
- `skills/status/scripts/status.sh` (retargeted)
- `skills/shared/external-reviewers.md` (bash blocks updated)
- `skills/research/references/validation-phase.md` (prose reference updated)
- `python/lint_codex_exec_auth.py` (allowlist entry removed)
- `python/migrated-scripts.tsv` (8 new entries)
- Retired: `scripts/check-reviewers.{sh,md}`, `scripts/test-check-reviewers.{sh,md}`, `scripts/run-negotiation-round.{sh,md}`, `scripts/test-run-negotiation-round.{sh,md}`

### Open questions
- None.
