### FINDING_12: [OUT_OF_SCOPE] Exit-2 `session-entry-gate` / `session-setup` lines lack redaction pipe
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: On exit 2, `scripts/implement-bootstrap-invoke.sh` (~92–97) still prints raw `GATE_ERROR=` / `PREFLIGHT_ERROR=` from bootstrap stdout to stderr without the `redact-secrets.sh` | `redact-tmpdir-paths.sh` pipe used for `copy-plan` / `gh-issue-view`. Inherited from old `_ib_handle_bootstrap_exit2` in SKILL.md, not introduced here; extend redaction if those diagnostics can contain tokens or paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: pipe those grep’d lines through `redact-secrets.sh | redact-tmpdir-paths.sh` before stderr emission (optional hardening follow-up).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] `IMPLEMENT_TMPDIR` from bootstrap KV without canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap-invoke.sh` (~175–179) takes `IMPLEMENT_TMPDIR` from bootstrap KV output without `realpath`/prefix validation. A compromised or buggy bootstrap could point log reads and `bootstrap-routing.env` writes outside the intended session tree. Pre-existing trusted-tmpdir pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: validate tmpdir is under an expected prefix and owned by the current user before use (broader bootstrap hardening, not specific to this PR).


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] `implement-bootstrap.md` edit-in-sync omits parse helper siblings
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.md` edit-in-sync (~164–171) omits `parse-bootstrap-routing-envelope.{sh,md}` while `implement-bootstrap-invoke.md` includes them; bootstrap.md-only edits may skip the parse helper.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] `_inv_routing_key_allowed` assigns non-`local` `_inv_key`
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: At `scripts/parse-bootstrap-routing-envelope.sh:35`, `_inv_key=$1` is not `local`, mutating the caller’s `_inv_key`. Callers pass `"$_inv_key"` immediately after parsing each line, so per-iteration behavior is correct and SKILL Step 0 fences only use `_inv_out` / `_inv_rc` before sourcing.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] Post-source parse helper symbols leak into orchestrator shell
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: Sourcing leaves `_inv_line`, `_inv_key`, `_inv_value`, `_preserve_coder`, `_inv_routing_keys`, and helper functions in the orchestrator shell. Current SKILL.md blocks do not reference those names after the `.` line; hygiene risk if multiple `/implement` bash fences run in one persistent shell.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] Bash 3.2 compatibility note for `printf -v`
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: `printf -v` at `scripts/parse-bootstrap-routing-envelope.sh:69` is fine for Bash 3.1+; no Bash 4-only constructs observed in this script.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] Branch commit inventory (since `main`)
- **Reviewer(s)**: dyn-sourced-scope-leak-output.txt
- **Severity**: nit
- **Concern**: Branch includes `16a4d9c20` (extract wrapper #3298) plus five review-fix rounds and one larch-logs flush (`d7b8dbd34` … `66f2a8ec0`).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (for voters, not machine output):** Raw FINDING_13–17 from `cursor-specialist-security-output.txt` were positive attestations (NEVER #14, exit-2 redaction design, allowlist envelope, narrower export surface, `--preserve-coder`) and are not emitted as findings. The dominant actionable cluster is FINDING_1 + FINDING_5 (parse gap + missing parse-after-symlink test).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] Duplicate logic between `_inv_apply_routing_line` and if-empty arms
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/parse-bootstrap-routing-envelope.sh` (lines 85–103) duplicates assignment patterns between `_inv_apply_routing_line` and `_inv_apply_routing_line_if_empty`. Pre-existing style concern amplified by the new file; not a functional regression from this PR.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

