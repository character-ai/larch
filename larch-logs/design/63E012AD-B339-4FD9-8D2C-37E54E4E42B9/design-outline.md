## Proposed Design Outline

### Goals
- Persist the Gate C architectural-guideline assessment (clean note or deviation text) to a committed `/design` run-log file.
- Make the assessment auditable post-hoc by `audit-runs` and `fluff-analysis`.

### Non-goals
- Step 1d.7 outline-assessment persistence (superseded by the Gate C plan assessment).
- Changing assessment content or the `present-note` clean/deviation logic.
- Touching the implement-side guideline machinery (staged/durable note, HEAD/diff fingerprinting).
- Editing the publish allowlist; the publish is exclude-based and the new file survives the filter.

### Approach sketch
- Add a Python verb `architectural-guidelines persist-design-assessment` in `python/architectural_guidelines.py`, registered in the `python/cli.py` dispatch table (G-CLI-1).
- The verb writes `$DESIGN_TMPDIR/architectural-guideline-assessment.md`: `--assessment clean` writes the deterministic `CLEAN_PRESENTATION_NOTE`; `--assessment-file` writes orchestrator-authored deviation prose. Present-only: `absent`/`invalid` write nothing and exit 0.
- Wire one call into the Gate C Presentation contract in `skills/design/references/approval-gates.md`, after the orchestrator's clean/deviation decision, on both the normal and `--skip-approve` paths.
- Reuse the existing exclude-based design-log publish plus `_copy_tree_redacted` redaction and secret-scrub; no allowlist edit.

### Surfaces in scope
- `python/architectural_guidelines.py`, `python/cli.py`
- `skills/design/references/approval-gates.md`
- `python/test_architectural_guidelines.py`
- `docs/run-logs.md` (document the new committed batch file)

### Open questions
- None.
