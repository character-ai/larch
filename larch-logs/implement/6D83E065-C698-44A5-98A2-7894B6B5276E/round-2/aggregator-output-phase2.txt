Normalized aggregator output from the 53 reviewer inputs. Merged items that describe the same behavioral risk; kept separate items that need different fixes or code paths.

### FINDING_1: Design OOS path resolution triplicated across bash and Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Design OOS path resolution is triplicated across a bash function, checkpoint inline logic, and Python with no shared module. A future fix to resolver order or existence checks can land in one site and be missed in others, breaking Python vs bash parity on design-export-only OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a single bash helper plus `python/oos_paths.py` and import from `ship.py`; source the bash helper from `ship-pr.sh` and `oos-disposition-checkpoint.sh`.

### FINDING_2: Manifest `oos_observations` jq count and materialize policy duplicated in three callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Manifest `oos_observations` jq count and fail-closed vs fail-open materialize policy is duplicated in three callers. One caller could treat empty-array materialize failure as blocking while another continues silently if only one copy is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize count and policy in `materialize-manifest-oos.sh` stdout contract or a shared lib wrapper invoked by all three sites.

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

### FINDING_6: `write_description` pipeline subshell drops Description lines from manifest OOS blocks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `write_description` uses `sanitize|while` inside a redirected compound command; pipeline subshell drops Description output. Manifest `oos_observations` with non-empty description yield `### OOS_N` blocks missing `- **Description**:` lines; `/issue` files title-only issues and loses reproduction detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore heredoc-fed `while` (pre-round-1 pattern) or avoid pipe subshell; add test asserting Description text in `oos-accepted-main-agent.md`.

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

### FINDING_9: No behavioral harness for ship-pr materialize failure / `OOS_PENDING` pr-create guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New pr-prep materialize failure handling and pr-create `OOS_PENDING` guard have no behavioral harness—only static awk order pins. With `LARCH_SHIP_PR_IMPL=bash` (default), a regression could skip setting `OOS_PENDING` on materialize failure with manifest OOS, or create a PR while `OOS_PENDING=true`, without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a small ship-pr harness stubbing `materialize-manifest-oos.sh` to assert `OOS_PENDING`/conservative exit and pr-create refusal paths.

### FINDING_10: Step 2 fail-closed `manifest-oos-materialization-failed` path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Fail-closed `emit_bailed` `manifest-oos-materialization-failed` when manifest has non-empty `oos_observations[]` is untested. External implementer completes with OOS in manifest; materialize helper breaks; Step 2 could still emit `STATUS=complete` and skip OOS filing until ship time or never.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend `test-step2-dispatch.sh` (or sibling) with stubbed helper failure and assert `STATUS=bailed` / `REASON=manifest-oos-materialization-failed`.

### FINDING_11: Step 9a.1 combine/issue/sentinel procedure lacks end-to-end offline harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 9a.1 combine/issue/sentinel/larch-log procedure is documentation plus fixed-string pins only; no end-to-end offline harness. Helper or `/issue` wiring regressions in steps 4–6 could pass structure tests while orchestrator mis-orders steps in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional follow-up harness with fixture tmpdir and stubbed `/issue` stdout, or accept doc-only scope explicitly.

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

### FINDING_18: Python writes `phase=pr-create` before OOS gates complete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `phase=pr-create` is written before OOS gates finish, so state shows pr-create while the run still needs Step 9a.1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Keep pr-prep or write `oos-filing` phase until disposition passes.

### FINDING_19: Resolver ordering lacks dedicated unit tests for bash/Python parity
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Resolver is inline without focused unit tests for `DESIGN_TMPDIR` vs design-export vs flat ordering; refactors can break bash/Python parity without failing tests until integration paths run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add focused tests for `resolve_oos_accepted_design_path` ordering in `python/test_oos.py` or `test_ship.py`.

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

### FINDING_24: `has_title` dedup compares redacted incoming title to non-redacted on-disk headings
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: important
- **Concern**: Title dedup is asymmetric: `has_title` normalizes the incoming title with `normalize_title` (redaction + whitespace collapse) but compares to on-disk headings that only get whitespace/case normalization in awk, not the same `sanitize_public_text` pass. PII/URL redaction can change the string vs an existing heading, dedup misses, and a second `### OOS_N:` block is appended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Apply the same `sanitize_public_text` + whitespace normalization to extracted heading text in `has_title`, or compare a pre-redaction dedup key while still writing the redacted public title.

### FINDING_25: `sanitize_public_text` omits link-local/metadata and some internal host patterns
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Mechanical redaction covers a fixed internal-host/PII regex set but omits common non-public endpoints (e.g. `169.254.169.254`) and internal hostnames outside the hard-coded TLD suffix list. Manifest descriptions flow to `oos-accepted-main-agent.md` and `/issue` batch mode verbatim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Reuse or extract the shared outbound scrubber used elsewhere (or expand the regex set to include link-local/metadata ranges) and add regression tests for metadata-style URLs and non-suffix internal hosts.

### FINDING_26: Security audit drops observation description needed for private disclosure
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Security-routed observations are withheld from public OOS markdown, but `append_security_audit` persists only normalized title plus disposition line; description (actionable security content for SECURITY.md private disclosure) is discarded from tmpdir artifacts except manifest JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Append a redacted copy of title, description, phase, and any focus-area metadata to `security-oos-observations.md` (never to `oos-accepted-main-agent.md`), using the same `sanitize_public_text` path, and test that security-routed items retain redacted body text in the audit file only.

### OOS_1: [OUT_OF_SCOPE] Duplicate `### Warnings` headers (same as in-scope materialize helper fix)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `append_security_audit` always prints new `### Warnings` header; multiple security-routed manifest OOS duplicate Warnings headers in `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Append bullets under existing Warnings section when present.

### OOS_2: [OUT_OF_SCOPE] `#308` triplet scan excludes `materialize-manifest-oos.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `#308` triplet scan excludes `skills/implement/scripts/materialize-manifest-oos.md`. Contract header drift in helper `.md` under scripts/ is not caught by references-headers job (pre-existing glob scope).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend references-headers scope or add implement-structure pin for helper contract triplet if desired.

### OOS_3: [OUT_OF_SCOPE] Schema trusts implementer to exclude security from `oos_observations[]` prose
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Security content without focus-area field can still be filed publicly after partial redaction; operational policy; out of branch scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Materialize fail-open when jq reports zero observations for malformed manifest shape
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest OOS in non-array shape may be silently dropped without `OOS_PENDING` when jq reports zero observations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Tighten jq validation or fail closed on materialize error when manifest object present.

### OOS_5: [OUT_OF_SCOPE] Security-only manifest OOS leaves private disclosure as manual operator step
- **Reviewer(s)**: dyn-oos-state-output.txt
- **Severity**: latent
- **Concern**: Manifest entries with dedicated security `focus-area` are excluded from `oos-accepted-main-agent.md` and only logged to `security-oos-observations.md`; with manifest-only security OOS, `ship-pr.sh` may never set `OOS_PENDING` because no accepted file grows. Matches security routing intent but not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-state-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Stale `DESIGN_TMPDIR` without fallback to `design-export/` (pre-existing)
- **Reviewer(s)**: dyn-oos-state-output.txt, dyn-manifest-bridge-output.txt, dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: When `DESIGN_TMPDIR` is set but `$DESIGN_TMPDIR/oos-accepted-design.md` is missing, resolvers do not fall back to `$IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md`. Branch adds Python parity with existing bash behavior rather than introducing the miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-state-output.txt: Address the concern above.
  - From dyn-manifest-bridge-output.txt: Address the concern above.
  - From dyn-bash-runtime-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Stale `oos-issue-cap.md` references nonexistent assertion `9g`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Edit-in-sync references nonexistent assertion 9g in `test-implement-structure.sh`; contributors may search for 9g and get false leads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update the reference to the actual OOS structure-test block or remove the stale label.

### OOS_8: [OUT_OF_SCOPE] `run_oos_disposition_gate_if_required` omits `--filed-urls-strict-file` for design path (pre-existing)
- **Reviewer(s)**: dyn-bash-runtime-output.txt, dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: `run_oos_disposition_gate_if_required_before_oos_pending_false` in pr-prep does not pass `--filed-urls-strict-file` for the design path while the Step 8+ checkpoint does. Not introduced by materialization hooks in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.
  - From dyn-python-parity-output.txt: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] Python driver has no `--resume-phase pr-create` equivalent (pre-existing)
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python driver reruns checks, postbump, and pr-prep on every invoke; predates branch but amplifies size-guard regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] Prompt-side sanitize at Step 9a.1 combine/file time (pre-existing)
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Steps 3.4, 4, and 6 rely on prompt-side “Sanitize before compose” rather than mechanical scrubber at combine/file time for design/review accepted-OOS sources that never pass through `materialize-manifest-oos.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] Full `manifest.json` descriptions in run-log artifacts (pre-existing)
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Security-routed manifest observations can remain in `$IMPLEMENT_TMPDIR/manifest.json` with full descriptions; unchanged by new security-routing helper; can leak if manifest is copied into committed run logs without redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

---

**Merge notes (brief):** Input findings 4/13/28, 5/24/35/36/38, 6/8, 9/25, 10→OOS_1, 18/48, 19/51, 23/35/27, 31/42, 32/45, 33/37/40→OOS_6, 34→OOS_5, 41/47→OOS_8 were merged. Generic “Address the concern above” bullets were omitted where the concern field already carried the substantive fix text from dyn reviewers; slots with only that placeholder and no inline fix in the concern were omitted per aggregator rules.
