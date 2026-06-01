### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Step 18 --print-stdout removal under-tested end-to-end
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 18 drops `write-final-report --print-stdout`; summary body is orchestrator-only when `EMIT_BODY=true`. Collapsible Bash output no longer shows the body (operators may think render failed); documented delta is not fully exercised against real renderer parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Keep documented intentional delta; no code change required
  - From cursor-specialist-testing-output.txt: Add a case asserting summary-final.md parity with/without --print-stdout and that the wrapper never prints the body


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: case-plugin-root-fallback does not hit wrapper-internal plugin-root path
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: `case-plugin-root-fallback` pre-sources `plugin-root.env` before invoking the wrapper, so `CLAUDE_PLUGIN_ROOT` is already set and the internal `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$tmpdir/plugin-root.env" ]` branch in `step-18b-final-report.sh` is never exercised; documented wrapper-only contract is unverified though production pre-sources via orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Add a case that invokes `"$impl_dir/step-18b-final-report.sh"` with `env -u CLAUDE_PLUGIN_ROOT` and only `$tmpdir/plugin-root.env` present (no `set -a` pre-source), asserting `EMIT_BODY=true` and stub helper usage; or narrow `step-18b-final-report.md:16` to state that plugin-root rehydration is orchestrator-owned and drop the unused internal branch if belt-and-suspenders coverage is not desired.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate malformed-line scan in state helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check_ship_pr_state_syntax` and `ship_pr_state_has_keys` duplicate malformed-line scanning; future format-rule changes may be updated in one function and forgotten in the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated atomic temp-write / mv commit chain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` and `seed-terminal-state` duplicate the temp-write, read-assert, mv, dest-assert chain; bugfixes to atomic commit semantics must be applied twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: STEP17_EMITTED_PRESENT parsed but unused in Step 18 prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `STEP17_EMITTED_PRESENT` is parsed in Step 18 orchestrator/SKILL prose but not used for branching; adds KV noise and may be mistaken as a required gate when `EMIT_BODY` already encodes emit gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove parse or document required orchestrator use
  - From cursor-specialist-correctness-output.txt: Remove parse or document as diagnostic-only
  - From cursor-specialist-plan-fidelity-output.txt: Mark informational-only in step-18b-final-report.md or reference once in Step 18b diagnostic prose


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: stall-recovery-report.sh growth / modularization
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Roughly 250 LOC added to an already large multi-purpose script; harder reviews and higher cross-subcommand regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Post-recovery orchestration when on-disk state is keyless
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `validate_ship_pr_state` is syntax-only; `clear-stall` refuses keyless present state while classify may still use session/in-memory layers. After recovery success with truncated empty `ship-pr-state.sh`, `clear-stall` returns `CLEARED=false` `exit 0` while orchestrator may still route to terminal despite recovery completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - (no slot-specific revision beyond generic “address concern” in source)


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

