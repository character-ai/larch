## Goal
Fix audit-runs skill: filter findings against in-flight/closed-with-version-window issues + narrow oos-category-mangle scan

## Implementation Plan

Issue #2523: four sub-fixes for the `/audit-runs` dev-only skill.

### Files to modify

1. `.claude/skills/audit-runs/SKILL.md` — C.1, C.2, C.4
2. `.claude/skills/audit-runs/scripts/audit-scan-run.sh` — C.3
3. `.claude/skills/audit-runs/scans.tsv` — C.3
4. `.claude/skills/audit-runs/scripts/audit-scan-run.md` — C.3 (sibling doc update)
5. `.claude/skills/audit-runs/scripts/test-audit-runs.sh` — new test cases for C.1, C.3, C.4

---

### C.1 — Remove `[IN PROGRESS]` from `proposed_new_issues` exclusion

**File**: `.claude/skills/audit-runs/SKILL.md` lines ~104-108

Current text excludes `^\[IN PROGRESS\]` from the issue title search, so open in-flight fixes
are never matched and the finding appears as a new proposal. Fix: only exclude
`^\[Run Logs Audit Report` (anti-recursion). `[IN PROGRESS]` issues are open and will match
the `gh issue list --state open` search naturally, routing the finding to `proposed_augmentations`.

Change:
- `proposed_new_issues` description: remove ` or ^\[IN PROGRESS\]` from the exclusion list
- Add prose clarifying that a match against an `[IN PROGRESS]` issue → `proposed_augmentations`
  with a "recurred this batch — pre-fix" note in the Open issues snapshot section.
- Keep the LLM classify step searching `--state open` (no change there); the exclusion
  removal is the only mechanical change needed.

---

### C.2 — Version-window filter for closed issues + `version_window_checks` frontmatter

**File**: `.claude/skills/audit-runs/SKILL.md`

Extend the LLM classification step:

1. Search both open AND closed issues:
   `gh issue list --state all --repo <repo> --search "<keywords>" --json number,title,state,closedAt`
2. Open/in-progress matches → `proposed_augmentations` (per C.1).
3. Closed matches → version-window check:
   - Get fix-PR mergedAt via `gh pr list --state merged --search "closes #<N>" --repo <repo> --json number,mergedAt`
     (or `gh issue view <N> --json closedAt`)
   - Find the next plugin version shipped after that date:
     `git log --oneline --grep="Bump version" --after="<mergedAt>" --reverse -- .claude-plugin/plugin.json | head -1`
     then read the version from that commit.
   - Compare fix_shipped_version against each audited run's `manifest.json::larch_version`.
   - If fix_shipped_version > every audited `larch_version` → fix post-dates audited runs → do NOT propose.
   - If fix_shipped_version ≤ any audited `larch_version` → fix was in scope but recurred → propose.

4. Record rationale in `version_window_checks` frontmatter block (new key alongside
   `proposed_new_issues` / `proposed_augmentations`).

Add `version_window_checks` to the frontmatter YAML schema in the "Frontmatter" section:

```yaml
version_window_checks:
  - finding: <slug>
    matched_issue: <N>
    matched_state: closed
    fix_shipped_in: vX.Y.Z
    audited_versions: [34.0.0, 34.0.1]
    in_scope: false
    decision: skip
```

`version_window_checks` is always present when any closed-issue match was evaluated
(possibly empty list `[]`).

---

### C.3 — Narrow `oos-category-mangle` to plan-review accepted rows only

**File**: `.claude/skills/audit-runs/scripts/audit-scan-run.sh` lines 196-203

Replace the `scan_oos_category_mangle()` body:

Old:
```bash
count=$(jq -r 'select(.category != null) | .category' "$jsonl" 2>/dev/null \
    | grep -cvE '^(code-quality|risk-integration|correctness|architecture|security)$' || true)
if [ "$count" -eq 0 ]; then
    emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
else
    detail="$count plan-review-phase rows with prose category"
    emit "{...\"detail\":\"$(jstr "$detail")\"}"
fi
```

New:
```bash
count=$(jq -r 'select(
    .phase == "plan-review" and
    .outcome == "accepted" and
    (.category // "") != "" and
    ((.category // "") | test("^(code-quality|risk-integration|correctness|architecture|security)$") | not)
) | .id' "$jsonl" 2>/dev/null | wc -l | tr -d '[:space:]')
if [ "$count" -eq 0 ]; then
    emit "{\"scan\":\"oos-category-mangle\",\"pr\":$PR_NUM,\"result\":\"pass\",\"count\":0}"
else
    detail="$count plan-review accepted rows with prose category (not canonical)"
    emit "{...\"detail\":\"$(jstr "$detail")\"}"
fi
```

Rationale: code-review accepted rows use best-effort category (by design, per
`compose-review-findings.sh:178` and the test at `test-compose-review-findings.sh:112-114`).
OOS blank rows are also by-design. Only plan-review accepted rows with non-canonical
non-empty category are the regression class from #2490.

**File**: `.claude/skills/audit-runs/scans.tsv` line 4

Update `oos-category-mangle` row:
- `pattern`: `plan-review accepted rows: .phase=="plan-review" and .outcome=="accepted" and (.category//""!="") and category not canonical`
- `expected_outcome`: `all plan-review accepted category fields use canonical values`

**File**: `.claude/skills/audit-runs/scripts/audit-scan-run.md`

Update the example `oos-category-mangle` fail NDJSON to use the new detail string:
`"detail":"12 plan-review accepted rows with prose category (not canonical)"`

---

### C.4 — Post-report session summary comment on audit-report issue

**File**: `.claude/skills/audit-runs/SKILL.md`

Add a new step after the post-report 3-way question walkthrough completes.
Position: after "act on the response" block in "Post-report user prompt", before "Output" section.

Logic:
1. After per-finding walkthrough completes (filing, augmenting, or skipping all items),
   compose `$TMPDIR/session-summary.md` with these sections (omit empty sections):

   ```markdown
   ## Post-report session summary

   **3-way decision**: <file-all | discuss-first | skip-filing>

   **Per-finding actions**:

   | Finding | Decision | Filed as | URL |
   |---|---|---|---|
   | ... | filed-as-drafted \| modified \| skipped | #N or — | url or — |

   **Augmentations**:

   | Target issue | Action | Comment URL |
   |---|---|---|
   | #N | posted \| skipped | url or — |

   ---
   *Posted by /audit-runs post-report session-summary step.*
   ```

2. Post via:
   ```bash
   gh issue comment "$AUDIT_REPORT_NUMBER" --repo "<repo>" --body-file "$TMPDIR/session-summary.md"
   ```

3. Unconditional after walkthrough: even skip-filing → all rows show "skipped" (useful history).
4. Skip when no audit-report was filed (zero-PR short-circuit).

Update the Revised Orchestrator Flow diagram to add:
```
[LLM: post-report 3-way question if proposed issues exist]
[LLM: post session-summary comment on audit-report issue]
```

---

### Tests — `test-audit-runs.sh`

Append new test cases after existing test 54:

**Test 55 (C.1)**: [IN PROGRESS] matching issue routes to proposed_augmentations, not proposed_new_issues.
- Inline logic: `has_in_progress_match=yes` → `proposed_augmentations`; `no` → `proposed_new_issues`
- Assertion: title `[IN PROGRESS] Fix EXON regression` → augmentation (not new issue)

**Test 56 (C.3 pass)**: audit-scan-run.sh oos-category-mangle with code-review-accepted prose category → pass.
- Create temp JSONL with `{"phase":"code-review","outcome":"accepted","category":"fixes auth","id":"ACC_001"}`
- Run `bash audit-scan-run.sh` against temp run-dir
- Assert scan line for `oos-category-mangle` has `result":"pass"`

**Test 57 (C.3 fail)**: audit-scan-run.sh oos-category-mangle with plan-review-accepted prose category → fail.
- Create temp JSONL with `{"phase":"plan-review","outcome":"accepted","category":"fixes auth","id":"ACC_002"}`
- Assert scan line for `oos-category-mangle` has `result":"fail"` and `"count":1`

**Test 58 (C.4)**: session-summary markdown composition.
- Inline: compose session-summary body for file-all decision with 2 findings
- Assert sections present: `## Post-report session summary`, table headers, `*Posted by /audit-runs`

**Test 59 (C.4 skip-filing)**: session-summary with skip-filing shows all-skipped rows.

**Test 60 (C.4 zero-findings)**: no session-summary posted when no audit-report filed.
- Assert: zero-PR short-circuit → no call to post comment

---


## Test plan

```bash
bash .claude/skills/audit-runs/scripts/test-audit-runs.sh
```
Then `/relevant-checks`.
