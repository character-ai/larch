# BASH_AUTHORING.md

Behavioral guidelines for authoring Bash commands. Merge with project-specific instructions as needed.

## 1. Exit-Code Safety for Bash Probes

**Probe commands should not create false error rows.**

For orchestrator-generated grep-family probes where "no match" is informational, guard the command so Bash transcripts stay clean:
- Use `|| true` to suppress the non-zero exit (works for all grep variants, including `grep -c` which already prints `0` on no-match).
- Use `|| echo 0` only for probes that produce **no stdout** on no-match — not for `grep -c`, which already emits a count before exiting 1.

Do not add these guards to conditionals like `if grep -q PATTERN file; then`, where exit 1 is the branch signal.

User-facing logs should not show error messages for expected no-match probes.

## 2. Bash Quoting Hygiene

**For Bash commands involving more than two nested quote/escape contexts, prefer file-backed scripts over inline composition.**

Triggers requiring this discipline:
- `python -c "<multi-line code>"` with embedded single-quoted Python literals and backslash-escaped double quotes
- `bash -c '<script>'` with internal `'"'"'` single-quote-switch escapes
- `awk '{...}'` with internal single-quoted regex literals
- Any combination that requires three or more levels of escaping

Robust alternatives (pick whichever fits the task):
1. **Write to a temp script, then invoke it.** Use the Write tool to create `/tmp/probe.sh` (or `.py`), then `Bash` runs `bash /tmp/probe.sh`. Plain content, no escape soup.
2. **Use a heredoc with a quoted delimiter.** `python3 <<'PY' ... PY` or `bash <<'EOF' ... EOF` lets you put arbitrary content in the body without escaping (since the quoted delimiter disables variable expansion and unquoting).
3. **Pipe stdin.** `printf '<script>' | python3 -` accepts the script as stdin and avoids quoting the body as a shell argument.

When you encounter a shell parse error (`unexpected EOF while looking for matching` …), do NOT iteratively patch escapes. Switch to one of the robust alternatives.

## 3. Bash 3.2 Portability

**Repository shell scripts must stay compatible with macOS system Bash 3.2 unless a script explicitly documents a narrower runtime.**

Do not use Bash 4+ constructs in committed shell scripts:
- associative arrays: `declare -A` / `typeset -A`
- namerefs: `declare -n` / `local -n`
- `mapfile` / `readarray`
- parameter case conversion: `${var^^}` / `${var^}` / `${var,,}` / `${var,}`
- append-all redirection: `&>>`
- coprocs: `coproc { ... }` / `coproc NAME { ... }`

Use Bash 3.2-compatible alternatives: newline-delimited temp files, `while IFS= read -r ...`, `case` or `tr` for case conversion, and `>>file 2>&1` instead of `&>>file`.

Run `make lint-bash32` after shell-script edits. If a regression harness intentionally contains a forbidden token as fixture text or static grep pattern, suppress only that line with an inline `# lint-bash32: ok <reason>` comment.

## 4. Background+propagate markers for blocking Family B script calls

Orchestrator-facing Markdown (`skills/*/SKILL.md`, `skills/*/references/*.md`, `skills/shared/*.md`, `.claude/skills/*/SKILL.md`, `.claude/rules/*.md`) often embeds fenced `bash` / `sh` / `shell` examples that invoke **blocking** plugin scripts (sentinel polling, PR dispatch, collector joins, etc.). Those long-running entrypoints must use the **background+monitor pair**: launch the denylisted script with Bash `run_in_background: true`, then block in the foreground on `${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh` in the **same Bash message** so breadcrumbs stream live and completion is coupled before the orchestrator continues.

**Why this is normative (not cosmetic).** Unpaired background launches defer completion to a task notification that may arrive **after** the model has already ended the turn — the failure mode behind `skills/implement/SKILL.md` NEVER **#16** and issue **#2454** (`ship-pr.sh` submitted without a paired monitor). Incident `984F0AA4-4436-40F3-A82E-9D114C1A58B4` exposed the sibling bug: the monitor can return after a done sentinel while the background writer is still running, leaving an orphaned `ship-pr.sh` that races with a re-invocation. The monitor reads explicit tmpdir paths (`LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_QUIET_LOG_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, `LARCH_PAIRED_PID_FILE`) allocated by the calling skill before launch. CI enforces the markers and the post-monitor PID wait invariant via `make lint-foreground-markers` (alias `make lint-foreground`), the `lint-foreground-markers` pre-commit hook, and the helper checks `scan_shell_file_for_family_b_wait` / `fence_has_family_b_pid_capture_and_wait` inside `scripts/lint-foreground-markers.sh`.

### Why Wait And Propagate?

Incident `984F0AA4-4436-40F3-A82E-9D114C1A58B4` is the concrete reason the fence requires both a foreground monitor and a post-monitor `wait`. Without the `wait`, a done sentinel can let the monitor return while the writer PID is still running, which creates an orphaned top-level Family B process. Without propagating the waited writer exit code on the success branch, the shell block can discard the writer's real failure and report only the monitor result, which hides regressions behind a false success path.

The canonical two-branch pattern avoids both failure modes:
- `monitor_rc=0` means the monitor infrastructure worked, so `wait "$PID"` must run and its exit code becomes the block exit code.
- `monitor_rc!=0` means the monitor itself failed (timeout/argv/path/infrastructure), so perform a bounded reap with `wait "$PID" 2>/dev/null || true` and exit with `monitor_rc` instead of a stale or unrelated writer code.

**Out of scope for this fence rule (Family A + external parallel launches).** Parallel subagent / multi-tool launches that the orchestrator **awaits** through a single foreground collector (the “Family A” pattern) are not on the Family B denylist — only the named blocking entrypoints are linted. Likewise, examples whose sole purpose is ad-hoc **Monitor**-style tailing of external logs or polling **non-Bash** state are not required to carry these markers when they do not invoke denylisted scripts in an invocation-shaped line. Scripts such as `implement-bootstrap.sh`, `rebase-checkpoint-probe.sh`, and `phantom-probe-with-warn.sh` remain ordinary foreground Bash calls.

When a fenced shell block contains an **invocation-shaped** line for one of the nine scripts enforced by `scripts/lint-foreground-markers.sh` (Family B denylist — ship/collect/dispatch/review-family entrypoints), the Markdown **immediately above** the opening fenced `bash` / `sh` / `shell` block must include this exact banner (you may prefix the banner line once with Markdown blockquote syntax: a `>` as the first non-whitespace character on that line):

`**⚠ Background required — must be paired with breadcrumb-monitor.sh.**`

**Per-anchor comment rule (matches the linter).** For **every** fence line the linter classifies as a denylisted-script anchor, there must be a line **strictly above** that anchor within the previous **five** in-fence lines that is exactly (leading shell whitespace allowed):

`# Background pair required: see BASH_AUTHORING.md §4`

**Per-anchor AND-semantics (matches the linter).** Each denylisted-script anchor within a fence must satisfy **both**:

1. The fence body contains the literal substring `run_in_background: true` (typically as `# Tool JSON: run_in_background: true` documenting the Bash tool JSON field for the long-script line).
2. The same fence contains a `breadcrumb-monitor.sh` invocation with `--stream`, `--done-sentinel`, `--status-file`, `--quiet-log`, `--surfaced-sentinel`, and, for top-level Family B writers, `--paired-pid-file` arguments pointing at shell variables.

**Top-level writer PID wait invariant.** Top-level Family B writers (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`) must use this same-fence shape: the writer command ends with shell `&`; the next three non-blank lines capture `$!` into a PID variable; the monitor runs in the foreground with `monitor_rc=0` / `|| monitor_rc=$?`; and a later `wait` references the same PID variable after the monitor invocation. The success branch exits with the writer's exit code. The monitor-failure branch performs a bounded reap and exits with the monitor's exit code so argv/path/timeout infrastructure failures are not masked by a stale writer-success result.

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/ship-pr.sh" \
  --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --repo "$REPO" &
SHIP_PR_PID=$!

monitor_rc=0
"${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" \
  --stream "$LARCH_BREADCRUMB_STREAM" \
  --done-sentinel "$LARCH_DONE_SENTINEL" \
  --status-file "$LARCH_STATUS_FILE" \
  --quiet-log "$LARCH_QUIET_LOG_FILE" \
  --surfaced-sentinel "$LARCH_BREADCRUMBS_SURFACED_FILE" \
  --paired-pid-file "$LARCH_PAIRED_PID_FILE" \
  || monitor_rc=$?

if [ "$monitor_rc" -eq 0 ]; then
  writer_rc=0
  wait "$SHIP_PR_PID" || writer_rc=$?
  exit "$writer_rc"
else
  wait "$SHIP_PR_PID" 2>/dev/null || true
  exit "$monitor_rc"
fi
```

**Shell `&` vs tool JSON `run_in_background`.** These are different layers and both apply when the writer and monitor share one Bash tool call. Shell `&` backgrounds the writer inside that shell so the foreground `breadcrumb-monitor.sh` can stream. Tool JSON `run_in_background: true` backgrounds the whole Bash tool call so the orchestrator turn is not blocked by the host tool timeout while the pair runs. When a writer is the only command in a Bash tool call and the monitor is launched in a separate foreground Bash tool call, shell `&` is not the coupling mechanism for that call; when the pair is in one Bash message, shell `&` is required.

The PID capture/wait pattern uses only Bash 3.2-safe syntax: `<var>=$!`, `wait "$<var>"`, `monitor_rc=0`, and `cmd || monitor_rc=$?`.

**Pre-launch path allocation.** Before the background launch line, export the six env vars under the calling skill's session tmpdir (`$DESIGN_TMPDIR` / `$IMPLEMENT_TMPDIR` / `$REVIEW_TMPDIR` / `$RESEARCH_TMPDIR`): create `$<TMPDIR>/breadcrumbs/`, allocate unique paths with `mktemp` / `touch`, and set `LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_QUIET_LOG_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, and `LARCH_PAIRED_PID_FILE`. Nested helpers inherit the breadcrumb stream vars so breadcrumbs propagate through the call tree.

`LARCH_PAIRED_PID_FILE` is owned only by top-level Family B entrypoints (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`). Their scripts write their own PID via `larch_quiet_write_paired_pid_file`, and parents unset the env var before synchronously invoking nested children (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`). The linter enforces allocation/export under a session `breadcrumbs/` directory, the monitor `--paired-pid-file` argument, and the shell `&` + PID capture + post-monitor `wait` invariant for the top-level set. It also enforces `unset LARCH_PAIRED_PID_FILE` before nested `dispatch-with-waterfall.sh` calls in shell scripts, looking back five non-blank non-comment lines and recognizing both literal and variable-backed invocations; exceptional lines require `# lint-foreground-markers: ok <reason>`.

Research and validation phase collector fences follow the same background+monitor pair. `scripts/lint-foreground-markers.sh` rejects contradictory post-fence prose such as `Do NOT set run_in_background: true` after a fence that already contains `run_in_background: true` and `breadcrumb-monitor.sh`.

One physical comment line may satisfy **multiple** anchors only when each of those anchors still lies within five lines below that comment. After more than five non-anchor in-fence lines since the last qualifying comment, the next anchor needs a **new** comment in its own five-line look-back window.

Do not paraphrase the banner or comment — CI's `make lint-foreground-markers` / pre-commit hook matches them literally (see `scripts/lint-foreground-markers.md`). Mentioning `run_in_background: true` only inside the fence body is **not** sufficient for the banner; the banner belongs in the prose window above the fence so operators see the contract before copying the block. If the linter reports a shell-shape failure, grep `scripts/lint-foreground-markers.sh` for `fence_has_family_b_pid_capture_and_wait` (fence Markdown) or `scan_shell_file_for_family_b_wait` (shell wrappers) first.
