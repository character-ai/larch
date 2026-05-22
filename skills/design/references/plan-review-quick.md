# Plan Review — Quick Mode

**Consumer**: `/design` Step 3 when `quick_mode=true`. Replaces `plan-review.md` (~17 KB) to save context on quick-mode runs.

**Contract**: Claude-only inline plan review for quick-mode `/design` Step 3. Produces the same four artifact files as normal mode (`voting-tally.md`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`) without external reviewers or a voting panel. OOS security routing uses the same detection rules as `plan-review.md`.

**When to load**: only when `quick_mode=true`. When `quick_mode=false`, load `plan-review.md` instead.

## Procedure

Claude reviews the plan inline — no external reviewers, no voting panel. Check:

1. **Completeness**: does the plan cover every part of the feature description?
2. **Correctness**: is the approach logically sound? Any obvious logic errors?
3. **Risk/integration**: breaking changes, security concerns, obvious failure modes?
4. **Verification**: concrete post-change check (`bash scripts/relevant-checks.sh`, a test, or a dry-run)?
5. **Scope**: stays within stated boundaries with no speculative additions?

Accept when the concern is clear and unambiguous. Reject nits and speculative concerns. Mark valid but out-of-scope items as OOS.

**Do NOT revise `$DESIGN_TMPDIR/plan.txt`** in this step. Quick-mode review only collects findings into the output files below; plan revision is owned by Gate B (Step 3.5) per explicit user choice. Leave `plan.txt` and `diff-lines.txt` unchanged.

## Output (verbosity depends on SESSION_ENV_PATH)

**When `SESSION_ENV_PATH` is non-empty** (nested under `/implement`): suppress inline prints. Token-reduction contract: nested runs MUST NOT push the full findings list into the parent context.

**When `SESSION_ENV_PATH` is empty** (standalone): print accepted findings under `## Plan Review Findings (Voted In)` and the tally inline.

## Output files (required — same artifact set as normal mode)

Write to `$DESIGN_TMPDIR/` after completing the review and plan revision:

- **`voting-tally.md`**: `Quick mode — Claude-only plan review.` + one sentence per finding (or `No findings.`).
- **`accepted-plan-findings.md`**: one `FINDING_N` block per accepted finding. Empty if none.
- **`rejected-findings.md`**: one `[Plan Review]` block per rejected finding. Empty if none.
- **`oos.md`**: one `OOS_N` block per non-security OOS observation. Empty if none. **Exclude security-tagged OOS** — same rule as `oos-accepted-design.md` below.

**OOS artifact write** (when `SESSION_ENV_PATH` is non-empty): write accepted non-security OOS to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md`. Skip when `SESSION_ENV_PATH` is empty.

**Security detection** (apply identically to both `oos-accepted-design.md` and `oos.md`): scan each OOS block for `focus-area\s*=\s*security` (case-insensitive). Classify occurrences as **fenced** (inside a backtick code span or triple-backtick fence) or **unfenced**. Route as security only when at least one unfenced occurrence exists — if every occurrence is fenced, treat as meta-discussion and route through the normal public OOS path. When prose indicates a security concern without the literal token, apply the same "if uncertain, do not file publicly" guidance (prose-security judgment). Real security findings MUST include at least one unfenced occurrence (security counter-invariant).

## Templates (structure-aligned with `plan-review.md`; keep in sync)

```
### FINDING_N: <title>
- **Concern**: <what was raised>
- **Proposed resolution**: <suggested change to the plan; applied at Step 3.5 Gate B only if the user chooses to apply this finding>
```

```
### [Plan Review] <Reviewer Name>
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
