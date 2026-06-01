### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Step 18b SKILL does not document --print-stdout removal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Intentional delta: Step 18 drops `write-final-report --print-stdout`; collapsible Bash no longer shows summary body (only orchestrator verbatim emit). Worth noting in release/review notes for panel awareness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No structural pin for CLEARED/SEEDED parsing on keyless exit-0 clear-stall
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No structural pin that the orchestrator must branch on `CLEARED`/`SEEDED` KVs for keyless exit-0 `clear-stall`; models may treat exit 0 alone as success and clear in-memory stall while disk is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Dead `token_rc` in step-18b-final-report.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `token_rc` is assigned on token-report failure but never emitted or branched on, adding dead state; readers may assume token failure affects `EMIT_BODY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: clear-stall keyless present file exits 0 with CLEARED=false vs plan exit 3
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `clear-stall` treats a syntax-valid keyless present `ship-pr-state.sh` as exit 0 `CLEARED=false` while malformed paths exit 3. Orchestration that branches only on exit code (not `CLEARED`) may treat a present keyless file as benign no-op instead of format failure; diverges from plan-specified `check_ship_pr_state_format` failure (exit 3) unless formally amended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Restore exit 3 for keyless present files per the original plan, or formally amend plan/acceptance to codify the documented three-tier asymmetry


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: seed-terminal-state overwrites present keyless state file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SEED_MODE=seed` overwrites a present keyless state file with minimal Step-8 keys only, dropping non-key content/comments that might have carried recoverable context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: SKILL Step 18b missing explicit handling when EMIT_BODY/WFR_RC KVs absent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Step 18b prose does not state that missing `EMIT_BODY`/`WFR_RC` KVs after awk parse mean no verbatim emit; polluted stdout yields empty `EMIT_BODY` (fail-closed in practice) but is not spelled out beside the parse block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: rewrite_ship_pr_state_keys gawk -v backslash escape footgun
- **Reviewer(s)**: dyn-awk-value-injection-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` passes replacement values through `gawk -v`, which interprets backslash escapes; unsanitized future callers could silently alter values before write. Current callers use literals or `safe_*` allowlists; pass-through keys are not fed via `-v` today—no present exploit path, but the helper is reusable risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-awk-value-injection-output.txt: centralize awk-safe encoding in `rewrite_ship_pr_state_keys` (e.g. double backslashes before building `awk_v`, or pass values via `ENVIRON` / a temp file instead of `-v`), document the invariant in `stall-recovery-report.md`, and add a harness case that writes a backslash-heavy value into a rewritten key and asserts the on-disk line is byte-identical.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: clear-stall duplicates three-tier state validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` inlines three-tier validation instead of calling `check_ship_pr_state_format`, so format rules can drift between helpers and docs when only one path is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: stall-recovery.md lacks concrete CLEARED/SEEDED parse example
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `stall-recovery.md` tells the orchestrator to parse `CLEARED`/`SEEDED` without a concrete stdout capture/parse example; models may improvise parsing unlike the pinned SKILL Step 18b awk block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicated Step 18 EMIT_BODY test matrix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 18 `EMIT_BODY` matrix is duplicated across `test-step-18b-final-report.sh` and `test-write-final-report.sh`; fixes to step-18b logic may require updating two stub trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: cmd_classify skips reads for keyless ship-pr-state.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `cmd_classify` now skips state-key reads when `ship-pr-state.sh` is keyless, changing classification inputs; edge runs with empty/comment-only state files classify from session-env only—a subtle behavior change that may be outside explicit plan scope unless documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Add a plan note that classify must ignore keyless on-disk state; no code change needed if asymmetry is accepted


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Temp files not removed on clear/seed assert failure paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Failed clear/seed attempts can leave `ship-pr-state.sh.tmp.*` files in `IMPLEMENT_TMPDIR` when destination assert paths fail without cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

