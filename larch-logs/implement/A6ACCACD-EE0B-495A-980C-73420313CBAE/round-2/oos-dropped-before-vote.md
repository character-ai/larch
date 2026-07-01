### OOS_1: [OUT_OF_SCOPE] measure_realized_cost skips validated runs when SKILL.md is missing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-corpus-metrics
- **Severity**: important
- **Concern**: `measure_realized_cost()` drops an entire skill when `_skill_md_path()` finds no current `SKILL.md`, even though `run_dirs_by_skill` already includes validated runs for that skill. Those runs never enter `invocations` or `realized_tokens`, so invocations undercount versus the `run_dirs` denominator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Count the run with skill_md_tokens=0 or emit an explicit zero-floor row instead of continue.
  - From codex-specialist-correctness: Keep the skill row with a zero floor or count the validated runs anyway instead of skipping the skill entirely
  - From cursor-specialist-edge-cases: Pre-existing; count runs at zero skill-md floor per plan denominator rules
  - From dyn-dyn-corpus-metrics: **Suggested fix:** (concern-only; no separate fix bullet in source beyond counting runs at zero floor per plan denominator rules)

### OOS_2: [OUT_OF_SCOPE] reference path scope and normalization duplicated across renderer and tokens
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-corpus-metrics, dyn-dyn-design-capture
- **Severity**: latent
- **Concern**: Reference read normalization and in-scope rules are duplicated between `render_session_transcript.py` and `tokens.py` beyond the shared cache-suffix helper. Future path or scope rule changes in one module only can desync preserved transcript reads from heatmap/realized-cost parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Extract one shared normalize_reference_read_path used by both renderer and tokens.
  - From cursor-specialist-edge-cases: Extract shared is_in_scope_reference_path helper used by both modules
  - From dyn-dyn-corpus-metrics: **Suggested fix:** (architecture duplication; extract shared normalization helper used by both modules)
  - From dyn-dyn-design-capture: **Suggested fix:** Extract shared reference-path normalization and in-scope rules across renderer and measurement modules.

### OOS_3: [OUT_OF_SCOPE] staged defer-commit transcript not cleared before capture retry
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-corpus-metrics, dyn-dyn-design-capture
- **Severity**: latent
- **Concern**: Mandatory cleanup removes only root `$DESIGN_TMPDIR/session-transcript.jsonl`, not the defer-commit staging file under `$DESIGN_TMPDIR/larch-logs/design/<run-id>/session-transcript.jsonl`. A prior capture wrote staging `session-transcript.jsonl`; retry capture could report success without rewriting the staged file, and hoist could promote stale content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove or overwrite staging transcript before capture or verify staged mtime matches fresh capture output.
  - From dyn-dyn-corpus-metrics: **Suggested fix:** Explicit staged cleanup before capture to match mandatory-stale hygiene on resume.
  - From dyn-dyn-design-capture: **Suggested fix:** Add explicit staged cleanup before capture to match the plan’s mandatory-stale hygiene story on resume.

### OOS_4: [OUT_OF_SCOPE] no test for redacted operator repo plus plugin-cache path combo
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: No test for redacted operator repo plus plugin-cache path combo. A regression in strip-then-cache normalization could miss implement corpus reads with combined path shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add fixture asserting <OPERATOR_REPO_PATH>/plugins/cache/larch-local/larch/<ver>/skills/... normalizes correctly

### OOS_5: [OUT_OF_SCOPE] round-1 capture fixes lack targeted regression tests
- **Reviewer(s)**: dyn-dyn-design-capture
- **Severity**: important
- **Concern**: Round-1 fixes (source-env refresh failure still captures, cached `claude-source.env` `SESSION_UUID` invalidation, `session-id-drift` routing) have no targeted tests; regressions on those paths would not be caught before merge.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Slot coverage check**: All nine inventory slots appear in at least one block: `cursor-specialist-correctness` (1, 2, 13–15), `codex-specialist-correctness` (3, 7, 13), `cursor-specialist-edge-cases` (1, 4, 5, 13–16), `codex-specialist-edge-cases` (3, 6), `cursor-specialist-testing` (8–10), `codex-specialist-testing` (11), `codex-generalist` (5), `dyn-dyn-corpus-metrics` (1, 5, 13–15), `dyn-dyn-design-capture` (1, 12, 14, 15, 17).

**Note on FINDING_13 / FINDING_14 / FINDING_17 revision bullets**: `dyn-dyn-corpus-metrics` FINDING_25 and FINDING_26, and `dyn-dyn-design-capture` FINDING_31, listed only “Address the concern above.” with fix text embedded in the concern; bullets above quote the embedded **Suggested fix** / concern tail where the source’s standalone `Suggested revision` field was not substantive. `dyn-dyn-design-capture` FINDING_31 had no separate fix direction beyond the concern, so FINDING_17 omits a `- From dyn-dyn-design-capture:` bullet per the no-fabrication rule.

