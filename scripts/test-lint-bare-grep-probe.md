# scripts/test-lint-bare-grep-probe.sh - contract

Regression harness for `scripts/lint-bare-grep-probe.sh`. The primary `.md`
contract is `scripts/lint-bare-grep-probe.md`.

The harness creates a private fixture root under `mktemp -d` and exercises
the lint contract, including:

- Clean tree (no markdown files) → exit 0.
- Bare `grep ... || X`, bare `grep ... > tmp`, `if grep ...; then`,
  `if ! grep ...; then` → exit 1 with the expected violation lines.
- No-path `rg` / `ripgrep` violations.
- Parent-ascent path violations for `command grep`, `rg`, and `ripgrep`,
  including `../path`, `path/../child`, trailing `path/..`, and `$TMP/../../../..`
  shapes.
- Multi-path parent-ascent violations where the first path is safe and a later
  path contains `../`.
- Multi-segment scanning for right-hand fallback, semicolon, logical-and, and
  later-pipeline candidates.
- Non-grep-family segment starts, such as `echo done; rg`, do not stop scanning.
- Safe earlier candidates do not stop later candidate scanning.
- `|&` pipe-stderr forms are pipe-fed: no-path probes are allowed, and
  parent-ascent operands still fail.
- Segment-relative bare-wrapper detection, including
  `false || grep PATTERN file.txt`.
- `-f` / `--file` parent-ascent cases for split, equals, and attached-short
  forms.
- Split `--include` / `--exclude` fixtures use `grep`, not `rg`.
- Parent-ascent checks before `< /dev/null` short-circuit.
- No-path `if rg`, `if ripgrep`, `if ! rg`, `if ! ripgrep`,
  `if ! command rg`, and other `if` / `if !` grep-family violations.
- Allowed path-bearing `if rg ... path`, `if ! ripgrep ... path`,
  `if command rg ... path`, and `if command ripgrep ... path` forms.
- No-path `command grep`, `command rg`, `command ripgrep`, and
  subshell-wrapped grep-family violations, including `( grep ... )`,
  `( ripgrep ... )`, and `( command ... )` forms.
- Brace-group `{ rg ...; }`, `{ ripgrep ...; }`, `{ grep ...; }`,
  `{ command rg ...; }`, `{ command ripgrep ...; }`, and
  `{ command grep ...; }` violations.
- Per-segment scanning across `||`, `|`, `&`, `&&`, `;`, and `|&` boundaries,
  plus redirect truncation so suffix tokens do not false-allow no-path probes.
- Unquoted `< /dev/null` short-circuit before `<` redirect truncation.
- False stdin-safe short-circuit cases where `< /dev/null` appears only in a
  quoted echo, quoted redirect token, inline comment, or comment substring.
- Explicit-path and `< /dev/null` allowed cases, including positive
  `( grep ... path )`, `( ripgrep ... path )`, `( command rg ... path )`,
  `{ command rg ... path; }`, `{ command ripgrep ... path; }`,
  `{ grep ... path; }`, and `{ command grep ... path; }` grouped forms.
- Env-prefixed path-bearing probes such as `LC_ALL=C rg ... python/`.
- Indented no-path `rg` / `ripgrep` inside fence bodies.
- Option-value handling for `--type py`, `--type=py`, `--regexp=...`, `-e`,
  attached short forms like `-A3`, and `--regexp`.
- Parent-ascent false-positive guards for pattern operands and option values,
  including `-e "../pattern"` and `--include="../*.py"`.
- Allowed `command grep ... FILE > tmp || true` producer shape.
- Safe path-bearing forms (`command grep ...`, explicit `( grep ... path )`
  subshell wrap, piped grep) → exit 0.
- Same-line `# lint-bare-grep-probe: ok <reason>` suppression and full-line
  comments inside the bash fence → exit 0, including a reviewed parent-ascent
  fixture.
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
