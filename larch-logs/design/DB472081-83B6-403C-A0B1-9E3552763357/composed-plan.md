## Plan

### Approach

Add a small shared state contract for `/learn-from-bugs`, then let `/audit-runs` read it and print one advisory nudge. Keep all behavior in Python CLIs. Keep skill Markdown thin.

Use `schema_version: 1` for the marker. Store at least:

- `run_date`: UTC ISO8601 timestamp for the successful `/learn-from-bugs` report run (Step 4 completion boundary).
- `scan_started_at`: UTC ISO8601 timestamp captured immediately before the Step 2 `gh issue list` call (the scan frontier boundary).
- `highest_closed_issue_number_scanned`: max issue `number` from the **unfiltered** `gh issue list` result for that run (computed from `raw_issues` before local bug-title filtering).
- `repo`: resolved repo.
- `search`, `state`, and `selected_count`: audit context for future readers (`selected_count` is the post-filter digest count, separate from the scan frontier).

Readers must tolerate missing files, malformed JSON, prior shapes (markers without `scan_started_at`), and symlinked paths. Missing, symlinked, or unusable marker means "never run" for nudge wording.

**Scan boundary capture:** In `run_prepare`, capture `scan_started_at` once as UTC ISO8601 immediately before calling `list_issues` / `gh issue list`. Emit it as `SCAN_STARTED_AT` in prepare stdout. Pass the same value through to `write-state`; do not synthesize it at commit time.

**Report boundary capture:** Capture `RUN_DATE` once when the Step 4 report is written (immediately before the post-Step-4 marker fences). Pass that same value through to `write-state`; do not synthesize it inside the commit step.

**Bug selection (G-Ext-3):** After every `gh issue list`, always filter digest rows through `bug_title_match` before building digests — including when `--search` is explicit. Explicit search only changes the upstream `gh` query; it does not bypass the shared title predicate. Keep `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED` from unfiltered `raw_issues`.

**Nudge boundary:** `/audit-runs bugs-backlog-nudge` compares closed bugs against `scan_started_at` when present; fall back to `run_date` for older markers missing `scan_started_at`. Also require local `closedAt > boundary` in UTC.

### Files to modify/create

### UPDATED: python/larch/core/config.py

Add:

- `LEARN_FROM_BUGS_NUDGE_THRESHOLD: Final = 25`
- `LEARN_FROM_BUGS_STATE_RELPATH: Final = "larch-logs/shared/learn-from-bugs-state.json"`

Use these constants from both writer and reader code.

### UPDATED: python/larch/issue/learn_from_bugs.py

Add a frozen state dataclass and helpers:

- `LearnFromBugsState`
- `read_state(path: Path) -> LearnFromBugsState | None`
- `write_state(path: Path, state: LearnFromBugsState) -> None`

**Write path:** resolve `path` under `--root`, call `larch_io.assert_no_symlink_path_or_ancestors(path)` before write, create parent directories, then `larch_io.atomic_write(..., nofollow=True)` to the fixed repo-relative path from `config`.

**Read path:** call `larch_io.assert_no_symlink_path_or_ancestors(path)`; on `OSError` from symlink rejection, return `None` (treat as no usable marker). Parse JSON tolerantly (ignore unknown fields; require `schema_version`, `run_date`, and `repo` for a usable marker). `scan_started_at` is optional on read; when absent, consumers fall back to `run_date`.

Extend `run_prepare`:

- Capture `scan_started_at` as UTC ISO8601 immediately before `list_issues`.
- Emit `SCAN_STARTED_AT` in the returned KV dict.
- **Always** filter digest input through `bug_title_match` after `gh` returns rows, regardless of `search_explicit`. Set `ISSUES_FILTERED_NON_BUG = len(raw_issues) - len(issues)` in all cases. `search_explicit` only records that the upstream query was operator-supplied; it does not skip title filtering.
- Emit `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED`: `max(int(row["number"]) for row in raw_issues)` when `raw_issues` is non-empty; **`0` when `raw_issues` is empty** (including `ISSUES_SELECTED=0`). Compute from `raw_issues` **before** `bug_title_match`; do not use digest/selected issue numbers for this field.
- Keep existing `ISSUES_SELECTED`, `SEARCH`, `STATE`, `REPO`, and related stats unchanged.

Add CLI verbs:

- `learn-from-bugs read-state --root <repo-root>`
  - Print KV output including `SCAN_STARTED_AT` when present.
  - Missing or unusable marker prints `LEARN_FROM_BUGS_STATE_FOUND=false`.
- `learn-from-bugs write-state --root <repo-root> --repo <repo> --search <query> --state <state> --selected-count <n> --highest-closed-issue-number-scanned <n> --run-date <iso> --scan-started-at <iso>`
  - `--run-date` and `--scan-started-at` are required (caller supplies Step 2 and Step 4 boundary timestamps).
  - Write schema version 1.
  - Print `STATE_PATH=...`, `RUN_DATE=...`, `SCAN_STARTED_AT=...`, and `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED=...`.

### UPDATED: python/larch/issue/audit_runs.py

Add `bugs_backlog_nudge_main`.

Behavior:

1. Resolve the marker path from `--root` plus `config.LEARN_FROM_BUGS_STATE_RELPATH`.
2. If missing, symlink-rejected, malformed, or missing `run_date`, print one suggestion line with "never run" wording and exit 0.
3. If present and usable, bind `boundary = scan_started_at` when non-empty, else `run_date`.
4. Run `gh issue list --state closed --repo <repo> --search "[BUG] in:title closed:><boundary>" --limit 100000 --json number,title,closedAt`.
5. Parse JSON.
6. Filter every row through `bug_title_match(str(row["title"]))`.
7. Also require `closedAt > boundary` locally (UTC comparison; accept `Z` and explicit offsets).
8. Count matching bugs.
9. If count is greater than `config.LEARN_FROM_BUGS_NUDGE_THRESHOLD`, print one suggestion line naming the count and `/learn-from-bugs`.
10. Stay silent at or below the threshold.

Do not modify audit counters, scan NDJSON, report frontmatter, or filed audit report body.

If `gh issue list` fails or returns malformed JSON, return a non-zero code with a clear stderr message. The skill wiring should treat this advisory failure as non-fatal to the audit run.

### UPDATED: python/larch/cli.py

Register:

- `("learn-from-bugs", "read-state")`
- `("learn-from-bugs", "write-state")`
- `("audit-runs", "bugs-backlog-nudge")`

### UPDATED: skills/learn-from-bugs/SKILL.md

**Contract carve-out:** keep the workflow report-only for proposals, guidelines, invariants, hooks, and lints (Step 5 approval gates unchanged). The **one exception** is the durable marker: after a successful Step 4 report, `/learn-from-bugs` must write and commit only `config.LEARN_FROM_BUGS_STATE_RELPATH` before Step 5.

**Step 2 — extend parse list.** Parse and retain through Step 4: `REPO`, `SEARCH`, `STATE`, `ISSUES_SELECTED`, `SCAN_STARTED_AT`, `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED`, plus existing `DIGEST_PATH`, `COVERAGE_INDEX_PATH`, `ISSUES_FILTERED_NON_BUG`, `STRUCTURED`, `FREEFORM_OR_TITLE_ONLY`, `DIGEST_TOKENS_EST`, and `*_INDEXED` counts. Abort if `DIGEST_PATH` is missing.

**Step 4 — capture run boundary.** Immediately after `${RUN_DIR}/report.md` is written and printed, capture `RUN_DATE` once as a UTC ISO8601 timestamp (e.g. `date -u +%Y-%m-%dT%H:%M:%SZ`) and retain it with the Step 2 KVs for the marker fences. `SCAN_STARTED_AT` was already captured at Step 2 prepare time; do not re-capture it here.

**Post-Step-4 marker fences (before Step 5):**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" learn-from-bugs write-state \
  --root "$PWD" \
  --repo "$REPO" \
  --search "$SEARCH" \
  --state "$STATE" \
  --selected-count "$ISSUES_SELECTED" \
  --highest-closed-issue-number-scanned "$HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED" \
  --run-date "$RUN_DATE" \
  --scan-started-at "$SCAN_STARTED_AT"
```

On non-zero `write-state` exit: report the failure clearly and **stop before Step 5** (durable marker not written).

Then commit only the marker path (no unrelated staged or dirty files):

python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit \
  -m "chore(larch-logs): update learn-from-bugs state" \
  --only "${LEARN_FROM_BUGS_STATE_RELPATH:-larch-logs/shared/learn-from-bugs-state.json}"

Use `config.LEARN_FROM_BUGS_STATE_RELPATH` for the `--only` argument in the skill (the constant value above is the default). Do not use `git add -A`, `git commit -a`, or a bare `git commit` without `--only`.

On non-zero commit exit, rollback explicitly before stopping:

MARKER_REL="${LEARN_FROM_BUGS_STATE_RELPATH:-larch-logs/shared/learn-from-bugs-state.json}"
if git -C "$PWD" ls-files --error-unmatch -- "$MARKER_REL" >/dev/null 2>&1; then
  git -C "$PWD" restore --staged --worktree -- "$MARKER_REL"
else
  rm -f "$PWD/$MARKER_REL"
fi

Report that the durable marker was not committed and **stop before Step 5**. Do not leave an uncommitted on-disk marker that readers could treat as durable.

Step 5 follow-up gates remain unchanged for issues, guidelines, invariants, hooks, and lints.

### UPDATED: .claude/skills/audit-runs/SKILL.md

Run the nudge **once after successful preflight** (`PREFLIGHT_OK=true`) and **before** `resolve-prs`, so zero-PR and other early exits still see the advisory. It does not need scan NDJSON; it only needs `--repo` and `--root`.

Add a new subsection **Bugs-backlog advisory** immediately after **Pre-flight** and before **Verbal-Description Resolution**:

NUDGE_OUT=$(python3 "$PWD/python/cli.py" audit-runs bugs-backlog-nudge \
  --repo "<owner/name>" \
  --root "$PWD" 2>"$TMPDIR/bugs-backlog-nudge.err") || true

- If stdout is non-empty, print it to chat as advisory text only.
- If the command fails, print a short non-fatal advisory failure (include stderr when helpful) and continue the audit.
- This output is **chat-only**. Do not include it in the filed audit report body, YAML frontmatter, `compute-counters` input, or scan NDJSON.

**Early-exit behavior:** On `resolve-prs` paths that fail-fast with non-empty `ERROR` (including zero new PRs on `since last audit`), print any non-empty `NUDGE_OUT` captured above, then fail-fast as today. Do not re-run the nudge on those exits.

Update **Revised Orchestrator Flow** to insert `python/cli.py audit-runs bugs-backlog-nudge` immediately after preflight and before `resolve-prs`. Do not add a second post-scan nudge hook.

### UPDATED: python/tests/issue/test_learn_from_bugs.py

Add tests for:

- Writing schema version 1 state (including `scan_started_at`) and reading it back.
- Missing marker returns a "not found" state without crashing.
- Prior or malformed shapes are tolerated; markers without `scan_started_at` still read `run_date`.
- `write-state` CLI creates parent directories and prints KV output.
- `run_prepare` emits `SCAN_STARTED_AT` before `gh issue list` and `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED=0` when `raw_issues` is empty / `ISSUES_SELECTED=0`.
- `run_prepare` computes `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED` from unfiltered `raw_issues` (including rows filtered out by `bug_title_match`), not from digest numbers.
- **Explicit `--search` still filters digests through `bug_title_match`**; non-bug rows land in `ISSUES_FILTERED_NON_BUG` and are excluded from the digest.
- Symlinked marker path or ancestor is rejected on read (returns unusable / not found) and on write.

### UPDATED: python/tests/issue/test_audit_runs.py

- Missing marker prints "never run" wording and does not call `gh`.
- Symlinked marker path treated as missing/unusable ("never run" wording).
- Present marker below threshold stays silent.
- Exactly threshold stays silent.
- Threshold plus one prints a suggestion line with the count and `/learn-from-bugs`.
- Raw GitHub results are filtered through `bug_title_match`, including lifecycle-prefixed bug titles.
- Rows with `closedAt <= boundary` are excluded even if GitHub returns them.
- Nudge uses `scan_started_at` when present; falls back to `run_date` for older markers.
- Malformed `gh` JSON or non-zero `gh` exits fail the CLI clearly.

### MAY_UPDATE: larch-logs/shared/learn-from-bugs-state.json

Do not seed this file as part of the implementation unless the operator explicitly wants a first committed marker. The runtime `/learn-from-bugs` run should create it.

### Edge cases

- Missing marker: print "never run" wording instead of a count.
- Malformed marker: treat as no usable marker, but do not crash.
- Symlinked marker path or ancestor: treat as no usable marker on read; reject on write.
- Missing `run_date`: treat as no usable marker.
- Missing `scan_started_at` on older markers: nudge falls back to `run_date` as the comparison boundary.
- Empty `raw_issues` / `ISSUES_SELECTED=0`: emit `HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED=0`; `write-state` must accept `0`.
- `highest_closed_issue_number_scanned` vs `selected_count`: frontier is the unfiltered list max; selected count is the post-filter digest count.
- Explicit search: upstream query may return non-bug titles; local `bug_title_match` always filters before digest/token spend.
- Timezone forms: parse `Z` and explicit offsets. Compare in UTC.
- GitHub search recall noise: always apply `bug_title_match` locally before counting.
- Boundary count: nudge only when `count > LEARN_FROM_BUGS_NUDGE_THRESHOLD`.
- Zero-PR audit exits: nudge runs after preflight, so `since last audit` with no new PRs still prints the advisory when eligible.
- Dirty tree during marker commit: commit only the marker path via `git commit --only`. Do not sweep unrelated staged changes into the metadata commit.
- Marker commit failure: `git restore --staged --worktree` when tracked, else `rm -f`; stop before Step 5 so uncommitted state is not left behind.

### Failure modes

- Marker write fails: stop `/learn-from-bugs` before follow-up gates and report the file error.
- Marker commit fails: run the explicit rollback fence, stop, and report that the durable marker was not committed.
- Nudge `gh` call fails: treat as advisory failure. Continue `/audit-runs`.
- JSON shape drift: state reader must ignore unknown fields and tolerate absent optional fields.
- Symlink escape: reader treats as unusable; writer refuses before `atomic_write`.
- Report contamination: do not add the nudge to audit report Markdown, YAML frontmatter, counters, or scan NDJSON.
- Late boundary capture: bugs closed after `scan_started_at` but before marker write remain eligible for nudge because the comparison boundary is the scan start, not report completion.

### Testing strategy

Run only changed-file checks:

- `python3 -m pytest python/tests/issue/test_learn_from_bugs.py`
- `python3 -m pytest python/tests/issue/test_audit_runs.py`
- `make py-lint`
- `make py-test` only if touched helpers affect broader Python typing or CLI registration.

Also run targeted CLI smoke checks with temp roots where possible:

- `python3 python/cli.py learn-from-bugs read-state --root <tmp-empty-root>`
- `python3 python/cli.py audit-runs bugs-backlog-nudge --repo o/r --root <tmp-empty-root>`

## Acceptance

Run only changed-file checks:

- `python3 -m pytest python/tests/issue/test_learn_from_bugs.py`
- `python3 -m pytest python/tests/issue/test_audit_runs.py`
- `make py-lint`
- `make py-test` only if touched helpers affect broader Python typing or CLI registration.

Also run targeted CLI smoke checks with temp roots where possible:

- `python3 python/cli.py learn-from-bugs read-state --root <tmp-empty-root>`
- `python3 python/cli.py audit-runs bugs-backlog-nudge --repo o/r --root <tmp-empty-root>`

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 720
diff_deleted: 35
mechanical_churn: false
diff_lines: 755
