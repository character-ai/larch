## Proposed Design Outline

### Goals
- Remove the byte-identical duplicate Step 5 checks-failed blockquote from `SKILL.md`.
- Trim five call sites that re-inline the `## Checks Failure Entry Macro` body down to bare macro invocations with pinned `--site` / `--checks-site` tokens.
- Collapse the verbose Preflight exit-3 sub-cases A/B/C to a one-line pointer to `preflight-plan-audit.md`.

### Non-goals
- No changes to runtime behavior or step routing.
- No changes to Python, Bash scripts, or the Step 0 bootstrap.
- No renaming or structural refactoring beyond what the issue specifies.

### Approach sketch
- In `skills/implement/SKILL.md`: remove line 546 (duplicate blockquote), keep line 550 as the single shared post-fence blockquote, and trim the MANDATORY-READ + REDACTED_LOG_FILE re-inline from all four SKILL.md call sites (lines 487, 550, 604, and 612).
- In `skills/implement/references/self-review.md`: trim the fifth call site (line 29) identically.
- In `SKILL.md` Preflight exit-3 table row: replace the Sub-case A/B/C expansion with a one-line pointer to `preflight-plan-audit.md ## Clarify-request flow after AUDIT=refuse`.
- Update `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` to drop the `REDACTED_LOG_FILE` / `NOT raw LOG_FILE` requirement from the 5-line window check, since those facts now live only in the macro definition.

### Surfaces in scope
- `skills/implement/SKILL.md`
- `skills/implement/references/self-review.md`
- `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh`

### Open questions
- None.
