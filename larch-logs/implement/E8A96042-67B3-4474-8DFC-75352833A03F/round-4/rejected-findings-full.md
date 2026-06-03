### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Harness omits non-regular `bootstrap-routing.env` fallback case
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Contract docs describe non-regular `bootstrap-routing.env` fallback, but the harness only tests symlink. A fifo or other non-regular file could break orchestrator parsing without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Exit-2 `GATE_ERROR` / `PREFLIGHT_ERROR` stderr not redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `GATE_ERROR` and `PREFLIGHT_ERROR` lines printed to stderr on exit 2 without `redact-secrets`. If bootstrap KV ever contains tokens, operators see them on the terminal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Run grepped KV lines through redact-secrets.sh and redact-tmpdir-paths.sh like copy-plan/gh-issue-view.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Wrapper still uses `_ib_*` locals after SKILL removed `_ib_*` helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Contributors searching for `_ib_` may edit the wrong layer after the SKILL removed `_ib_*` helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Three-layer Step 0 split exceeds original plan; needs contract doc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 0 split into invoke plus parse scripts exceeds the original two-layer plan, increasing cognitive load for Step 0 edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Canonical `_inv_routing_keys` list duplicated in four places
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-envelope-key-completeness-output.txt
- **Severity**: latent
- **Concern**: The canonical routing key list is duplicated in `implement-bootstrap-invoke.sh`, `parse-bootstrap-routing-envelope.sh`, `test-implement-structure.sh`, and `test-implement-bootstrap-invoke.sh` with only partial sync checks. Adding a consumer key can update one copy while degraded-tools or ship-pr routing breaks until another copy is noticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-envelope-key-completeness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `_inv_apply_routing_line_if_empty` duplicates allowlist as large `case`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_inv_apply_routing_line_if_empty` duplicates the allowlist as a large `case` statement. A new envelope key requires edits in the allowlist, case arms, export list, and three other files. The `case` should be replaced with allowlist-guarded `printf -v` and an empty check after `_inv_routing_key_allowed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: No dedicated offline harness for `parse-bootstrap-routing-envelope.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The parse helper has no dedicated behavioral harness. `--preserve-coder`, file-first vs stdout fallback, symlink skip, and stale-file behavior can regress while structure grep pins still pass until a live dirty-tree resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add fixture-based harness for parse-bootstrap-routing-envelope.sh covering stale file symlink and preserve-coder.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Success-path routing temp install lacks cleanup on `set -e` failure
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: On the success path in `implement-bootstrap-invoke.sh` (lines 201–205), under `set -euo pipefail`, failure of `cat "$_inv_routing_buf" >"$_inv_routing_tmp"` or `mv -f "$_inv_routing_tmp" "$_inv_routing_file"` aborts before stdout envelope emission and before `rm -f "$_inv_routing_buf"`, leaving temp files and yielding non-zero / partial `_inv_out` capture after bootstrap already completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Wrap the write in a small cleanup handler (e.g. `trap 'rm -f "$_inv_routing_buf" "$_inv_routing_tmp"' EXIT` scoped to that block, or `mv` then emit stdout from the installed file and `rm -f` both temps in a single `|| { …; exit 1; }` branch) so temp files are always removed and, if `bootstrap-routing.env` was written, stdout still emits the envelope (or a documented non-zero exit after printing it).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: `mktemp` failure in exit-2 redaction arms can yield exit 1 instead of 2
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: In the `copy-plan` / `gh-issue-view` exit-2 arms, `_ib_redacted_err=$(mktemp …)` runs under `set -e`. If `mktemp` fails, the wrapper exits 1 before the arm’s operator `printf` and before `exit 2`, so callers expecting bootstrap exit 2 (and the SKILL `if [ "$_inv_rc" -eq 2 ]; then exit 2` path) see the wrong code and may miss the canonical stderr message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Guard `mktemp` (e.g. `if _ib_redacted_err=$(mktemp … 2>/dev/null); then … redact …; rm -f "$_ib_redacted_err"; fi`) and always emit the existing operator string and `exit 2` even when redaction temp allocation fails.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

