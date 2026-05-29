# scripts/degraded-tools-gate.sh — contract

Issue #3207 degraded-external-tools gate **detector**. Given the four Step-0
presence keys produced by `scripts/session-setup.sh --check-reviewers`
(`CODEX_BINARY_FOUND` / `CODEX_PRESENT` / `CURSOR_BINARY_FOUND` /
`CURSOR_PRESENT`), it decides whether the session is running degraded (Codex
and/or Cursor unavailable) and composes a presentable explanation of what is
down, why, and what the backup waterfall does about it.

It is a **pure detector**: it never prompts and never blocks. The interactive
gate itself lives in the skill orchestrator — see the "Degraded-tools gate
(Step 0)" procedure in `skills/shared/external-reviewers.md`, which `/design`,
`/implement`, `/review`, and `/research` Step 0 invoke. The orchestrator runs
this helper, and when `DEGRADED=true` presents the explanation and asks the
operator (via `AskUserQuestion`) whether to continue with the degraded
waterfall or abort.

## Availability rule

A tool is `ok` only when **both** its binary is found **and** its runtime probe
passed (`*_BINARY_FOUND=true` AND `*_PRESENT=true`), matching the
`codex_available` / `cursor_available` rule in
`skills/shared/external-reviewers.md`. Otherwise:

- `binary-missing` — `*_BINARY_FOUND` is not `true` (CLI not on `PATH`).
- `probe-failed` — binary present but `*_PRESENT` is not `true` (runtime/auth/quota probe failed, skipped, or timed out).

Any value other than the literal `true` normalizes to not-true.

## Flags

- `--codex-binary-found <bool>` / `--codex-present <bool>`
- `--cursor-binary-found <bool>` / `--cursor-present <bool>`
- `--skill <name>` — optional label woven into the explanation header (default `this`).

## Output (stdout KV)

- `DEGRADED=true|false` — `true` iff either tool's state is not `ok`.
- `CODEX_STATE=ok|binary-missing|probe-failed`
- `CURSOR_STATE=ok|binary-missing|probe-failed`
- When `DEGRADED=true`, a multi-line explanation block bracketed by
  `DEGRADED_EXPLANATION_BEGIN` / `DEGRADED_EXPLANATION_END` (lifted verbatim by
  the orchestrator for presentation).

Exit code is `0` on valid argv (degraded or not); `2` on an unknown flag
(caller bug).

## Test harness

`scripts/test-degraded-tools-gate.sh` — covers the state-classification matrix
(ok / binary-missing / probe-failed for each tool), the `DEGRADED` boolean,
explanation-block presence/absence, the `--skill` label, and the unknown-flag
exit-2 path. Wired into `make lint` via the `test-degraded-tools-gate` target.

## Edit-in-sync

| File | Relationship |
|------|----------------|
| `scripts/degraded-tools-gate.sh` | Source of truth |
| `skills/shared/external-reviewers.md` | "Degraded-tools gate (Step 0)" procedure that invokes this helper |
| `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/review/SKILL.md`, `skills/research/SKILL.md` | Step 0 callers |
| `scripts/check-reviewers.sh` | Upstream producer of the four presence keys this helper consumes |
