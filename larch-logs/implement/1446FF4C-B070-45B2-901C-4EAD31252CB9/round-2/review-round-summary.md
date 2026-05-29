# Review Round 2

- Mode: `diff`
- 9 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: 1 MB staged-context hard cap aborts scout before tiers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: After removing the 256 KB input gate, `stage_context_file` still hard-fails above `MAX_STAGED_BYTES` (1 MB) with exit 2. Diffs between ~1 MB and prior limits (or above 1 MB after trim) hit `validation-failed` in dispatch-panel and yield zero dynamic reviewers instead of fail-open scouting—contradicting any-size / gate-removal acceptance for large PRs (~855 KB–900 KB class and beyond).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove or soften the hard cap (warn-only fail-open), or document and test the new ceiling explicitly
  - From cursor-specialist-correctness-output.txt: Align acceptance with 1MB cap or WARN-only above soft limit with fail-open empty manifest.
  - From cursor-specialist-testing-output.txt: Add regression tests for ~900 KB (ok) and >1 MB (documented behavior); align cap with acceptance (remove/raise) or fail-open instead of exit 2.
  - From cursor-specialist-edge-cases-output.txt: Drop cap or fail-open with explicit status; add >1 MB harness
  - From cursor-specialist-plan-fidelity-output.txt: Remove staged hard fail or align plan/acceptance; add >1 MB harness if a cap remains.


### FINDING_10: Multi-tier waterfall terminal statuses lack dedicated harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `codex-failed` / all-tiers-launcher-failure terminal paths and staged bulk >1 MB boundary lack dedicated CI cases; launcher-status and 1 MB policy regressions could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed LAUNCH_REVIEW_SH / LAUNCH_SH cases for codex launch fail and both tiers launch fail.
  - From cursor-specialist-plan-fidelity-output.txt: Add staged >1 MB accept/reject test per chosen policy.


### FINDING_11: `--read-tools` CLI reject paths untested in launch-claude-subprocess harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: New `--read-tools` / `--read-tools-add-dir` invalid combinations lack launcher-argv-test coverage; regressions may not be caught by `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert exit 2 for --read-tools-add-dir without --read-tools and for add-dir outside session root.


### FINDING_12: WARN when staged file exceeds 256 KB is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Large-but-under-1MB inputs may stop emitting operator-visible `WARN=staged` without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep SCOUT stdout for WARN=staged on large-diff and large description-file harness cases.


### FINDING_14: Codex scout tier `--add-dir` exposes full review tmpdir, not staged-context only
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: With `--codex-present true`, Codex gets `--add-dir` on `CANON_OUTPUT_DIR` (full review tmpdir), allowing reads of sibling launch env sidecars, prior scout raw, parse errors—broader than SECURITY.md staged-context-only model for Claude.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Narrow Codex --add-dir to staged-context (relocate tier raw output or add scout-specific add-dir flag).


### FINDING_17: `tier_raw_is_scout_json` can leak `.fenced-probe.*` temps on failed `cp`
- **Reviewer(s)**: dyn-temp-file-lifecycle-output.txt
- **Severity**: nit
- **Concern**: On empty `fenced_tmp` branch, `cp` failure removes only `probe_tmp` before return, leaving `${raw_path}.fenced-probe.*` under `$SESSION_ROOT`; repeated probe misses can accumulate; `cleanup_temps` does not cover probe artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-file-lifecycle-output.txt: On the empty-`fenced_tmp` `cp` failure path, remove both temps in the handler (e.g. `{ rm -f "$probe_tmp" "$fenced_tmp"; return 1; }`), matching the `cp "$fenced_tmp" "$probe_tmp"` branch at line 162; optionally add a single `rm -f "$fenced_tmp"` immediately before that `return 1` so every exit from the fenced branch clears `fenced_tmp`.


### FINDING_19: dispatch-panel dynamic tests invoke real Codex `launch-review.sh` when only Claude is stubbed
- **Reviewer(s)**: dyn-harness-codex-stub-gap-output.txt
- **Severity**: latent
- **Concern**: `dynamic4`, `dynamic8`, `dynamic-empty`, and `oversized-diff` use `--codex-available true` with only `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` stubbed; real Codex tier runs (preflight, lock, retries, 180s) before Claude stub wins—CI latency/flakiness risk and weak offline guard for large-diff panel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-codex-stub-gap-output.txt: Reuse the lightweight `codex_tier_stub` pattern from `scripts/test-scout-dynamic-archetypes.sh:532-563` and export `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` on these cases (and in `scout_wrapper` for `dynamic4`), matching the plan’s “stubbed launchers; no real Codex” testing strategy and `test-scout` waterfall cases at `565-627`.
  - From dyn-harness-codex-stub-gap-output.txt: Either set `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` to the shared `codex_tier_stub`, or use `--codex-available false` here so the case tests panel dispatch + large-diff staging without running the Codex waterfall.


### FINDING_2: Codex tier materializes/truncates description on argv; asymmetry, E2BIG, and dead weight
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-argv-materialization-output.txt
- **Severity**: important
- **Concern**: `run_codex_tier` passes staged/inline description via `head -c` into `--description-text` on `launch-review.sh`, while Claude read-tools reads the full staged file. Truncation (256 KB), byte-boundary UTF-8 splits, and command-substitution newline stripping make tier context unequal and can break large descriptions. On `--prompt-file`, `DESCRIPTION_TEXT` is not merged into the Codex prompt (dead argv) but still risks `E2BIG` when a single argv element exceeds ~128 KiB (`MAX_ARG_STRLEN`) for staged files between ~128 KiB–1 MiB—so Codex may fail to exec while Claude succeeds; waterfall outcome depends on tier order and argv limits, not model quality alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add --description-file to launch-review.sh for Codex or stop embedding/truncating and use the same path+Read contract as Claude
  - From cursor-specialist-correctness-output.txt: Omit --description-text for scout Codex launches; rely on staged path in prompt plus --add-dir SESSION_ROOT. Add harness: codex-present true + large description-file + stub Codex launcher recording argv length.
  - From dyn-argv-materialization-output.txt: Stop passing `--description-text` from `run_codex_tier` when using `--prompt-file` (description is already in the scout prompt via staged-path Read instructions or inline embed, and `launch-review.sh` does not merge `DESCRIPTION_TEXT` into the Codex prompt on the `--prompt-file` path). If a launcher ever needs file-backed description, pass a path flag (e.g. `--description-file "$STAGED_DESC"`) and teach `launch-review.sh` to use it without argv materialization, or cap materialization at `min(MAX_CONTEXT_BYTES, 131072)`.
  - From dyn-argv-materialization-output.txt: Prefer `--description-file "$STAGED_DESC"` (no substitution) or drop the argument entirely and rely on the prompt’s staged-path Read instruction plus Codex `--add-dir "$CANON_OUTPUT_DIR"`.
  - From dyn-argv-materialization-output.txt: Same as above: avoid byte-oriented `head -c` into argv; let Codex read the staged file by path (already referenced in the scout prompt under `$SESSION_ROOT/staged-context/description.txt`).
  - From dyn-argv-materialization-output.txt: Remove the `codex_args+=(--description-text …)` branches in `run_codex_tier` for `--prompt-file` launches; ensure `CANON_OUTPUT_DIR` (already `dirname` of `${OUTPUT}.raw`) covers `$SESSION_ROOT/staged-context/` so Codex can read staged files named in the prompt.


### FINDING_9: Exit-0 empty `${OUTPUT}.raw` does not set `had_probe_miss`; mis-reports launcher failure status
- **Reviewer(s)**: dyn-waterfall-state-machine-output.txt
- **Severity**: important
- **Concern**: Empty tier raw on exit 0 returns early from tier without `had_probe_miss=1`. If Codex launch failed and Claude exits 0 with empty raw (or both tiers exit 0 empty), terminal block uses `had_probe_miss=0` and emits `codex-failed` or default `claude-failed` even when Claude launcher did not fail—neither probe-exhaustion `empty` nor faithful last-tier launcher failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-state-machine-output.txt: Record per-tier outcomes (e.g. `had_exit0_nonempty=1` only when `last_launch_rc=0` and `[[ -s "$tier_raw" ]]`, or treat exit-0 empty as a probe-tier miss). When any tier produced exit-0 nonempty non-scout JSON, emit `SCOUT_STATUS=empty`; reserve `codex-failed` / `claude-failed` / `timeout` for cases where every attempted tier had a true launcher failure (`last_launch_rc≠0` or timeout/cap_hit), using the **last** such tier’s status.


