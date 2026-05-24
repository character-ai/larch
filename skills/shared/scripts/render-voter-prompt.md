# render-voter-prompt.sh

## Purpose

Emit the full body of the external judge voter prompt (stdout) for `/design` plan-review voters and `/review` code-review voters. Centralizes duplicated prose so OOS problem-vs-solution instructions and verification rules stay aligned.

## Primary callers

- `scripts/dispatch-plan-voters.sh` — `make_prompt_file()` (`--id-grammar finding-oos`, `--verification-context plan`).
- `scripts/dispatch-code-voters.sh` — `make_voter_prompt_file()` (`--id-grammar finding-only`, `--verification-context diff-plan`).

## Flags

| Flag | Values | Meaning |
|------|--------|--------|
| `--ballot-file` | path | Ballot path printed into the prompt (read-only contract). |
| `--panel-role` | free-form string | Text after the literal prefix `You are a` plus a space — the script prints `You are a {role}.` Callers pass trusted literals. |
| `--id-grammar` | `finding-oos` \| `finding-only` | Selects OOS clause wording and whether `OOS_N:` example lines are included (`finding-oos` only). |
| `--verification-context` | `plan` \| `diff-plan` | `plan` keeps the silent plan/repo inspection allowance; `diff-plan` adds diff/plan bounded file reads. |

Exit `0` on success, `2` on usage / validation errors.

## Output contract

- Writes the entire prompt to **stdout** only (no stderr payload on success).
- Preserves markdown emphasis markers (`**`, `` ` ``, `*`) expected by downstream voters.

## lib-quiet divergence

This script **does not** call `larch_quiet_init` and **does not** source `scripts/lib-quiet.sh`. After `larch_quiet_init`, stdout is redirected for the quiet stream; sourcing it here would empty the prompt when the helper runs inside quiet-aware parents.

## Executable mode invariant

`render-voter-prompt.sh` must remain executable (`chmod +x`); dispatchers invoke it by path.

## Harness

`scripts/test-render-voter-prompt.sh` (see `scripts/test-render-voter-prompt.md`).

## Edit-in-sync rules

The canonical OOS problem-vs-solution clause exists in **six** logical places:

1. This helper — `finding-only` and `finding-oos` grammar variants (two strings).
2. `skills/shared/voting-protocol.md` — prose above the fenced voter template (`finding-only` lowest-common-denominator).
3. `skills/design/SKILL.md` — Step 3 main-agent vote-required paragraph (`finding-oos`).
4. `skills/implement/SKILL.md` — Step 5 MAV paragraph (`finding-only`, scoped to `[OUT_OF_SCOPE]` findings).
5. `skills/design/references/plan-review.md` — Voter 1 instruction (`finding-oos`).

The drift harness `case_canonical_text_drift_guard` greps a **shared substring** (identical tail of both grammar variants) across the four Markdown / SKILL locations (2–5). When you change OOS wording, update all six locations and run `make test-render-voter-prompt`.
