# BASH_AUTHORING.md

Behavioral guidelines for authoring Bash commands. Merge with project-specific instructions as needed.

## 1. Exit-Code Safety for Bash Probes

**Probe commands should not create false error rows, and bare `grep` is not safe at the top level of a Bash tool block.**

### Wrapped-grep trap (Claude Code Bash tool)

Inside an orchestrator Bash tool block, `grep` is **not** the system `/usr/bin/grep`. It is a Claude Code shell function that rewrites the call into the `claude` CLI in `ugrep` mode (`( exec -a ugrep "$CLAUDE_CODE_EXECPATH" -G ... )`). When that subshell exits non-zero at the top level of the script, the harness treats the top-level `claude` subprocess exit as a fatal tool error and terminates the **whole** Bash tool block — even with `|| true`, `|| echo NO_MATCH`, `if grep ...; then`, or `{ grep ...; } || X` guards. Subsequent lines never run; the orchestrator sees `Exit code 1` and the next step starts mid-state. Issue #3104 captures the full reproduction; the canonical bug shape is `grep -q PATTERN FILE || echo X` aborting before `echo X` runs.

Two patterns are safe and equivalent in semantics to bare `grep`:

- **`command grep PATTERN FILE || X`** — `command` bypasses the function and runs the system binary directly. Preferred (no wrapper detour, no extra subshell). Use this for `if command grep -q ...; then`, `command grep -v ... > tmp`, and any other probe shape.
- **`( grep PATTERN FILE ) || X`** — explicit subshell wraps the function's inner exec subshell so the harness sees a normal subshell exit, not a top-level `claude` exit. Useful when you specifically want the function's `ugrep`-mode behavior (e.g. ignoring `.git/`); otherwise prefer `command grep`.

Piped grep (`printf X | grep Y`, `cat file | grep Y`) is safe — the pipeline already runs grep in a subshell. Plain `grep` *inside* a `bash script.sh` invocation is also safe: the wrapper function is not exported, so child `bash` processes see the real `grep`. The hazard is specific to top-level `grep` lines in Markdown bash/sh/shell fences (and direct Bash tool blocks).

A static lint (`scripts/lint-bare-grep-probe.sh`, wired into pre-commit) scans orchestrator-facing Markdown for bare top-level grep probes and rejects them. Suppress fixture or intentional lines only with a trailing `# lint-bare-grep-probe: ok <reason>` comment.

### Probe stdout guards (still required after the safe form is chosen)

For grep-family probes where "no match" is informational, keep the original guidance so Bash transcripts stay clean:
- `... || true` to suppress the non-zero exit (works for all grep variants, including `grep -c` which already prints `0` on no-match).
- `... || echo 0` only for probes that produce **no stdout** on no-match — not for `grep -c`, which already emits a count before exiting 1.

Apply these guards on top of the safe form, e.g. `command grep -q PATTERN file || true` or `( grep -c PATTERN file ) || true`. In `if` conditionals where exit 1 is the branch signal, `command grep` alone is sufficient — no extra `|| true`.

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

### Renderer Substitution Safety

Avoid `${var//pattern/$replacement}` when `$replacement` can contain file, user, or prompt content. Bash 5.x treats an unescaped `&` in the replacement as the matched text, while macOS Bash 3.2 treats it literally, so content like `Strunk & White` can be corrupted only in CI.

Prefer the split form around a literal marker token:

```bash
before="${template%%<FEATURE_DESCRIPTION>*}"
after="${template#*<FEATURE_DESCRIPTION>}"
rendered="${before}${feature_description}${after}"
```

This is the canonical `%%` / `##` split pattern for prompt renderers. If you truly need global replacement, pre-escape `&` only inside a Bash-version-scoped helper with a comment explaining the constraint. CI enforces this via `make lint-renderer-substitution-safety`.

Run `make lint-bash32` after shell-script edits. If a regression harness intentionally contains a forbidden token as fixture text or static grep pattern, suppress only that line with an inline `# lint-bash32: ok <reason>` comment.
