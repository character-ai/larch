## Proposed Design Outline

### Goals
- Remove the render-corruption exposure for the 13 known `awk -F=` KV-parsing call sites (`.claude/skills/release/SKILL.md` Step 8, `skills/pause/SKILL.md`, `skills/deps/SKILL.md`) by invoking a Python helper instead of retyping awk from rendered Markdown context.
- Reuse the existing `larch.io` KV-parsing helpers (`kv_value`/`read_kv`) rather than reimplementing parsing, per G-IO-1.
- Add a static lint flagging bare `$<digit>` awk field/record references inside `SKILL.md` code fences, to catch regressions in files this change doesn't touch, per G-Enf-1.

### Non-goals
- Confirming or fixing the actual external rendering root cause (suspected Claude Code CLI content-loading pipeline) — outside this repo's control.
- `skills/deps/SKILL.md`'s `$1`/`$2` shell-argv flag dispatch (lines 35-47) — bash's own positional-parameter syntax, not an awk field reference; not mitigable the same way.
- The `$0` bootstrap-recovery awk idiom in `skills/implement/SKILL.md`, `bootstrap-recovery.md`, `extracted-script-registry.md` — resolves `CLAUDE_PLUGIN_ROOT` itself, so a `python3 python/cli.py` helper would be circular.

### Approach sketch
- Add one new `python3 python/cli.py` verb wrapping existing `larch.io.kv_value` / `read_kv` to extract a single key's value from stdin text or a file, with first-match/last-match selectable per call site.
- Repoint the 13 awk call sites across the 3 files to the new verb instead of `awk -F=`.
- Preserve each file's existing invocation convention: relative `python3 python/cli.py` for the dev-only release skill; `${CLAUDE_PLUGIN_ROOT}/python/cli.py` for the public pause/deps skills.
- Add a new lint script (Python, alongside the `lint-bare-grep-probe.sh` / `lint-awk-multibyte-regex` family) scanning `SKILL.md` fences for bare `$<digit>` awk tokens, wired into the Makefile lint sweep.

### Surfaces in scope
- `python/cli.py` registry plus a small KV-get helper (wrapping `python/larch/io.py`).
- `.claude/skills/release/SKILL.md`, `skills/pause/SKILL.md`, `skills/deps/SKILL.md`.
- A new lint script/module plus its Makefile target.

### Open questions
- None.
