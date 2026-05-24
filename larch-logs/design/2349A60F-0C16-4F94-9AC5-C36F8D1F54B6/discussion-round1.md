## Decision 1: L3 cross-issue notification mechanism
- **Question**: How should L1 ensure #2672 (L3 panel) tracks the deferred per-round velocity check?
- **Resolution**: Post a comment on #2672 at end of Step 5 (best-effort, after `larch:plan` write + design log publish + [DESIGNED] rename). The comment notes that L1 (#2670) deferred per-round velocity to L3 and lists the trigger spec (>20% plan growth AND >10 accepted findings between rounds, skipped on `--trivial`).
- **Source**: user

## Decision 2: Split-path behavior in the interim (until L3 lands)
- **Question**: When the user picks "Let my panel of agents split this feature for you", what does L1 do?
- **Resolution**: Hard-fail (non-zero exit) with a user-visible message indicating the decomposition panel is in development and will be available soon. `$DESIGN_TMPDIR` is preserved on this exit so the operator can re-run after L3 lands or revise the feature description first. No `larch:plan` write, no `[DESIGNED]` rename, no design log publish.
- **Source**: user

## Decision 3: Plan-format migration depth
- **Question**: How deep does the `### NEW:`/`### UPDATED:`/`### REWRITTEN:` heading retrofit go?
- **Resolution**: Step 2b prose updated to require the heading format, AND reviewer-prompt rendering + relevant test fixtures updated to standardize on it. Old `larch-logs/` history examples remain immutable; the change is forward-looking for new plans but normalizes the rendering pipeline now.
- **Source**: user

## Decision 4: Threshold check re-fire on plan revisions
- **Question**: When Gate B applies findings or Gate C re-runs the review and produces a revised plan, does the Step 2b threshold check re-fire?
- **Resolution**: Yes — the check is per-plan-write. Every finalized `plan.txt` (initial Step 2b, Gate B Apply, Gate C re-run, post-plan discussion sub-round revision) re-fires `check-plan-size.sh`. If a soft/hard trigger fires on a revision, the same Split/Cancel AskUserQuestion runs.
- **Source**: user

## Decision 5 (codebase-derived): L3 issue exists at #2672
- **Question**: Is #L3-issue (referenced in the feature description) filed yet?
- **Resolution**: Yes — #2672 "Lesson 3: Decomposition / break-up analysis panel for /design" is open. The multi-round loop dependency referenced in the feature description (the venue for the per-round velocity check) is #2677.
- **Source**: codebase

## Decision 6 (codebase-derived): Eliminated "ownership domains" trigger from Step 1c
- **Question**: What counts as an "ownership domain" for the >3-domains trigger?
- **Resolution**: The domain-count trigger is eliminated entirely (per Step 1c answer). Soft triggers remaining: plan body >250 lines, `diff_lines` >600, files-count (heading count) >8, main-agent semantic guesstimate. Hard triggers remaining: plan body >800 lines, `diff_lines` >1500.
- **Source**: user (Step 1c)
