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
