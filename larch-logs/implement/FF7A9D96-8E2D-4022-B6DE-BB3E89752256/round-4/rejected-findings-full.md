### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Stale RUN_ID no longer triggers ndjson find fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: When `session-id` / `RUN_ID` is non-empty but the keyed `oos-issues.ndjson` is missing, the extracted helper only runs `find` when `RUN_ID` is empty. The removed inline SKILL block also find-bound when the keyed path was missing. A resume with a stale session-id and exactly one foreign ndjson under `larch-logs/implement/` could previously bind via find and pass (including non-security OOS clear); the helper now exits 2 and blocks `OOS_PENDING` clear. Security treats this as intentional hardening (closes foreign-batch bind while OOS is pending); other reviewers flag plan/acceptance drift vs inline 1:1 port and operator impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align plan/acceptance with documented policy or restore find when keyed path is missing but RUN_ID is set.
  - From cursor-specialist-correctness-output.txt: Document in SKILL.md Step 8+ (or revert to inline find-when-missing if 1:1 port is required); keep harness stale-RUN_ID case if hardening stands.
  - From cursor-specialist-testing-output.txt: Document as intentional contract change and keep stale-RUN_ID test; revert only if product requires old fallback.
  - From cursor-specialist-edge-cases-output.txt: Keep hardening; add operator-facing remediation in SKILL Step 8+ and log the keyed path in fail_validation output.
  - From cursor-specialist-plan-fidelity-output.txt: Restore inline find when keyed path missing (keep ambiguity exit 2 only for empty RUN_ID + multiple matches), or update plan/acceptance to authorize stale-RUN_ID hardening.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: No test for `DESIGN_TMPDIR` env without `--design-tmpdir` flag
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness covers `--design-tmpdir` CLI but not exported `DESIGN_TMPDIR` alone. Standalone or future callers relying on env-only binding could regress design-path resolution undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one exported-DESIGN_TMPDIR checkpoint case parallel to --design-tmpdir tests.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `--help` exits 0 without validation logging
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `oos-disposition-checkpoint.sh --help` exits 0 without going through `fail_validation`. A thin wrapper could misread `-h` as checkpoint pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Exit 2 through fail_validation or drop help from production CLI.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: SKILL invokes checkpoint via `bash` instead of direct executable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan, harness, and `oos-disposition-checkpoint.md` expect direct `+x` invocation; SKILL.md invokes via `bash …/oos-disposition-checkpoint.sh`. The harness `[ -x ]` check does not cover the orchestrator path, so a 100755 regression or wrong shebang may surface only as shell exit 127 at runtime, with orchestrator fallback/mis-branch risk vs the 0/1/2 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align SKILL with direct invocation or document bash as canonical and adjust acceptance/harness accordingly.
  - From cursor-specialist-edge-cases-output.txt: Align checkpoint.md with bash wrapper or change SKILL to direct invocation consistent with harness.
  - From cursor-specialist-plan-fidelity-output.txt: Use direct `"${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-disposition-checkpoint.sh"` invocation per plan refinement #2.
  - From cursor-specialist-plan-fidelity-output.txt: Align SKILL with doc or document bash in the contract sibling.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `log_checkpoint_failure` swallows append failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `log_checkpoint_failure` uses `append-tool-failure.sh … || true` and does not pre-touch `execution-issues.md`. If append fails (permissions/redaction), the checkpoint exits non-zero with no Tool Failures row; the orchestrator fallback may also be skipped (FINDING_2), leaving no audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Touch execution-issues.md before append; consider logging append failure to stderr without overriding checkpoint rc.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Orchestrator fallback append path lacks regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: When the checkpoint fails without writing to `execution-issues.md` (missing/swallowed `append-tool-failure.sh`), the orchestrator fallback is the only audit trail; no harness forces non-zero checkpoint rc with empty `execution-issues.md` and asserts fallback append, so grep/append drift can ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness or integration case forcing non-zero checkpoint rc with empty execution-issues.md and assert fallback append.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

