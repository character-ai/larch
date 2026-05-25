## Plan

# Plan — [OOS #2721] Note Claude voter subprocess surface in SECURITY.md

## Files to modify/create

### UPDATED: `SECURITY.md`

Insert one new paragraph between the existing "Claude review subprocesses" paragraph (covers `launch-claude-subprocess.sh`) and the "Public review scout logs" paragraph. The new paragraph is dedicated to `scripts/launch-claude-review.sh` as the plan-ballot Claude voter surface, covers subprocess data paths and secret-handling expectations, and explicitly contrasts the wrapper-mediated subprocess against the prior in-process Agent voter so the trust/logging-boundary delta is documented.

## Approach

1. Read the surrounding paragraphs (line 44 "Claude review subprocesses" — covers `launch-claude-subprocess.sh`; line 46 "Public review scout logs") to anchor placement and match the existing prose register (single dense paragraph, backticked file paths, sidecar contract references).
2. Compose one new paragraph that opens with a bold leader `**Claude voter subprocess (`launch-claude-review.sh`)**:` and covers, in this order:
   - **Wrapper identity**: `scripts/launch-claude-review.sh` is the sibling wrapper to `launch-claude-subprocess.sh`; it runs Claude as a read-only subprocess in `--role voter` (or `--role reviewer`) and is the path `scripts/dispatch-plan-voters.sh` uses for Voter 1 on plan ballots (`--timing-task-kind claude-plan-voter`), replacing the historical in-process Agent-tool voter path.
   - **Subprocess data paths**: the ballot output file is written to the dispatcher-provided `--output` path under the session tmpdir; the wrapper additionally emits `.meta`, `.done`, and `.dirty-tree` sidecars under the same tmpdir; `dispatch-plan-voters.sh` waits on the wrapper sentinels before returning voter paths and captures `gh`-style error metadata via `append-tool-failure.sh` on non-OK.
   - **Trust/logging boundary delta vs in-process Agent voter**: the in-process Agent voter ran inside Claude Code's main process and inherited its tool surface and logging; the subprocess voter is a fresh `claude` invocation with its own stdout/stderr, .meta/.done/.dirty-tree sidecars, and per-launch timing emitted under `claude-plan-voter` — so launcher-level observability replaces in-process tool-call telemetry. Argv shape (output/prompt/context paths, model, timeout, role) is the same surface validated by `launch-claude-review.sh` as for other voters/reviewers (containment-root checks, symlink rejection, control-character rejection, context cap 20 files × 1 MB).
   - **Secret-handling expectations**: the wrapper itself has no mechanical read-only CLI sandbox — read-only behavior is prompt-level only and enforced post-hoc through the `.dirty-tree` sidecar; the wrapper does not run output through `redact-secrets.sh`. Downstream consumers (ballot aggregator, `compose-review-findings.sh`, `tracking-issue-write.sh`, `larch-log.sh`, `design-log-publish.sh`) apply the redaction pipeline at the publish boundary, the same as for other reviewer-produced material. The plan-voter dispatcher uses a narrower do-not-modify voter prompt but does not publish launcher-owned dirty-tree sidecars itself; the wrapper-emitted sidecar remains the post-hoc backstop. Cross-reference the existing line 40 "Claude Voter 1" sentence so the two are read together.
   - **Cross-references**: `scripts/launch-claude-review.sh`, `scripts/launch-claude-review.md`, `scripts/dispatch-plan-voters.sh`, `scripts/dispatch-plan-voters.md`, `scripts/lib-timing-kinds.sh` (`claude-plan-voter` enum), `scripts/lib-voter-parse-rate.sh` (parse-rate probe path).
3. Insert the new paragraph at the blank line between the existing "Claude review subprocesses" paragraph and the "Public review scout logs" paragraph (so `launch-claude-review.sh` and `launch-claude-subprocess.sh` documentation sit adjacent).
4. Do **not** modify the existing line 40 "External tool delegation" / "Claude Voter 1" sentence or the line 44 "Claude review subprocesses" paragraph in this change (per Decision 1 — new dedicated paragraph, not augmentation).

## Edge cases

- **Existing line 40 mention**: SECURITY.md line 40 already names "Claude Voter 1 ... runs as a `scripts/launch-claude-review.sh` subprocess". The new paragraph must add detail without contradicting that sentence; cross-reference it explicitly rather than repeating its exact wording.
- **Markdown lint (MD038)**: backtick code spans for filenames/flags must not start or end with whitespace; multi-word literals stay outside spans. Per `.claude/rules/markdown-no-space-in-code-span.md`.
- **Drift-prone counts**: do NOT hardcode literal sidecar counts, voter counts, or line numbers; refer to symbols/file paths only. Per `.claude/rules/drift-prone-prose-in-docs.md`.
- **Submodule guard**: `SECURITY.md` is in the superproject (top-level path) — `block-submodule-edit.sh` does not apply. Edit goes through the normal Edit tool.
- **Pre-commit secret scanners**: SECURITY.md is on the non-allowlisted gitleaks Layer-1 / Layer-2 scan path; the new paragraph must not introduce any token-shaped literals beyond the existing redaction-pipeline mentions (already token-free).
- **Bash-authoring rule**: this is a doc-only paragraph; no shell snippets are added, so foreground-required banner rules do not apply.

## Testing strategy

- `make lint` — runs the markdownlint pre-commit hook (MD038/MD037/MD001), the gitleaks pre-commit hook, and `make lint-foreground-markers`. The new paragraph is plain prose with backticked file paths; it should pass cleanly.
- Manual sanity check by re-reading the new paragraph in-place to confirm it sits between the "Claude review subprocesses" and "Public review scout logs" paragraphs and that the bold leader matches the existing register.
- No automated test harness fixture changes — this is doc-only.

diff_lines: 12

## Acceptance

- `SECURITY.md` has exactly one new paragraph inserted between the existing **Claude review subprocesses** paragraph (the one led with `launch-claude-subprocess.sh`) and the **Public review scout logs** paragraph.
- The new paragraph opens with a bold leader of the form `**Claude voter subprocess (`launch-claude-review.sh`)**:` and contains, in order: wrapper identity (sibling to `launch-claude-subprocess.sh`; `--role voter` path used by `dispatch-plan-voters.sh` Voter 1 with `--timing-task-kind claude-plan-voter`); subprocess data paths (`--output` file plus `.meta`/`.done`/`.dirty-tree` sidecars under the session tmpdir; dispatcher wait-on-sentinels and `append-tool-failure.sh` capture on non-OK); trust/logging-boundary delta vs the prior in-process Agent voter (subprocess stdout/stderr + sidecars + `claude-plan-voter` timing replace in-process tool telemetry); and secret-handling expectations (no mechanical CLI sandbox; `.dirty-tree` post-hoc backstop; downstream consumers apply `redact-secrets.sh` at the publish boundary).
- The paragraph cross-references the existing line-40 "Claude Voter 1" sentence (by content, not by line number) so the two are read together. The existing line-40 "External tool delegation" paragraph and the existing line-44 "Claude review subprocesses" paragraph are **not** modified.
- No hard-coded line numbers, sidecar counts, or other drift-prone literals appear in the new paragraph (per `.claude/rules/drift-prone-prose-in-docs.md`); references use file paths and paragraph-leader names instead.
- Backtick code spans contain no leading/trailing whitespace (MD038); multi-word literals stay outside spans (per `.claude/rules/markdown-no-space-in-code-span.md`).
- `make lint` is green after the edit (markdownlint MD037/MD038/MD001, gitleaks Layer 1, foreground-markers).

diff_lines: 12
