### FINDING_1: Invariant exhaustion lacks a wired cancellation terminal outcome
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Invariant tier-2 exhaustion does not define the existing cancellation terminal flow. The plan omits a named `SUMMARY_OUTCOME`, allowlist updates, and the export → Final summary → operator line → terminal emit sequence. Since `render-final-summary` rejects unknown outcomes, the hard-fail acceptance path may stop without a renderable terminal outcome or published output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror outline cancel hygiene for invariant exhaustion: e.g. `SUMMARY_OUTCOME=cancelled-invariant-violation`, Final summary block, operator cancel breadcrumb, and lifecycle/summary tests; keep issue title `[DESIGNING]`.
  - From Cursor-Innovation: Add a named cancelled-* outcome (for example cancelled-invariant-violation) to design_summary.py _VALID_OUTCOMES, skills/design/SKILL.md Final summary SUMMARY_OUTCOME export list, and approval-gates-gate-c.md terminal sequence (export outcome, run Final summary block, operator line, emit cached summary). Add a lifecycle test that render-final-summary accepts the new outcome.
  - From Cursor-Pragmatic: Add a stable cancelled outcome (for example cancelled-invariant-violation), register it in design_summary.py _VALID_OUTCOMES and the SKILL.md Final summary export list, and document in approval-gates-gate-c.md the exact export, operator line, Final summary block, and exit sequence with no Step 5 or publish.
  - From Cursor-Requirements: After invariant tier-1 and tier-2 fixes both fail reassessment, the orchestrator has no wired terminal sequence. Implementers may hard-stop without rendering a final summary, or pick an ad hoc outcome that fails render-final-summary validation. The hard-fail acceptance criterion becomes unverifiable. Add a named cancelled-* outcome (for example cancelled-invariant-violation) to approval-gates-gate-c.md with explicit terminal steps mirroring design-outline.md Cancel hygiene: export SUMMARY_OUTCOME, run the Final summary block, print a bounded operator line, emit cached summary, exit without Step 5. Extend the Final summary outcome enumeration in skills/design/SKILL.md, add the token to python/larch/design/design_summary.py _VALID_OUTCOMES, and cover render acceptance in python/tests/design/test_design_summary.py.

### FINDING_2: Adverse invariant assessments may persist mid-ladder
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan does not forbid persisting adverse invariant assessments before the ladder completes. A persisted violation note could survive pause/resume or a failed tier-2 attempt and conflict with later reassessment or publication handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep violation/deviation notes in sidecars during the ladder; call `persist-design-assessment` for invariants only on `clean` after reassessment. On tier-2 exhaustion cancel, remove any adverse invariant artifact before terminal summary.

### FINDING_3: Gate C postplan can write Step 2b completion markers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: On `POSTPLAN_RC=12` or `13`, `design_step2b.py` appends `paths.step2b_done` regardless of site. A Gate C size-refusal or partition path could therefore mark Step 2b complete and corrupt resume or downstream guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend _postplan_decide so POSTPLAN_RC=12 and 13 touch step2b_done only when site is step2b or empty. Add a gate-c postplan matrix test covering rc 0, 12, and 13 sentinel writes.

### FINDING_4: Sibling design-log publishing lacks the assessment content gate
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The sibling design-log publisher can publish when persisted invariant violations or malformed/bare guideline deviations exist as regular files, because it does not enforce the planned fail-closed assessment validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add this file and `python/tests/design/test_design_log_publish_flow.py` to the plan; classify persisted notes with the shared validator and prevent log publication for invariant violations or invalid guideline deviations.

### FINDING_5: Guideline tier-2 failure lacks a terminal outcome
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: After tier-1 is consumed, a guideline tier-2 repair may still leave a bare deviation without an exception block. The plan blocks publication but does not define a Gate C terminal cancellation when both tiers are exhausted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror invariant exhaustion: when tier-2 guideline repair still leaves a bare deviation, refuse approval, export a named cancelled outcome through the Final summary block, and skip Step 5 and publication.

### FINDING_6: Validator-failure recovery omits Gate C
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Gate C ladder revisions lack a validator-failure repair site. A postplan `rc=10` during a Gate C revision has no documented Fix-and-retry path back to `design-step35-settle.sh --site gate-c`, so fallback may mis-route to Gate A or stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add design Gate C to validator-failure.md: bind _validator_target_file to plan.txt, include design Gate C in the site list, and on ok or Fix-and-retry re-enter design-step35-settle.sh --site gate-c before resume@4b reassessment.

### FINDING_7: Exception disclosure lacks secret redaction
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A validated exception rationale is appended to an issue-upserted final summary without a redaction requirement, so secret-shaped values from the plan or note could be published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add secret redaction before appending the exception disclosure and test that a valid exception with a secret-shaped rationale is redacted in the final summary.

### FINDING_8: Tier-2 counters lack defined consumption points
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The plan does not define when tier-2 counters are consumed. Repairs, failed settles, pause/resume, or guideline declines could re-enter Gate C without charging the round, violating the one-round-per-kind bound.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify atomic tier-2 counter consumption before each main-agent repair or guideline decline, including failed-settle recovery, and add pause/re-entry coverage for that bound.

### FINDING_9: Generated implementer outputs are omitted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Changes to `agents/_implementer-base.md` would leave the generated external implementer prompts stale, causing agent-sync or generation checks to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `agents/codex-implementer.md` and `agents/cursor-implementer.md` as regenerated updated files; run both generators and `python3 python/cli.py generate check`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: agents/claude-implementer.md
- **Concern**: [SCOPE-REDUCTION] Tier 1 replaces the required `design.plan_revision` autonomous lane with a Claude-only `MODE=plan-revise` carve-out. Scenario: Binding scope requires tier 1 to use the existing autonomous plan-revision machinery (plan-review apply lane). `python/larch/core/config.py` already owns `design.plan_revision` as Codex→Cursor→Claude via `python/cli.py plan revise-waterfall`. The plan routes tier 1 through a second `/design` subagent mode instead, bypassing registry policy (G-Cfg-1), expanding AGENTS/agent surfaces, and conflicting with the non-goal to keep plan-review machinery untouched.
- **Proposed resolution**: Route tier 1 through `design.plan_revision` / `plan revise-waterfall` with a synthetic single-finding input for the named violation or deviation; reserve main-agent tier 2 and fresh `larch:arch-assessor` respawns. Drop `MODE=plan-revise`, `agents/_implementer-base.md`, and the second AGENTS carve-out unless scope is explicitly renegotiated.
