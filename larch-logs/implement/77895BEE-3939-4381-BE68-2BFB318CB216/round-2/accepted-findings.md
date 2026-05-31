### FINDING_15: four SKILL.md callers use incompatible interactive envelopes around BOTH_DOWN branches
- **Reviewer(s)**: dyn-cross-caller-parity-output.txt
- **Severity**: latent
- **Concern**: The new BOTH_DOWN two-way split is nested under four different “interactive” envelopes (bare interactive, [[ -t 0 ]], interactive, non-subagent), so the same degraded availability can auto-proceed on one skill and still enter AskUserQuestion on another in the same environment (e.g. non-TTY /design vs /research). That undermines the cross-skill invariant this change centralizes via BOTH_DOWN.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-caller-parity-output.txt: Define one canonical interactive predicate (plus the existing `/review` subagent carve-out) in `skills/shared/external-reviewers.md` and have each SKILL.md reference it instead of re-stating incompatible guards around the `BOTH_DOWN` branches.


### FINDING_3: external-reviewers.md BOTH_DOWN=true Continue path over-generalizes post-Continue dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The BOTH_DOWN=true Continue path says availability-gated dispatch for all skills. Readers of only the shared procedure may assume /review and /research use reduced-panel dispatch after Continue, but those skills use waterfall dispatch. An orchestrator following only external-reviewers.md could apply wrong post-Continue dispatch semantics for /review or /research after the operator chooses Continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Restore explicit reduced-panel vs waterfall post-Continue behavior per skill in that bullet.
  - From cursor-specialist-plan-fidelity-output.txt: Restore per-skill post-Continue dispatch wording (reduced panel vs waterfall) or replace availability-gated dispatch per skill with proceed per that skill Step 0 dispatch contract.


### FINDING_5: degraded-tools-gate.md and external-reviewers.md:40 prompt predicate omits empty/unset BOTH_DOWN fail-safe
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-cross-caller-parity-output.txt
- **Severity**: latent
- **Concern**: Detector contract intro in degraded-tools-gate.md says prompt only when BOTH_DOWN=true and omits fail-safe for empty/unset/malformed BOTH_DOWN; an orchestrator reading only that doc could auto-proceed for any value other than literal true. Separately, external-reviewers.md:40 titles the prompt path as Interactive run, BOTH_DOWN=true (both tools unavailable) while all four SKILL.md callers fold true or empty/unset (both tools unavailable or parse failed) into the prompt-branch condition. A maintainer wiring [[ "$BOTH_DOWN" == "true" ]] from the :40 header alone would skip prompting on parse failure (empty BOTH_DOWN), breaking the shared fail-safe the SKILL prose enforces. Match external-reviewers.md fail-safe: auto-proceed only when BOTH_DOWN is exactly false; all other values prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-caller-parity-output.txt: Align `skills/shared/external-reviewers.md:40` with the SKILL wording (e.g. rename the branch to **`BOTH_DOWN` not exactly `false`** or add **or empty/unset (parse failed)** inline) so the canonical procedure and per-skill bullets share one prompt predicate; keep the exact-string `[[ "$BOTH_DOWN" == "false" ]]` auto-proceed rule in `:41`.


### FINDING_7: Case 1 omits BOTH_DOWN=false assertion on healthy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case 1 omits BOTH_DOWN=false assertion on healthy path. Refactor could stop emitting BOTH_DOWN before early exit; consumers expecting four KVs every run would break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert_contains BOTH_DOWN=false to Case 1


