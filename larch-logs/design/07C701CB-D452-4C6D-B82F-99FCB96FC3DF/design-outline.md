## Proposed Design Outline

### Goals
- Prevent background grep probes from scanning unbounded directories by documenting a new `../` ascent prohibition in `BASH_AUTHORING.md` and `stall-recovery.md`.
- Enforce the prohibition mechanically by extending `scripts/lint-bare-grep-probe.sh` to flag grep-family path arguments containing `../`.

### Non-goals
- Harness-level output-size or wall-clock limits (out of larch's control).
- Fixing any historical probe that already ran; guidance applies prospectively.
- Touching Python code, `cli.py`, or any non-Bash/markdown surface.

### Approach sketch
- Add a "Bounded search root" subsection to `BASH_AUTHORING.md` §1 forbidding `../` ascents from tmpdir variables in background grep probes.
- Add a one-sentence note to `stall-recovery.md` sub-step 5 (retry dispatch) referencing the `BASH_AUTHORING.md` rule.
- Extend the token-analysis loop in `lint-bare-grep-probe.sh` to detect when a path argument contains `../` and emit a new violation class; add a `# lint-bare-grep-probe: ok` suppression path for intentional uses.
- Update `lint-bare-grep-probe.sh` comments and `BASH_AUTHORING.md` to document the new suppression path.
- Add test fixtures to `skills/design/scripts/` (or the existing test harness) covering the new lint check.

### Surfaces in scope
- `BASH_AUTHORING.md`
- `skills/implement/references/stall-recovery.md`
- `scripts/lint-bare-grep-probe.sh`

### Open questions
- None.
