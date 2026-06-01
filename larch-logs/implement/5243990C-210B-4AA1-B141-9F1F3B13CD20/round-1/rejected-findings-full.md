### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate state-format validation scans
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_ship_pr_state` and `check_ship_pr_state_format` duplicate malformed-line validation, risking drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Implement validate_ship_pr_state as a thin wrapper around check_ship_pr_state_format plus larch_err/exit 3.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Step 18 structure test omits non-empty summary pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Structural tests do not require the `-s "$IMPLEMENT_TMPDIR/summary-final.md"` guard for Step 18 emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend awk or grep to require [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ] in emit prose


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Non-atomic regular-file check before mv
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ship-pr-state.sh` can be replaced with a symlink between the regular-file check and the subsequent `mv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use directory-fd + renameat / O_NOFOLLOW-style writes, or document single-runner + strict tmpdir permissions as the only control.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Helpers accept arbitrary implement tmpdirs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `clear-stall`, `seed-terminal-state`, and `step-18b-final-report` accept any existing directory as `--implement-tmpdir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse canonical_dir + validate_tmpdir_path (or session resolver binding) before touching paths under tmpdir.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate clear/seed guard and commit plumbing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `cmd_clear_stall` and `cmd_seed_terminal_state` repeat guard, temp-write, `mv`, and reread-assert logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared guard and commit helpers used by both subcommands.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Orchestrator KV parsing is not strict
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: First-match `awk -F=` parsing of `EMIT_BODY` / `WFR_RC` can be skewed by duplicate or malformed contract lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse with anchored patterns (e.g. ^EMIT_BODY=(true|false)$) or a shared strict KV parser.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: mv failure leaves orphan tmp files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Failed `mv` after successful temp write can leave `.tmp` files in `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: rm -f "$tmp" in mv failure handlers before emit_cleared_false_exit / emit_seeded_false_exit.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Wrapper no-write sentinel check is not universal
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: The Step 18b harness only checks `.step17-emitted` is not written in one case, not across the full wrapper matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: After each `run_wrapper`, assert `[ ! -f "$tmpdir/.step17-emitted" ]` (or centralize that check in `run_wrapper`).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Unused token-report return variable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `token_rc` is assigned on token-report failure but never read or emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove token_rc or emit TOKEN_REPORT_RC for operators.
  - From cursor-specialist-edge-cases-output.txt: Remove token_rc or emit TOKEN_REPORT_RC if orchestrators need visibility.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

