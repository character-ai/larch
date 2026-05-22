### FINDING_1: Issue-anchored plan doc and AGENTS index still read as aspirational / not LIVE
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `docs/issue-anchored-plan.md` and the `AGENTS.md` pointer still describe the wire format as future or not wired, while `/implement` preflight and related behavior treat plan/clarify mechanics as live—contributors and operators get wrong runbooks, skip `/design`, or misunderstand enforcement.
- **Suggested revision**: Bring `docs/issue-anchored-plan.md` to LIVE status with the promised sections (plan adequacy, clarify loop, `NEXT_ID`, single-writer warnings, cross-links to SKILL preflight/clarify); update the `AGENTS.md` bullet to match.


### FINDING_11: `SECURITY.md` and `sessionstart-health.sh` still describe deprecated manifest / Stop hook recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Security and SessionStart guidance still describe post-`/design` PostToolUse + Stop behavior, manifest mtime / `.boundary-gate-passed` gating, and advising `post-design-boundary.sh` when scripts are neutralized or no-op—false trust model and wasted operator debugging.
- **Suggested revision**: Rewrite the plugin-shipped hooks subsection and dependent “residual risk” prose to current behavior (or clearly mark legacy as historical); remove or retarget SessionStart probes/advisory; extend `scripts/test-sessionstart-health.sh` (and related) for the cutover recovery story.


### FINDING_13: `/fix-issue` lacks pre-lock plan presence probe; lock then `/implement` can fail preflight
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Without an early `plan-block-read` / plan-missing exit, the flow can lock the issue then fail `/implement` preflight, leaving IN PROGRESS locked and manual recovery—ordering and harness gaps vs desired operator ergonomics.
- **Suggested revision**: Add Step 4a probe + `gh` comment and skip-to-cleanup without lock when plan missing; extend `scripts/test-fix-issue-step-order` (or equivalent) for ordering.


### FINDING_14: `skills/compress-skill/SKILL.md` still references removed `/implement` argv
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Delegation examples cite `/implement --merge --auto`, `/implement --inline`, `--design-only`, etc.—operators hit removed argv or wrong prerequisites.
- **Suggested revision**: Update to `/implement --merge <issue-N>` with plan prerequisites; drop dead flags.


### FINDING_15: Preflight refuse: `gh` comment vs label ordering and partial-failure semantics (latent)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Exit `3` claims both mutations done, but partial failure (comment without label or inverse) is not spelled—idempotency and ordering unclear for integrators.
- **Suggested revision**: Specify failure handling, ordering guarantees, and idempotency notes for the two `gh` mutations.


### FINDING_16: `scripts/clarify-label.md` understates existing harness coverage (nit)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Text says no dedicated harness though clarify is covered elsewhere (e.g. `scripts/test-clarify-state.sh`)—contributors may skip relevant tests.
- **Suggested revision**: Point the Test Harness section at the existing script or add a tiny label-focused harness.


### FINDING_18: `README.md` examples still show pre-cutover `/implement` and `/design` argv
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: New users copy stale examples and hit removed flags or wrong shapes (plan K.2 gap per reviewer).
- **Suggested revision**: Update README examples to positional issue and current tier/public flags.


### FINDING_2: Consumer `plugin.json` description still advertises removed or internal argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Marketplace-facing copy still mentions public `--panel` “hard” and `/design --quick/--full` (and similar), contradicting the unified panel / tier-based story after the cutover.
- **Suggested revision**: Rewrite the description for the current public CLI: unified panel, tier flags, and no removed public argv tokens.


### FINDING_20: Design driver / classify harnesses may still pin removed public argv
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/design/scripts/test-design-driver.sh` and `test-classify-issue.sh` may assert removed `--quick/--full/--subagent` or miss tier/sketch_budget mapping regressions (plan M5–M6).
- **Suggested revision**: Update harness assertions for current public argv and mapping.


### FINDING_21: Cross-cutting test harness literal pins may be stale (anti-wakeup, SessionStart, Step1 plan)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `scripts/test-anti-improvised-wakeup.sh`, `scripts/test-sessionstart-health.sh`, `scripts/test-run-step1-plan-log.sh` called out for M7/M8/M14 pin updates—risk of CI false failures or false passes vs post-cutover invariants.
- **Suggested revision**: Apply specified pin updates for NEVER #12 placeholder, Stop hook neutralization, and Step1 plan path behavior.


### FINDING_23: `plugin.json` version bump may under-signal breaking argv removals (latent)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Version moved patch-style (e.g. 34.0.13→34.0.17) while argv removals may warrant MAJOR per bump-version rules—consumer semver signal may be wrong.
- **Suggested revision**: Re-run bump-version classification; align semver and changelog with `skills` bump rules.


### FINDING_24: Sibling `.md` docs for changed shell scripts risk stale hook/argv contracts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `review-and-fix.md`, `run-step5-review.md`, `hook-post-design.md`, `post-design-boundary.md` may lag shell edits—future editors could reintroduce wrong contracts (nit / sibling-doc hygiene).
- **Suggested revision**: Update those markdown siblings in sync with the shell behavior they document.


### FINDING_4: `/fix-issue` still documents and tests the old `/implement` argv surface
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `/fix-issue` text (steps, flag table, NEVER bullets) still forwards `--issue`, `--auto`, `--hard`, `--inline`, and similar into `/implement`, while `/implement` expects positional `<issue-N>` and rejects or misroutes removed flags—orchestrators following the published skill can fail at argv parse or adopt the wrong semantics; harnesses may still pin the old shape.
- **Suggested revision**: Align Step 5a (and related) with `skills/implement/SKILL.md`; update `scripts/test-fix-issue-bail-detection.sh` and related fix-issue harnesses to assert the new invocation.


### FINDING_5: `agnix-fix` still delegates to `/implement` with removed flags and wrong positional shape
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Dev skill still documents `--auto` and piping/tailing a large feature file into `/implement`, conflicting with positional issue id, plan-in-body expectations, and forked semantics—runs can fail immediately or mis-handle tokens.
- **Suggested revision**: Rewrite delegation to `/implement --forked … <issue-N>` (drop `--auto` and file-as-tail argv); document `/design`-first and exit `3` clarify handling per the new contract.


### FINDING_6: Nested / `SESSION_ENV_PATH` orchestration docs and examples contradict post-cutover `/implement`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Residual “nested under `/implement`” narrative in design SKILL, ambiguous `SESSION_ENV_PATH` consumption when `--session-env` left argv, and stale examples in `subskill-invocation.md` (manifest handoff, `/implement --inline/--session-env`) mislead orchestrators and risk reintroducing dead paths.
- **Suggested revision**: Rephrase nested mode without `/implement`-specific handoff fiction; document the env-based `SESSION_ENV_PATH` contract explicitly; refresh shared examples for issue-anchored positional `/implement` and the current tier/design `--inline` story.


### FINDING_7: Audit-refusal exit code contract inconsistent across issue text, docs, and wrappers (latent)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Brief vs `skills/implement/SKILL.md` disagree on refuse exit (`0` vs `3`), so wrappers and CI may branch incorrectly on success vs needs-clarify.
- **Suggested revision**: Pick one contract and align issue text, CHANGELOG, SKILL, and wrappers (e.g. `agnix-fix`, CI) to that code.


### FINDING_8: `skills/im` alias prose over-claims flag passthrough (nit)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Copy implies all `/implement` flags pass through though several were removed—minor operator confusion.
- **Suggested revision**: Restrict the sentence to supported flags plus the positional issue requirement.


### FINDING_9: `skills/design/SKILL.md` opening overstates panel cost for trivial tier (nit)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Summary reads like a 10-reviewer plan review for all tiers though trivial uses a quick budget—operators over-expect cost on `--trivial`.
- **Suggested revision**: Qualify the opening line for trivial vs full plan review.


