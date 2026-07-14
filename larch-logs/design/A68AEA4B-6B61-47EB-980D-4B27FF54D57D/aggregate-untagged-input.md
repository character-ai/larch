### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates-gate-c.md
- **Concern**: Invariant tier-2 exhaustion lacks the wired cancellation terminal contract the acceptance criteria require. Scenario: Acceptance requires the run to end via the existing cancellation outcome with nothing published. The plan only says to skip approval, Step 5, and publication. It does not name a `SUMMARY_OUTCOME`, add it to the Step 0 Final-summary allowlist in `skills/design/SKILL.md`, extend `python/larch/design/design_summary.py` `_VALID_OUTCOMES`, or mirror the `cancelled-outline` hygiene in `skills/design/references/design-outline.md` (Final summary block, operator cancel line, exit 0, no `[DESIGNED]`). Exhaustion can stop mid-Gate C with no renderable terminal outcome.
- **Proposed resolution**: Mirror outline cancel hygiene for invariant exhaustion: e.g. `SUMMARY_OUTCOME=cancelled-invariant-violation`, Final summary block, operator cancel breadcrumb, and lifecycle/summary tests; keep issue title `[DESIGNING]`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates-gate-c.md
- **Concern**: Mid-ladder persistence of adverse invariant assessments is not forbidden. Scenario: The plan blocks publishing invariant violation notes and requires fresh reassessment after fixes, but it never says to withhold `persist-design-assessment` while an invariant remains in `violation`. Current Gate C already persists guideline `deviation` notes before approval. A persisted violation note can survive pause/resume or a failed tier-2 attempt and collide with later clean reassessment or publish refusal handling (I-Stale-1).
- **Proposed resolution**: Keep violation/deviation notes in sidecars during the ladder; call `persist-design-assessment` for invariants only on `clean` after reassessment. On tier-2 exhaustion cancel, remove any adverse invariant artifact before terminal summary.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:24-31
- **Concern**: Invariant tier-2 exhaustion names cancellation but omits terminal-outcome wiring. Scenario: The plan requires invariant cancellation after exhausted tier 2 with no publish, and acceptance requires the existing cancellation outcome with nothing published. It only assigns design_summary.py for guideline-exception disclosure, not a new SUMMARY_OUTCOME. skills/design/SKILL.md Final summary export list also lacks a matching cancelled-* token. render-final-summary rejects unknown outcomes at design_summary.py:670, so the hard-fail path cannot emit a terminal summary.
- **Proposed resolution**: Add a named cancelled-* outcome (for example cancelled-invariant-violation) to design_summary.py _VALID_OUTCOMES, skills/design/SKILL.md Final summary SUMMARY_OUTCOME export list, and approval-gates-gate-c.md terminal sequence (export outcome, run Final summary block, operator line, emit cached summary). Add a lifecycle test that render-final-summary accepts the new outcome.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:201-217
- **Concern**: Gate C postplan can still write Step 2b completion on size or split paths. Scenario: The plan says gate-c is a non-initial postplan site without Step 2b completion semantics. design_step2b.py only skips step-2b touches on POSTPLAN_RC=0 for non-step2b sites. POSTPLAN_RC=12 and 13 still append paths.step2b_done regardless of site. A Gate C ladder revision that hits plan-size refusal or partition routing would mark step-2b complete mid-Gate-C and corrupt resume or downstream guards.
- **Proposed resolution**: Extend _postplan_decide so POSTPLAN_RC=12 and 13 touch step2b_done only when site is step2b or empty. Add a gate-c postplan matrix test covering rc 0, 12, and 13 sentinel writes.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_log_publish_flow.py:522-579
- **Concern**: Sibling design-log publisher does not enforce the new assessment content gate. Scenario: A persisted invariant violation or bare/malformed guideline deviation is present as a regular file, so direct or recovery `design log-publish` emits no warning and publishes the run log despite the planned fail-closed sibling-publisher contract.
- **Proposed resolution**: Add this file and `python/tests/design/test_design_log_publish_flow.py` to the plan; classify persisted notes with the shared validator and prevent log publication for invariant violations or invalid guideline deviations.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:24-31
- **Concern**: Invariant tier-2 exhaustion lacks wired cancellation terminal flow. Scenario: The plan requires skipping approval, Step 5, and publication after invariant ladder exhaustion, but it does not add a named SUMMARY_OUTCOME, extend the Final summary allowlist in skills/design/SKILL.md, or register the outcome in design_summary _VALID_OUTCOMES. render-final-summary rejects unknown outcomes, so the acceptance hard-fail path cannot emit a terminal summary cleanly.
- **Proposed resolution**: Add a stable cancelled outcome (for example cancelled-invariant-violation), register it in design_summary _VALID_OUTCOMES and the SKILL.md Final summary export list, and document in approval-gates-gate-c.md the exact export, operator line, Final summary block, and exit sequence with no Step 5 or publish.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates-gate-c.md
- **Concern**: Guideline tier-2 fix failure has no terminal ladder outcome. Scenario: After tier-1 is consumed, tier-2 may attempt a guideline fix instead of declining. If reassessment still yields a bare deviation without an Exception block, the plan only blocks publish at Step 5c and does not define a Gate C terminal when both tiers are exhausted. The operator can remain in Gate C with no approve path and no documented cancellation.
- **Proposed resolution**: Mirror invariant exhaustion: when tier-2 guideline repair still leaves a bare deviation, refuse approval, export a named cancelled outcome through the Final summary block, and skip Step 5 and publication.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/references/validator-failure.md:3-28
- **Concern**: Gate C ladder revisions lack a validator-failure repair site. Scenario: The plan adds gate-c settle and settle-rc-dispatch branches, but validator-failure.md still documents only Step 2b, Gate B, Gate A, discussion-round2, and Step 5c. A postplan rc=10 during a Gate C plan revision has no Fix-and-retry path back to design-step35-settle.sh --site gate-c, so autofix fallback can mis-route to Gate A or stall.
- **Proposed resolution**: Add design Gate C to validator-failure.md: bind _validator_target_file to plan.txt, include design Gate C in the site list, and on ok or Fix-and-retry re-enter design-step35-settle.sh --site gate-c before resume@4b reassessment.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/design/design_summary.py:96-99
- **Concern**: Validated exception rationale is appended to an issue-upserted final summary without a redaction requirement. Scenario: A main-agent rationale can contain a secret-shaped value from the assessed plan or note; the new disclosure then publishes it to the tracking issue despite log publication scrubbing artifacts
- **Proposed resolution**: Add secret redaction before appending the exception disclosure and test that a valid exception with a secret-shaped rationale is redacted in the final summary.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates-gate-c.md:21-27
- **Concern**: Tier-2 counters have no defined consumption point. Scenario: The plan only says tier 1 is consumed for revised, no-progress, or bail. A tier-2 repair, failed settle, pause/resume, or guideline decline can re-enter Gate C without charging the main-agent round, violating the one-round-per-kind bound.
- **Proposed resolution**: Specify atomic tier-2 counter consumption before each main-agent repair or guideline decline, including failed-settle recovery, and add pause/re-entry coverage for that bound.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates-gate-c.md
- **Concern**: Invariant tier-2 exhaustion lacks the standard cancellation terminal contract. Scenario: The acceptance path requires a hard fail with nothing published via the existing cancellation machinery. The plan only says to skip approval, Step 5, publication, and waiver paths in skills/design/SKILL.md. It does not name a SUMMARY_OUTCOME token, add it to design_summary.py _VALID_OUTCOMES, or document the export → Final summary block → operator line → terminal emit sequence used by cancelled-outline and other cancellation paths. render-final-summary rejects unknown outcomes, so a new cancelled-* token is required and must be enumerated.
- **Proposed resolution**: After invariant tier-1 and tier-2 fixes both fail reassessment, the orchestrator has no wired terminal sequence. Implementers may hard-stop without rendering a final summary, or pick an ad hoc outcome that fails render-final-summary validation. The hard-fail acceptance criterion becomes unverifiable. Add a named cancelled-* outcome (for example cancelled-invariant-violation) to approval-gates-gate-c.md with explicit terminal steps mirroring design-outline.md Cancel hygiene: export SUMMARY_OUTCOME, run the Final summary block, print a bounded operator line, emit cached summary, exit without Step 5. Extend the Final summary outcome enumeration in skills/design/SKILL.md, add the token to python/larch/design/design_summary.py _VALID_OUTCOMES, and cover render acceptance in python/tests/design/test_design_summary.py.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: agents/_implementer-base.md:1-220
- **Concern**: Generated implementer outputs omitted from firm changes. Scenario: `python/cli.py generate check` renders both external implementer prompts directly from this base, so the planned base edit leaves committed generated files stale and fails CI agent-sync.
- **Proposed resolution**: Add `agents/codex-implementer.md` and `agents/cursor-implementer.md` as regenerated updated files; run both generators and `python3 python/cli.py generate check`.
