# BASH_AUTHORING.md

Behavioral guidelines for authoring Bash commands. Merge with project-specific instructions.

## 1. Exit-Code Safety for Bash Probes

**Probe commands should not create false error rows, and bare `grep` is not safe at the top level of a Bash tool block.**

### Wrapped-grep trap (Claude Code Bash tool)

Inside an orchestrator Bash tool block, `grep` is a Claude Code shell function, not `/usr/bin/grep`. It rewrites to the `claude` CLI in `ugrep` mode. A non-zero top-level wrapper exit can terminate the whole Bash block even with `|| true`, `|| echo NO_MATCH`, `if grep ...; then`, or `{ grep ...; } || X`. The canonical issue #3104 shape is `grep -q PATTERN FILE || echo X` aborting before `echo X` runs.

Two patterns are safe for the wrapper-exit trap. They solve only that trap. Producer probes still need an explicit path operand such as `.`, `python/`, or `docs/file.md`, or `< /dev/null` for intentional empty-stdin searches.

- **`command grep PATTERN FILE || X`**: bypasses the function and runs the system binary. Prefer it for `command grep -v ... > tmp` and other non-`if` probes. **Not safe in `if` conditions on bash 3.2**.
- **`( grep PATTERN FILE ) || X`**: wraps the function's inner exec subshell so the harness sees a normal subshell exit. Use **`( command grep ... )`** for Bash 3.2 `if` probes. Use this when you want `ugrep` behavior; otherwise prefer `command grep`.

Every grep-family producer probe needs an explicit path operand such as `.`, `python/`, or `docs/file.md`, or `< /dev/null`, including inside subshells and `command` forms. Wrapping does not prevent background stdin blocking.

> **`if command grep` is NOT safe on bash 3.2**: on macOS bash 3.2.57, `if command grep ...; then` triggers `set -e` when grep exits non-zero. For `if` probes, use `( command grep PATTERN FILE )`, and still pass a path or `< /dev/null`.

Piped grep (`printf X | grep Y`, `cat file | grep Y`) is safe because the pipeline already subshells grep. Plain `grep` inside `bash script.sh` is safe because the wrapper function is not exported. The hazard is top-level `grep` in Markdown bash/sh/shell fences and direct Bash tool blocks.

A static lint, `scripts/lint-bare-grep-probe.sh`, scans orchestrator-facing Markdown for bare top-level grep probes. Suppress fixtures only with trailing `# lint-bare-grep-probe: ok <reason>`.

### Background stdin hangs

Probe `rg`, `ripgrep`, and `grep` calls must pass an explicit path when they may run as the first command in an orchestrator Bash block. Use `.` or a concrete path such as `python/`, `skills/`, or `docs/file.md`.

Use `< /dev/null` only for intentional empty stdin. A no-path grep-family probe can block forever in background Bash mode because stdin may be an open pipe with no EOF.

The same `# lint-bare-grep-probe: ok <reason>` pragma covers rare intentional stdin-search fixtures.

### Probe stdout guards (still required after the safe form is chosen)

For expected no-match probes, keep Bash transcripts clean:
- `... || true` suppresses non-zero exit.
- `... || echo 0` only when no-match emits **no stdout**, not for `grep -c`.

Apply guards on top of the safe form, such as `command grep -q PATTERN file || true` or `( grep -c PATTERN file ) || true`. In `if` conditionals, use `( command grep ... )` and no `|| true`.

User-facing logs should not show expected no-match errors.

## 2. Bash Quoting Hygiene

**For Bash commands with more than two nested quote/escape contexts, prefer file-backed scripts over inline composition.**

Triggers:
- `python -c "<multi-line code>"` with embedded single-quoted Python literals and escaped double quotes
- `bash -c '<script>'` with internal `'"'"'` single-quote-switch escapes
- `awk '{...}'` with internal single-quoted regex literals
- Any composition with three or more escape levels

Robust alternatives:
1. **Temp script:** write `/tmp/probe.sh` or `.py`, then run it.
2. **Quoted heredoc:** `python3 <<'PY' ... PY` or `bash <<'EOF' ... EOF`.
3. **Pipe stdin:** `printf '<script>' | python3 -`.

Avoid `cat > file << EOF` with `${LARGE_VAR}` expansion inside `run_in_background`. Prefer Write or a file-backed handoff. Quoted heredocs are fine for literal scripts, not large runtime expansion.

On shell parse errors, do NOT patch escapes repeatedly. Switch to a robust alternative.

## 3. Bash 3.2 Portability

**Repository shell scripts must stay compatible with macOS system Bash 3.2 unless a script documents a narrower runtime.**

Forbidden in committed shell scripts:
- associative arrays: `declare -A` / `typeset -A`
- namerefs: `declare -n` / `local -n`
- `mapfile` / `readarray`
- case conversion: `${var^^}` / `${var^}` / `${var,,}` / `${var,}`
- append-all redirection: `&>>`
- coprocs: `coproc { ... }` / `coproc NAME { ... }`

Use Bash 3.2 alternatives: newline-delimited temp files, `while IFS= read -r ...`, `case` or `tr`, and `>>file 2>&1`.

### Renderer Substitution Safety

Avoid `${var//pattern/$replacement}` when `$replacement` can contain file, user, or prompt content. Bash 5.x treats unescaped `&` in the replacement as the matched text, while macOS Bash 3.2 treats it literally.

Prefer the split form around a literal marker token:

```bash
before="${template%%<FEATURE_DESCRIPTION>*}"
after="${template#*<FEATURE_DESCRIPTION>}"
rendered="${before}${feature_description}${after}"
```

This is the canonical `%%` / `##` split pattern for prompt renderers. If global replacement is necessary, pre-escape `&` inside a Bash-version-scoped helper with a comment. CI enforces this via `make lint-renderer-substitution-safety`.

Run `make lint-bash32` after shell-script edits. Suppress fixture tokens only on that line with `# lint-bash32: ok <reason>`.

## Residual Bash after E3

For the shared residual-Bash policy, see `AGENTS.md`. Unique Bash contracts remain here: contract-bearing hooks define local `hook_emit` functions and keep hook JSON on the contract stream. `sessionstart-health.sh` keeps a direct stdout fallback for stripped PATH environments.

Use `scripts/residual-bash-paths.txt` through `python3 python/cli.py residual-bash paths [--root PATH]` when a linter or CI job needs the residual shell set.
