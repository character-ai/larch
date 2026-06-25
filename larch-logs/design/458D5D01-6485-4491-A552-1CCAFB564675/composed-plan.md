## Plan

## Approach

- Draft from direct repository inspection only. `approach-synthesis.txt` is `NO_SKETCHES`.
- Scope to mechanical chains only:
  - Step 5 self-review checks → commit-route.
  - Step 5 MAV/coder handoff checks → ready-to-commit resume.
  - Step 6 checks → Step 7 commit-route.
- Leave Step 3 unchanged.
  - It is a candidate from discussion, but inspection shows the next action is Step 4 branch-specific commit and rebase logic, not an unconditional next immediate-background fence.
- Add Python composite verbs that:
  - Run relevant checks via a **timeout-bounded child invocation** (not a blocking in-process call the parent cannot interrupt).
  - Relay the same whitespace-delimited checks stdout the CLI helper emits today.
  - Gate pass on `RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true` from the captured dict.
  - **Do not** use line-oriented `_parse_kv` / `larch_io.parse_kv` on checks stdout; those parsers treat multi-token lines as a single value.
  - On checks pass, run the next mechanical route leg under its own timeout-bounded child invocation.
  - On checks failure or checks-leg timeout, relay checks stdout (including `REDACTED_LOG_FILE` / `FAILURE_REASON` when present), emit exactly one line-anchored `NEXT_ACTION=checks-failed`, and do not seed durable stall.
  - Reserve line-anchored parsing for composite-owned `NEXT_ACTION` and relayed commit/resume KVs only.
- **Module wiring**:
  - Add `import checks` at module scope in `implement_dispatch.py` (today it imports `proc` but not `checks`).
  - Pass the existing `proc` runner into `checks.run_relevant_checks` from the timeout-bounded checks child (or call `checks run-relevant` via `_run_leg_with_timeout`).
  - Relay formatter must match live `checks_run_relevant_main` envelope (pass: `RELEVANT_CHECKS_OK` / `RELEVANT_CHECKS_SKIPPED` plus `SITE` / `COVERAGE` / `PHASE` / optional `WARN`; fail: `STATUS=fail FAILURE_REASON=...` plus `EXIT_CODE` / `PHASE` / `REDACTED_LOG_FILE` when present). Do not narrow to `review_and_fix._checks_result_capture` alone.
- **Per-leg hard timeouts via killable subprocesses**:
  - Pre/post `time.monotonic()` comparisons around blocking in-process calls **cannot** enforce per-leg ceilings. Each leg must run in an isolated child the parent can terminate.
  - Add `_run_leg_with_timeout(*, argv, deadline_ms, label) -> CompletedProcess | TimeoutExpired` that:
    - Spawns with `start_new_session=True` (new process group).
    - Forwards optional `timeout=deadline_ms/1000` to `subprocess.run` / `proc.run`.
    - On `TimeoutExpired`: kill the **process group** (`os.killpg` after `os.getpgid`) so nested `review-and-fix` / checks descendants cannot keep mutating the tree after the leg deadline; then drain stdout/stderr best-effort.
    - Reuse `proc.run` timeout plumbing where possible; extend only when group-kill semantics are missing.
  - **Checks leg**: invoke `python/cli.py checks run-relevant --site <site> --tmpdir <tmpdir>` via `_run_leg_with_timeout` (default `checks_deadline_ms=10800000` / 3h). On timeout: emit `NEXT_ACTION=checks-failed` with `FAILURE_REASON=checks-leg-timeout`; do not start commit/resume.
  - **Commit leg**: invoke only the documented child-safe CLI surface (see **Commit-leg child IPC** below) via `_run_leg_with_timeout` (default `commit_deadline_ms=3600000` / 1h). Start commit deadline only after checks leg finishes. On timeout: parent performs durable stall seeding per commit-route site config; map to composite `NEXT_ACTION=stall` only on `seeded-stall`.
  - **Resume leg** (`checks-step5-resume`): invoke `implement step-5-resume --ready-to-commit` in a child via `_run_leg_with_timeout` (default `resume_deadline_ms=21600000` / 6h). Start resume deadline only after checks leg finishes. Relay child stdout unchanged on success. On timeout: relay partial stdout if any; do **not** emit composite `NEXT_ACTION=continue`.
  - Outer Bash `timeout` values remain sum ceilings only (`14400000` for checks-commit-route, `32400000` for checks-step5-resume); per-leg child timeouts preserve prior sequential leg budgets independent of how long earlier legs ran within the outer ceiling.
- **Commit-leg child IPC** (blocking gap closure):
  - Register a child-only surface in `python/cli.py`:
    - Preferred: extend standalone `implement commit-route` with `--emit-next-action false` (default `true`; standalone behavior unchanged).
    - Child argv pin: `python/cli.py implement commit-route --site <site> --implement-tmpdir <tmpdir> --emit-next-action false`.
    - **Forbid** spawning the public `commit-route` CLI with default `emit_next_action=True` from composite parents (duplicate `NEXT_ACTION` risk).
  - Child stdout grammar (no line-anchored `NEXT_ACTION`):
    - Exactly one line-anchored `COMMIT_ROUTE_OUTCOME=continue|seeded-stall|seed-failed`.
    - Relayed commit KVs (`COMMITTED`, `ERROR`, `SHA`, `COMMIT_OUTCOME`, etc.) via existing `_relay_commit_kvs(..., include_next_action=False)` shape.
  - Parent `_run_commit_route_leg` parses only that child envelope after `_run_leg_with_timeout`; maps to `CommitRouteOutcome`.
  - On commit-leg `TimeoutExpired` after group kill: parent seeds stall (not child); emit composite `NEXT_ACTION=stall` only when seeding succeeds.
- **Commit-route emission split**:
  - Refactor `_commit_route_run` and `_commit_route_stall` to accept `emit_next_action: bool = True`.
  - When `emit_next_action=False`: return `CommitRouteOutcome` (`continue` | `seeded-stall` | `seed-failed`); emit child `COMMIT_ROUTE_OUTCOME=`; relay commit KVs; **do not** print `NEXT_ACTION`.
  - Standalone `commit_route_main` keeps default `emit_next_action=True` (unchanged behavior).
  - `checks_commit_route_main` calls commit leg only via the child CLI above; emits **exactly one** authoritative line-anchored composite `NEXT_ACTION` after the full checks+commit chain.
- **Structured commit-leg stall outcomes**:
  - `continue` → composite emits exactly one `NEXT_ACTION=continue`.
  - `seeded-stall` → composite emits exactly one `NEXT_ACTION=stall`.
  - `seed-failed` → composite emits **no** `NEXT_ACTION`; return non-zero; orchestrator invalid-envelope fail-closed at folded sites.
  - Standalone `commit_route_main` with `emit_next_action=True` preserves current behavior: `seed-failed` returns rc `1` without `NEXT_ACTION=stall`.
- **Verb-specific `NEXT_ACTION` ownership**:
  - `checks-commit-route`: composite emits exactly one `NEXT_ACTION` (`continue` | `stall` | `checks-failed`) only after the full checks+commit chain. Never emit `NEXT_ACTION=stall` on `seed-failed`.
  - `checks-step5-resume`: composite emits `NEXT_ACTION=checks-failed` only on checks failure or checks-leg timeout. On checks pass, invoke resume child and **relay resume stdout unchanged**. Do **not** emit composite-level `NEXT_ACTION=continue`. Step 6 authorization still requires `STEP5_REVIEW_STATUS=` from relayed resume output (NEVER #4).
- **Composite stdout parsing slice** (orchestrator pin):
  - Capture the **full** composite Bash stdout as one string.
  - **Checks slice**: whitespace-token-scan **only the first physical line** of the capture for checks keys (`REDACTED_LOG_FILE`, `FAILURE_REASON`, `RELEVANT_CHECKS_OK`, `RELEVANT_CHECKS_SKIPPED`, `STATUS`, `EXIT_CODE`, `PHASE`). Do **not** use line-oriented `parse_kv` on that line.
  - **Composite routing**: parse exactly one line-anchored composite `NEXT_ACTION=` anywhere in the capture (existing invalid-envelope rules). Ignore tokens on the leading checks relay line for composite `NEXT_ACTION` / resume authorization.
  - **`checks-step5-resume` success path**: apply resume lacks-envelope branches and `STEP5_REVIEW_STATUS` gate to the **full capture** using token-aware KV extraction (same key set as today's ~682–684 contract). Composite `NEXT_ACTION=continue` alone is **not** Step 6 authorization. When `STEP5_REVIEW_STATUS=` is present, route by the Step 5 status table only.
  - **`checks-step5-resume` lacks-envelope path** (when capture lacks `STEP5_REVIEW_STATUS=`): evaluate in order on the full capture — (1) relayed line-anchored `NEXT_ACTION=stall` → Step 18; (2) relayed `NEXT_ACTION=continue` without `STEP5_REVIEW_STATUS=` → preflight/resume failure, `STALL_STEP=5`, Step 18; (3) missing/duplicate/malformed/non-zero-without-`NEXT_ACTION` → invalid envelope, Step 18; (4) non-zero rc with parsed `NEXT_ACTION=continue` → envelope failure. Do **not** apply lacks-envelope handling when composite emitted `NEXT_ACTION=checks-failed` (checks never passed).
- Keep repair paths in prose.
  - `NEXT_ACTION=checks-failed` enters the Checks Failure Entry Macro.
  - After repair-loop `NEXT_ACTION=continue` at folded sites, re-invoke the **same composite launcher** with identical argv.
  - Terminal Step 5 handoff stalls still run the existing `--record-only` timing path before durable bail.
- **Background timeouts** preserve prior sequential ceilings at the Bash layer:
  - Step 3: `timeout: 10800000` (unchanged; checks-only).
  - `checks-commit-route`: `timeout: 14400000`.
  - `checks-step5-resume`: `timeout: 32400000`.
- Retire conflicting prose at folded sites (see Files section for SKILL, `step5-review-branches.md`, harness needles).

## Files to modify/create

### UPDATED: python/implement_dispatch.py

- Add `import checks` at module scope (alongside existing `import proc`).
- Add `_run_leg_with_timeout(*, argv, deadline_ms, label)`.
  - Spawn with `start_new_session=True`.
  - Forward `timeout=deadline_ms/1000` to `subprocess.run` or `proc.run`.
  - On `TimeoutExpired`: `os.killpg` the child process group; drain output; return timeout result.
  - Extend `_run_cli_capture` with optional `timeout: float | None = None` forwarded to the same helper (do not call with unsupported kwargs).
- Add `_checks_relay_line(captured: dict[str, str]) -> str`.
  - Format one whitespace-delimited line matching `checks_run_relevant_main` stdout grammar.
- Add `_parse_whitespace_kv_line(line: str) -> dict[str, str]`.
  - Token-scan `KEY=value` pairs; used for checks relay only.
- Add `_run_relevant_checks_for_site(*, implement_tmpdir, checks_site, deadline_ms) -> tuple[dict[str, str], bool]`.
  - Run checks via `_run_leg_with_timeout(["checks", "run-relevant", "--site", checks_site, "--tmpdir", str(implement_tmpdir)], ...)`.
  - Parse relay line from child stdout first line via `_parse_whitespace_kv_line`.
  - On timeout: synthetic `{"STATUS": "fail", "FAILURE_REASON": "checks-leg-timeout"}` and `timed_out=True`.
- Add `_relay_checks_stdout`, `_checks_pass`.
- Add `CommitRouteOutcome` tagged result (`continue`, `seeded-stall`, `seed-failed`).
- Refactor `_commit_route_run` / `_commit_route_stall`:
  - Add `emit_next_action: bool = True`.
  - When `emit_next_action=False`: return `CommitRouteOutcome`; print exactly one line-anchored `COMMIT_ROUTE_OUTCOME=<value>`; relay commit KVs without `NEXT_ACTION`.
  - `_commit_route_stall`: `seeded-stall` only when `_seed_durable_stall_state` succeeds; else `seed-failed`.
- Extend `commit_route_main`:
  - Add `--emit-next-action` (`store_true` default `True` via `nargs='?'` / `const` pattern or explicit `choices` default `true`; child passes `false`).
  - When `--emit-next-action false`: print child envelope only; no `NEXT_ACTION`.
- Add `_run_commit_route_leg(*, site_name, implement_tmpdir, deadline_ms) -> tuple[CommitRouteOutcome, str]`.
  - Spawn **only** `implement commit-route --site ... --implement-tmpdir ... --emit-next-action false` via `_run_leg_with_timeout`.
  - Parse `COMMIT_ROUTE_OUTCOME=` from child stdout (line-anchored).
  - On child timeout: parent seeds stall; return `seeded-stall` or `seed-failed`.
- Add `checks_commit_route_main` (using child commit leg + composite `NEXT_ACTION` ownership).
- Add `_run_step5_resume_leg(*, implement_tmpdir, final_round_num, deadline_ms) -> tuple[int, str]`.
  - Spawn `implement step-5-resume --final-round-num N --ready-to-commit` via `_run_leg_with_timeout`; relay stdout on completion.
- Add `checks_step5_resume_main` (composite `NEXT_ACTION` only for `checks-failed`).
- Keep standalone `commit-route` (default emit) and `step-5-resume` behavior unchanged at orchestrator call sites outside composites.
- Avoid adding new Bash scripts.

### UPDATED: python/cli.py

- Register:
  - `("implement", "checks-commit-route")`
  - `("implement", "checks-step5-resume")`
- Ensure `implement commit-route` forwards `--emit-next-action`.
- Add all three to the machine-stdout allowlist near `implement commit-route`.

### UPDATED: python/test_implement_dispatch.py

- Registry tests for new verbs and `--emit-next-action false` on `commit-route`.
- Unit coverage for checks relay + whitespace parsing (pass/fail; multi-token line; monkeypatch negative test that `_parse_kv` is not used for checks envelope).
- Unit coverage for `emit_next_action=False` / `COMMIT_ROUTE_OUTCOME=` child envelope:
  - Inner path relays commit KVs without `NEXT_ACTION`.
  - `seeded-stall` vs `seed-failed` distinct.
  - Standalone `commit_route_main` still emits exactly one `NEXT_ACTION`.
  - Composite child spawn uses `--emit-next-action false` (assert argv; forbid default public CLI in composite parent).
- Unit coverage for `_run_leg_with_timeout`:
  - Hung child is group-killed on timeout.
  - Checks timeout → `NEXT_ACTION=checks-failed`; commit leg not started.
  - Commit timeout → parent seeds stall; composite `NEXT_ACTION=stall` only on success.
  - Resume timeout → no composite `NEXT_ACTION=continue`; resume child gets full `resume_deadline_ms` regardless of checks duration.
- Unit coverage for `checks-commit-route` and `checks-step5-resume` (plus `COMMIT_ROUTE_OUTCOME` parsing).
- Reuse existing monkeypatch patterns for `_invoke_cli`, `_run_leg_with_timeout`, subprocess timeout, and `checks.run_relevant_checks`.

### UPDATED: skills/implement/SKILL.md

- **Checks Failure Entry Macro**:
  - Opener: after Step 3 `STATUS=fail` **or** folded composite `NEXT_ACTION=checks-failed`.
  - Item 1: at folded sites, read relayed `REDACTED_LOG_FILE` via whitespace scan of **first line** of composite capture.
  - Item 3: Step 3 capture remains `run-step-checks.sh --site step3`; folded sites use composite verbs per `checks-repair-loop.md` §2.
  - Item 4 — site split (sole normative rule):
    - **Step 3 only**: repair-loop `NEXT_ACTION=continue` → proceed on Step 3 success path; do **not** re-invoke checks fence.
    - **Folded sites** (Step 5 self-review, Step 5 MAV/coder, Step 6): repair-loop `NEXT_ACTION=continue` → re-run the §2-pinned composite launcher with **identical argv** before any success-path routing.
  - Item 5: after repair-loop `continue` at folded sites, re-run same composite launcher (not `run-step-checks.sh` alone).

- **Step 5 self-review** — replace legacy steps 7–8 with **one numbered step**:

```
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review
```

  - `run_in_background: true`, `timeout: 14400000`.
  - Parse exactly one line-anchored composite `NEXT_ACTION`; `continue` → steps 9–11; `stall` → Step 18; `checks-failed` → repair macro `--site step5-self-review`; seed-failed / missing `NEXT_ACTION` → invalid envelope fail-closed `STALL_STEP=5`.
  - Delete legacy fences.

- **Step 5 MAV/coder handoff** — one background composite fence:

```
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"
```

  - `run_in_background: true`, `timeout: 32400000`.
  - `checks-failed`: repair macro `--site step5-mav --checks-site step5-review-fixes`.
  - On checks pass: apply Composite stdout parsing slice and full resume envelope contract.
  - Retain `--record-only` timing fence for terminal repair stalls.
  - Delete legacy fences.

- **Step 6 / Step 7** (FILES_CHANGED=true) — one background fence:

```
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement checks-commit-route --checks-site step6 --commit-site step7 --emit-step7-breadcrumb
```

  - `run_in_background: true`, `timeout: 14400000`.
  - `continue` → Step 7 7.r; `checks-failed` → repair `--site step6`; `stall` → Step 18; seed-failed → invalid envelope `STALL_STEP=7`.
  - Delete standalone Step 7 `commit-route` on FILES_CHANGED=true path.
  - Preserve FILES_CHANGED=false skip path unchanged.

### UPDATED: skills/implement/references/step5-review-branches.md

- Update contract header and `main-agent-vote-required` / `coder-main-agent-required` endings: retarget from shared captured relevant-checks fence + timing/commit/reinvoke sequence to single `checks-step5-resume` fence + resume-envelope parsing blockquote.

### UPDATED: skills/implement/references/checks-repair-loop.md

- §1: add folded-site entry via composite `NEXT_ACTION=checks-failed`.
- §2: replace capture/re-capture sentences at folded sites with composite one-liners.
- §4: site-split-only normative prose; delete global `run-step-checks.sh` re-capture mandate.

### UPDATED: scripts/test-implement-structure.sh

- Replace folded standalone needles with three composite verb invocations.
- Keep Step 3 `run-step-checks.sh --site step3`.
- Add structure assertions for `NEXT_ACTION=checks-failed`, composite parsing slice, `COMMIT_ROUTE_OUTCOME` / `--emit-next-action false` child pin, process-group kill, macro item 4 folded-site re-capture.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

- Extend `is_invocation_site` to count composite verbs plus Step 3 `run-step-checks.sh`; keep expected site count at 4.

### UPDATED: scripts/test-implement-fence-shape.sh

- Update `EXPECTED_NEW` / `EXPECTED_OLD` after three paired fence removals (net reduction of three immediate-background fences).

## Edge cases

- **Checks failure with no redacted log**: composite emits `NEXT_ACTION=checks-failed`; §1 structural gate still routes to stall when `FAILURE_REASON` is structural.
- **Checks-leg timeout**: process group killed; `NEXT_ACTION=checks-failed` with `FAILURE_REASON=checks-leg-timeout`; commit/resume not started.
- **Nested descendants on commit/resume timeout**: group kill prevents post-timeout tree mutation before stall seeding.
- **Checks pass + commit `seeded-stall`**: exactly one composite `NEXT_ACTION=stall`.
- **Checks pass + commit `seed-failed`**: no composite `NEXT_ACTION`; invalid-envelope fail-closed.
- **Resume preflight failure**: `STEP5_REVIEW_STATUS` gate on full capture unchanged; composite does not add `NEXT_ACTION=continue` after checks alone.
- **Resume-leg timeout**: partial stdout relayed; no composite `NEXT_ACTION=continue`.
- **Duplicate `NEXT_ACTION`**: prevented by `--emit-next-action false` and composite-only emission.
- **Step 6 `FILES_CHANGED=false`**: skip composite; proceed to Step 7a.
- **Repair re-entry at folded sites**: full composite re-run per macro item 4 / §4 site-split.

## Failure modes

- Checks child raises unexpectedly: `NEXT_ACTION=checks-failed`; no commit/resume.
- Composite verb missing `IMPLEMENT_TMPDIR`: usage error; fail-closed.
- Invalid `FINAL_ROUND_NUM` or missing `--checks-site`: argparse error.
- Composite spawns public `commit-route` without `--emit-next-action false`: duplicate `NEXT_ACTION`; mitigated by tests + argv pin.
- Orchestrator uses `parse_kv` on checks relay line: mis-read `REDACTED_LOG_FILE`; mitigated by first-line whitespace scan + tests.
- Composite maps `seed-failed` to `NEXT_ACTION=stall`: mitigated by `CommitRouteOutcome` + tests.
- Timeout kills wrapper only: nested processes survive; mitigated by `start_new_session` + `killpg`.
- SKILL / `step5-review-branches.md` drift: mitigated by reference retarget + structure harness needles.

## Testing strategy

- `python3 -m pytest python/test_implement_dispatch.py -q`
- `python3 -m pytest python/test_cli.py -q`
- `bash scripts/test-implement-structure.sh`
- `bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh`
- `bash scripts/test-implement-fence-shape.sh`
- `make lint && make py-lint && make py-test`

## Acceptance

- Two new Python verbs (`checks-commit-route`, `checks-step5-resume`) registered in `python/cli.py` and implemented in `python/implement_dispatch.py`.
- `commit-route` extended with `--emit-next-action false`; child-only surface tested.
- `SKILL.md` Step 5 self-review, Step 5 MAV/coder handoff, and Step 6/7 each replaced with one composite background fence.
- `step5-review-branches.md` and `checks-repair-loop.md` reference targets updated.
- All static harnesses pass: `test-implement-structure.sh`, `test-implement-relevant-checks-anti-halt.sh`, `test-implement-fence-shape.sh`.
- `make lint`, `make py-lint`, `make py-test` all pass.

review_status: complete
rounds_completed: 5
diff_lines: 960
