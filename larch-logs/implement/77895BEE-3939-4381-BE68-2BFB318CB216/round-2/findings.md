### FINDING_1: test-degraded-tools-gate.sh Cases 13–16 duplicate primary matrix coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Cases 13–16 duplicate argv and assertions already added to Cases 2–4 and 3/7. Future edits to explanation text may require updating four cases instead of one, with no extra branch coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Merge text assertions into the primary matrix cases; keep at most Case 14 for design both-down if Case 4 stays review-only.

### FINDING_2: duplicated BOTH_DOWN closing if/else in degraded-tools-gate.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated BOTH_DOWN closing if/else in design and non-design branches. One branch could get the auto-proceed line updated and the other left stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor shared auto-proceed emit; keep only skill-specific Continue strings in the BOTH_DOWN=true branch.

### FINDING_3: external-reviewers.md BOTH_DOWN=true Continue path over-generalizes post-Continue dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The BOTH_DOWN=true Continue path says availability-gated dispatch for all skills. Readers of only the shared procedure may assume /review and /research use reduced-panel dispatch after Continue, but those skills use waterfall dispatch. An orchestrator following only external-reviewers.md could apply wrong post-Continue dispatch semantics for /review or /research after the operator chooses Continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Restore explicit reduced-panel vs waterfall post-Continue behavior per skill in that bullet.
  - From cursor-specialist-plan-fidelity-output.txt: Restore per-skill post-Continue dispatch wording (reduced panel vs waterfall) or replace availability-gated dispatch per skill with proceed per that skill Step 0 dispatch contract.

### FINDING_4: [OUT_OF_SCOPE] collaborative-sketches.md Step 0 gate wording stale vs BOTH_DOWN behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Sketch doc still describes unconditional operator warning at Step 0 gate. Doc overstates prompting when only Codex or Cursor is down. Not introduced by this branch diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update when editing sketch docs to match BOTH_DOWN behavior.

### FINDING_5: degraded-tools-gate.md and external-reviewers.md:40 prompt predicate omits empty/unset BOTH_DOWN fail-safe
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cross-caller-parity-output.txt
- **Severity**: latent
- **Concern**: Detector contract intro in degraded-tools-gate.md says prompt only when BOTH_DOWN=true and omits fail-safe for empty/unset/malformed BOTH_DOWN; an orchestrator reading only that doc could auto-proceed for any value other than literal true. Separately, external-reviewers.md:40 titles the prompt path as Interactive run, BOTH_DOWN=true (both tools unavailable) while all four SKILL.md callers fold true or empty/unset (both tools unavailable or parse failed) into the prompt-branch condition. A maintainer wiring [[ "$BOTH_DOWN" == "true" ]] from the :40 header alone would skip prompting on parse failure (empty BOTH_DOWN), breaking the shared fail-safe the SKILL prose enforces. Match external-reviewers.md fail-safe: auto-proceed only when BOTH_DOWN is exactly false; all other values prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-caller-parity-output.txt: Align `skills/shared/external-reviewers.md:40` with the SKILL wording (e.g. rename the branch to **`BOTH_DOWN` not exactly `false`** or add **or empty/unset (parse failed)** inline) so the canonical procedure and per-skill bullets share one prompt predicate; keep the exact-string `[[ "$BOTH_DOWN" == "false" ]]` auto-proceed rule in `:41`.

### FINDING_6: no mechanical CI check for BOTH_DOWN fail-safe parse path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fail-safe parse path (empty/unset BOTH_DOWN → prompt) has no mechanical CI check. An orchestrator edit could use [[ "$BOTH_DOWN" != "true" ]] or drop BOTH_DOWN parsing; degraded single-tool runs would auto-proceed without AskUserQuestion and CI would stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep/structure contract on SKILL.md + external-reviewers.md for exact-string BOTH_DOWN == false check

### FINDING_7: Case 1 omits BOTH_DOWN=false assertion on healthy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case 1 omits BOTH_DOWN=false assertion on healthy path. Refactor could stop emitting BOTH_DOWN before early exit; consumers expecting four KVs every run would break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert_contains BOTH_DOWN=false to Case 1

### FINDING_8: both-down matrix lacks binary-missing (or mixed-mode) BOTH_DOWN=true coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Both-down matrix only covers dual probe-failed. Misclassification for dual binary-missing would not be caught by current BOTH_DOWN=true assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one both-binary-missing (or mixed-mode) BOTH_DOWN=true case with explanation closing-line pins

### FINDING_9: [OUT_OF_SCOPE] relevant-checks.sh does not map SKILL-only gate edits to test-degraded-tools-gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: SKILL-only edits do not map to test-degraded-tools-gate in incremental checks. Local pre-commit on prose-only gate edits may skip the harness until full lint. Pre-existing pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend relevant-checks mapping if desired

### FINDING_10: BOTH_DOWN=false auto-proceed allows env fallback when argv probe flags omitted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Auto-proceed on BOTH_DOWN=false still allows env fallback when argv flags are omitted. Stale CURSOR_PRESENT=true in shell + Codex probe-failed with partial flags → BOTH_DOWN=false → interactive run auto-proceeds without AskUserQuestion; pre-change behavior prompted on any DEGRADED=true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require all four probe flags on argv before BOTH_DOWN=false can authorize auto-proceed; treat any omission as prompt path.

### FINDING_11: interactive gate branching lacks shell mechanical enforcement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Interactive gate branching is LLM-orchestrated only; no shell enforces exact BOTH_DOWN parse or sentinel write. Misparsed or empty BOTH_DOWN with loose inequality could auto-proceed when both tools are down, or re-show gate on resume if sentinel omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add a mechanical interactive gate helper script with exact-string BOTH_DOWN handling and sentinel management.

### FINDING_12: [OUT_OF_SCOPE] --skill label unvalidated in degraded-tools-gate.sh explanation text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: --skill label is unvalidated in explanation text. Pre-existing presentation-only risk if orchestrator passes unexpected --skill value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate against allowlist design|implement|review|research or default to this.

### FINDING_13: [OUT_OF_SCOPE] --caller-env can skip probes and hide both-tools-down before gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: --caller-env can skip probes and set presence from caller file. Pre-existing; can hide both tools down before gate runs. Out of scope for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document or harden separately.

### FINDING_14: sentinel prevents re-prompt but procedure lacks skip-if-exists gate entry guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sentinel prevents re-prompt but procedure lacks skip-if-exists entry guard. Orchestrator always runs degraded-tools-gate.sh on Step 0 re-entry; sentinel only prevents re-AskUserQuestion so auto-proceed path can re-print full explanation on implement resume-plan-tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add normative if-sentinel-exists skip entire gate block; mirror in four SKILL.md gate bullets

### FINDING_15: four SKILL.md callers use incompatible interactive envelopes around BOTH_DOWN branches
- **Reviewer(s)**: dyn-cross-caller-parity-output.txt
- **Severity**: latent
- **Concern**: The new BOTH_DOWN two-way split is nested under four different “interactive” envelopes (bare interactive, [[ -t 0 ]], interactive, non-subagent), so the same degraded availability can auto-proceed on one skill and still enter AskUserQuestion on another in the same environment (e.g. non-TTY /design vs /research). That undermines the cross-skill invariant this change centralizes via BOTH_DOWN.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-caller-parity-output.txt: Define one canonical interactive predicate (plus the existing `/review` subagent carve-out) in `skills/shared/external-reviewers.md` and have each SKILL.md reference it instead of re-stating incompatible guards around the `BOTH_DOWN` branches.

### FINDING_16: [OUT_OF_SCOPE] pre-existing cross-skill abort, subagent, and sentinel-path inconsistencies
- **Reviewer(s)**: dyn-cross-caller-parity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing / skill-specific (not introduced by this diff): /implement abort uses STALL_TRACKING=true + Step 18 cleanup while external-reviewers.md:40 generically says cleanup-tmpdir on Abort; /review subagent/non-interactive paths bypass BOTH_DOWN and do not spell out when to write .degraded-tools-gate-prompted on degraded subagent runs; auto-proceed paths say write .degraded-tools-gate-prompted without the $*_TMPDIR/ prefix while Continue paths use the fully qualified path (consistent across all four callers).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Subsumed / omitted from structured list**

- **FINDING_19** (branch commit inventory) and **FINDING_20** (parity checklist attesting no defect) are informational attestations, not actionable behavioral risks; excluded per aggregator scope.
- Generic “Address the concern above” placeholders were not quoted as revisions where substantive fix text appears in the concern or **Suggested fix** blocks above.
