## Decision 1: Fix scope — primary re-derivation + flush/batch backstop
- **Question**: The issue's suggested fix has two parts: (1) a primary fix that re-derives the outcome from live ship evidence at the run's own pre-ship flush, and (2) a backstop that reconciles stale "stalled" labels in the run-log flush/batch path using manifest PR/merge evidence. Should this design cover both, or just the primary fix?
- **Resolution**: Both. No response was received from the operator within 60s; the recommended default was applied. Rationale: the audit's evidence (29/31 mislabeled runs carry PR numbers with all 29 merged, "verified via gh") suggests these runs likely shipped through a path that never re-invokes ship-pr's own state-writing code (e.g. manual recovery outside the ship-pr retry loop), so the primary fix alone may not reach every case; the backstop is needed as defense-in-depth.
- **Source**: default (no user response within 60s; recommended option auto-applied)

## Decision 2: Historical run-log correction is out of scope
- **Question**: Should this change also rewrite the 31 already-committed run-log entries that currently show the wrong "Outcome: stalled" label, or is that out of scope for this bug fix?
- **Resolution**: Out of scope. No response was received from the operator within 60s; the recommended default was applied. Rationale: this bug fix's job is to stop future mislabeling; correcting already-committed historical run-log files is a distinct one-time data-repair task with its own blast radius (rewriting many committed files) that can be filed as its own follow-up if wanted.
- **Source**: default (no user response within 60s; recommended option auto-applied)
