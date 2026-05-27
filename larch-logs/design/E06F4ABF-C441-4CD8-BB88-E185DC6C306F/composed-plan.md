## Plan

This is a SIMPLE-tier design. Smallest change that delivers the three minimal `monitor_rc` token checks the issue requests, scoped to the top-level Family B writer set already gated by `family_b_pid_writer_required`. No structural two-branch verification; no widening of the Family B writer set; no edits to `BASH_AUTHORING.md` §4 prose or canonical example.

### Files to modify/create

### UPDATED: `scripts/lint-foreground-markers.sh`

Extend `fence_has_family_b_pid_capture_and_wait` (defined at lines 334-415) with three additional non-fatal token checks that run **after** the existing block that confirms a `wait` identifier matches the captured PID and follows the monitor.

1. **`monitor_rc=` init within 3 non-blank lines above the monitor's start line.**
   - Walk backwards from `monitor_idx - 1` over `${lines[@]}`, skipping blank lines, comments, and heredoc bodies (heredoc state tracked by the same `try_begin_heredoc` / `heredoc_close_matches` helpers used by `scan_fence_buffer_for_anchors`).
   - Stop after 3 non-blank non-comment lines or on a line matching the ERE `^[[:space:]]*(local[[:space:]]+)?monitor_rc=[[:space:]]*[0-9]+([[:space:]]|$)`. Strict integer literal mirrors the canonical `monitor_rc=0` shape; reject `monitor_rc=$something` because that defeats the failure-vs-success default.
   - Missing → emit `<rel>:<abs_anchor>: missing monitor_rc= initialization within 3 non-blank lines above breadcrumb-monitor.sh for <bn>`. Increment `VIOLATIONS`. Do **not** return — continue to checks (2) and (3) so a single fence reports all three defects in one run.

2. **`|| monitor_rc=` on the monitor's logical-end line.**
   - Compute the merged logical line that begins at `monitor_idx` by walking forward over `${lines[@]}` while each line ends with backslash-continuation (reuse `line_ends_with_backslash_continuation`). The "monitor's logical-end line" is the last line in that chain.
   - Match the ERE `\|\|[[:space:]]+monitor_rc=\$\?[[:space:]]*(#.*)?$` on the merged logical line. Strict `monitor_rc=$?` mirrors the canonical shape; anchoring on end-of-line tolerates a trailing comment but not unrelated trailing tokens.
   - Missing → emit `<rel>:<abs_anchor>: missing "|| monitor_rc=$?" on breadcrumb-monitor.sh logical-end line for <bn>`. Increment `VIOLATIONS`. Continue.

3. **Conditional branching on `monitor_rc` between the monitor's logical-end line and end-of-fence (canonical: condition opens *before* line-initial waits).**
   - Per FINDING_1: the canonical Family B pattern is `if [ "$monitor_rc" -eq 0 ]; then wait "$PID"; else wait "$PID" 2>/dev/null || true; fi`. The `if` opens between the monitor and the matching `wait`, not after the `wait`. Scan starts at `monitor_end_idx + 1` — not at `wait_idx + 1`.
   - From `monitor_end_idx + 1` through `n - 1`, find any line whose **first non-blank token** matches `^[[:space:]]*(if|elif|case|while|until)\b` and whose body within the same fence references the bareword `monitor_rc`. Match `monitor_rc` appearing as a separate word on any line from the keyword line through end-of-fence. The check is satisfied if at least one such conditional exists.
   - Skip heredoc bodies in the forward scan.
   - Missing → emit `<rel>:<abs_anchor>: missing conditional branching on monitor_rc between breadcrumb-monitor.sh and end-of-fence for <bn>`. Increment `VIOLATIONS`.

Implementation detail: restructure the trailing portion of `fence_has_family_b_pid_capture_and_wait` so that the matching-wait branch falls through into the three new checks (and a final `return 0`) rather than returning eagerly. The pre-existing early-return paths (missing `&`, missing PID capture, missing monitor, identifier mismatch, missing wait, wait-before-monitor) are preserved exactly. Per-anchor `# lint-foreground-markers: ok <reason>` suppression at line 344 already covers the new checks. Bash 3.2-safe (no associative arrays, namerefs, `mapfile`, or `${var,,}`).

### UPDATED: `scripts/test-lint-foreground-markers.sh`

1. **Update existing positive Markdown fixtures to the canonical multiline `monitor_rc` shape** (per FINDING_2: keep `wait` line-initial so `extract_wait_ident` still recognizes it). For every `assert_case_clean` fixture whose fence anchors on a top-level Family B writer (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`), splice in:

   ```
   monitor_rc=0
   ${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh --stream s --done-sentinel d --status-file f --quiet-log q --surfaced-sentinel u --paired-pid-file "$LARCH_PAIRED_PID_FILE" || monitor_rc=$?
   if [ "$monitor_rc" -eq 0 ]; then
       wait "$COLLECTOR_PID"
   else
       wait "$COLLECTOR_PID" 2>/dev/null || true
   fi
   ```

   Checklist: `grep -nE 'assert_case_clean|^# [0-9]+ — ' scripts/test-lint-foreground-markers.sh` then inspect each `assert_case_clean` body for the five denylisted basenames.

2. **NEG-A (Markdown)** — no monitor_rc capture at all. Canonical PID+monitor+bare-`wait` shape; `monitor_rc=0` absent; `|| monitor_rc=$?` absent; no conditional. Expect `assert_case` exit 1 with needles `missing monitor_rc= initialization`, `missing "|| monitor_rc=$?"`, `missing conditional branching on monitor_rc`.

3. **NEG-B (Markdown)** — monitor_rc capture present but no branch. Fixture has `monitor_rc=0` init and `|| monitor_rc=$?` on monitor; line-initial bare `wait "$PID"`; no `if`/`case` referencing `monitor_rc`. Expect `assert_case` exit 1 with needle `missing conditional branching on monitor_rc`.

4. **NEG-HEREDOC (Markdown)** — `monitor_rc=0` only inside a heredoc body above the monitor (FINDING_4 mitigation). `cat <<'EOF' ... monitor_rc=0 ... EOF` precedes a `breadcrumb-monitor.sh` line with `|| monitor_rc=$?` plus a canonical conditional. Expect `assert_case` exit 1 with exactly the `missing monitor_rc= initialization` needle (checks 2 and 3 must not false-pass).

5. **Update existing shell-file fixture (`assert_case_clean` case 46)** invoking `ship-pr.sh` + breadcrumb-monitor + bare `wait` (FINDING_3 mitigation). Splice in the canonical multiline three-token shape so the fixture still passes once `scan_shell_file_for_family_b_wait` inherits the new checks.

6. **New negative shell-file fixture**: same canonical shape minus `monitor_rc=0`. Expect `assert_case` exit 1 with needle `missing monitor_rc= initialization`.

7. Numbering: append new cases after the highest existing case number; do not renumber existing cases.

### UPDATED: `scripts/lint-foreground-markers.md`

1. In the emit-tokens paragraph (around lines 16-26), append three new tokens to the comma-separated list:
   - `missing monitor_rc= initialization within 3 non-blank lines above breadcrumb-monitor.sh for <basename>`
   - `missing "|| monitor_rc=$?" on breadcrumb-monitor.sh logical-end line for <basename>`
   - `missing conditional branching on monitor_rc between breadcrumb-monitor.sh and end-of-fence for <basename>`
2. Add a short paragraph describing the new contract: top-level Family B writers must initialize `monitor_rc=0` within 3 non-blank lines above `breadcrumb-monitor.sh`, capture the monitor's exit code via `|| monitor_rc=$?` on the monitor's logical-end line (backslash-continuation aware), and route the post-monitor wait through an `if`/`case` conditional that branches on `monitor_rc` (the conditional opens before the line-initial waits in each branch). Reference `BASH_AUTHORING.md` §4 for the canonical two-branch shape.

### Approach

Minimal-presence approach (Step 1c decision). The three new checks run only when the existing wait/identifier validation succeeds, so fences with pre-existing PID/wait defects still report those defects first. New checks accumulate (each emits its own diagnostic) so one CI run surfaces every missing token. Per-anchor suppression inherits via the existing short-circuit. The shell-file scanner inherits the new checks via its existing call to `fence_has_family_b_pid_capture_and_wait`. Restructuring the helper's trailing portion preserves every early-return path. The conditional scan starts at monitor's logical-end + 1 (not after the matched wait) because the canonical Family B pattern opens the `if` before the line-initial waits.

### Edge cases

- Heredoc bodies above and after the monitor: reuse `try_begin_heredoc` / `heredoc_close_matches`; treat heredoc body as opaque "non-counting" region in both walks.
- Backslash-continuation on the monitor: check (2) operates on the merged logical line; reuse `line_ends_with_backslash_continuation`.
- Comment-only lines between writer and monitor: init walk skips both blanks and comment-only lines.
- `monitor_rc` reference in conditional body but keyword on a prior line: match keyword-line-or-any-subsequent-line-through-end-of-fence.
- Canonical Family B `if` opens before the waits; fixtures must preserve line-initial wait shape so `extract_wait_ident` still finds them.
- Per-anchor `# lint-foreground-markers: ok` suppression at the writer invocation covers all three new checks (no separate token).
- Existing `assert_case` (exit-1) fixtures unaffected: extra stderr lines do not break `grep -Fq` needle matching.

### Failure modes

1. Heredoc tracking diverges between init-window and forward-scan walks → factor into one helper or use single linear walk; NEG-HEREDOC fixture is the dedicated negative-coverage test.
2. Test-fixture update sweep misses a passing fixture (Markdown or shell-file) → enumerate `assert_case_clean` blocks anchoring on top-level Family B writers as a pre-edit checklist; case 46 is the known shell-file example.
3. Backslash-continuation merge logic differs between writer-side `&` check and new monitor-side `|| monitor_rc=` check → reuse `line_ends_with_backslash_continuation` verbatim and pre-flight the lint against the live repo before opening the PR.

### Testing strategy

- Add four new fixtures (NEG-A, NEG-B Markdown per issue Acceptance; NEG-HEREDOC for FINDING_4; one new shell-file negative).
- Update all `assert_case_clean` fixtures (both Markdown and shell-file paths, including case 46) anchoring on top-level Family B writers to the canonical multiline three-token shape.
- Re-run `bash scripts/test-lint-foreground-markers.sh` (all PASS lines must remain).
- Run `make lint-foreground-markers` over the live repo (no regressions in the nine existing canonical-shape SKILL.md / reference files).
- Run `make test-background-monitor-wait`, `make lint-bash32`, `make lint`.

## Acceptance

- `make lint-foreground-markers` fails on a Markdown fence or shell-script wrapper that anchors on a top-level Family B writer, has a matching `wait "$PID"` after `breadcrumb-monitor.sh`, but omits `monitor_rc=0` initialization, `|| monitor_rc=$?` capture, or any `if`/`case` referencing `monitor_rc` between the monitor and end-of-fence.
- `make lint-foreground-markers` passes on all nine existing canonical-shape fences (`skills/research/`, `skills/design/`, `skills/shared/`, `skills/implement/`) — no regressions.
- New negative fixtures in `scripts/test-lint-foreground-markers.sh` (NEG-A no-capture, NEG-B capture-without-branch, NEG-HEREDOC heredoc-only-monitor_rc, plus one shell-file negative) all fail with the expected `assert_case` needles.
- All existing `assert_case_clean` fixtures anchoring on top-level Family B writers (Markdown and shell-file paths) still pass after being updated to the canonical multiline three-token shape.
- `make lint-bash32` passes (no Bash 4+ tokens introduced).
- `scripts/lint-foreground-markers.md` lists the three new error-message tokens and describes the new contract.

diff_lines: 300
