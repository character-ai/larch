## Decision 1: Which gate's assessment to commit
- **Question**: Capture the architectural-guideline assessment at Gate C only, or also at Step 1d.7 (outline)?
- **Resolution**: Gate C only. Gate C assesses the final approved `plan.txt` and runs on every completed design run (normal and `--skip-approve`), satisfying the acceptance criteria with the smallest change. Step 1d.7 outline-assessment persistence is OUT of scope.
- **Source**: user

## Decision 2: Committed surface for the assessment text
- **Question**: Dedicated `architectural-guideline-assessment.md`, an `execution-issues.md` entry, or both?
- **Resolution**: Dedicated file `architectural-guideline-assessment.md` written to `$DESIGN_TMPDIR` (committed to `larch-logs/design/<RUN_ID>/`). Stable, predictable name for `audit-runs` / `fluff-analysis`. No `execution-issues.md` entry.
- **Source**: user

## Decision 3: Behavior when guidelines are absent or invalid
- **Question**: What to persist when `ARCHITECTURAL_GUIDELINES.md` is absent or invalid?
- **Resolution**: Persist only when guidelines are `present` (acceptance criteria scope: "a design run where guidelines are present"). `absent` -> write nothing. `invalid` -> write nothing (the existing chat warning is sufficient; no committed artifact).
- **Source**: codebase (acceptance criteria + `present_note_main` semantics)

## Hard constraints (scope boundaries)
- Reuse the existing design-log publish path: write `architectural-guideline-assessment.md` to `$DESIGN_TMPDIR`. The publish (`design_log_publish_flow._publish_excluded`) is exclude-based; this `.md` name survives the filter, so NO allowlist edit is needed. Redaction + secret-scrub are applied by `_copy_tree_redacted` on copy.
- Read guidelines only through `architectural_guidelines.read_guidelines()` / the `present-note` helper. Never `Read`/`Write` the repo-root `ARCHITECTURAL_GUIDELINES.md`.
- Do NOT modify the implement-side guideline machinery (staged/durable note, HEAD/diff fingerprinting). Design has no code diff at assessment time, so that machinery is not mirrored.
- Do NOT change assessment content or the `present-note` clean/deviation logic. Only PERSIST what is already produced. The clean note is deterministic (`CLEAN_PRESENTATION_NOTE`); the deviation text is orchestrator-authored prose handed to the persistence helper.
- Gate C may be re-entered (Discuss further / Re-run review panel); the file is overwritten each time so the committed copy reflects the assessment at the point of approval.
