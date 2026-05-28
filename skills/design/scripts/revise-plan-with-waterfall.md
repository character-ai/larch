# revise-plan-with-waterfall.sh

## Purpose

Between-round /design plan revision driver. It is a standalone library script for the Codex -> Cursor -> Claude revision waterfall; `skills/design/scripts/plan-review-loop.sh` is the intended primary caller in the next integration piece, and ad-hoc use is supported when `--plan-file` resolves to `$DESIGN_TMPDIR/plan.txt`.

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg, directory-exists, and input-readability checks, before `mkdir -p $REVISE_DIR`.

## Argv

| Flag | Required | Meaning |
| --- | --- | --- |
| `--design-tmpdir DIR` | yes | Session tmpdir. Outputs are written under `DIR/plan-review/round-<N>/revise/`. |
| `--plan-file FILE` | yes | The in-place plan to revise. It must canonically resolve to `$DESIGN_TMPDIR/plan.txt`, including the final `plan.txt` path component; mismatch exits 2. |
| `--findings-file FILE` | yes | Accepted in-scope plan-review findings for the current round. |
| `--feature-file FILE` | yes | Feature description context. |
| `--round-num N` | yes | Numeric round identifier for output paths. |
| `--codex-present true\|false` | yes | Availability snapshot for the Codex tier. |
| `--cursor-present true\|false` | yes | Availability snapshot for the Cursor tier. |
| `--timeout SECS` | no | Per-tier launcher timeout, default `1800`; forwarded to every launcher. |
| `--patch-format unified-diff\|file-replacement` | no | Candidate format, default `unified-diff`. |
| `--help` | no | Print usage and exit 0. |

Argv defects exit 2 with `larch_err`. Logical waterfall outcomes always exit 0 and are reported through KVs.

## Inputs

- `$DESIGN_TMPDIR/plan.txt`, also passed as `--plan-file`
- Accepted findings file
- Feature description file
- Design driver, defaulting to `skills/design/scripts/design-driver.sh` and overridable with `LARCH_TEST_DESIGN_DRIVER`
- Launchers, overridable with `LARCH_TEST_LAUNCH_CODEX_REVIEW`, `LARCH_TEST_LAUNCH_CURSOR_REVIEW`, and `LARCH_TEST_LAUNCH_CLAUDE_REVIEW`

## Outputs

Under `$DESIGN_TMPDIR/plan-review/round-<N>/revise/`:

- `prompt.txt`: composed revision prompt.
- `codex-output.txt`, `cursor-output.txt`, `claude-output.txt`: raw launcher output for attempted tiers.
- `<tier>-candidate.patch`: extracted candidate used for validation and apply.
- `<plan-file>.before-revise`: snapshot kept on overall failure, removed on success.

## KV Contract

KVs are emitted in this order on every logical invocation:

1. `REVISE_TIER_1_STATUS`: Codex status.
2. `REVISE_TIER_2_STATUS`: Cursor status.
3. `REVISE_TIER_3_STATUS`: Claude status.
4. `REVISE_STATUS`: `ok`, `failed-no-patch`, `failed-validation`, or `failed-apply`.
5. `REVISE_TIER`: winning tier name, or empty on failure.
6. `REVISE_PATCH_PATH`: winning raw output path, or empty on failure.
7. `REVISE_PLAN_HASH_BEFORE`: SHA-256 of the original plan.
8. `REVISE_PLAN_HASH_AFTER`: SHA-256 after a successful revision, or the original hash on failure.

Per-tier status values are `skipped-not-present`, `not-attempted`, `no-patch`, `invalid-patch`, `apply-failed`, `emit-plan-failed`, and `ok`. The ordinal mapping is part of the public contract: 1 is always Codex, 2 is always Cursor, and 3 is always Claude.

## Patch Validator

In `unified-diff` mode, the candidate may be raw diff text or wrapped in one outer ```diff fence. Header validation requires every file header path to be exactly `a/plan.txt` or `b/plan.txt`, and every `diff --git` header to be exactly `a/plan.txt b/plan.txt`. No other path form is accepted. The script then runs `git apply --check --whitespace=nowarn` from `dirname "$plan_file"` and classifies any failure there as `invalid-patch`; only a failing live `git apply --whitespace=nowarn` is reported as `apply-failed`. The script never uses `--unsafe-paths`.

In `file-replacement` mode, the candidate must be non-empty and its last non-blank line must be `diff_lines: <N>` with numeric `N`.

After either apply path, if the original plan had any `### NEW:`, `### UPDATED:`, or `### REWRITTEN:` headings, the revised plan must still have at least one such heading. The final structural gate is `ACTION=EMIT_PLAN` through the design driver. The script does not parse further plan semantics.

## Apply And Revert

The script snapshots the plan to `$plan_file.before-revise` before launching any tier. Validation, apply, heading-check, and emit-plan failures restore the plan from that snapshot before the next tier is attempted. Restore failures are fatal and stop the waterfall immediately rather than continuing on a partially mutated plan. The snapshot is removed only when one tier succeeds; on overall failure it remains for caller inspection.

## Invariants

- `--plan-file` must resolve to `$DESIGN_TMPDIR/plan.txt`, so the file revised by the waterfall is the same file validated by `ACTION=EMIT_PLAN`.
- `--prompt-file "$prompt_path"` is the sole prompt source for every tier. `--description-text` is never passed.
- Bash 3.2 portability: no associative arrays, namerefs, `mapfile`, `readarray`, `&>>`, or lowercase parameter expansion.
- If the input plan is already malformed, such as missing a `diff_lines: <N>` trailer, the emit-plan gate rejects candidate revisions; the script does not invent missing trailer data.
- Concurrent invocations against the same round directory are not supported; callers own single-runner serialization.

## Primary Callers

Planned caller: `skills/design/scripts/plan-review-loop.sh` in the next integration piece. Standalone operator calls are valid when they satisfy the canonical-plan invariant.

## Harness

Run `make test-revise-plan-with-waterfall`. The cross-tree harness is `scripts/test-revise-plan-with-waterfall.sh`, with a sibling stub at `scripts/test-revise-plan-with-waterfall.md`.
