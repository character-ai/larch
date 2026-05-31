### FINDING_12: [OUT_OF_SCOPE] code-quality — `session_get` duplicates phase-driver primitive in implement Step 2
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/run-step2-dispatch.sh` duplicates `lib-phase-driver.sh` KV reader; future Step 2 edits may drift from shared phase-driver reader.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source lib-phase-driver.sh from run-step2-dispatch when touching Step 2 stack (not required for this PR).


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] architecture — SKILL fence duplicated in orchestrator-fence harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Step 3 orchestrator handoff is mirrored in `test-step3-orchestrator-fence.sh`; skill fence and harness can drift without shared extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep harness committed; consider lib or structure-test extraction in a follow-up.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] risk-integration — no `--help` exit-0 launcher smoke for `test-run-step3-review.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Pre-existing launcher harness pattern; not a regression on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: add --help case aligned with launcher-argv-test-coverage.md conventions.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### FINDING_15: [OUT_OF_SCOPE] security — cap env and review-round-count writes lack symlink hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `.step3-review-cap.env` and `review-round-count.txt` are still written with plain `cat`/`printf` without symlink-target checks while `.step3-review-result.env` is hardened; matches pre-extract inline SKILL behavior and documented same-UID `/design` tmpdir trust model; defense-in-depth only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] security — stdout KV merge lacks newline rejection from `phase_driver_read_result_env`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Stdout KV merge does not apply `phase_driver_read_result_env` newline rejection (file path does); trust boundary remains in-tree `plan-review-loop.sh`; unchanged from former inline fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] architecture — tier cap vs HARD cursor use different run-params keys
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tier cap uses `design_classification` while HARD cursor uses `workflow_path`; inconsistent or hand-edited run-params can desync cap vs cursor (e.g. SIMPLE cap with HARD workflow_path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider single source of truth in a follow-up.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] correctness — `read-cursor` under `set -e` aborts driver before normalized result env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-zero `read-cursor` exit aborts driver before writing `.step3-review-result.env`; orchestrator infers panel-failed only from empty `LOOP_STATUS`. Pre-existing pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional set +e and explicit panel-failed handoff if abort is too harsh.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] architecture — `approval-gates.md` still cites inner plan-review result env
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `approval-gates.md` still references `.step3-plan-review-result.env` as primary; operators may inspect stale file instead of `.step3-review-result.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Sync approval-gates.md to .step3-review-result.env primary (follow-up).

---

**Aggregation notes (non-voting):**
- Input items 16–22 from `cursor-specialist-security-output.txt` are security **improvement attestations**, not defects; they are not promoted to `### FINDING_N:` blocks.
- Original input 2 (missing `.md` sibling) is folded into **FINDING_1** (same integration failure surface).
- Original 3, 8, 25 (allow-list portion), and 31 → **FINDING_2**; original 26 and 25 (stale file-first portion) → **FINDING_3** (distinct fix: merge semantics vs allow-list normalization).
- Original 11 and 13 remain separate (**FINDING_8** vs **FINDING_9**): fence behavior vs harness coverage.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

