## Decision 1: Lint extension
- **Question**: Should `scripts/lint-bare-grep-probe.sh` be extended to detect `../` relative path ascents in grep probes?
- **Resolution**: Yes — extend the linter to flag grep-family probes whose path argument contains `../` ascents in orchestrator-facing SKILL.md and references.
- **Source**: user

## Decision 2: Documentation scope
- **Question**: Add the relative-ascent rule to `BASH_AUTHORING.md` only, or also `stall-recovery.md`?
- **Resolution**: Both files — add the rule to `BASH_AUTHORING.md` and add a targeted note in `stall-recovery.md` sub-step 5 (retry dispatch) about bounded-root probes.
- **Source**: user
