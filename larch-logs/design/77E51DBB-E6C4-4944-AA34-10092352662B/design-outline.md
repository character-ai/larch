## Proposed Design Outline

### Goals
- Stop the `/design` Step 2b.5 hard gate from firing on deletion-heavy or mechanical-churn plans (the #3118 false positive on a leaf partition piece).
- Key the hard diff trigger on estimated ADDED lines (`diff_added > 2000`), not total churn.
- Keep full backward compatibility with the existing `diff_lines:` trailer and its ~41 consumers.

### Non-goals
- Do not change the separate `plan_lines > 800` hard trigger.
- Do not add a Continue/override option to the hard Split/Cancel prompt.
- Do not change the `emit-plan.sh` → `diff-lines.txt` output contract.

### Approach sketch
- Add three OPTIONAL plan trailers — `diff_added: <N>`, `diff_deleted: <N>`, `mechanical_churn: true` — above the still-required last-line `diff_lines: <N>`.
- In `check-plan-size.sh`: when `diff_added` is present, fire the hard diff trigger on `diff_added > 2000`; deletions never trip it; when `diff_added` is absent, fall back to today's `diff_lines > 1500` (byte-identical legacy behavior).
- When `mechanical_churn: true`, suppress the hard diff trigger and emit a SOFT advisory machine signal instead (no Split/Cancel).
- Extend the machine output (new keys for added/deleted/soft-advisory) and teach SKILL.md Step 2b.5 to read them and print the advisory.
- Update the Step 2b drafting instruction, `flags.md` thresholds, and the regression harness.

### Surfaces in scope
- `skills/design/scripts/check-plan-size.sh` (+ sibling `.md`)
- `skills/design/SKILL.md` — Step 2b "Diff size estimate" + Step 2b.5 hard-branch handling
- `skills/design/references/flags.md` — Plan-size thresholds section
- `skills/design/scripts/test-check-plan-size.sh` — regression harness
- `skills/design/scripts/emit-plan.sh` / `design-driver.sh` — inspect; expected untouched since `diff_lines:` stays the last line

### Open questions
- None. Direction settled in Step 1c/1d Q&A.
