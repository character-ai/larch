# Review Round 2

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: SessionStart cleanup inherits `LARCH_TEST_TMP_ROOT` and may sweep wrong directory
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `scripts/cleanup-sessionstart.sh:21` — The new implicit SessionStart cleanup inherits `LARCH_TEST_TMP_ROOT`, and `python/larch/core/cleanup_skill.py:52-54` treats that test hook as the temp root to sweep. A developer or CI shell that has this exported can now silently delete matching stale `larch-*` entries under an arbitrary directory at session start, whereas the old risk required an explicit `/cleanup` run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Invoke the background cleanup with `LARCH_TEST_TMP_ROOT` removed, for example `env -u LARCH_TEST_TMP_ROOT python3 "$CLI" cleanup run`, or gate that override so production SessionStart cleanup always targets the real temp roots.


