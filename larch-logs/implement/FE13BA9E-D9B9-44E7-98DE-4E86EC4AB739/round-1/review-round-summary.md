# Review Round 1

- Mode: `diff`
- 9 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: clear_stale leaves stale .dialectic-raw-pending.json after plan rewrite
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: `clear_stale()` removes promoted candidates and related dialectic artifacts but does not unlink `.dialectic-raw-pending.json`. Postplan rewrites call `clear-stale` when `plan.txt` changes, so a stale raw-pending sidecar can survive, later be promoted with a refreshed fingerprint, and let Gate C debate a fork that no longer matches the current plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Unlink RAW_PENDING in clear_stale on fingerprint mismatch / plan-rewrite; or reject promotion when sidecar plan hash differs from current plan.txt
  - From codex-specialist-testing-output.txt: Unlink RAW_PENDING during plan-rewrite stale clearing; add the required postplan-rewrite stale-sidecar test.
  - From dyn-dyn-dialectic-lifecycle-output.txt: In `clear_stale()`, unlink `.dialectic-raw-pending.json` whenever `auto_valid` is false or the current plan fingerprint no longer matches the promoted candidate file; alternatively drop the sidecar inside the postplan hash-change hook before promotion runs.


### FINDING_2: Free-form manual debate hardcodes drafter_pick to option_a
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Manual free-form debate construction always sets `drafter_pick=option_a` even when the current plan follows option B. That inverts THESIS/current-plan semantics, misstates the drafter pick in the digest, and can skew panel lean when the operator lists the alternative first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Infer drafter_pick from matching auto candidate or fingerprint-valid prior pick; or use neutral manual ballot without THESIS binding to left-hand option
  - From codex-specialist-correctness-output.txt: Require or infer the current-plan side before constructing manual candidates.
  - From cursor-specialist-edge-cases-output.txt: Infer pick from plan/candidates or omit drafter pick when unknown.


### FINDING_4: Missing lifecycle tests for postplan rewrite, promotion, and startup cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required acceptance tests are absent for postplan rewrite plus promotion/cleanup behavior. `step2b_drafter_main` could stop promoting correctly after postplan, promote stale plan bytes, or skip required cleanup while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test: raw pending + plan.txt mutation via postplan → pending cleared or promotion refused; add lifecycle promotion/cleanup tests from plan
  - From cursor-specialist-testing-output.txt: Add tests for prompt dialectic instructions, artifact cleanup at drafter start, promote only after POSTPLAN_RC=0, and final plan_fingerprint binding.


### FINDING_6: Candidate-derived digest fields are not sanitized before Gate C output
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Candidate-derived title, id, and option text are rendered into Gate C digest stdout without the same prefix/control-token escaping used for steelmen and rationale. Untrusted candidate content containing newlines or control-looking tokens can inject extra structure into advisory output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Sanitize all candidate-derived digest fields with the same prefix and control-token escaping used for steelmen and rationale.
  - From cursor-specialist-edge-cases-output.txt: Reject or escape structural fields; keep all model-originating text inside prefixed untrusted lines.
  - From codex-specialist-testing-output.txt: Escape or prefix every candidate-derived display field, or reject unsafe multiline/control content during validation; add a malicious candidate regression test.


### FINDING_7: Gate C docs/flow can rerun Step 4 tail and emit duplicate previews/digests
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Gate C documentation still requires running the Step 4 tail at Presentation even though Step 4 already ran it. Normal Gate C entry can therefore emit duplicate final plan previews and duplicate cached dialectic digest output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Make approval-gates consume fresh tail stdout on normal entry and only use recovery reads/reruns on resume or missing stdout.


### FINDING_9: Debater attribution stripping is not applied before ballot assembly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: Ballot assembly embeds debater steelmen verbatim without the vendor/model attribution-stripping rules required by the dialectic protocol. Judge prompts and digest output can retain model-identifying cues, weakening the clarifier trust boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Strip protocol-listed vendor/model substrings from steelmen before _ballot_text and digest output.
  - From dyn-dyn-dialectic-lifecycle-output.txt: Add a clarifier-local attribution stripper (reuse or factor the protocol's substring rules) on steelman text before ballot assembly and digest rendering.


### FINDING_14: Judge vote parsing counts duplicate lines from the same judge
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Judge vote parsing counts duplicate lines from the same judge. One malformed judge can repeat the same vote twice and satisfy the 2-of-3 threshold without two judges agreeing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Dedupe by judge and decision, treating duplicate or conflicting votes as malformed; add a malformed-output regression test.


### FINDING_15: Manual digest cache is ignored on gatec re-entry, causing duplicate auto debate
- **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: `dialectic-gatec` only treats a cached digest as valid when status `kind=="auto"`. A successful manual run writes `kind="manual"` into shared status/digest files while fingerprint-valid auto candidates remain. Re-entering Gate C without a plan rewrite can miss the manual digest, launch a full auto debate again, overwrite manual artifacts, and emit a second digest for the same plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dialectic-lifecycle-output.txt: Before auto debate, short-circuit when a fingerprint-valid manual status+digest exists for the current plan; or split auto/manual status+digest files so manual completion does not invalidate auto cache semantics, and document which digest Step 4 should emit on re-entry.


### FINDING_16: _cached_digest_valid ignores generation counter after fail-open bumps
- **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: `_cached_digest_valid()` keys only on fingerprint, ordered candidate ids, kind, and terminal state. It ignores `dialectic-clarifier-generation.txt`. After fail-open paths bump generation without writing a new digest, an older complete status/digest pair can still satisfy the cache predicate and be replayed on the next `gatec` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dialectic-lifecycle-output.txt: Require `status.generation == read_generation(design)` in `_cached_digest_valid()`, or mark/invalidate status on every generation bump.


