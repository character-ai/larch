## Decision 1: Fix strategy
- **Question**: Which of the issue's three fix directions should this design pursue?
- **Resolution**: Unblock + fast-fail. Fix the sandbox so Codex's `checks run-relevant` verification runs (evidence: the verify command writes to `<TMPDIR>`, outside the workspace + `run_dir`/`repo_root` add-dirs, so the `workspace-write` sandbox rejects the `exec_command` spawn), AND add early event-stream detection of policy rejections as a fast-fail safety net. Prefer the least-privilege unblock (relocate the verify tmpdir into an already-writable root, or grant it via `--add-dir`) over broadening the sandbox.
- **Source**: user

## Decision 2: Breadth
- **Question**: How wide should the fix reach across `agent launch-codex-exec` call sites?
- **Resolution**: Audit and fix all call sites that ask Codex to run shell commands. The shared fast-fail detection belongs in the common `launch_codex_exec_main` choke point (`python/agents.py`) so every caller benefits without duplication. Audit finding (codebase): runtime workspace-write callers are lint-fix (`checks.py:1613` — the reported bug; asks Codex to run `checks run-relevant`), plan auto-fix (`plan_quality.py:1902` — orchestrator re-runs `plan validate` after Codex exits), and review-and-fix (`review_and_fix.py:2090` — `/review` runs `checks run-relevant` after Codex exits). Read-only lanes (research, validation, voter, judge, OOS-combine `oos_filer.py:461`, design Step 2b drafter) do not run shell and are unaffected. Confirm during drafting whether the plan-autofix / review-and-fix prompts ask Codex to `exec`; if not, the shared fast-fail still covers any future regression.
- **Source**: user + codebase

## Decision 3: Lint-fix timeout
- **Question**: Should `_RUN_EXTERNAL_TIMEOUT = 300` be shortened for lint-fix?
- **Resolution**: Keep 300s. Fast-fail already caps the deterministic policy-rejection case to seconds; the constant is shared by the Codex/Cursor/Claude lint-fix tiers, so do not change it.
- **Source**: user

## Hard constraints (preserved)
- Do NOT broaden Codex's sandbox beyond the current least-privilege posture unless strictly required; prefer keeping `workspace-write` and making the verify command's paths fall within already-writable roots.
- Preserve `read-only` callers (oos_filer combine, research/validation/voter/judge lanes, design Step 2b drafter) unchanged.
- Respect `.claude/rules/external-tool-launcher-parity.md`: audit Codex/Cursor parity for any launcher-argv change; add same-PR regression coverage per `.claude/rules/launcher-argv-test-coverage.md` (`python/test_agents.py` for `launch-codex-exec`).
- Update `SECURITY.md` if the sandbox/exec posture of any lane changes.
