# scripts/test-lint-awk-multibyte-regex.sh - contract

Regression harness for `scripts/lint-awk-multibyte-regex.sh`. The primary `.md`
contract is `scripts/lint-awk-multibyte-regex.md`.

The harness creates a private fixture root under `mktemp -d` and exercises 19 cases:

- Clean ASCII-only `awk -v` / `$0 ~` fixture → exit 0.
- Rule 1 em-dash and CJK in `-v` values → exit 1 with `awk-v-nonascii`.
- Rule 2 em-dash in `match()` and on a `$0 ~ var` line → exit 1 with
  `awk-body-nonascii-regex`.
- Rule 2 false-positive guard: non-ASCII only inside `printf` format → exit 0.
- Same-line pragma with required reason → exit 0; pragma without reason → exit 1.
- Excluded `node_modules/` and `larch-logs/` prefixes → exit 0.
- Standalone `.awk` file with non-ASCII at `match(` → exit 1.
- Invalid `--root` → exit 2.
- Shell comments that mention `awk -v ...` → exit 0.
- Backslash continuation with split `-v NAME = \` assignment → exit 1.
- Heredoc awk body with non-ASCII regex callsite → exit 1.
- Non-awk heredoc body that merely contains an `awk -v ...` sample → exit 0.
- Single-quoted awk body followed by a pipeline suffix still closes correctly → exit 1.
- Additional Rule 2 callsites `!~`, `gsub(`, `sub(`, and `split(` all report → exit 1.
- `substr(` does not false-positive as `sub(`, and a trailing EOF continuation still applies Rule 2 → exit 1.

Fixtures map to PR #3144's em-dash family (`orchestrator_style_anchor`, surrounding
`awk -v …` and `match($0, "…" VAR "…"—…)` patterns). The harness does not assert
`[[:` POSIX-class portability (wrong #3134 hypothesis).

Assertions use `command grep -F` to avoid awk in the harness itself.

Wired through Makefile target `test-lint-awk-multibyte-regex` and
`test-harnesses-5`.
