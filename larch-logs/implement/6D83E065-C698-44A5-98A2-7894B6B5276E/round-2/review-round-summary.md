# Review Round 2

- Mode: `diff`
- 17 accepted, 9 rejected (8 exonerated)

## Accepted Findings

### FINDING_10: Step 2 fail-closed `manifest-oos-materialization-failed` path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Fail-closed `emit_bailed` `manifest-oos-materialization-failed` when manifest has non-empty `oos_observations[]` is untested. External implementer completes with OOS in manifest; materialize helper breaks; Step 2 could still emit `STATUS=complete` and skip OOS filing until ship time or never.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend `test-step2-dispatch.sh` (or sibling) with stubbed helper failure and assert `STATUS=bailed` / `REASON=manifest-oos-materialization-failed`.


### FINDING_12: Harness lacks Description-field and security-audit regression assertions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-materialize-manifest-oos.sh` does not assert `- **Description**:` presence, security-routed audit trail (`security-oos-observations.md`), or dual-invocation idempotency. Regressions in `write_description`, security routing, or duplicate security append on re-run would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add contains check for `- **Description**:` with expected sanitized substring; optional multiline case.
  - From cursor-specialist-testing-output.txt: Add a case checking `security-oos-observations.md` and/or `execution-issues.md` Warnings breadcrumb.
  - From cursor-specialist-edge-cases-output.txt: Add second-invocation security-only case.


### FINDING_13: Security-routed OOS titles written into public `execution-issues.md` Warnings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `append_security_audit` writes security-routed OOS titles into `execution-issues.md` Warnings; that file is flushed to committed larch-logs and the PR, so security finding titles become durable public metadata despite `/issue` filing being skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use title-free warnings or reference `security-oos-observations.md` only in execution-issues; keep titles in session-local security audit file.


### FINDING_14: Security routing inspects description only, not title or structured focus-area fields
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: `security_focus_area` only inspects description, not title, JSON `focus-area`/`focus_area`, or heading-embedded markers. Security-only signals in title/JSON can materialize into `oos-accepted-main-agent.md` and be counted non-security by `oos-non-security-block-count.awk`, reaching public `/issue` filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Run gate-aligned predicate on composed block or copy focus-area into body; add title-only focus-area harness case.
  - From dyn-public-redaction-output.txt: Before append, evaluate title, description, and structured manifest fields with the same gate-aligned predicate used in `oos-non-security-block-count.awk`; when routing to the private path, emit a proper `- **focus-area**:` field line in the security audit artifact (not in public markdown) and add harness cases for JSON-field and title-only markers.


### FINDING_15: `redact-secrets.sh` optional in `sanitize_public_text` fails open on secrets
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: If `redact-secrets.sh` is missing or not executable, `sanitize_public_text` passes manifest title/description through with only local sed rules, failing open on the secrets family while Step 2 fail-closes and `/issue` relies on that scrubber. Token-bearing manifest text can reach gate-visible accepted-OOS files and public `/issue` bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed when `redact-secrets` missing and observations non-empty; add secret redaction regression test.
  - From dyn-public-redaction-output.txt: Fail closed (non-zero exit) when `oos_observations[]` is non-empty and `redact-secrets.sh` is not executable, mirroring the Step 2 redactor contract; keep fail-open behavior only for empty/absent observation arrays.


### FINDING_16: Security-only manifest OOS never sets `OOS_PENDING` or blocks PR
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When all `oos_observations` are security-routed, materialize exits 0, ship-pr/ship.py see no non-empty accepted OOS files, disposition gate passes with zero non-security blocks, and PR opens without SECURITY.md handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After materialize, gate on non-empty `security-oos-observations.md` (set `OOS_PENDING` / `NEEDS_USER` with explicit security-routing reason).


### FINDING_17: Security-routed manifest OOS not idempotent across Step 2 and ship double materialize
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-manifest-bridge-output.txt
- **Severity**: important
- **Concern**: `append_security_audit` always appends another `### Security OOS:` block and Warnings section on every run; only non-security paths use `has_title`. Designed double invocation (Step 2 + ship pr-prep) duplicates security audit noise and multiplies Warnings headers even when `oos-accepted-main-agent.md` is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip security append when title already recorded; use `append-execution-issue.sh` for warnings.
  - From dyn-manifest-bridge-output.txt: Before `append_security_audit`, skip when the title is already recorded (e.g. grep `security-oos-observations.md` for `### Security OOS: <title>` or track normalized titles in a small sentinel), and append the warning bullet via `scripts/append-execution-issue.sh --category Warnings` so existing category headers are reused instead of emitting a new `### Warnings` block each time.


### FINDING_20: Python blocks on non-empty accepted-OOS file size before `_oos_gate`, blocking post–Step 9a.1 reinvoke
- **Reviewer(s)**: dyn-oos-state-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: After `materialize-manifest-oos.sh`, the driver returns `NEEDS_USER_OOS_FILING` whenever any accepted-OOS markdown file is non-empty (`st_size > 0`) before `_oos_gate` runs. Bash `run_pr_create_phase` blocks only on `OOS_PENDING=true`. After Step 9a.1, accepted files remain populated, so reinvoke hits the size guard again and PR creation never proceeds even when disposition is satisfied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-state-output.txt: Remove the non-empty-file shortcut at `421-434`. Match bash: return `NEEDS_USER_OOS_FILING` when `ctx.oos_pending` is true (and persist `OOS_PENDING=true` in `ship-pr-state.sh` on the first blocking pass, e.g. when materialization adds accepted OOS or the gate fails); after the orchestrator clears `OOS_PENDING` and filing completes, allow `ensure_pr` to run—optionally call `_oos_gate` once before PR create when files remain, but do not treat mere file presence as sufficient to block forever.
  - From dyn-python-parity-output.txt: Remove the size-only shortcut or run `_oos_gate` first and only hand back on `disposition_ok` failure; optionally add a Python `pr-create`-only resume path aligned with bash so post-filing reinvokes do not re-enter full `pr-prep`.


### FINDING_21: Python path does not set or persist `OOS_PENDING=true` when filing should remain pending
- **Reviewer(s)**: dyn-oos-state-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` serializes `OOS_PENDING` from `ctx.oos_pending`, but the Python path does not set `oos_pending=True` on accepted OOS, materialize failure with non-empty `oos_observations[]`, or failed `_oos_gate` (unlike bash `state_set OOS_PENDING true`). Runs can emit `NEEDS_USER_OOS_FILING` while `ship-pr-state.sh` still has `OOS_PENDING=false`; `RunContext.from_env()` does not read state back.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-state-output.txt: When returning `NEEDS_USER_OOS_FILING` for accepted OOS, materialization failure with non-empty `oos_observations[]`, or a failed `_oos_gate`, call `_write_ship_state(ctx.with_(oos_pending=True), phase="pr-create")` before returning; clear it only after the documented checkpoint + `OOS_PENDING=false` persistence path.
  - From dyn-python-parity-output.txt: On the same failure predicate as bash, persist `OOS_PENDING=true` via `_write_ship_state` before returning `NEEDS_USER_OOS_FILING`, or document and test that the Python path is JSON-outcome-only and never consults state for OOS pending.


### FINDING_22: Python `_oos_gate` uses commit subjects only; bash scans full commit bodies
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: `_oos_gate` feeds `oos.disposition_ok` from `git log --format=%s` (subjects only) and only when `ctx.run_id` is set. Bash `oos-disposition-gate.sh` scans full bodies (`--format=%B`) over `merge-base..HEAD`. Inline-triage breadcrumbs in commit bodies can satisfy bash but be invisible to Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Mirror bash: always resolve `merge-base..HEAD` (or `origin/main..HEAD`) and pass full commit messages into `commit_range_messages`, or invoke `oos-disposition-gate.sh` instead of the inlined helper.


### FINDING_23: Python pre-PR OOS enforcement duplicated instead of invoking gate/checkpoint scripts
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Pre-PR OOS enforcement is duplicated in `oos.disposition_ok` instead of calling `oos-disposition-gate.sh` / `oos-disposition-checkpoint.sh`. Checkpoint-only rules (e.g. requiring `--oos-issues-ndjson` when `non_sec_oos > 0`) are not applied on the Python path, so bash and Python can disagree on pass/fail at the same tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Subprocess the same gate/checkpoint scripts with the same argv shape as `ship-pr.sh` / `oos-disposition-checkpoint.sh`, or add explicit parity tests that run both paths on identical fixtures.


### FINDING_26: Security audit drops observation description needed for private disclosure
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Security-routed observations are withheld from public OOS markdown, but `append_security_audit` persists only normalized title plus disposition line; description (actionable security content for SECURITY.md private disclosure) is discarded from tmpdir artifacts except manifest JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Append a redacted copy of title, description, phase, and any focus-area metadata to `security-oos-observations.md` (never to `oos-accepted-main-agent.md`), using the same `sanitize_public_text` path, and test that security-routed items retain redacted body text in the audit file only.


### FINDING_3: Python materialize failures skip `append-tool-failure.sh` stderr capture
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Python materialize failures use ad-hoc `execution-issues.md` append instead of `append-tool-failure.sh` with captured stderr. Operators lose helper stderr on `LARCH_SHIP_PR_IMPL=python` runs, making ship-time materialize regressions harder to debug than bash Step 2 or ship-pr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Write materialize stderr to a tmp log and call `append-tool-failure.sh` with site `pr-create` and redact mirroring `step2-implement.sh`.


### FINDING_4: Structure test does not pin MANDATORY load directive at each OOS entry point
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Structure/regression guards count `oos-pipeline.md` path references (≥3) instead of requiring the MANDATORY load-directive substring at each Step 9a.1 entry point (Exit 0, OOS checkpoint, Python dispatch) as the plan specifies. A refactor can remove load lines while unrelated path citations remain and CI still passes, repeating silent-deletion failure modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add per-entry-point window checks that `MANDATORY READ ENTIRE FILE` appears within N lines of Exit 0, OOS_PENDING, OOS checkpoint, and oos-filing dispatch anchors.
  - From cursor-specialist-testing-output.txt: Count `MANDATORY — READ ENTIRE FILE before executing the OOS pipeline` (≥3) and tie to Exit 0 / OOS checkpoint / Python dispatch blocks.
  - From cursor-specialist-plan-fidelity-output.txt: Add scoped greps or awk windows that require the exact MANDATORY load-directive string within the Exit 0 OOS_PENDING branch, the OOS checkpoint paragraph, and the Python `needs_user_reason=oos-filing` dispatch.


### FINDING_5: Security audit appends duplicate `### Warnings` headers instead of category upsert
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-manifest-bridge-output.txt, dyn-bash-runtime-output.txt
- **Severity**: important
- **Concern**: `append_security_audit` always inserts a new `### Warnings` header (raw `>> execution-issues.md`) instead of reusing `append-execution-issue.sh` category merge/locking. Multiple security-routed manifest OOS items—or re-runs—produce duplicate Warnings sections, bypassing the execution-issues category contract and confusing operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use `append-execution-issue.sh --category Warnings` or append under an existing Warnings header when present.
  - From cursor-specialist-edge-cases-output.txt: Use `append-execution-issue.sh` under one Warnings header.
  - From dyn-manifest-bridge-output.txt: Replace the raw `>> execution-issues.md` block with `append-execution-issue.sh --log "$implement_tmpdir/execution-issues.md" --category Warnings --entry '...'` (or equivalent locked upsert logic) so bullets append under a single warnings category.
  - From dyn-bash-runtime-output.txt: Route each security breadcrumb through `append-execution-issue.sh --category Warnings` (or mirror its awk-based header merge + lock) and only write `security-oos-observations.md` from `append_security_audit`.


### FINDING_7: Materialize failure leaves no accepted markdown; Step 9a.1 can pass and create PR without filing manifest OOS (bash)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Materialize failure sets `OOS_PENDING` but leaves no markdown; Step 9a.1 step-2 no-input exit + disposition pass + `--resume-phase pr-create` skips pr-prep rematerialize. Non-empty manifest `oos_observations[]` + `materialize-manifest-oos.sh` failure → orchestrator runs empty Step 9a.1 → gate passes with 0 blocks → PR created without filing manifest OOS (Python path blocks; bash does not).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-run materialize at start of Step 9a.1 or fail gate when manifest has OOS but no accepted blocks; or resume full ship/pr-prep not pr-create only until materialize succeeds.


### FINDING_8: `DESIGN_TMPDIR` preferred without existence check misses design-export OOS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `DESIGN_TMPDIR` is set but stale/missing, resolvers return `$DESIGN_TMPDIR/oos-accepted-design.md` and never fall through to `design-export/oos-accepted-design.md`. Accepted design OOS only under export can be missed for `OOS_PENDING` sizing and gate accepted-file lists (bash, Python, checkpoint).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Prefer `DESIGN_TMPDIR` only when that path exists; else design-export then flat path (bash+Python+checkpoint).
  - From cursor-specialist-edge-cases-output.txt: Unset env after export or fall through when env path missing (with bash parity if changed).


