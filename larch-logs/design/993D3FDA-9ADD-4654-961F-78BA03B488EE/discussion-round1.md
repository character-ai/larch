## Decision 1: Which of the 3 fix options to pursue
- **Question**: The issue lists 3 fix options (step2-implement.sh recovery; remove write_stdin from prompt; TTY/setsid wrapper). Which to pursue?
- **Resolution**: Option 2 only — remove write_stdin (and broader interactive-subprocess patterns) from the Codex implementer prompt and the Codex CI fixer prompt.
- **Source**: user

## Decision 2: Launcher scope
- **Question**: Should the fix cover only `launch-codex-implement.sh`, or also `launch-codex-ci.sh` which has the same gap?
- **Resolution**: Cover both — the Codex implementer (Step 2) and the Codex CI fixer use the same Codex CLI tool family, so any prompt-level prohibition must apply to both.
- **Source**: user

## Decision 3: Coordination with #2973
- **Question**: How should this design coordinate with #2973 (same root cause in `launch-review.sh`, currently `[IMPLEMENTING]`)?
- **Resolution**: #2973 is already in flight and is assumed to land first. The current GitHub issue #2991 is marked **blocked by #2973** (recorded natively via `/larch:block-issue`). #2973's plan adds `< /dev/null` to all background Codex spawns in `scripts/run-external-agent.sh`, which addresses a related but distinct failure mode (Codex's own stdin closed by parent shell exit) — that fix does **not** prevent Codex from spawning interactive subprocess sessions via `exec_command` and failing on `write_stdin` against them, which is #2991's specific failure surface. Hence #2991's prompt-level fix is complementary and still warranted post-#2973.
- **Source**: user + codebase (`scripts/run-external-agent.sh:206-213`, `<!-- larch:plan -->` block on #2973)

## Decision 4: Prohibition scope (write_stdin vs. broader)
- **Question**: Should the prompt prohibit just the literal `write_stdin` tool, or the broader family of interactive-subprocess patterns?
- **Resolution**: Broader scope — prohibit `write_stdin` AND any pattern that keeps an interactive subprocess session alive (persistent `exec_command` sessions, paired `read_stdout` polling). Implementer should use one-shot commands and feed input via pipes, heredocs, or files. More robust against future failures in the same class.
- **Source**: user

## Decision 5: Cursor-implementer parity
- **Question**: Cursor uses a different agent CLI without `write_stdin`. Should the same prohibition appear in `agents/cursor-implementer.md`?
- **Resolution**: Codex-specific. The base file `agents/_implementer-base.md` generates both `codex-implementer.md` and `cursor-implementer.md` via `scripts/generate-codex-implementer.sh` and `scripts/generate-cursor-implementer.sh`. The prohibition is Codex-tool-name-specific (`write_stdin`, `exec_command` interactive sessions are Codex CLI tools), so the cleanest placement is either (a) only in the Codex generator's tail-augmentation (if such a path exists) or (b) in the base file with a parenthetical "(Codex-specific; Cursor does not expose these tools)" annotation. Architecture decision deferred to Step 2a sketches per Round 1 prohibition on file-organization decisions.
- **Source**: codebase (`scripts/generate-codex-implementer.sh`, `scripts/generate-cursor-implementer.sh`)
