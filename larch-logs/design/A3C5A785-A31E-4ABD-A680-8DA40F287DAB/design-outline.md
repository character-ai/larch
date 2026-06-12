## Proposed Design Outline

### Goals
- Collapse Preflight items 1-3 into one `scripts/implement-preflight.sh` call, eliminating the forked-fence duplication.
- Move emergency fallback composition and bypass-log grammar into the new script, removing the long prompt-side prose.
- Add an offline harness covering the four required cases.

### Non-goals
- No change to Preflight items 4-7 (audit, audit-refuse handling, semantic materiality, pass gate).
- No change to `step-0-bootstrap.sh` interface or `bootstrap.py` plan-materialization.
- No behavioral change visible to callers: exit codes 0/2 for items 1-3, bypass log grammar byte-compatible.

### Approach sketch
- New `scripts/implement-preflight.sh`: argv `--issue N [--repo R] [--emergency] --preflight-tmpdir D`, runs admission gate, writes issue JSON to `$PREFLIGHT_TMPDIR/issue.json`, runs plan-block extraction, handles emergency fallback, emits KV envelope.
- KV envelope fields: `ADMISSION_RESULT=`, `RESUME=`, `TITLE=`, `BLOCK_PRESENT=`, `PLAN_PATH=`, `ISSUE_JSON_PATH=`, `BYPASS_COUNT=`.
- SKILL.md: replace the three admission/gh/plan-block read fences (plus forked variants) with one call to `implement-preflight.sh`; remove the emergency-fallback composition paragraphs from item 3; update the stale note at line 122; update item 4 to write `audit.txt` only on refuse path.
- Harness: `scripts/test-implement-preflight.sh` covers admission-fail, no-block, malformed-block, emergency title-fallback (including empty-title abort).

### Surfaces in scope
- `scripts/implement-preflight.sh` (new)
- `scripts/test-implement-preflight.sh` (new)
- `skills/implement/SKILL.md` (updated: Preflight section, item 3 prose, item 4 audit.txt guard, line 122 note)

### Open questions
- None.
