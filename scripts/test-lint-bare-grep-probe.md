# scripts/test-lint-bare-grep-probe.sh - contract

Regression harness for `scripts/lint-bare-grep-probe.sh`. The primary `.md`
contract is `scripts/lint-bare-grep-probe.md`.

The harness creates a private fixture root under `mktemp -d` and exercises
twenty cases covering:

- Clean tree (no markdown files) → exit 0.
- Bare `grep ... || X`, bare `grep ... > tmp`, `if grep ...; then`,
  `if ! grep ...; then` → exit 1 with the expected violation lines.
- Safe forms (`command grep ...`, explicit `( grep ... )` subshell wrap,
  piped grep) → exit 0.
- Same-line `# lint-bare-grep-probe: ok <reason>` suppression and full-line
  comments inside the bash fence → exit 0.
- Non-bash fences (`python`, untagged) and out-of-fence prose `grep` → exit 0.
- `sh` and `shell` info-strings count as bash fences.
- `.claude/skills/**/*.md` and `.claude/rules/*.md` are scanned.
- Top-level `README.md`, `docs/`, and `larch-logs/` are out of scope.
- Multiple violations in one file and indented violations inside fence bodies
  are reported.
- Git ls-files and find-walk fallbacks produce the same results.
- Invalid `--root` exits 2 with the expected stderr.

Wired through Makefile target `test-lint-bare-grep-probe` and one
`test-harnesses-N` shard.
