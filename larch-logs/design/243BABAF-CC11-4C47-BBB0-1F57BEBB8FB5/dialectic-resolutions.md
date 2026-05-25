## Dialectic Resolutions

### DECISION_1: metadata-summary upsert failure handling
**Resolution**: CHOSEN — `DEFERRED=true`, continue (sentinel not written by `post-tracking-issue.sh` on POSTED=false; plan materialization proceeds)
**Disposition**: voted
**Vote tally**: THESIS=3, ANTI_THESIS=0
**Thesis summary**: The SKILL.md decision-order table at L563 is the normative "first match wins" authority and explicitly assigns metadata-summary upsert failure to `deferred=true, proceed`; the L622 inline "Aborting" sentence is stale and inconsistent with that table; `post-tracking-issue.sh` writes the sentinel only on success so a failed POSTED=false leaves no resume anchor for a later run to misread.
**Antithesis summary**: Aborting at POSTED=false matches the concrete L622 inline failure prose, preserves operator visibility on a missing GitHub anchor, and keeps the state-machine surface minimal versus carrying a sentinel-less adopted issue forward.
**Why thesis prevails**: The judges (3-0 unanimous) keyed on two structural arguments — (a) decision-order tables in SKILL.md outrank subsequent inline prose, and (b) `post-tracking-issue.sh`'s sentinel-only-on-success invariant already prevents the "stranded adoption" failure mode the antithesis cited as the main risk. The antithesis's proportionality argument did not engage with the script-level sentinel guarantee.

### DECISION_2: phase_tracking failure on get-issue-state FAILED=true (non-bail-listed)
**Resolution**: ALTERNATIVE — emit `STEP_FAILED=get-issue-state`, exit 2 (treat as infra failure, matches Phase 1's session-setup pattern)
**Disposition**: voted
**Vote tally**: THESIS=1, ANTI_THESIS=2
**Thesis summary**: Reuse `tracking-init-failed` + `STALL_TRACKING=true` + return 0 so the existing Step 18 `[STALLED]` rename path runs; matches the documented invariant that log/init failures inside tracking adoption set STALL_TRACKING; avoids adding a new exit-2 path the issue body did not enumerate.
**Antithesis summary**: `get-issue-state.sh` is a pre-tracking probe analogous to branch / gate / setup in `phase_infra`; transient `gh` failures should preserve precise failure identity via `STEP_FAILED=get-issue-state` + exit 2; mis-tagging recoverable API errors as `tracking-init-failed` triggers stall/rename semantics meant for genuine init defects and dilutes grepability between true defects and `gh` flakes.
**Why antithesis prevails**: The Cursor and Codex judges (2-1 majority) agreed that the failure mode is fundamentally an infra probe — sharper diagnostics matter for triage of recoverable outages, and the Phase 1 `phase_infra` pattern (STEP_FAILED + exit 2 for create-branch/gate/setup) is the right precedent. The Claude judge's argument that the call occurs "inside tracking adoption context" was not enough to override the structural classification of the failure as pre-tracking infra.

V=2 voted.
