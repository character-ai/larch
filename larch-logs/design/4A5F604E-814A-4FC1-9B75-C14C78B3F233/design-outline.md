## Proposed Design Outline

### Goals
- Move three prose sections from `skills/implement/SKILL.md` to `skills/implement/references/` files to cut ~130 lines from the always-loaded prompt.
- Eliminate all inline Bash logic from SKILL.md by creating self-rehydrating wrapper scripts; every ```bash fence becomes a single script call.
- Merge consecutive fence pairs (Steps 4/6/7/16/17/18) so each step is one Bash tool call instead of two, saving ~6 turns/run.

### Non-goals
- Changing the external behavior of any existing `/implement` step.
- Modifying scripts other than as strictly required by the wrapping approach.
- Altering CI configurations or GitHub Actions workflows.

### Approach sketch
- Extract Rebase Checkpoint Macro, Phantom Untracked Probe, and ship-driver exit-matrix (+ autonomous CI-fix sub-procedure) to three new reference `.md` files; replace in-file bodies with `MANDATORY — READ ENTIRE FILE` pointers.
- Add `--forked-target` flag to `scripts/rebase-checkpoint-probe.sh` to absorb the `BASE_ARGS=()` inline logic at Steps 1.r/4.r/7.r.
- Create per-step wrapper scripts that internalize token/timing rehydration and step-specific logic; each script is self-rehydrating from `plugin-root.env` and `session-env.sh`.
- Fold step-telemetry-mark into `step-16.sh` and `step-17.sh`, and OOS-checkpoint error handling into step-8+ entry script.
- Rewrite `scripts/test-implement-timing-rehydration.sh` to assert NO inline session read-key calls in SKILL.md and add structural fence-shape check.
- Update `scripts/test-implement-structure.sh` for MANDATORY pointers and new reference file locations.

### Surfaces in scope
- `skills/implement/SKILL.md`
- `skills/implement/references/` (3 new files)
- `skills/implement/scripts/` (13 new step-wrapper scripts + sibling .md files)
- `scripts/rebase-checkpoint-probe.sh` + `.md`
- `scripts/test-implement-timing-rehydration.sh`
- `scripts/test-implement-structure.sh`
- `Makefile` (if new test targets needed)

### Open questions
- None.
