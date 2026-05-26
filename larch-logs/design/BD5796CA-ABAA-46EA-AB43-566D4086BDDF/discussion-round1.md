## Decision 1: Cross-skill scope
- **Question**: Should the design scope to /design only, or also harden other skills (research/implement/fix-issue) that may show the same re-entry pattern?
- **Resolution**: /design only. Cross-skill generalization is out of scope. If audit incidentally finds a similar pattern in another skill, do not fix here — at most note as OOS for follow-up.
- **Source**: user

## Decision 2: Defensive guard mandate
- **Question**: Must the design produce a defensive guard at /design entry to refuse spurious same-session re-entry, even if the code audit fails to identify a specific internal /design trigger?
- **Resolution**: Yes, always add a guard. Log forensics are unavailable (logs are flushed before the re-fire — confirmed by user), so the guard is the only reliable verification surface. The audit still runs to find any obvious internal trigger, but the guard ships regardless of audit findings.
- **Source**: user

## Decision 3: Anti-halt machinery touchability
- **Question**: Is the anti-halt continuation reminder block in `skills/design/SKILL.md` (and any related shared anti-halt prose) modifiable as part of this work?
- **Resolution**: Modify only with clear textual evidence of a specific mis-trigger pattern. The anti-halt machinery exists to fix the opposite problem (halts — see #1606, #1683, #2290, #2134); loosening it without evidence risks regressing that work. If audit produces clear evidence, modify surgically with regression coverage that pins both directions (no halts, no spurious re-entry).
- **Source**: user

## Decision 4: Regression test harness mandate
- **Question**: Is a regression test harness in-scope (a test that simulates a /design re-invocation on an issue already [DESIGNED] or with a larch:plan block, and verifies the bail + guard hit)?
- **Resolution**: Yes, in-scope. Add a sibling `test-*` harness wired into `make lint`. Coverage: lifecycle-prefix bail ([DESIGNING] and [DESIGNED]), larch:plan-block bail, the new session-cache sentinel hit, and the per-guard breadcrumb shape.
- **Source**: user

## Decision 5: Operator-visible breadcrumb on guard fire
- **Question**: When the defensive guard fires (refusing a spurious re-entry), should /design produce a prominent operator-visible signal naming which guard tripped (lifecycle | larch:plan | session-cache)?
- **Resolution**: Yes, prominent instrumented breadcrumb. Print a clearly-formatted `**⚠ /design: spurious re-entry detected** ...` line that names the guard, and for session-cache hits includes the timestamp of the prior completion. This is also what makes the regression harness in Decision 4 useful (the test can assert on the breadcrumb text).
- **Source**: user

## Decision 6 (codebase-resolved): Existing lifecycle-prefix guard already covers both states
- **Question**: Does the existing guard cover only `[DESIGNED]` (per the issue body) or also `[DESIGNING]` (mid-run re-entry)?
- **Resolution**: Both. The lifecycle regex in `scripts/lib-title-eligibility.sh` is `^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]` (case-insensitive). Mid-run and post-run re-entry attempts are both refused by the existing guard. Therefore the new session-cache sentinel is additive: it covers the narrow window AFTER /design returns but BEFORE the title is observable (e.g., GitHub eventual consistency on rename) AND the case where the title rename failed but the run completed.
- **Source**: codebase

## Decision 7 (codebase-resolved): Investigation surface bounded by issue + code
- **Question**: What investigation artifacts are available?
- **Resolution**: User confirmed: the larch run logs for `/design` are flushed before the spurious re-fire happens, so log forensics are not useful. The investigation surface is bounded to: (a) reading `skills/design/SKILL.md` end-to-end paying special attention to the anti-halt continuation reminder, Step 5 machine footer, Step 6 cleanup, and the Step 0b already-planned router; (b) grepping the plugin tree for `ScheduleWakeup`, `SendMessage`, `<<autonomous-loop`, and other re-entry-shaped touchpoints; (c) the examples and suspected mechanisms documented in the issue.
- **Source**: user + codebase

## Out-of-scope (explicit)

- The existing `[DESIGNED]` / `[DESIGNING]` title-prefix guard and the `larch:plan` in-body guard. They work and remain the safety net.
- Cross-skill generalization (research/implement/fix-issue re-entry hardening).
- Any redesign of /design unrelated to the spurious re-entry.

## Hard constraints

- Anti-halt machinery may only be modified with code-level evidence of a specific mis-trigger.
- Defensive guard must be additive — it does not replace the existing title-prefix / larch:plan guards.
- Log-forensics-based acceptance criteria are unattainable; acceptance test is hermetic regression coverage + code review.
