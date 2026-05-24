## Plan

Consolidate `/implement`'s **Rebase Checkpoint Macro** (4 mid-run sites: `1.r`, `4.r`, `7.r`, `7a.r`) and **Phantom Untracked Probe** (5 sites: `2-post-dispatch`, `4.r-post-rebase`, `7.r-post-rebase`, `7a.r-post-rebase`, `8-pre-bump`) into two new wrapper scripts plus a shared library helper. Per-run effect: ~6-12 mid-run Bash calls collapse to **6 total** (4 combined + 2 standalone) — ~6 calls saved per `/implement` run.

This plan reflects the dialectic-resolved DECISION_1 (library-based reuse via `scripts/lib-phantom-probe.sh`; voted 2-1) plus 12 accepted plan-review findings (FINDING_1, _2, _3, _4, _5, _6, _7, _8, _9, _10, _12, _16). 7 findings were exonerated as disproportionate to ship (FINDING_11, _13, _14, _15, _17, _18, _19) and recorded in the unimplemented-suggestions log. OOS_1 (topology.tsv regeneration concern) was neutral 1Y/1N/1E and is not filed.

### Files to modify/create

**NEW (10 files):**
- `scripts/lib-phantom-probe.sh` — sourced-only library; `phantom_probe_with_warn` shell function; `LARCH_LIB_PHANTOM_PROBE_LOADED=1` idempotency guard; emits phantom KVs through caller's already-initialized FD-3 quiet stream; parses `append-execution-issue.sh` ERROR via combined stdout+stderr capture, `ERROR=` line first then stderr fallback (FINDING_1); newline-folds `PHANTOM_APPEND_WARN_ERROR` before emit.
- `scripts/lib-phantom-probe.md` — sibling per `script-md-siblings`; documents the stdout-first/stderr-fallback parsing contract.
- `scripts/rebase-checkpoint-probe.sh` — combined wrapper. Argv: `<step-prefix> <short-name> [--base-remote <name>] [--base-ref <branch>]`. `SCRIPT_DIR`-relative helper resolution (FINDING_8); `set -euo pipefail`; sources `lib-quiet.sh` + `lib-phantom-probe.sh`; one `emit_breadcrumb '→ rebase-probe: <step-prefix> <short-name>'`; invokes `rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict [base args]`; captures stdout (lib-quiet contract stream) + stderr separately; branches on rc:
  - rc=0: parses `SKIPPED_ALREADY_PUSHED` BEFORE `SKIPPED_ALREADY_FRESH` (precedence preserved); emits `REBASE_OUTCOME=ok|skipped`; calls `phantom_probe_with_warn` for the post-rebase phantom probe (including new `1.r-post-rebase` uniform site).
  - rc=1 (conflict): parses `CONFLICT_FILES=<list>` from contract stream (FINDING_1); defensive `git diff --name-only --diff-filter=U` fallback when missing; emits `REBASE_OUTCOME=conflict` + `CONFLICT_FILES`; does NOT run phantom probe; exits 1.
  - rc=3 (non-conflict failure): parses `REBASE_ERROR` from contract stream first (FINDING_1), stderr fallback; emits `REBASE_OUTCOME=failed` + sanitized `REBASE_ERROR`; exits 3.
  - other rc: emits `REBASE_OUTCOME=failed` + `REBASE_ERROR=unexpected-rc-<n>` (FINDING_9 prefix discriminator); exits `$rc`.
  Wrapper does NOT set `STALL_TRACKING`; orchestrator parses `REBASE_OUTCOME` and sets it. `chmod +x` required (FINDING_10).
- `scripts/rebase-checkpoint-probe.md` — sibling; argv, exit codes, full KV grammar, FINDING_1 channel rules, FINDING_8 SCRIPT_DIR note, FINDING_9 unexpected-rc prefix rule, FINDING_10 chmod note.
- `scripts/phantom-probe-with-warn.sh` — standalone wrapper for `2-post-dispatch` and `8-pre-bump`. Argv: `--step <step-token>`. Same `SCRIPT_DIR`-relative pattern; one `emit_breadcrumb '→ phantom-probe: <step-token>'`; calls `phantom_probe_with_warn`; always exits 0 (phantom is advisory). `chmod +x` required.
- `scripts/phantom-probe-with-warn.md` — sibling; argv, KV grammar, advisory-exit-0 note.
- `scripts/test-rebase-checkpoint-probe.sh` — offline harness (per discussion-round1 Decision 2 — separate from standalone-wrapper harness). **Stubbing strategy** (FINDING_8): copies production scripts + libs into per-test-case temp directory with stub sibling helpers in the same dir; wrapper's `SCRIPT_DIR` picks up stubs naturally; no PATH injection. Exports `LARCH_QUIET_BREADCRUMBS=1` in harness env so breadcrumb-count assertions are independent of SKILL.md call-site exports. **17 cases**: green path, SKIPPED_ALREADY_PUSHED precedence, SKIPPED_ALREADY_FRESH, conflict, conflict+defensive fallback, rc=3 contract-stream parsing (FINDING_1), rc=3 stderr fallback, unexpected rc, phantom STATUS variants (clean/tracked-only/phantom/unknown), append failure contract-stream parsing, append failure stderr fallback, `--base-remote`/`--base-ref` pass-through, regex rejection, breadcrumb count, library idempotency, chmod +x assertion.
- `scripts/test-rebase-checkpoint-probe.md` — sibling; cases, SCRIPT_DIR-temp-dir stubbing strategy, breadcrumb export note.
- `scripts/test-phantom-probe-with-warn.sh` — offline harness for the standalone wrapper. Same SCRIPT_DIR-temp-dir stubbing. **10 cases**: STATUS variants (clean/tracked-only/phantom/unknown), append failure contract-stream + stderr fallback, breadcrumb count, bad-step surfacing, chmod +x assertion.
- `scripts/test-phantom-probe-with-warn.md` — sibling.

**UPDATED (6 files):**
- `skills/implement/SKILL.md` — three edit regions:
  - **Region 1** (Rebase Checkpoint Macro section, current L119-156): delete the entire M1/M2/M3 procedure body; replace with thin pointer + Call-site registry table + orchestrator-side M2 routing prose distinguishing the two `REBASE_OUTCOME=failed` branches (FINDING_9 — `unexpected-rc-<n>` prefix → "failed unexpectedly" string; otherwise → "failed (non-conflict)" string). Then replace each of the 4 macro call-site invocations (Steps 1.r/4.r/7.r/7a.r) with a foreground-marked Bash fence containing `export LARCH_QUIET_BREADCRUMBS=1` (FINDING_12), conditional `BASE_ARGS=()` shell (FINDING_5 — real conditional, not bracket placeholder) with forked-target argv at ALL 4 sites (FINDING_4 — not just 1.r), and the canonical `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh" <step-prefix> '<short-name>' "${BASE_ARGS[@]+"${BASE_ARGS[@]}"}"` line. Step 7.r fence stays inside the existing `if [ "$FILES_CHANGED" = "true" ]` guard.
  - **Region 2** (Phantom Untracked Probe section, current L448-513): delete full call-form/parse/warning-block body; replace with thin pointer that says "**6 sites total**" (FINDING_16 — 4 combined absorbed + 2 standalone, including new uniform `1.r-post-rebase`). Then replace the 2 standalone-probe call-site inline blocks (Step 2 post-dispatch around L1059; Step 8 pre-bump) with foreground-marked fences invoking `phantom-probe-with-warn.sh --step <step-token>` with `export LARCH_QUIET_BREADCRUMBS=1`.
  - **Region 3** (FINDING_3): explicitly delete the "After the macro returns, run the Phantom Untracked Probe" paragraphs at Steps 4.r/7.r/7a.r (skills/implement/SKILL.md:1178-1179, 1370-1373, 1464-1465). The combined wrapper now owns those probes; leaving the prose would double-invoke `check-phantom-dirty.sh`.
- `scripts/lint-foreground-markers.sh` — append `rebase-checkpoint-probe.sh` and `phantom-probe-with-warn.sh` to the DENYLIST heredoc.
- `scripts/test-implement-rebase-macro.sh` — pivot from literal-string assertions in SKILL.md macro body to wrapper-invocation pins:
  - (A), (B), (F), (I): unchanged.
  - (C): assert `"${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh"` invocation appears exactly 4 times in SKILL.md with the canonical `<step-prefix>` / `<short-name>` pairs.
  - (C') new sub-assertion (FINDING_4): assert `if [ "${forked_target:-false}" = "true" ]` / `BASE_ARGS=(--base-remote upstream --base-ref main)` conditional appears within 10 lines above all 4 wrapper invocation lines (forked argv at all 4 sites).
  - (E) retargeted (FINDING_2): anchor changes from legacy `Apply the Rebase Checkpoint Macro` 7.r prose to the new `rebase-checkpoint-probe.sh 7.r 'commit (review)'` invocation line; still inside the `FILES_CHANGED=true` block.
  - (G): assert thin-pointer macro section contains `scripts/rebase-checkpoint-probe.sh`, `caller_kind=early_rebase`, **both** FINDING_9 bail strings (non-conflict + unexpected-exit), and (FINDING_3) zero occurrences of `After the macro returns, run the Phantom Untracked Probe` anywhere in SKILL.md.
  - (H): pivot literal `rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict` count from "exactly 1 in SKILL.md" to "exactly 1 in scripts/rebase-checkpoint-probe.sh" + "zero in SKILL.md".
  - (J) new (FINDING_3): assert exactly 2 standalone phantom-probe invocations in SKILL.md (`--step 2-post-dispatch` and `--step 8-pre-bump`), each inside a foreground-marked fence; combined with the (G) anti-FINDING_3 grep, the two-site count is pinned.
- `Makefile` — append `test-rebase-checkpoint-probe` and `test-phantom-probe-with-warn` to the `.PHONY` list; add their two recipes (`bash scripts/test-*.sh` — FINDING_15 exonerated, no harness-timer wrapper); append each as a prerequisite of exactly one `test-harnesses-N` shard (FINDING_6 — confirmed via `bash scripts/test-harness-shards-coverage.sh`); do NOT add a top-level `make test` aggregate (repo has none).
- `agent-lint.toml` (FINDING_7) — add allowlist entries (with comments) for `scripts/lib-phantom-probe.sh`, `scripts/lib-phantom-probe.md`, `scripts/test-rebase-checkpoint-probe.sh`, `scripts/test-rebase-checkpoint-probe.md`, `scripts/test-phantom-probe-with-warn.sh`, `scripts/test-phantom-probe-with-warn.md` — matching the existing `lib-dirty-tree-sidecar` / `test-implement-rebase-macro` peer pattern.
- `docs/linting.md` — two new bullets documenting `make test-rebase-checkpoint-probe` and `make test-phantom-probe-with-warn` alongside the existing `make test-implement-rebase-macro` entry.

### Architecture diagram

See `architecture-diagram.md` for a mermaid `graph TD` showing the 6 SKILL.md call sites, the 2 new wrappers, the new shared library, and the existing helpers / lib-quiet dependency. Validated by `scripts/sanitize-mermaid-fragment.sh` (STATUS=ok).

### Edge cases

- KV ordering: `SKIPPED_ALREADY_PUSHED` BEFORE `SKIPPED_ALREADY_FRESH` (test case 2 pins).
- `CONFLICT_FILES` missing on rc=1: defensive `git diff` fallback (test case 5).
- `REBASE_ERROR` / `append-execution-issue.sh ERROR` channel (FINDING_1): contract-stream first, stderr fallback (test cases 6/6b and 11/11b).
- Forked-target argv (FINDING_4): caller passes at all 4 sites via `BASE_ARGS=()`; wrapper does not detect forked state.
- Wrapper exits 0 even on `append-execution-issue.sh` failure (advisory KV surface).
- `chmod +x` required on `rebase-checkpoint-probe.sh` + `phantom-probe-with-warn.sh` (FINDING_10).
- 6 sites total in SKILL.md phantom-probe pointer (FINDING_16).
- Bash 3.2 portable throughout (no `declare -A`, no namerefs, no `mapfile`, no `${var^^}`/`${var,,}`, no `&>>`).

### Failure modes

1. **KV-ordering regression**: signal = test case 2 fails.
2. **Conflict-path regression** (wrapper accidentally invoking phantom probe on rc=1): signal = test case 4 fails.
3. **Wrong-channel parsing regression** (FINDING_1 reverted): signal = test cases 6 + 11 fail.

### Testing strategy

1. `scripts/test-rebase-checkpoint-probe.sh` — 17 cases.
2. `scripts/test-phantom-probe-with-warn.sh` — 10 cases.
3. `scripts/test-implement-rebase-macro.sh` — pivoted invariants C/E/G/H/J + new C'.
4. `make lint` — lint-foreground-markers (new DENYLIST entries), lint-bash32, agent-lint G004 / script-md-siblings (now allowlisted), all test-harnesses shards (FINDING_6).
5. `make test-harness-shards-coverage` — verifies both new targets are wired into exactly one shard each AND listed in `.PHONY`.
6. End-to-end `/implement <issue>` clean-run (operator-driven validation per FINDING_11 exonerate-with-rationale): record baseline mid-run Bash call count pre-consolidation, run `/implement` post-consolidation, capture delta in PR description. ~6 fewer calls expected.

## Acceptance

- New `scripts/rebase-checkpoint-probe.sh` exists and absorbs M1 (rebase-push.sh) + M2 (rc branching) + M3 (KV emit) + post-rebase phantom probe + conditional warn appends.
- New `scripts/phantom-probe-with-warn.sh` exists and absorbs standalone phantom probe + conditional warn appends.
- New `scripts/lib-phantom-probe.sh` exists as sourced-only library; both wrappers source it and call the `phantom_probe_with_warn` shell function (dialectic DECISION_1 binding).
- Sibling `.md` files document argv, output KV grammar, exit codes, the FINDING_1 stdout-first / stderr-fallback contract for parsing helper error KVs, and the SCRIPT_DIR-relative helper resolution pattern.
- Test harness `scripts/test-rebase-checkpoint-probe.sh` covers all 17 enumerated cases: green path, SKIPPED_ALREADY_PUSHED precedence, SKIPPED_ALREADY_FRESH, rebase conflict + defensive `git diff` fallback, rc=3 contract-stream + stderr-fallback parsing, unexpected rc, phantom STATUS variants (clean/tracked-only/phantom/unknown), append-execution-issue.sh failure contract-stream + stderr-fallback parsing, argv pass-through, regex rejection, breadcrumb count, library idempotency, chmod +x assertion.
- Test harness `scripts/test-phantom-probe-with-warn.sh` covers all 10 enumerated cases (parallel structure to the combined-wrapper harness).
- `skills/implement/SKILL.md` Rebase Macro section is reduced to a thin pointer (with the orchestrator-side M2 routing prose retained, including both FINDING_9 bail strings — non-conflict and unexpected-exit branches). The 4 macro call sites use foreground-marked `rebase-checkpoint-probe.sh` invocations with `export LARCH_QUIET_BREADCRUMBS=1`, real conditional `BASE_ARGS=()` shell (FINDING_5), and forked-target argv at all 4 sites (FINDING_4). The 2 standalone phantom-probe sites use foreground-marked `phantom-probe-with-warn.sh` invocations.
- The existing "After the macro returns, run the Phantom Untracked Probe" paragraphs at Steps 4.r, 7.r, and 7a.r in SKILL.md are explicitly deleted (FINDING_3) so the combined wrapper does not double-invoke `check-phantom-dirty.sh`.
- The SKILL.md phantom-probe pointer says "**6 sites total**" (FINDING_16 — 4 combined absorbed + 2 standalone, including the new uniform 1.r-post-rebase site).
- `make lint` passes: `lint-foreground-markers` (new DENYLIST entries for both wrappers), `lint-bash32` (new shell files Bash 3.2 portable), `agent-lint` G004 / `script-md-siblings` (new lib-/test-/.md files allowlisted in `agent-lint.toml` per FINDING_7), and all `test-harnesses-N` shards including the two new shard prerequisites (FINDING_6 — verified via `bash scripts/test-harness-shards-coverage.sh`).
- `scripts/test-implement-rebase-macro.sh` is extended: invariants A/B/F/I unchanged; C asserts 4 canonical `rebase-checkpoint-probe.sh` invocations; C' (new) asserts forked-target conditional `BASE_ARGS=()` shell appears within 10 lines above all 4 wrapper invocations (FINDING_4); E is retargeted to the new 7.r wrapper invocation line (FINDING_2); G asserts the thin-pointer macro section plus zero "After the macro returns" prose anywhere in SKILL.md (FINDING_3 anti-pattern guard); H pivots the literal `rebase-push.sh --no-push --skip-if-pushed --keep-on-conflict` count (exactly 1 in `rebase-checkpoint-probe.sh`, zero in SKILL.md); J (new) asserts exactly 2 standalone phantom-probe invocations in SKILL.md.
- Both runtime wrappers (`rebase-checkpoint-probe.sh`, `phantom-probe-with-warn.sh`) have `chmod +x` mode (FINDING_10); each test harness asserts the executable bit at entry.
- An `/implement <issue>` clean-run transcript demonstrates reduced mid-run Bash call count (~6 fewer calls vs. the pre-consolidation baseline). Operator-driven validation per FINDING_11 exonerate-with-rationale: baseline captured in PR description.

diff_lines: 950
