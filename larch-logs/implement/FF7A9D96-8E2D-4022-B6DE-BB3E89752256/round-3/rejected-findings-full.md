### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: correctness: skills/implement/scripts/test-oos-disposition-gate.sh:538-539
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Disposition-gap grep uses substring step-8-oos-checkpoint. If negative validation grep is removed, validation-site log lines can false-pass disposition-gap assertion. Grep exact site token or Step step-8-oos-checkpoint — anchor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for former inline path: RUN_ID set, keyed ndjson missing, sole foreign ndjson discoverable. Regression reintroducing find-with-RUN_ID would ship without harness signal. Add positive keyed-path case and keep stale-RUN_ID as negative guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.sh:140
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Exported DESIGN_TMPDIR resolution is untested. Env-only DESIGN_TMPDIR could drift from --design-tmpdir without CI failure. Add harness case with export DESIGN_TMPDIR and no CLI flag.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:538-539
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Disposition-gap log grep uses substring that matches validation site name. False pass if logging format embeds both site tokens on one line. Use anchored grep on append header e.g. Step step-8-oos-checkpoint —.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Command injection:** Gate args use quoted expansions; `_oos_range` is derived from `git merge-base` / fixed literals (`HEAD`, `origin/main..HEAD`), not from session file contents. `git log --format=%B "$range"` in the gate keeps the range as a single operand (pre-existing gate behavior).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Command injection:** Gate args use quoted expansions; `_oos_range` is derived from `git merge-base` / fixed literals (`HEAD`, `origin/main..HEAD`), not from session file contents. `git log --format=%B "$range"` in the gate keeps the range as a single operand (pre-existing gate behavior).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Path handling:** `find` is rooted at `$IMPLEMENT_TMPDIR/larch-logs/implement` with `-mindepth 2 -maxdepth 2`. `RUN_ID` comes from `session-id` (typically `uuidgen`); path segments are not validated, but that matches the removed inline block and normal IDs do not contain `/` or `..`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path handling:** `find` is rooted at `$IMPLEMENT_TMPDIR/larch-logs/implement` with `-mindepth 2 -maxdepth 2`. `RUN_ID` comes from `session-id` (typically `uuidgen`); path segments are not validated, but that matches the removed inline block and normal IDs do not contain `/` or `..`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **AuthZ / bypass:** Fork / `REPO_UNAVAILABLE` skips still come from `ship-pr-state.sh` grep — same trust as before. Non-zero exits still block `OOS_PENDING` clear in `SKILL.md`; gate exit `2` now propagates instead of being collapsed to `1` (fail-closed for validation vs disposition gap).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **AuthZ / bypass:** Fork / `REPO_UNAVAILABLE` skips still come from `ship-pr-state.sh` grep — same trust as before. Non-zero exits still block `OOS_PENDING` clear in `SKILL.md`; gate exit `2` now propagates instead of being collapsed to `1` (fail-closed for validation vs disposition gap).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **Secrets:** Failures go through `append-tool-failure.sh` with `--redact`; checkpoint uses `|| true` on append so logging cannot override the saved exit code.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secrets:** Failures go through `append-tool-failure.sh` with `--redact`; checkpoint uses `|| true` on append so logging cannot override the saved exit code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **Ndjson binding:** When `session-id` is set but the keyed ndjson is missing, find-fallback no longer runs (harness “stale RUN_ID” case). That closes a prior confused-deputy where a sole foreign ndjson could satisfy disposition — a correctness hardening, not a regression.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ndjson binding:** When `session-id` is set but the keyed ndjson is missing, find-fallback no longer runs (harness “stale RUN_ID” case). That closes a prior confused-deputy where a sole foreign ndjson could satisfy disposition — a correctness hardening, not a regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: risk-integration: skills/implement/scripts/oos-disposition-checkpoint.sh:125-138
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Find fallback for oos-issues.ndjson is disabled whenever session-id is non-empty, unlike the removed inline block that re-discovered when the keyed file was missing. Stale session-id with one valid ndjson under another run dir now exits 2 (precondition) instead of adopting the sole file; run stalls until session-id or paths are repaired manually. Document RUN_ID-keyed-only semantics in checkpoint.md/SKILL; optionally restore single-candidate find when keyed path is missing only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: correctness: skills/implement/scripts/test-oos-disposition-gate.sh:546-548
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Disposition-gap log grep uses a substring that also appears inside step-8-oos-checkpoint-validation. Polluted execution-issues.md with both site strings could false-pass the exit-1 logging test. Grep the full Step header for the checkpoint site only, not a bare substring.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: **architecture** `skills/implement/scripts/oos-disposition-checkpoint.sh:72-76,19-30` — On `--design-tmpdir` CLI errors, if `IMPLEMENT_TMPDIR` is still unset and `prescan_implement_tmpdir` cannot find a later `--implement-tmpdir <dir>` (e.g. `"$CHECKPOINT" --design-tmpdir` alone, or `--design-tmpdir --implement-tmpdir` with no directory operand), `fail_validation` calls `log_checkpoint_failure` while `IMPLEMENT_TMPDIR` remains empty. That makes `append-tool-failure.sh` receive `--log /execution-issues.md` (root-relative), so required logging is best-effort dropped (`|| true`) and diagnostics land on the wrong filesystem path even though `_chk_log` correctly uses `${IMPLEMENT_TMPDIR:-/tmp}/…`. This breaks the contract that every non-zero exit records to `$IMPLEMENT_TMPDIR/execution-issues.md`. **Suggested fix:** Before any `fail_validation` in the parse loop, normalize unset `IMPLEMENT_TMPDIR` the same way as other CLI failures (e.g. `IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-/nonexistent}"` and set `_chk_log` under it), or derive `--log` from the directory of `_chk_log` when `IMPLEMENT_TMPDIR` is empty so `log_checkpoint_failure` always targets the implement tmpdir being validated.
- **Reviewer**: dyn-shell-safety-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/oos-disposition-checkpoint.sh:72-76,19-30` — On `--design-tmpdir` CLI errors, if `IMPLEMENT_TMPDIR` is still unset and `prescan_implement_tmpdir` cannot find a later `--implement-tmpdir <dir>` (e.g. `"$CHECKPOINT" --design-tmpdir` alone, or `--design-tmpdir --implement-tmpdir` with no directory operand), `fail_validation` calls `log_checkpoint_failure` while `IMPLEMENT_TMPDIR` remains empty. That makes `append-tool-failure.sh` receive `--log /execution-issues.md` (root-relative), so required logging is best-effort dropped (`|| true`) and diagnostics land on the wrong filesystem path even though `_chk_log` correctly uses `${IMPLEMENT_TMPDIR:-/tmp}/…`. This breaks the contract that every non-zero exit records to `$IMPLEMENT_TMPDIR/execution-issues.md`. **Suggested fix:** Before any `fail_validation` in the parse loop, normalize unset `IMPLEMENT_TMPDIR` the same way as other CLI failures (e.g. `IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-/nonexistent}"` and set `_chk_log` under it), or derive `--log` from the directory of `_chk_log` when `IMPLEMENT_TMPDIR` is empty so `log_checkpoint_failure` always targets the implement tmpdir being validated.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:33-51,72-76
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] prescan_implement_tmpdir adds complexity for rare CLI ordering edge case. Extra code path to maintain; prescan only handles first --implement-tmpdir in argv. Log validation failures without prescan when IMPLEMENT_TMPDIR unknown unless ordering edge case is production-proven.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/implement/scripts/oos-disposition-checkpoint.sh:184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stray set -e after gate with no script-wide set -e. Misleading for readers expecting errexit semantics outside the gate subprocess. Remove set -e or comment it as intentional no-op after set +e gate wrapper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: skills/implement/scripts/test-oos-disposition-gate.sh:485-874
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] 872-line harness mixes gate and checkpoint fixtures. Harder to navigate and extend; risk of accidental coupling between unrelated cases. Keep single Makefile target; optionally source checkpoint cases from a fragment if file grows further.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

