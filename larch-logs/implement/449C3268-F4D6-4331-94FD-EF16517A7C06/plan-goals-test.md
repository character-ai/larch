## Goal
Implement issue #5839: [IMPLEMENTING] [BUG] implement/SKILL.md:91 fabricated "merge-conflict" stall class (round IX).

## Implementation Plan
**Severity**: High (orchestrator-guidance correctness; runtime Python classifier unaffected).

**What**: The round-IX Strunk & White compression of `skills/implement/SKILL.md` (#5787, PR #5830) rewrote a code-accurate recovery description into one that contradicts the live classifier, and deleted the operator action.

- **Before** (correct): *"Operators must resolve postbump rebase conflicts manually (abort or finish the rebase locally). Step 18a classifies this as `transient-infra` / `step8-shippr` so a Step 8 retry can be dispatched after the operator resolves the conflict."*
- **After** (`SKILL.md:91`, wrong): *"Step 18a recovery classifies it as `merge-conflict` and re-enters conflict resolution."*

**Evidence**:
- `python/larch/state/_classify.py:123-124` returns `("transient-infra", "step8-shippr", "rebase-transient")` for `step == "rebase-failed"`. `merge-conflict` is **not a failure class** anywhere in the code (grep finds it only as prose).
- The before-text explicitly said conflict-resolution handoff is *absent* on this path; the after-text claims the opposite ("re-enters conflict resolution").
- The compression also **deleted** the manual-resolution sentence — the only operator action for this degraded path.

**Consequence**: misdirects the orchestrator at the postbump Step 8b rebase recovery point (it will expect a classification that never appears and auto-recovery that does not exist). It is prose, so the deterministic Python classification is unaffected — but the guidance is now actively wrong at a fragile recovery point that no lint covers.

**Fix**:
- Restore `transient-infra` / `step8-shippr` and the manual-resolution sentence.
- De-stale the "postbump" wording in the same line (per-PR version bump was retired; see the terminology-cleanup issue) — e.g. *"Step 8b force-push-gate rebase conflicts"* / *"resolve these Step 8b rebase conflicts manually."*

**Fold in (same file, same PR origin)**:
- `SKILL.md:547` — the `7.r` Rebase Checkpoint Macro short-name was changed `commit (review)` to `checks (2)`. Per the macro convention (`4.r` uses Step 4's name `commit (impl)`; `7a.r` uses Step 7a's name `pre-ship`) and the implement `step-name-registry.tsv` (Step 6 = `checks (2)`, Step 7 = `commit (review)`), `7.r` must be `commit (review)`. Low severity (a progress-breadcrumb label), but an unjustified token mutation in a "prose-only" change.

**Verify while fixing** (lower-confidence audit suspicions from the same PR):
- `SKILL.md:628` — *"deviations are warnings only and never block PR creation"* was softened to *"...unless a helper exit code says otherwise"*; confirm the "never block" invariant is intact.
- Dropped operative specifics that may or may not be covered by referenced files: the Step 10 `run-log refresh` line; the *"do not call `final-report write` in the 7a pre-ship checkpoint"* prohibition; exact `UNTRACKED_BASELINE=missing` / `GIT_PROBE_FAILED=true` warning strings.

**Origin**: PR #5830 (#5787), umbrella #5788 (md-to-py round IX), merged under a degraded review panel.

## Test plan
(no test plan section in plan-file)
