## Goal
Implement issue #3596: [IMPLEMENTING] [BUG] (URGENT) render-voter-prompt.sh silently truncates voter prompts on scope-anchor failure — breaks /design plan-review voting (dispatch-plan-voters.sh); dispatch-code-voters.sh latently exposed\n\n## Context.

## Implementation Plan
## Context

Found during `/design` on issue #3513. The Step 3 plan-review **voting** panel collapsed to `panel-failed`: the Claude voter returned *"Ready to review. Please share the plan modifications or findings you'd like me to vote on."* (0 votes), the Codex voter produced no parseable votes, and only Cursor voted — by **searching** for the ballot it noticed the launcher *"should have attached."* All three saved voter prompts were exactly **955 bytes**.

## Root cause (deterministic; byte-exact reproduction)

`scripts/dispatch-plan-voters.sh` builds each voter prompt via `skills/shared/scripts/render-voter-prompt.sh --ballot-file <DESIGN_TMPDIR>/ballot.txt --scope-anchor-file <DESIGN_TMPDIR>/plan-review-scope-anchor.txt …`. `render-voter-prompt.sh`'s `validate_scope_anchor_file` only allows scope-anchor paths under `$REPO_ROOT`, `/tmp`, `/private/tmp`, `/var/folders`, `/private/var/folders`. The scope anchor lives in `DESIGN_TMPDIR` = `~/.cache/larch/sessions/<run>/`, which is **not** in that allowlist, so the script `exit 2`s **after emitting only the ~955-byte preamble** — dropping the `Read the ballot from this path: …` line **and** the entire `FINDING_N: YES|NO|EXONERATE` output grammar.

`make_prompt_file` in `dispatch-plan-voters.sh` runs `render-voter-prompt.sh … > "$prompt_file"` and **never checks the exit code**, so the truncated 955-byte prompt is silently used for all three voters.

Byte-exact reproduction (matches the failing run's 955-byte `claude-plan-voter-prompt.txt`):

```text
$ render-voter-prompt.sh … --verification-context plan \
    --scope-anchor-file ~/.cache/larch/sessions/<run>/plan-review-scope-anchor.txt
render-voter-prompt rc=2
prompt bytes = 955
stderr: --scope-anchor-file must resolve under an allowed local workspace or tmpdir
ballot-pointer: MISSING
```

Regression from #3511 ("Anchor design plan review to staged issue scope"), which added `--scope-anchor-file` to the voter dispatch without extending the allowlist to the session-tmpdir location.

## Impact

Silent degradation of **every** `/design` plan-review voting panel since #3511 whenever `DESIGN_TMPDIR` is under `~/.cache` (the default): Claude and Codex voters get a content-stripped prompt and never really vote; the panel limps on Cursor's agentic recovery alone and collapses to `panel-failed` whenever Cursor also stumbles — silently dropping all findings or forcing main-agent adjudication.

## Scope — both voter dispatchers (plan-review active, code-review latent)

The truncating early-exit lives in the **shared** `render-voter-prompt.sh`, so the fix belongs there, and **both** dispatchers must be hardened:

- **`/design` plan-review — actively broken.** `scripts/dispatch-plan-voters.sh` passes `--scope-anchor-file` under `~/.cache` → truncation on essentially every run.
- **`/implement` Step 5 + `/review --diff` code-review — latently exposed.** `scripts/dispatch-code-voters.sh` renders with `--verification-context code` and does **not** currently pass `--scope-anchor-file` (its usage does not even accept one), so it is **not broken today**. But it shares the **identical unchecked-exit pattern** (`render-voter-prompt.sh … > "$prompt_file"` with no `$?` check). The day code-review anchors to issue scope (a natural mirror of #3511), it hits the **same silent truncation**. Harden it now as defense-in-depth.

## Fix

1. `render-voter-prompt.sh` `validate_scope_anchor_file`: accept the ballot's own directory / session root (validate the anchor resolves under `dirname(--ballot-file)`, or add a `--session-root` parameter) instead of a hardcoded path allowlist — auto-covers `~/.cache/larch/sessions/`, `IMPLEMENT_TMPDIR`, `REVIEW_TMPDIR`.
2. `render-voter-prompt.sh`: make scope-anchor validation **non-fatal** — on an invalid/oversized anchor, warn to stderr and **skip the anchor block but still emit the ballot pointer + output grammar**. (This also covers the `--scope-anchor-file is only valid with --verification-context plan` early-exit, which truncates the same way.)
3. `scripts/dispatch-plan-voters.sh` `make_prompt_file`: capture and **check** `render-voter-prompt.sh`'s exit code; abort loudly on non-zero, and assert the rendered prompt contains `Read the ballot from this path` before launching any voter.
4. `scripts/dispatch-code-voters.sh` `make_voter_prompt_file`: apply the **same** exit-code check + post-render ballot-pointer assertion (defense-in-depth; future-proofs the code-review path so it can never regress the way plan-review did).

## Verified (not part of the bug)

File-by-reference transport is sound: with a complete prompt, Claude, Codex, and Cursor each read the by-reference ballot and produce votes (confirmed by direct launches, both `plan` and `code` grammar). The ballot must stay by-reference (size-safe); this fix is purely about keeping the prompt intact.

## Acceptance

- A voter prompt rendered with a scope-anchor under `~/.cache/larch/sessions/<run>/` exits 0 and contains both the ballot-pointer line and the `FINDING_N: YES|NO|EXONERATE` grammar.
- **Both** `dispatch-plan-voters.sh` and `dispatch-code-voters.sh` fail loudly (non-zero) if `render-voter-prompt.sh` errors, instead of emitting a truncated prompt.
- `make lint` green.


## Test plan
(no test plan section in plan-file)
