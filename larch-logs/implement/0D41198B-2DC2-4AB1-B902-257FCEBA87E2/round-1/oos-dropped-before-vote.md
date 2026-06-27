### OOS_1: [OUT_OF_SCOPE] Python probe coverage missing STEP4_MODE=foreground branches
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-step4-mode-output.txt
- **Severity**: important
- **Concern**: Probe-only coverage exercises the `DIALECTIC_GATEC_DEBATE_REQUIRED=true` path only. `STEP4_MODE=foreground` cases (`--skip-approve`, cached digest, no candidates) are untested at the Python layer even though `_run_gatec` implements them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add probe-only tests asserting `false` for those branches.
  - From dyn-dyn-step4-mode-output.txt: Extend `test_design_dialectic.py` with parametrized probe-only cases for those edge paths.

### OOS_2: [OUT_OF_SCOPE] Optional offline harness for finalize fail-closed marker/sidecar absence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3b finalize behavior is pinned by static `grep`/`awk`, not a harness that runs the wrapper and asserts non-zero probe exit leaves `.completed/step-3b` and `.step4-mode.env` absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional offline harness with a stubbed `dialectic-gatec` failure.

### OOS_3: [OUT_OF_SCOPE] Gate B Step 3.5 SETTLE_NEXT_ACTION timing ambiguity on fresh entry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3.5 items 1–2 require `SETTLE_NEXT_ACTION` before "Execute the Gate B body," which is ambiguous on a fresh Gate B entry before any settle call (pre-existing shape; this change only tightens wording).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clarify that items 1–2 apply after settle returns, or on the post-apply resume branch only.

### OOS_4: [OUT_OF_SCOPE] Reference docs still stale on STEP4_MODE despite SKILL.md authority shift
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step3b-tail.md:24` and `dialectic-clarifier.md:76` still say the Step 4 orchestrator backgrounds the tail when "debate may run," while `SKILL.md` now binds routing to `STEP4_MODE` from Step 3b finalize. Wrapper-doc readers can reintroduce the deleted `_step4_debate_may_run` pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Align those two reference files with the `STEP4_MODE` contract; optional structural `not_contains` pins.

### OOS_5: [OUT_OF_SCOPE] Shell finalize integration risk remains prose/ordering-only covered
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New finalize probe/KV/sidecar behavior is enforced by static `test-design-structure.sh` grep/order checks, not an offline harness that executes `--mode finalize` against a fixture tmpdir. Python probe semantics are covered in `python/test_design_dialectic.py`; shell integration risk is mostly prose/ordering drift.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Exact-line assert_line_precedes pin fragile to probe-call reformatting
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `assert_line_precedes` at `scripts/test-design-structure.sh:431` matches exact physical lines (e.g. the `--probe-only \` continuation). Reformatting the probe call can break CI without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Only if you want hardening: anchor on a stabler substring or add a small offline finalize fixture test.

### OOS_7: [OUT_OF_SCOPE] Re-entry sentinel clear omits .step4-mode.env sidecar
- **Reviewer(s)**: dyn-dyn-step4-mode-output.txt
- **Severity**: latent
- **Concern**: `_step3_clear_downstream_sentinels` clears `.completed/step-3b` / `.completed/step-4` on Step 3 `--reentry` but not the new `$DESIGN_TMPDIR/.step4-mode.env`. Normal routing is safe because finalize clears the sidecar on entry; the gap is stale on-disk state during the re-entry window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step4-mode-output.txt: Add `.step4-mode.env` and `.step4-mode.env.tmp` to `_step3_clear_downstream_sentinels` when touching downstream sentinels.

### OOS_8: [OUT_OF_SCOPE] Gate A routing prose uses direct --reentry invocation instead of parameterized flag
- **Reviewer(s)**: dyn-dyn-step4-mode-output.txt
- **Severity**: nit
- **Concern**: Gate A "Ready for review" prose still names `design-step3-entry.sh --reentry` directly while Step 3 entry was collapsed to `${STEP3_REENTRY_FLAG}` elsewhere. Behavior is unchanged, but dual invocation styles can confuse orchestrators during re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step4-mode-output.txt: Point Gate A routing prose at the parameterized flag pattern for consistency.

### OOS_9: [OUT_OF_SCOPE] approval-gates.md retains residual rc-based Step 3 continuation authority
- **Reviewer(s)**: dyn-dyn-settle-contract-output.txt
- **Severity**: latent
- **Concern**: Shared post-apply step 10 still gates Step 3 continuation on wrapper rc `0` (plus drift / Split / Override carve-outs) even though step 8.2 now routes only on `SETTLE_NEXT_ACTION`. That leaves residual rc-based authority on the Gate B continuation path; it predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] Pause check not inserted between FINALIZE driver and probe
- **Reviewer(s)**: dyn-dyn-structure-pins-output.txt
- **Severity**: nit
- **Concern**: `design_pause_check` runs only before `run_step3b_finalize`, not between FINALIZE and the probe. A pause requested after driver success but before probe can re-run FINALIZE on resume. The plan noted this edge case; behavior is acceptable but not pause-optimal.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_11: [OUT_OF_SCOPE] Missing not_contains guard on deleted Step 4 intro routing text
- **Reviewer(s)**: dyn-dyn-structure-pins-output.txt
- **Severity**: nit
- **Concern**: The plan asked for a `not_contains` guard on old Step 4 intro text (`dialectic-gatec when appropriate` as primary routing). Only `_step4_debate_may_run` and prompt-side `--probe-only` are pinned; partial reintroduction of the deleted intro could slip through.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_12: [OUT_OF_SCOPE] Gate-B-bypass dedup coverage split across harnesses
- **Reviewer(s)**: dyn-dyn-structure-pins-output.txt
- **Severity**: nit
- **Concern**: Negative guards for deleted standalone bypass paragraphs live only in `test-design-structure.sh`; Gate-B-bypass dedup coverage should stay centralized in the structure harness.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Validation fix note:** `cursor-specialist-edge-cases-output.txt` is attributed on **FINDING_11–13**, all `[OUT_OF_SCOPE]`, satisfying the rule that an exclusively-OOS reviewer must not appear on in-scope blocks. Commit-attestation lines from `cursor-specialist-testing-output.txt` (input FINDING_9–11) are subsumed as non-actionable noise; that slot remains covered via FINDING_14–16.

