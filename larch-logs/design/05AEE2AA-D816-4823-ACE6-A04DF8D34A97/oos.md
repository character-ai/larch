### FINDING_10: Self-review OOS sinks are missing from the file-gate sink list
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Self-review paths can still write OOS directly to filing sinks, so they can bypass the new accepted-panel plus strict-majority-major gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add these self-review paths to the plan and keep self-review OOS logged-only unless they pass the same shared fileable predicate through a normal vote/classification artifact.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Retired latent-reroute branches remain after severity collapse
- **Description**: Retired latent-reroute branches remain after severity collapse. Scenario: Body Severity: latent reroute still flips classification/outcome on legacy-shaped blocks; new runs should not emit latent, so this is stale compatibility surface only
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/review/review_tally.py:635-660
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Disposition-gate bash harness not listed in plan file matrix
- **Description**: Disposition-gate bash harness not listed in plan file matrix. Scenario: Harness cases exercise checkpoint behavior against oos-accepted-* sinks; if fixtures assume vote-accepted semantics they may need refresh after fileable-only sinks
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_3: python/larch/review/review_tally.py:635-660
- **Description**: python/larch/review/review_tally.py:635-660. Scenario: Latent-reroute branches still key on body `Severity: latent` after `latent` is retired from live reviewer output
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/review/plan_review_tally.py:38-47
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Operator voting docs still describe every vote-accepted non-security OOS as filed
- **Description**: Operator voting docs still describe every vote-accepted non-security OOS as filed. Scenario: After the file gate lands, `docs/voting-process.md` will still tell operators that accepted non-security OOS is filed, with no strict-majority-`major` requirement
- **Reviewer**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/voting-process.md:118-124
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: Latent body-severity reroute branches survive after `latent` is retired
- **Description**: Latent body-severity reroute branches survive after `latent` is retired. Scenario: `_ledger_entry` and `_finding_oos_reroute_marker` still key on `**Severity**: latent`, leaving dead reroute logic once body severity is `major|minor|nit` only
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/review/review_tally.py:635-657
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

