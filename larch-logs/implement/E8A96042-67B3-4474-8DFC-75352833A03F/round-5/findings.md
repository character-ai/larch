Normalizing reviewer inputs into merged findings. Verifying a few code references for accurate titles (read-only).
Structured aggregator output (plain text). Positive security attestations (raw FINDING_13–17) are omitted — they describe enforced properties, not behavioral risks requiring fixes.

### FINDING_1: Stdout fallback omits `coder` / `coder_fallback` in parse script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sourced-scope-leak-output.txt
- **Severity**: important
- **Concern**: `_inv_apply_routing_line_if_empty` in `scripts/parse-bootstrap-routing-envelope.sh` (roughly lines 72–104) has no `coder` / `coder_fallback` arms, while `_inv_apply_routing_line` assigns them via `printf -v`. When `bootstrap-routing.env` is skipped (symlink / non-regular file per `implement-bootstrap-invoke.sh`) or missing keys, only the stdout envelope in `_inv_out` remains; `coder` and `coder_fallback` stay unset after the initial `unset` even though the wrapper stdout includes `coder=…` from phase selection. Step 0 routing can miss the continue row or pick the wrong implementer — a regression vs the old `_ib_kv_scan` path that parsed every stdout line including `coder=*`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add coder/coder_fallback to if-empty case or printf -v when empty; add symlink+parse harness coverage
  - From cursor-specialist-correctness-output.txt: Add coder/coder_fallback branches to _inv_apply_routing_line_if_empty (or reuse _inv_apply_routing_line for empty keys) and test parse after the symlink wrapper harness case.
  - From cursor-specialist-testing-output.txt: Add coder and coder_fallback to _inv_apply_routing_line_if_empty assignment case with the same non-empty guard used in _inv_apply_routing_line
  - From cursor-specialist-edge-cases-output.txt: Add coder/coder_fallback to _inv_apply_routing_line_if_empty or unify apply helpers; add parse+symlink harness case
  - From dyn-sourced-scope-leak-output.txt: Add `coder` and `coder_fallback` arms to `_inv_apply_routing_line_if_empty` (e.g. `[ -z "${coder:-}" ] && coder="$_inv_value"` with the same empty-value skip and `--preserve-coder` early-return as the file path), or call `_inv_apply_routing_line` for the stdout loop when the file pass was skipped; add a harness case that sources the parse script against a symlinked `bootstrap-routing.env` and asserts `coder` is exported.

### FINDING_2: Mixed `_ib_*` vs `_inv_*` names in bootstrap invoke wrapper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: New `scripts/implement-bootstrap-invoke.sh` wrapper (lines 42–68) uses `_ib_*` internal names while SKILL and parse helpers use `_inv_*`, adding trace friction in Step 0.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_3: Routing key allowlist duplicated in multiple places
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Canonical routing key list is duplicated (e.g. `scripts/test-implement-structure.sh` around line 555 and invoke/parse literals). Harness `expected_routing_keys` can drift even when invoke and parse still match.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_4: Overly broad `grep '*)'` pin in structure harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-structure.sh` (lines 588–589) pins default exit-2 handling with `grep '*)'`, which can false-positive on unrelated `case` arms containing the same token.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_5: No end-to-end test for symlink stdout path through parse script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Documented symlink / stdout-only routing path is covered at the wrapper level (`skills/implement/scripts/test-implement-bootstrap-invoke.sh` ~301–318 / ~1808–1827) but harness does not source `parse-bootstrap-routing-envelope.sh` afterward. CI can pass while the parse step drops `coder` on the documented fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Test wrapper then source parse-bootstrap-routing-envelope.sh with symlinked bootstrap-routing.env
  - From cursor-specialist-testing-output.txt: Add harness case that sources parse-bootstrap-routing-envelope.sh after wrapper success with symlinked bootstrap-routing.env and asserts coder and REPO from _inv_out
  - From cursor-specialist-edge-cases-output.txt: Add sourced-parse test with symlinked bootstrap-routing.env asserting exported coder

### FINDING_6: [OUT_OF_SCOPE] Duplicate logic between `_inv_apply_routing_line` and if-empty arms
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/parse-bootstrap-routing-envelope.sh` (lines 85–103) duplicates assignment patterns between `_inv_apply_routing_line` and `_inv_apply_routing_line_if_empty`. Pre-existing style concern amplified by the new file; not a functional regression from this PR.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_7: Default `*)` exit-2 handler not exercised in invoke harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-implement-bootstrap-invoke.sh` pins structural requirements for the wrapper default handler (e.g. ~335–343) but has no case with an unknown `STEP_FAILED`. Operator-message regressions on the generic exit-2 branch may not fail CI (related to structure harness gap at FINDING_4).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add run_exit2_case with unknown STUB_STEP_FAILED and assert bootstrap failed at step= on stderr
  - From cursor-specialist-plan-fidelity-output.txt: Add one exit-2 test with an unlisted STEP_FAILED and assert stderr message plus empty stdout.

### FINDING_8: Redaction failure operator strings untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-implement-bootstrap-invoke.sh` (~345–371) tests `copy-plan` / `gh-issue-view` redaction success but not `redact-secrets.sh` failure fallbacks; stderr operator text for redaction failure is unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub redact-secrets.sh to fail and assert stderr redaction failed operator text without leaking raw secrets

### FINDING_9: Success path without `IMPLEMENT_TMPDIR` in bootstrap stdout untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap-invoke.sh` (~423–427) exits 1 when bootstrap omits `IMPLEMENT_TMPDIR`, but the invoke harness has no regression stub for that success shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub success output without IMPLEMENT_TMPDIR line and assert exit 1

### FINDING_10: `mv` failure on `bootstrap-routing.env` aborts wrapper under `set -e`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `scripts/implement-bootstrap-invoke.sh` (~201–205), if bootstrap succeeds but `mv` to a read-only `bootstrap-routing.env` fails, `set -e` aborts the wrapper before emitting the stdout envelope. Orchestrator sees non-zero rc and no routing keys despite valid bootstrap stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On mv failure emit stdout envelope and warn (mirror symlink path) or exit 2 with operator message

### FINDING_11: Plan file inventory omits `parse-bootstrap-routing-envelope` artifacts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Implementation plan called for inline parse in SKILL.md; delivery uses `scripts/parse-bootstrap-routing-envelope.sh` (and contract sibling) not listed in the plan “Files to modify/create” inventory. Follow-ups scoped only to the plan list can miss parse contract and `--preserve-coder` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add parse-bootstrap-routing-envelope.{sh,md} to the plan file list and to implement-bootstrap.md edit-in-sync.

### FINDING_12: [OUT_OF_SCOPE] Exit-2 `session-entry-gate` / `session-setup` lines lack redaction pipe
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: On exit 2, `scripts/implement-bootstrap-invoke.sh` (~92–97) still prints raw `GATE_ERROR=` / `PREFLIGHT_ERROR=` from bootstrap stdout to stderr without the `redact-secrets.sh` | `redact-tmpdir-paths.sh` pipe used for `copy-plan` / `gh-issue-view`. Inherited from old `_ib_handle_bootstrap_exit2` in SKILL.md, not introduced here; extend redaction if those diagnostics can contain tokens or paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: pipe those grep’d lines through `redact-secrets.sh | redact-tmpdir-paths.sh` before stderr emission (optional hardening follow-up).

### FINDING_13: [OUT_OF_SCOPE] `IMPLEMENT_TMPDIR` from bootstrap KV without canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap-invoke.sh` (~175–179) takes `IMPLEMENT_TMPDIR` from bootstrap KV output without `realpath`/prefix validation. A compromised or buggy bootstrap could point log reads and `bootstrap-routing.env` writes outside the intended session tree. Pre-existing trusted-tmpdir pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: validate tmpdir is under an expected prefix and owned by the current user before use (broader bootstrap hardening, not specific to this PR).

### FINDING_14: [OUT_OF_SCOPE] `implement-bootstrap.md` edit-in-sync omits parse helper siblings
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.md` edit-in-sync (~164–171) omits `parse-bootstrap-routing-envelope.{sh,md}` while `implement-bootstrap-invoke.md` includes them; bootstrap.md-only edits may skip the parse helper.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_15: [OUT_OF_SCOPE] `_inv_routing_key_allowed` assigns non-`local` `_inv_key`
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: At `scripts/parse-bootstrap-routing-envelope.sh:35`, `_inv_key=$1` is not `local`, mutating the caller’s `_inv_key`. Callers pass `"$_inv_key"` immediately after parsing each line, so per-iteration behavior is correct and SKILL Step 0 fences only use `_inv_out` / `_inv_rc` before sourcing.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_16: [OUT_OF_SCOPE] Post-source parse helper symbols leak into orchestrator shell
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: Sourcing leaves `_inv_line`, `_inv_key`, `_inv_value`, `_preserve_coder`, `_inv_routing_keys`, and helper functions in the orchestrator shell. Current SKILL.md blocks do not reference those names after the `.` line; hygiene risk if multiple `/implement` bash fences run in one persistent shell.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_17: [OUT_OF_SCOPE] Bash 3.2 compatibility note for `printf -v`
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: `printf -v` at `scripts/parse-bootstrap-routing-envelope.sh:69` is fine for Bash 3.1+; no Bash 4-only constructs observed in this script.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_18: [OUT_OF_SCOPE] Branch commit inventory (since `main`)
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: Branch includes `16a4d9c20` (extract wrapper #3298) plus five review-fix rounds and one larch-logs flush (`d7b8dbd34` … `66f2a8ec0`).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters, not machine output):** Raw FINDING_13–17 from `cursor-specialist-security-output.txt` were positive attestations (NEVER #14, exit-2 redaction design, allowlist envelope, narrower export surface, `--preserve-coder`) and are not emitted as findings. The dominant actionable cluster is FINDING_1 + FINDING_5 (parse gap + missing parse-after-symlink test).
