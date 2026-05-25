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

**Why this is normative (not cosmetic).** Unpaired background launches defer completion to a task notification that may arrive **after** the model has already ended the turn — the failure mode behind `skills/implement/SKILL.md` NEVER **#16** and issue **#2454** (`ship-pr.sh` submitted without a paired monitor). The monitor reads explicit tmpdir paths (`LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_QUIET_LOG_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`) allocated by the calling skill before launch. CI enforces the markers below via `make lint-foreground-markers` (alias `make lint-foreground`) and the `lint-foreground-markers` pre-commit hook.

**Out of scope for this fence rule (Family A + external parallel launches).** Parallel subagent / multi-tool launches that the orchestrator **awaits** through a single foreground collector (the “Family A” pattern) are not on the Family B denylist — only the named blocking entrypoints are linted. Likewise, examples whose sole purpose is ad-hoc **Monitor**-style tailing of external logs or polling **non-Bash** state are not required to carry these markers when they do not invoke denylisted scripts in an invocation-shaped line. Scripts such as `implement-bootstrap.sh`, `rebase-checkpoint-probe.sh`, and `phantom-probe-with-warn.sh` remain ordinary foreground Bash calls.

When a fenced shell block contains an **invocation-shaped** line for one of the nine scripts enforced by `scripts/lint-foreground-markers.sh` (Family B denylist — ship/collect/dispatch/review-family entrypoints), the Markdown **immediately above** the opening fenced `bash` / `sh` / `shell` block must include this exact banner (you may prefix the banner line once with Markdown blockquote syntax: a `>` as the first non-whitespace character on that line):

`**⚠ Background required — must be paired with breadcrumb-monitor.sh.**`

**Per-anchor comment rule (matches the linter).** For **every** fence line the linter classifies as a denylisted-script anchor, there must be a line **strictly above** that anchor within the previous **five** in-fence lines that is exactly (leading shell whitespace allowed):

`# Background pair required: see BASH_AUTHORING.md §4`

**Per-anchor AND-semantics (matches the linter).** Each denylisted-script anchor within a fence must satisfy **both**:

1. The fence body contains the literal substring `run_in_background: true` (typically as `# Tool JSON: run_in_background: true` documenting the Bash tool JSON field for the long-script line).
2. The same fence (or the next fenced `bash` block within ten Markdown lines after the closing fence) contains a `breadcrumb-monitor.sh` invocation with `--stream`, `--done-sentinel`, `--status-file`, `--quiet-log`, and `--surfaced-sentinel` arguments pointing at shell variables.

**Pre-launch path allocation.** Before the background launch line, export the five env vars under the calling skill's session tmpdir (`$DESIGN_TMPDIR` / `$IMPLEMENT_TMPDIR` / `$REVIEW_TMPDIR` / `$RESEARCH_TMPDIR`): create `$<TMPDIR>/breadcrumbs/`, allocate unique paths with `mktemp` / `touch`, and set `LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_QUIET_LOG_FILE`, and `LARCH_BREADCRUMBS_SURFACED_FILE`. Nested helpers inherit these vars so breadcrumbs propagate through the call tree.

One physical comment line may satisfy **multiple** anchors only when each of those anchors still lies within five lines below that comment. After more than five non-anchor in-fence lines since the last qualifying comment, the next anchor needs a **new** comment in its own five-line look-back window.

Do not paraphrase the banner or comment — CI's `make lint-foreground-markers` / pre-commit hook matches them literally (see `scripts/lint-foreground-markers.md`). Mentioning `run_in_background: true` only inside the fence body is **not** sufficient for the banner; the banner belongs in the prose window above the fence so operators see the contract before copying the block.
