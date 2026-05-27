## Plan

# Plan — fix Bash 3.2 nounset hazard in render-final-summary.sh

## Files to modify/create

### UPDATED: `skills/design/scripts/render-final-summary.sh`

Apply the `${arr[@]+"${arr[@]}"}` safe-empty idiom to the three empty-prone array expansions inside `invoke_render`:

- **Line ~304** (`render_cost_args=("${COST_ARGS[@]}")`): change to `render_cost_args=(${COST_ARGS[@]+"${COST_ARGS[@]}"})`. Defense-in-depth — control flow currently guarantees `COST_ARGS` is populated whenever this line fires (the `_cost_unavailable=true` branch takes the other arm), but a uniform rule across all three sites lets the static-grep harness pin one idiom for the whole `invoke_render` body.
- **Line ~338** (`"$PLUGIN_ROOT/scripts/render-run-summary.sh" "${_rr_args[@]}" "${render_cost_args[@]}" "${note_args[@]}"`): change `"${render_cost_args[@]}"` to `${render_cost_args[@]+"${render_cost_args[@]}"}` and `"${note_args[@]}"` to `${note_args[@]+"${note_args[@]}"}`. `_rr_args` is always populated (no guard needed).
- Add one comment line immediately above line 338 explaining the idiom and pointing at `BASH_AUTHORING.md §3`. No other edits.

Lines 119, 298, 300, 311, 313 (the `=()` declarations and re-assignments themselves) do NOT change — the bug lives at the expansion, not the declaration.

No reformatting, no unrelated cleanup.

### NEW: `scripts/test-render-final-summary-bash32.sh`

Mirror the structure of `scripts/test-collect-agent-bash32.sh` (the precedent named in the issue):

- **Header comment**: name the hazard (`note_args[@]: unbound variable` on Bash 3.2), reference issue #3039, link `BASH_AUTHORING.md §3`, document the Case 1 / Case 2 layering.
- **`set -uo pipefail`** (mirror precedent — `set -e` deliberately omitted so individual case failures still produce a final summary line).
- **Globals**: `REPO_ROOT`, `SUBJECT="$REPO_ROOT/skills/design/scripts/render-final-summary.sh"`, `PASS=0`, `FAIL=0`, `SKIP=0`, `FAILED=()`, `TMPROOT=$(mktemp -d ...)` with `trap rm -rf EXIT`.
- **Case 1 (static idiom check, always runs)**: exactly **two** `grep` calls wired with `&&`, using literal regex patterns:
  1. `grep -q 'render_cost_args=(\${COST_ARGS\[@\]+"\${COST_ARGS\[@\]}"})' "$SUBJECT"` — pins the guarded `COST_ARGS` copy at the line ~304 site.
  2. `grep -q '"\${_rr_args\[@\]}" \${render_cost_args\[@\]+"\${render_cost_args\[@\]}"} \${note_args\[@\]+"\${note_args\[@\]}"}' "$SUBJECT"` — pins the `render-run-summary.sh` invocation line at line ~338 with **both** `render_cost_args[@]+` and `note_args[@]+` guards in the same line. Both `\${` escapes and `\[@\]` escapes are intentional to keep the dollar/bracket characters literal in the grep regex; the regex matches any literal whitespace between tokens by adopting the same single-space separator the source line uses.
  Two greps wired with `&&` — the test PASSes only when both sites are guarded. Backstop on CI under bash 5.x.
- **Case 2 (dynamic empty-array path, only under /bin/bash < 4.4)**: detect the bash version of `/bin/bash` (mirror the version-extract pattern from `test-collect-agent-bash32.sh` Cases 2/3). Skip-with-loud-message on ≥4.4. On vulnerable versions:
  - Build a minimal fixture `$DESIGN_TMPDIR` (same shape as `skills/design/scripts/test-render-final-summary.sh`: `run-params.json` with `classification:SIMPLE`, `voting-tally.md`, `accepted-plan-findings.md`, `oos-accepted-design.md`, `execution-issues.md`, `oos-issues-created.md`).
  - **Hermetic env**: invoke the SUBJECT with `ISSUE_NUMBER=""` and a fake test `SESSION_ID="TEST-BASH32-FIXTURE"`, plus explicit `DESIGN_TMPDIR="$D"` and `CLAUDE_PLUGIN_ROOT="$REPO_ROOT"`, so `--post-publish-only` cannot trigger `tracking-issue-summary.sh upsert-summary` (issue-bound publishing requires non-empty `ISSUE_NUMBER`).
  - Invoke `/bin/bash "$SUBJECT" --outcome approved --mode SIMPLE --post-publish-only` capturing rc, harness stdout, and harness stderr.
  - Assert **all four**:
    1. `rc == 0`.
    2. `final-summary.md` exists and is non-empty.
    3. **Primary regression assertion**: `! grep -q 'unbound variable' "$D/render-final-summary.stderr.log"` — `invoke_render` redirects `render-run-summary.sh` stderr into this file (see `render-final-summary.sh` around the `append_render_warning` site); a bash 3.2 nounset failure surfaces here, **not** in the outer harness stderr. The compose-self-fallback path can still write `final-summary.md` with rc=0 even when `invoke_render` failed, so this grep is the only reliable witness.
    4. `! grep -q 'render-run-summary' "$D/execution-issues.md"` — the `append_render_warning` site writes a `Warnings` entry under that tool name when `invoke_render` fails, so the absence of that entry confirms the fallback did not fire.
  - Mirror precedent's `ok` / `fail` / `skipm` accounting and final summary line.

### NEW: `scripts/test-render-final-summary-bash32.md`

Sibling stub per `.claude/rules/script-md-siblings.md`. Names the primary (`scripts/test-render-final-summary-bash32.sh`), the SUBJECT it tests (`skills/design/scripts/render-final-summary.sh`), the issue (#3039), the Makefile registration target (`test-harnesses-14`), the agent-lint exclude entry, and the two-case layering rationale. Short — ~25-35 lines.

### UPDATED: `agent-lint.toml`

Add `scripts/test-render-final-summary-bash32.sh` (and the `.md` sibling stub, only if the existing `test-collect-agent-bash32.sh` precedent already lists its sibling `.md`) to the lint exclude array near the existing `scripts/test-collect-agent-bash32.sh` entry. Comment: `# issue #3039: Makefile-only harness wired via test-render-final-summary-bash32` mirroring the comment shape on the precedent entry. The exclude prevents `make lint` from flagging the harness as a dead/unreachable script because `agent-lint` does not follow Makefile target reachability.

### UPDATED: `Makefile`

- Add `test-render-final-summary-bash32` to the leading `.PHONY:` list (line 4).
- Wire it into `test-harnesses-14` (the shard that hosts `test-collect-agent-bash32`, the topical cousin and closest bash32-portability sibling). Shard 12 has more entries than shard 14 today, so placing the new harness in `-14` preserves the documented equal-count balance.
- Add the target rule after the existing `test-render-final-summary` rule (line ~468):

  ```make
  test-render-final-summary-bash32:
  	bash scripts/harness-timer.sh $@ bash scripts/test-render-final-summary-bash32.sh
  ```

## Approach

Surgical fix at the failing expansions + parallel regression harness mirroring the established precedent at `scripts/test-collect-agent-bash32.sh` (which covered the same class of bug for `scripts/collect-agent-results.sh` under issue #511).

The safe-empty idiom `${arr[@]+"${arr[@]}"}` uses Bash's `+altvalue` parameter expansion: when `arr` is set (even empty), it expands to the alt-value (the bare `"${arr[@]}"`); when unset, it expands to nothing. Under Bash 3.2 + `set -u`, treating an empty array as "unset" at expansion time is the bug — the idiom side-steps the issue by gating on the array's set-ness instead of its element count. Bash 4.4+ already fixed the underlying nounset hazard, so the idiom is a no-op there. This matches the BASH_AUTHORING.md §3 portability discipline and the precedent at `scripts/create-pr.sh:105`, `scripts/compose-review-findings.sh`, `scripts/launch-codex-ci.sh`, and `scripts/launch-claude-review.sh`.

`scripts/render-run-summary.sh` and `scripts/render-cost-line.sh` were inspected during Step 1d and are hazard-free: their `*_args` arrays are always populated inline on creation. No edits to either file.

## Edge cases

- **Bash version detection for Case 2**: the macOS system `/bin/bash` is 3.2.57. CI runners use bash 5.x where the bug does not manifest at runtime. Case 2 MUST loud-skip on ≥4.4 with a `SKIPPED` log line so a missed-skip in CI surfaces; PASS on 3.x with rc/stderr assertion all green.
- **`invoke_render` stderr is redirected**: the SUBJECT calls `render-run-summary.sh` from `invoke_render` (in `skills/design/scripts/render-final-summary.sh`); that subshell's stderr is captured into `$DESIGN_TMPDIR/render-final-summary.stderr.log` (see `append_render_warning`), NOT propagated to the outer harness stderr. Case 2 MUST grep that redirected log file — the outer harness stderr cannot witness the nounset failure.
- **`compose_self_fallback` can mask the bug**: when `invoke_render` fails, the SUBJECT falls back to `compose_self_fallback` which writes a degraded `final-summary.md` with rc=0 anyway. A rc=0 + non-empty `final-summary.md` assertion is therefore insufficient to prove the bug was avoided; the redirected-stderr grep is the only reliable witness. Case 2 layers all four assertions for redundancy.
- **Issue-bound publishing**: `render-final-summary.sh --post-publish-only` calls `tracking-issue-summary.sh upsert-summary` when `ISSUE_NUMBER` is non-empty and `gh` is available. Case 2 sets `ISSUE_NUMBER=""` explicitly so the test cannot mutate any GitHub issue from a developer's environment.
- **Fixture parity with existing harness**: the fixture must include every artifact `render-final-summary.sh` reads (`run-params.json`, `voting-tally.md`, `accepted-plan-findings.md`, `oos-accepted-design.md`, `execution-issues.md`, `oos-issues-created.md`). Use the same shape as `skills/design/scripts/test-render-final-summary.sh` so the fixture stays a known-good shape.
- **Stderr not empty**: the SUBJECT emits diagnostic lines on success (e.g., timing/token marks). The outer-harness stderr assertion is *not* "stderr is empty" — Case 2 checks the redirected `render-final-summary.stderr.log` for `unbound variable`.
- **`set -euo pipefail` line 3 preservation**: the safe-empty idiom does NOT require relaxing nounset; the fix preserves the existing strict-mode contract.
- **`COST_ARGS` guard is defense-in-depth**: line 304 fires only inside the `else` arm of `if [ "$_cost_unavailable" = true ]`, which means lines 156 or 162 already populated `COST_ARGS`. Adding the guard there does not change behavior; it only prevents future control-flow drift from re-introducing the bug.
- **`agent-lint` reachability**: agent-lint does not follow Makefile target reachability, so any new test-only harness needs an explicit `agent-lint.toml` exclude (precedent: `scripts/test-collect-agent-bash32.sh`).

## Failure modes

1. **Static-grep pin too loose (partial fix passes Case 1)** — if Case 1 only checks one site, a future edit could regress one expansion silently. **Earliest signal**: Case 2 fails on macOS dev loop. **Mitigation**: Case 1 uses exactly **two** literal-regex `grep` calls wired with `&&` so both guarded sites are pinned together; the test fails until every site is intact.
2. **Bash version detection mis-skip** — if `/bin/bash --version` parsing breaks (e.g., on a host without `/bin/bash`), Case 2 silently SKIPs and the regression goes uncaught locally. **Earliest signal**: CI never sees the skip because CI runs bash 5, so manual macOS test loop is the only consumer. **Mitigation**: print `SKIPPED: case 2 (bash <version> >= 4.4)` loudly; mirror the precedent's loud-skip line exactly so macOS developers notice the SKIPPED log on every `make lint` run.
3. **Byte-format regression in `final-summary.md`** — the safe-empty idiom should be a no-op when arrays are non-empty, but a typo could change argv passed to `render-run-summary.sh`. **Earliest signal**: the existing `skills/design/scripts/test-render-final-summary.sh` harness includes `cmp -s "$D/final-summary.md" "$std"` (byte-identical between stdout and file output) which fires on argv changes that shift output. **Mitigation**: re-run `make test-render-final-summary` after the patch before committing.
4. **Case 2 grep targets the wrong surface** — if Case 2 only checks the outer harness stderr, the `compose_self_fallback` path can mask a still-broken `invoke_render` (rc=0, final-summary.md present, but the nounset failure happened invisibly). **Earliest signal**: a regressed `invoke_render` ships and Step 5c's published `larch:final-summary` comment is the degraded fallback body instead of the rich render. **Mitigation**: Case 2's primary assertion is `! grep -q 'unbound variable' "$D/render-final-summary.stderr.log"`; the rc/non-empty checks are secondary corroboration.
5. **Test mutates GitHub from a developer's environment** — if `ISSUE_NUMBER` leaks through from the developer's shell, `--post-publish-only` calls `tracking-issue-summary.sh upsert-summary` and posts to a real issue. **Earliest signal**: a developer notices an unexpected comment on a tracking issue. **Mitigation**: Case 2 explicitly sets `ISSUE_NUMBER=""` and a fake `SESSION_ID` in the invocation env block.

## Testing strategy

- **New**: `scripts/test-render-final-summary-bash32.sh` (Case 1 static + Case 2 dynamic, with redirected-stderr witness assertion and hermetic env), wired into `make lint` via `test-harnesses-14` (shard-balance choice; `test-collect-agent-bash32` cluster).
- **Existing, must continue passing**: `skills/design/scripts/test-render-final-summary.sh` — byte-identical `final-summary.md` body assertion catches argv regressions from the patch.
- **`agent-lint` updated**: `agent-lint.toml` exclude entry prevents `make lint` from failing on the new harness as an unreachable script.
- **`make lint`**: full pre-commit + harness suite. Both new harness and existing harness run.
- **Manual local sanity (macOS Bash 3.2.57)**: `bash scripts/test-render-final-summary-bash32.sh` — expect PASS Case 1, PASS Case 2.
- **Manual local sanity (Bash 5)**: same harness — expect PASS Case 1, SKIPPED Case 2 with loud log line.


## Acceptance

- `make lint` passes locally on macOS Bash 3.2.57 and on Linux CI (Bash 5).
- `bash scripts/test-render-final-summary-bash32.sh` PASS Case 1 + PASS Case 2 on macOS; PASS Case 1 + SKIPPED Case 2 on Linux CI.
- `bash skills/design/scripts/test-render-final-summary.sh` continues passing unchanged (byte-identical assertion).
- `skills/design/scripts/render-final-summary.sh` invocation at line 338 expands `${render_cost_args[@]+...}` and `${note_args[@]+...}` (and line 304 expands `${COST_ARGS[@]+...}`).
- `agent-lint.toml` lists `scripts/test-render-final-summary-bash32.sh` in the exclude array near the existing `test-collect-agent-bash32.sh` entry.
- A subsequent `/design` or `/implement` run on macOS produces a non-empty `final-summary.md` and renders the rigid `larch:final-summary` block on the tracking issue after Step 5c publish.

diff_lines: 160
