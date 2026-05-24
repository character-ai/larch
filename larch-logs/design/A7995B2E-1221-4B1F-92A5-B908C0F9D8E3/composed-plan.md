## Plan

### Problem

`/design` Step 5b invokes `/larch:issue` via the Skill tool to file accepted OOS items. The sub-skill returns three visually-terminal signals (an `ISSUES_*` machine block, a sentinel-write line, and a human-readable summary) that collectively read like a /design machine footer. After Step 5b returned, the orchestrator produced a summary and ended the turn, silently skipping:

- Step 5b annotate (`file-design-oos.sh annotate`)
- Step 5c.1–3 (compose `composed-plan.md`, `redact-secrets.sh`, `plan-block-write.sh`)
- Step 5c.5–7 (resolve `REPO`, `design-log-publish.sh`, `tracking-issue-write.sh rename --state designed`)
- Step 6 cleanup

The current anti-halt continuation reminder (skills/design/SKILL.md line 28) enumerates inter-step transitions `1c→1d→1e→2a→2a.5→2b→3→3.5→3b→4→4b→5→6` but does NOT enumerate the intra-Step-5 sub-step transitions, and there is no continuation banner at the end of Step 5b like the ones that follow Steps 2b/3/3.5/3b/4/4b.

### Scope

In scope: all four fixes from the issue body (Fix 1, Fix 2, Fix 3, Fix 4) + generic NEVER entry in `skills/shared/orchestrator-never.md`. Out of scope: any change to Step 5 mechanics (order of OOS filing, compose, plan-block-write, publish, rename remains unchanged).

### Files to modify

1. **`skills/design/SKILL.md`** (anti-halt reminder + Step 5b banner)
   - Line 28: extend the inline sub-step transition list. Current text reads `(1c→1d→1e→2a→2a.5→2b→3→3.5→3b→4→4b→5→6)`. Change to `(1c→1d→1e→2a→2a.5→2b→3→3.5→3b→4→4b→5→5a→5b→5c.1→5c.6→5c.7→6)`. Mapping: `5c.1` = item 1 in Step 5c body (compose `composed-plan.md`); `5c.6` = item 6 (`design-log-publish.sh`); `5c.7` = item 7 (`tracking-issue-write.sh rename --state designed`). The issue body's draft enumeration `5c.5 publish` is corrected here because item 5 in the current Step 5c body is "resolve `REPO`", not publish.
   - Between the end of Step 5b body and the `### 5c — Write` heading: insert a new continuation banner blockquote that explicitly names `/larch:issue` as a non-terminal sub-skill return. Exact text:
     ```
     > **Continue to Step 5c IMMEDIATELY.** The `/larch:issue` Skill tool's `ISSUES_*` machine block, sentinel-write line, and human-readable summary are the SUB-skill's terminal output — NOT the `/design` machine footer. Step 5b annotate (when /issue was invoked) and Step 5c (compose → redact → `plan-block-write.sh` → `design-log-publish.sh` → `tracking-issue-write.sh` rename to `[DESIGNED]`) still must run.
     ```

2. **`skills/shared/orchestrator-never.md`** (new generic NEVER entry — Fix 4)
   - Append a new numbered bullet `2.` after the existing entry 1 (the `ScheduleWakeup` rule). The entry follows the existing CI-backed-anchor format used by entry 1 (rule statement + `**Why**:` + `**How to apply**:` + `**CI-backed**: yes — <script>` markers). Wording:
     ```
     2. **NEVER treat a sub-skill's terminal output as the parent skill's terminal output.** **Why**: skills invoked via the Skill tool (for example `/larch:issue`, `/larch:review`, `/larch:design`) produce visually-terminal output — machine footers (`ISSUES_*`, `REVIEW_*`), sentinel writes, and human-readable summaries — that collectively read like a stopping point. Producing a summary and ending the turn after a sub-skill returns has caused observed regressions (issue #2681: `/design` Step 5b halt skipped Step 5c rename to `[DESIGNED]` after `/larch:issue` returned). The sub-skill's terminal output marks the SUB-skill's end, NOT the parent skill's. **How to apply**: when a Skill-tool sub-skill returns, immediately continue with the parent skill's NEXT numbered step (or sub-step) before producing any summary or human-readable closing prose. See `skills/design/SKILL.md` `Anti-halt continuation reminder` and the per-sub-step `Continue to Step` banners for the /design-specific application. **CI-backed**: yes — `scripts/test-design-structure.sh` pins the literal at this site.
     ```

3. **`scripts/test-design-structure.sh`** (Fix 3 + Fix 4 anchoring)
   - Add a new check block (numbered `(17)` to follow existing `(16)` block) that pins three literals:
     a. The `Continue to Step 5c IMMEDIATELY` banner exists in `skills/design/SKILL.md`, lies strictly between the `### 5b — File accepted OOS issues` heading line and the `### 5c — Write \`larch:plan\`` heading line, and names `/larch:issue` as a sub-skill.
     b. The intra-Step-5 enumeration `5→5a→5b→5c.1→5c.6→5c.7→6` appears in the anti-halt reminder.
     c. The new generic NEVER entry literal — specifically `NEVER treat a sub-skill's terminal output as the parent skill's terminal output` — appears in `skills/shared/orchestrator-never.md`.
   - The existing `5→6` pin in check 15b becomes obsolete because `5→6` is NOT a substring of the new token `5→5a→5b→5c.1→5c.6→5c.7→6`. Adjust check 15b's `grep -Fq '5→6'` to `grep -Fq '5c.7→6'` (or `5→5a` — both are unambiguous Step-5-boundary tokens in the new enumeration). This must land in the same PR to keep check 15b green.

### Approach

- All four fixes are surgical text edits in three files. No script logic, no helper changes, no `run-params.json` schema bumps.
- The anti-halt reminder edit is a single-token swap of the literal `5→6` → `5→5a→5b→5c.1→5c.6→5c.7→6` inside the existing parenthetical.
- The Step 5b banner mirrors the existing banner style at the end of Steps 2b / 3 / 3.5 / 3b / 4 / 4b. Uses the same `> **Continue to Step X IMMEDIATELY.**` prefix and a single explanatory sentence.
- The generic NEVER entry follows the existing entry-1 schema in `orchestrator-never.md` so the file stays homogeneous.
- The test pin extends the existing structural test (no new test script) to keep proportionality with trivial mode.

### Edge cases

- **Existing `5→6` grep in test-design-structure.sh check 15b**: `5→6` is NOT a substring of the new token `5→5a→5b→5c.1→5c.6→5c.7→6` (no adjacent `5`-`→`-`6` substring anywhere). The existing pin would FAIL after the edit. Fix: replace the existing pin's matched literal with `5c.7→6` (or `5→5a`) in the same PR.
- **Banner placement**: the banner must lie strictly between the last line of Step 5b body and the `### 5c — Write` heading. Use a single blank line above and below the banner to match the styling of the other Continue-banners.
- **NEVER entry placement**: append as item `2.` so the existing CI-backed pin reference to entry 1 (`test-anti-improvised-wakeup.sh`) remains valid.
- **Backward compatibility with `test-anti-improvised-wakeup.sh`**: that script greps for the literal `NEVER improvise ScheduleWakeup outside skill-script direction`. Adding entry 2 does not touch entry 1's text — the existing pin keeps passing.

### Failure modes

Omitted: changes are documentation/contract-text only with mechanical pins. No new failure paths are introduced.

### Testing strategy

- Run `bash scripts/test-design-structure.sh` after the edits. The new check (17) must PASS; the adjusted check (15b) must continue to PASS with the new boundary token.
- Run `bash scripts/test-anti-improvised-wakeup.sh` to confirm the existing entry-1 pin still holds after appending entry 2 to `orchestrator-never.md`.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) to exercise the pre-commit lint surface across all three edited files.

## Acceptance

- `skills/design/SKILL.md` line 28 anti-halt reminder enumerates intra-Step-5 sub-step transitions including the literal token `5→5a→5b→5c.1→5c.6→5c.7→6` (sub-step header granularity for `5a`/`5b`/`5c`, with bash-item granularity for the major continuation points inside Step 5c: compose / publish / rename).
- `skills/design/SKILL.md` Step 5b body ends with a `> **Continue to Step 5c IMMEDIATELY.**` banner that explicitly names the `/larch:issue` Skill-tool return (`ISSUES_*` block + sentinel + human summary) as a NON-terminal output. The banner is placed strictly between the last line of Step 5b body and the `### 5c — Write` heading.
- `skills/shared/orchestrator-never.md` contains a new numbered entry `2.` with the literal rule statement `NEVER treat a sub-skill's terminal output as the parent skill's terminal output.` followed by `**Why**:`, `**How to apply**:`, and `**CI-backed**: yes — scripts/test-design-structure.sh pins the literal at this site.` markers.
- `scripts/test-design-structure.sh` contains a new check block `(17)` that grep-pins (a) the `Continue to Step 5c IMMEDIATELY` banner literal + its placement strictly between Step 5b and Step 5c headings; (b) the literal `5→5a→5b→5c.1→5c.6→5c.7→6` in the anti-halt reminder; (c) the literal `NEVER treat a sub-skill's terminal output as the parent skill's terminal output` in `skills/shared/orchestrator-never.md`. The existing check 15b literal `5→6` is updated to `5c.7→6` (or `5→5a`) and continues to PASS.
- No change to actual Step 5 mechanics (the order of OOS filing, plan composition, plan-block-write, publish, and rename remains the same).
- `bash scripts/test-design-structure.sh`, `bash scripts/test-anti-improvised-wakeup.sh`, and `bash scripts/relevant-checks.sh` all PASS after the edits.


diff_lines: 22
