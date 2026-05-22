Here is the normalized aggregator output. Same behavioral risks are merged; `[OUT_OF_SCOPE]` is preserved where any merged source used it; verbatim suggested-revision lines are quoted per slot (identical generic “Address the concern above.” lines from one slot are collapsed to a single bullet for that slot).

---

### FINDING_1: Stale Step 2 contract: `run-step2-dispatch.md` vs script (`plan.txt` / HARD)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The launcher contract doc still describes `PLAN_FILE` and `POST_PLAN_WORKFLOW_PATH` as derived from `session-env` / argv mapping, while the implementation uses conventional `plan.txt` and a hardcoded HARD workflow. Operators and harness authors can follow the wrong contract, misconfigure keys the launcher no longer reads, and debug Step 2 / tmpdir wiring against false assumptions (including drift vs `SKILL.md` §2.1 called out by edge review).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_2: `CLASSIFY` in design driver: docs, fail-closed behavior, and plan fidelity (`design-driver.md` / `design-driver.sh`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The markdown contract omits normative description of deprecated `CLASSIFY` fail-closed behavior that tests exercise, so readers may assume passthrough or full support and be surprised by `STEP_FAILED` on stale action files. The shell still carries an explicit deprecated / plan-divergent `CLASSIFY` path in `process_line`, which reads as incomplete removal versus the written plan and blurs whether fail-closed rejection is intentional for stale transcripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Remove the CLASSIFY branch per plan and realign test-design-driver.sh expectations to the new routing semantics.

---

### FINDING_3: Step 2 always forwards HARD workflow — launcher timeout semantics vs former SIMPLE
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Step 2 always passes HARD into `step2-implement.sh`, so external implementer runs use the longer (7200s) launcher timeout path instead of the former SIMPLE (3600s) mapping; stuck runs fail later unless policy is intentional and documented, or a single derived workflow signal is restored as a product requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Document HARD-only forwarding in sibling contract docs and pin the intended timeout policy in test-run-step2-dispatch commentary or assertions

---

### FINDING_4: Duplicated Step 5 plan-path / round-cap prose in `skills/implement/SKILL.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The same long explanations of Step 5 plan path and round-cap rules appear in multiple places; partial edits can leave contradictory guidance within one skill file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_5: `CHANGELOG.md` 36.0.x release-date ordering looks inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Under adjacent 36.0.x headings, dates can read as chronologically wrong (e.g. 36.0.1 dated after 36.0.2 / 36.0.3), inviting mistaken backdating or cherry-pick-order inferences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_6: `scripts/run-step5-review.md` implies a `WORKFLOW_PATH` input the script does not read
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The doc references a `WORKFLOW_PATH` input that the shell does not consume, wasting maintainer time reconciling doc vs code (e.g. grepping the launcher).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_7: [OUT_OF_SCOPE] Stale Step 5 / round-cap wiring in `docs/review-agents.md` (deferred OOS_2)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Consumer doc still attributes round-cap derivation (and Step 5 inputs) to `POST_PLAN_WORKFLOW_PATH` / stale wiring relative to `run-step5-review.sh` and the fixed-cap / degraded-inflation story; explicitly deferred in the implementation plan (OOS_2). Misleading for operators; not necessarily proven as a new regression from the reviewed script hunks alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_8: [OUT_OF_SCOPE] Residual retired surfaces in `skills/shared/subskill-invocation.md` (deferred OOS_1)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Shared guidance may still reference retired manifest / persist-post-plan paths, contradicting the issue-anchored materialization story for nested hosts; deferred follow-up (OOS_1). Security review frames it as doc drift / misleading handoff rather than a new shell trust boundary from the reviewed diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_9: `scripts/ship-pr.sh` — `resolve_plan_file` fallbacks lack regression harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Conventional `plan.txt` fallbacks were added without visible `ship-pr` harness updates; CI-fix or rebase-rebump paths could regress plan forwarding while `make lint` stays green if no fixture exercises the new branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ship-pr regression cases covering missing PLAN_FILE plus present plan.txt and the outside-tmpdir warning fallback

---

### FINDING_10: Acceptance (“grep-clean”) vs deferred OOS doc work (`review-agents.md`, `subskill-invocation.md`)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Acceptance calls for grep-clean hygiene while the plan defers updates to `subskill-invocation.md` and `review-agents.md`, creating a latent mismatch between stated acceptance and OOS filings unless wording or scope is reconciled before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_11: [OUT_OF_SCOPE] Large `larch-logs/**` hunks as review noise
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Massive run-log diffs dominate review surface and paging time; framed as expected merge noise per repo rules, not a code defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_12: [OUT_OF_SCOPE] Version / marketing text in `CHANGELOG.md` and `.claude-plugin/plugin.json`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Marketing / version text updated alongside behavior changes; no runtime risk identified in review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: None unless release process requires extra checks beyond bump-version skill

---

### FINDING_13: `AGENTS.md` — strength of “do not write `session-env` from the orchestrator” guidance
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Wording may read softer than a hard prohibition (detail delegated to `SKILL.md` NEVER #14), so authors might append `session-env` lines via raw `printf`, bypassing `write-session-env.sh` validation and risking malformed env or accidental token materialization where downstream steps assume canonical shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_14: `docs/installation-and-setup.md` — missing `jq` vs hook JSON parsing / halt consequences
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: The `jq` install bullet no longer carries an explicit post-`/design` halt / consequence chain after hook stack changes; operators may underestimate impact on structured parsing for remaining bump/stop hook paths until subtle tmpdir or stop-guard issues surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_15: `AGENTS.md` — `/design` SendMessage bullet removed without replacement top-level guidance
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The `/design` `SendMessage` bullet was deleted rather than rewritten to concise inline-only guidance per plan, diluting top-level recovery text now buried in deeper docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a concise replacement bullet describing inline-only /design and pointers to flags.md / design SKILL.md.

---

### FINDING_16: Git history shape vs plan’s atomic single-commit expectation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Multiple commits (including log flushes) vs the plan’s single atomic commit guidance increases the cost to see the full mechanical change set that was intended to be co-landed (deletion + callsites + CI coupling).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

Because this output contains one or more `### FINDING_N:` blocks, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included.
