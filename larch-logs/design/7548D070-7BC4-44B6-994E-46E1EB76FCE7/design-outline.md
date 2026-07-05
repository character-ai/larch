## Proposed Design Outline

### Goals
- Guarantee `architectural-guideline-assessment.md` is always persisted on the `--skip-approve` Gate C path when the repo has `ARCHITECTURAL_GUIDELINES.md`.
- Make design-session repo-root resolution deterministic so guidelines never resolve falsely `absent` from an ambient cwd/env fallback.
- Fix the shared "Larch version: unknown" final-summary symptom on the same runs (user-confirmed in scope).

### Non-goals
- No redesign of the architectural-guidelines subsystem or implement-side note handling.
- No change to genuinely-absent-guidelines behavior (still returns 0, no artifact, no warning).
- No new guessing heuristics inside `_resolve_repo_root` itself.

### Approach sketch
- Capture an authoritative repo-root once at Step 0 session setup (known-good cwd) and persist it into the design session env.
- Thread an explicit `--repo-root` into the Gate C `present-note` + `persist-design-assessment` calls (and Step 1d.7 present-note), removing the fragile cwd/env fallback.
- Resolve the design final-summary version from that same authoritative root/manifest.
- Preserve the fail-closed contract: a non-zero persist still logs a bounded `Warnings` line and stops Gate C.

### Surfaces in scope
- Step 0 session-env writer (`python/larch/state/session_env.py` / `design step0-session`): capture + expose repo-root.
- `skills/design/references/approval-gates.md`: thread `--repo-root` into Gate C guideline calls.
- `python/larch/state/_report.py` version resolver (`_read_larch_version`): fix "version: unknown".
- New regression under `python/tests/` driving the `skip_approve_requested=true` Gate C persist path.

### Open questions
- None.
