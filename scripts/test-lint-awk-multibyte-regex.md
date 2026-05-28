# scripts/test-lint-awk-multibyte-regex.sh - contract

Regression harness for `scripts/lint-awk-multibyte-regex.sh`. The primary `.md`
contract is `scripts/lint-awk-multibyte-regex.md`.

The harness creates a private fixture root under `mktemp -d` and exercises:

- Clean ASCII-only `awk -v` / `$0 ~` fixture → exit 0.
- Rule 1 em-dash and CJK in `-v` values → exit 1 with `awk-v-nonascii`.
- Rule 2 em-dash in `match()` and on a `$0 ~ var` line → exit 1 with
  `awk-body-nonascii-regex`.
- Rule 2 false-positive guard: non-ASCII only inside `printf` format → exit 0.
- Same-line pragma with required reason → exit 0; pragma without reason → exit 1.
- Excluded `node_modules/` and `larch-logs/` prefixes → exit 0.
- Standalone `.awk` file with non-ASCII at `match(` → exit 1.
- Invalid `--root` → exit 2.

Fixtures map to PR #3144's em-dash family (`orchestrator_style_anchor`, surrounding
`awk -v …` and `match($0, "…" VAR "…"—…)` patterns). The harness does not assert
`[[:` POSIX-class portability (wrong #3134 hypothesis).

Assertions use `command grep -F` to avoid awk in the harness itself.

Wired through Makefile target `test-lint-awk-multibyte-regex` and
`test-harnesses-5`.
