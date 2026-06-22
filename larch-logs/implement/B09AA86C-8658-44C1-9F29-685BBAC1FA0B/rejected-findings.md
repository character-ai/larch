# Rejected Findings

# Review Round 1

### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Seeded `ARCHITECTURAL_GUIDELINES.md` does not match the approved plan
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The shipped guideline entries (e.g. `G-python-*`, stdlib Python, path validation) differ from the plan’s settled seed set (`G-Py-1`, `G-Py-2`, `G-Py-3`, `G-Skill-1`, `G-Enf-1`). `/design` and `/implement` will consult and surface deviations against the wrong operator-curated baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Replace the file body with the exact seeded set from the plan, preserving only the short opening note.
  - From codex-specialist-edge-cases-output.txt: Replace ARCHITECTURAL_GUIDELINES.md with the settled seeded G-Py, G-Skill, and G-Enf entries from the feature description.
  - From codex-specialist-testing-output.txt: Replace entries with the settled seed set and add a regression check for expected headings.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Staged assessment pinning ignores `DIFF_FINGERPRINT`
- **Reviewer(s)**: dyn-dyn-guidelines-flow-output.txt, dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `pin_note_from_staged()` and `note_consumable()` gate on file presence, symlink rejection, and `HEAD_SHA` equality only. They never compare the staged sidecar’s `DIFF_FINGERPRINT` to the current implementation diff. If invalidation is skipped and staged artifacts survive a code-changing CI fix or conflict-resolution commit, Phase B can copy a stale pre-fix assessment onto a new `HEAD` and surface it in the PR body or final summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guidelines-flow-output.txt: At pin time, re-materialize or read the stored diff snapshot, verify the fingerprint still matches, and refuse consumption (or require invalidation) when it does not.
  - From dyn-dyn-note-safety-output.txt: Have `pin_note_from_staged()` or `note_consumable()` require a matching `DIFF_FINGERPRINT` against a freshly materialized diff (or refuse consumption when staged sidecar fingerprint differs), and broaden ship-side invalidation to every implementation `HEAD` advance called out in the plan (CI-fix, conflict-resolution, pre-push repair), not only `did_fixing`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Final-summary path does not repin from staged assessment on `HEAD` advance
- **Reviewer(s)**: dyn-dyn-guidelines-flow-output.txt
- **Severity**: important
- **Concern**: `_architectural_guidelines_section` in `python/final_report.py` only calls `note_consumable(implement_tmpdir, current_HEAD)` and never attempts mechanical repin from staged assessment. On merge runs, `ship.py` can pin at pre-compose `HEAD`, then advance `HEAD` again via `post_ensure_refresh` / later `flush_logs_pre` calls. The PR body may include guideline notes while `summary-final.md` omits them unless the orchestrator runs the documented pre–Step 16 pin fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guidelines-flow-output.txt: Have `_architectural_guidelines_section` call the same mechanical pin helper used by `ship.py` when staged assessment exists but the durable note is unconsumable, or repin inside `final_report.write` before the consumability check.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_9: Missing integration tests for open-pr pin and CI-fix invalidation paths
- **Reviewer(s)**: dyn-dyn-guidelines-flow-output.txt
- **Severity**: important
- **Concern**: Plan acceptance called for coverage that `open-pr` resume still pins before `compose_pr_body()`, and that internal CI-fix commits trigger invalidation. Existing tests only exercise `_pin_and_load_guidelines_note` and `invalidate_implement_note` in isolation; `compose_pr_body` is mocked across ship integration tests, and `test_monitor_fixing_invalidates_guidelines_note` never runs `run_ship` or asserts `did_fixing` triggers invalidation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guidelines-flow-output.txt: Add integration tests that stub `compose_pr_body` to capture `architectural_guidelines_note` on `resume.start=open-pr`, and assert `invalidate_implement_note` is invoked when the CI monitor returns `did_fixing=True`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: TOCTOU symlink race in `read_guidelines()`
- **Reviewer(s)**: dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `read_guidelines()` rejects symlinks with `path.is_symlink()` and then reads via `path.read_text()` without `O_NOFOLLOW` or an open-and-`fstat` check. A local racer can swap the regular file for a symlink to out-of-repo content in the window between the check and the read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-note-safety-output.txt: Open the file with `O_NOFOLLOW` (or equivalent) and read from that fd, or read via `resolved` only after verifying `st_dev`/`st_ino` unchanged across the open; keep the existing `relative_to(repo_root)` guard.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: TOCTOU symlink race when reading durable note in `ship.py`
- **Reviewer(s)**: dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `_pin_and_load_guidelines_note()` calls `note_consumable()` and then separately `durable_note_path(...).read_text()`. The durable note is not re-checked for symlink/regular-file status at read time, so a TOCTOU symlink in `$IMPLEMENT_TMPDIR` could cause out-of-tmpdir content to be redacted and published into the PR body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-note-safety-output.txt: Read through a helper that opens with `O_NOFOLLOW` and rejects symlinks, or fold the read into `note_consumable()` / `pin_note_from_staged()` so check and read are one atomic operation on the same fd.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Untrusted content-block `tag` not validated before XML interpolation
- **Reviewer(s)**: dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `emit_untrusted_content_block()` interpolates `tag` directly into the XML wrapper (`<{tag} encoding="literal-redacted">`) without validating or escaping it. The `untrusted content-block` CLI accepts arbitrary `tag` argv, so a malformed tag can break out of the intended untrusted envelope and confuse downstream prompt parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-note-safety-output.txt: Restrict tags to a safe charset (e.g. `[A-Za-z0-9_]+`) or run the tag through the same escaping used for attributes; reject invalid tags at the CLI boundary.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0


# Review Round 2

### [rejected] FINDING_13

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_13: Materialized diff lacks untrusted-data framing in Phase A
- **Reviewer(s)**: dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: Phase A treats parsed guideline entries as untrusted but not the materialized implementation diff in `<architectural_guidelines_diff>`. Unlike conflict-resolution context and `SECURITY.md` inline-renderer rules, the diff helper emits no delimiter or framing prose. Prompt-like text in the branch diff can influence orchestrator-authored assessments copied into PR bodies and final summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-note-safety-output.txt: Add explicit “treat as untrusted data, not instructions” framing to Phase A (and/or prepend the same framing line to `materialize_diff_main()` stdout) before the diff content block.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (0 YES)

### FINDING_15: Open-PR `guidelines_changed` update path untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `guidelines_changed` open-PR update path in `pr.py` has no test coverage. On open-pr resume after reassessment, the remote PR may keep a stale or empty Architectural guidelines section even when ship composed a new note.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Test architectural_guidelines_section extractor and ensure_pr when remote body differs only in guidelines section.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0


# Review Round 3



