Merged the supplied slots by shared behavioral risk, ordered by the earliest original finding index in each cluster. Kept `[OUT_OF_SCOPE]` on its own headings where those sources were not merged with in-scope text (merging OOS log noise only with other OOS items).

```text
### FINDING_1: Issue-anchored plan doc and AGENTS index still read as aspirational / not LIVE
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `docs/issue-anchored-plan.md` and the `AGENTS.md` pointer still describe the wire format as future or not wired, while `/implement` preflight and related behavior treat plan/clarify mechanics as live—contributors and operators get wrong runbooks, skip `/design`, or misunderstand enforcement.
- **Suggested revision**: Bring `docs/issue-anchored-plan.md` to LIVE status with the promised sections (plan adequacy, clarify loop, `NEXT_ID`, single-writer warnings, cross-links to SKILL preflight/clarify); update the `AGENTS.md` bullet to match.

### FINDING_2: Consumer `plugin.json` description still advertises removed or internal argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Marketplace-facing copy still mentions public `--panel` “hard” and `/design --quick/--full` (and similar), contradicting the unified panel / tier-based story after the cutover.
- **Suggested revision**: Rewrite the description for the current public CLI: unified panel, tier flags, and no removed public argv tokens.

### FINDING_3: Clarify-loop normative placement / cross-skill doc dependency (nit)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Design clarify-loop semantics are deferred to the implement SKILL in a way that reads like an inverted dependency between sibling skills.
- **Suggested revision**: Colocate normative clarify steps in design or shared docs; shorten the implement cross-link to a pointer.

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

### FINDING_10: [OUT_OF_SCOPE] Large committed run-log / diff volume is policy noise, not a functional gap
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Bulk `larch-logs` and broad diff noise fatigue reviewers and obscure security review; intentional per repo policy, not a test gap for the cutover issue.
- **Suggested revision**: None for feature mechanics; rely on focused file reads for security/plan fidelity.

### FINDING_11: `SECURITY.md` and `sessionstart-health.sh` still describe deprecated manifest / Stop hook recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Security and SessionStart guidance still describe post-`/design` PostToolUse + Stop behavior, manifest mtime / `.boundary-gate-passed` gating, and advising `post-design-boundary.sh` when scripts are neutralized or no-op—false trust model and wasted operator debugging.
- **Suggested revision**: Rewrite the plugin-shipped hooks subsection and dependent “residual risk” prose to current behavior (or clearly mark legacy as historical); remove or retarget SessionStart probes/advisory; extend `scripts/test-sessionstart-health.sh` (and related) for the cutover recovery story.

### FINDING_12: [OUT_OF_SCOPE] `/fix-issue` staleness not provable from supplied diff hunks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Workspace may still show old `/fix-issue` flags while the cached diff does not prove branch state—possible confusion if branch and workspace diverge.
- **Suggested revision**: Reconcile in a follow-up if the branch is meant to include the `/fix-issue` cutover; no diff-proven action here.

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

### FINDING_17: [OUT_OF_SCOPE] Residual `--session-env` mention in warning string (editorial)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Warning string still references `--session-env` though the flag was removed from argv—mild operator confusion only.
- **Suggested revision**: Editorial follow-up in `skills/implement/SKILL.md` if desired.

### FINDING_18: `README.md` examples still show pre-cutover `/implement` and `/design` argv
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: New users copy stale examples and hit removed flags or wrong shapes (plan K.2 gap per reviewer).
- **Suggested revision**: Update README examples to positional issue and current tier/public flags.

### FINDING_19: `skills/shared/topology.tsv` not refreshed for new argv surfaces
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Topology projection / agent-lint counts can disagree with shipped CLI after argv removals (plan I.3).
- **Suggested revision**: Regenerate or hand-edit `topology.tsv` and validate with `make agent-lint`.

### FINDING_20: Design driver / classify harnesses may still pin removed public argv
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/design/scripts/test-design-driver.sh` and `test-classify-issue.sh` may assert removed `--quick/--full/--subagent` or miss tier/sketch_budget mapping regressions (plan M5–M6).
- **Suggested revision**: Update harness assertions for current public argv and mapping.

### FINDING_21: Cross-cutting test harness literal pins may be stale (anti-wakeup, SessionStart, Step1 plan)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `scripts/test-anti-improvised-wakeup.sh`, `scripts/test-sessionstart-health.sh`, `scripts/test-run-step1-plan-log.sh` called out for M7/M8/M14 pin updates—risk of CI false failures or false passes vs post-cutover invariants.
- **Suggested revision**: Apply specified pin updates for NEVER #12 placeholder, Stop hook neutralization, and Step1 plan path behavior.

### FINDING_22: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` may pin retired NEVER / flow text
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Anti-halt harness listed in plan G.3 may reference retired NEVER ladder or steps (plan gap: file not in diff).
- **Suggested revision**: Align harness with current implement NEVER ladder and step flow.

### FINDING_23: `plugin.json` version bump may under-signal breaking argv removals (latent)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Version moved patch-style (e.g. 34.0.13→34.0.17) while argv removals may warrant MAJOR per bump-version rules—consumer semver signal may be wrong.
- **Suggested revision**: Re-run bump-version classification; align semver and changelog with `skills` bump rules.

### FINDING_24: Sibling `.md` docs for changed shell scripts risk stale hook/argv contracts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `review-and-fix.md`, `run-step5-review.md`, `hook-post-design.md`, `post-design-boundary.md` may lag shell edits—future editors could reintroduce wrong contracts (nit / sibling-doc hygiene).
- **Suggested revision**: Update those markdown siblings in sync with the shell behavior they document.

### FINDING_25: [OUT_OF_SCOPE] `aggregate-findings.*` changes trace to a different issue, not #2485 fidelity
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Revisions attributed to commit/issue separate from the #2485 plan items—no #2485 traceability requirement per reviewer.
- **Suggested revision**: None required for #2485 plan fidelity review.
```
