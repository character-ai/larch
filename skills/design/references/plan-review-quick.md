# Plan Review — Quick Mode

**Consumer**: `/design` Step 3 when `quick_mode=true`. Replaces `plan-review.md` (~17 KB).

**When to load**: only when `quick_mode=true`. When `quick_mode=false`, load `plan-review.md` instead.

## Procedure

Claude reviews the plan inline — no external reviewers, no voting panel. Check:

1. **Completeness**: does the plan cover every part of the feature description?
2. **Correctness**: is the approach logically sound? Any obvious logic errors?
3. **Risk/integration**: breaking changes, security concerns, obvious failure modes?
4. **Verification**: concrete post-change check (`/relevant-checks`, a test, or a dry-run)?
5. **Scope**: stays within stated boundaries, no speculative additions?

Accept when the concern is clear and unambiguous. Reject nits and speculative concerns. Mark valid but out-of-scope items as OOS.

Revise `$DESIGN_TMPDIR/plan.txt` for each accepted finding, then write the output files.

## Output files (required — same contract as normal mode)

- **`$DESIGN_TMPDIR/voting-tally.md`**: `Quick mode — Claude-only plan review.` + one sentence per finding (or `No findings.`).
- **`$DESIGN_TMPDIR/accepted-plan-findings.md`**: one `FINDING_N` block per accepted finding. Empty if none.
- **`$DESIGN_TMPDIR/rejected-findings.md`**: one `[Plan Review]` block per rejected finding. Empty if none.
- **`$DESIGN_TMPDIR/oos.md`**: one `OOS_N` block per OOS item. Empty if none.

When `SESSION_ENV_PATH` is non-empty, write accepted non-security OOS to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md` (apply the same `focus-area\s*=\s*security` unfenced detection as `plan-review.md`).

## Templates (byte-preserved; keep in sync with `plan-review.md`)

```
### FINDING_N: <title>
- **Concern**: <what was raised>
- **Resolution**: <how the plan was revised>
```

```
### [Plan Review] Claude (quick mode)
**Finding**: <description including concern and suggested revision>
**Reason not implemented**: <justification>
```

```
### OOS_N: <short title>
- **Description**: <full description; include affected file paths and line ranges when applicable>
- **Reviewer**: Claude (quick mode)
- **Vote tally**: N/A — quick-mode self-review
- **Phase**: design
```
