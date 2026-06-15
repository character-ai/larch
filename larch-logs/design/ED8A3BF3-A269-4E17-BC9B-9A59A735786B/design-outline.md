## Proposed Design Outline

### Goals
- Move OOS filing to after `python/cli.py ship pr` returns `outcome=OK`, not before PR creation.
- Add `python/cli.py oos file` subcommand: runs combine (Codex CLI), cap, file-conflict pre-pass, `gh issue create` calls, and writes `run-statistics.md`.
- Fix `steps_ran={}` bug: always write `run-statistics.md` after Python path `outcome=OK`.

### Non-goals
- Bash-path OOS pipeline (remains unchanged).
- `oos-pipeline.md` body changes (bash-path reference, leave as-is).
- Replacing the disposition-checkpoint invariant for the bash path.

### Approach sketch
- Remove `oos_pending` check + `NEEDS_USER_INPUT(oos-filing)` from `ship.py`; keep `materialize_manifest_oos` call.
- Add `python/oos_filer.py` with `cmd_file` entry point; wire as `python/cli.py oos file`.
- `oos_filer.py` calls Codex CLI subprocess for combine, then `gh issue create` for each item, writes sentinel and `run-statistics.md`.
- SKILL.md: update Python Exit 0 routing — after `outcome=OK`, check accumulated OOS files and run `python/cli.py oos file`; remove `oos-filing` from Exit 3 routing table.
- `run_logs.py`: `_step9a1_heuristic` detects `run-statistics.md` already; no heuristic change needed since the filer always writes it.

### Surfaces in scope
- `python/ship.py` (remove OOS block)
- `python/oos_filer.py` (new)
- `python/cli.py` (add `oos file` subcommand entry)
- `python/test_oos_filer.py` (new test file)
- `skills/implement/SKILL.md` (update Step 8+ Python routing)
- `scripts/write-final-report.sh` / `python/run_logs.py` (Bug #6 is handled by always writing run-statistics.md — no code change needed here)
- `python/pr_body.py` / `scripts/create-pr.sh` (audit-only, no code change)

### Open questions
- None.
