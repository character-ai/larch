Normalized aggregator output from the supplied reviewer slots. Positive-only audits (e.g. FINDING_29, 40, 44) are omitted. Merged items share one behavioral risk; verbatim revision bullets are kept per slot when wording differs.

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

### FINDING_3: Default 180s scout timeout may be insufficient for large read-tools diffs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Default 180s timeout is unchanged for `--read-tools` Claude tier on large staged diffs (~900 KB after trim). Read loops can time out; scout emits timeout/claude-failed and zero dynamic reviewers like an intentional empty manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Raise default timeout for read-tools scout launches or scale timeout from staged byte size; consider a distinct status for read-timeout

### FINDING_4: Duplicate scout-JSON probe logic between waterfall and post-winner validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `tier_raw_is_scout_json` duplicates fence/JSON probe logic used again after a waterfall winner; divergent edits can cause inconsistent tier vs post-winner behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor a single probe helper shared by waterfall selection and post-winner validation

### FINDING_5: Triplicated terminal fail-open KV blocks in multi-tier exhaustion paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_empty_manifest` + `emit_kv` blocks are repeated in multi-tier exhaustion paths, making `SCOUT_STATUS` terminal contract harder to keep consistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a small helper that emits the shared fail-open KV envelope

### FINDING_6: `CURSOR_PRESENT` parsed but unused; Cursor tier not in waterfall
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `CURSOR_PRESENT` is parsed but not used in tier selection; issue acceptance still describes Codex→Cursor→Claude while scout implements Codex→Claude only—readers expect a Cursor tier without code path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document API-only flag inline or rename to signal intentional non-use
  - From cursor-specialist-correctness-output.txt: Update issue acceptance or add Cursor tier when launch-review supports staged reads.

### FINDING_7: [OUT_OF_SCOPE] `commit-log.txt` still includes larch-logs-only commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `gather-branch-context.sh` commit log still includes commits touching only `larch-logs` while `diff.txt` is trimmed; log-only consumers may see run-log noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Apply the same pathspec to log formatting if log-driven reviewers are added later

### FINDING_8: Multi-tier terminal `SCOUT_STATUS` vs plan (probe miss + launcher failure → `claude-failed` not `empty`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-state-machine-output.txt
- **Severity**: important
- **Concern**: When Codex probe-misses and Claude launcher fails, terminal block emits `claude-failed` instead of plan/older text expecting `empty` on probe exhaustion. Case (2) is documented/intentional in `scout-dynamic-archetypes.md` and harness `waterfall-probe-claude-fail`, but plan acceptance and operator/diag expectations may disagree—sync docs or change behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Sync issue/plan acceptance with scout-dynamic-archetypes.md or change branch to always emit empty when had_probe_miss.
  - From cursor-specialist-plan-fidelity-output.txt: Emit empty whenever had_probe_miss under --codex-present true; launcher statuses only when every tier failed launch with no probe miss.
  - From dyn-waterfall-state-machine-output.txt: The audited four-way matrix is otherwise implemented as intended and tested where covered: (1) Codex probe-miss + Claude probe-miss → `empty`; (2) Codex probe-miss + Claude launch-fail → `claude-failed` (documented in `scripts/scout-dynamic-archetypes.md:14`, harness `waterfall-probe-claude-fail`); (3) Codex launch-fail + Claude probe-miss → `empty`; (4) both launch-fail → `claude-failed` (last tier). Case (2) intentionally overrides the plan text’s “any probe miss ⇒ `empty`” rule in favor of surfacing the final launcher status.

### FINDING_9: Exit-0 empty `${OUTPUT}.raw` does not set `had_probe_miss`; mis-reports launcher failure status
- **Reviewer(s)**: dyn-waterfall-state-machine-output.txt
- **Severity**: important
- **Concern**: Empty tier raw on exit 0 returns early from tier without `had_probe_miss=1`. If Codex launch failed and Claude exits 0 with empty raw (or both tiers exit 0 empty), terminal block uses `had_probe_miss=0` and emits `codex-failed` or default `claude-failed` even when Claude launcher did not fail—neither probe-exhaustion `empty` nor faithful last-tier launcher failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-state-machine-output.txt: Record per-tier outcomes (e.g. `had_exit0_nonempty=1` only when `last_launch_rc=0` and `[[ -s "$tier_raw" ]]`, or treat exit-0 empty as a probe-tier miss). When any tier produced exit-0 nonempty non-scout JSON, emit `SCOUT_STATUS=empty`; reserve `codex-failed` / `claude-failed` / `timeout` for cases where every attempted tier had a true launcher failure (`last_launch_rc≠0` or timeout/cap_hit), using the **last** such tier’s status.

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

### FINDING_13: CI validates `--read-tools` argv only, not runtime Read under `--print`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Harness checks `.meta` argv, not that Read actually runs; hosts ignoring flags could yield silent zero archetypes in production while lint passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional guarded integration test or explicit SECURITY.md contract that CI is argv-only.
  - From cursor-specialist-plan-fidelity-output.txt: Add Read execution probe or document manual verify-external-tool-invocations in PR.

### FINDING_14: Codex scout tier `--add-dir` exposes full review tmpdir, not staged-context only
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: With `--codex-present true`, Codex gets `--add-dir` on `CANON_OUTPUT_DIR` (full review tmpdir), allowing reads of sibling launch env sidecars, prior scout raw, parse errors—broader than SECURITY.md staged-context-only model for Claude.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Narrow Codex --add-dir to staged-context (relocate tier raw output or add scout-specific add-dir flag).

### FINDING_15: Read-tools scout relies on plan permission mode and argv allowlist without runtime denial tests
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Harness only checks argv; misconfigured or evolving Claude CLI might allow Write/Bash under `--add-dir`, enabling edits in session tmpdir despite prompt preamble.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add verify-external-tool-invocations smoke test that Write/Bash fail; document residual risk or use stricter permission mode.

### FINDING_16: `SCOUT_DYNAMIC_ARCHETYPES_SH` / `LAUNCH_*` env overrides can replace binaries
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Compromised operator env can run arbitrary code with Codex auth and review-tmpdir read access during scout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document trusted-operator-only overrides in SECURITY.md; keep overrides out of production shells.

### FINDING_17: `tier_raw_is_scout_json` can leak `.fenced-probe.*` temps on failed `cp`
- **Reviewer(s)**: dyn-temp-file-lifecycle-output.txt
- **Severity**: nit
- **Concern**: On empty `fenced_tmp` branch, `cp` failure removes only `probe_tmp` before return, leaving `${raw_path}.fenced-probe.*` under `$SESSION_ROOT`; repeated probe misses can accumulate; `cleanup_temps` does not cover probe artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-file-lifecycle-output.txt: On the empty-`fenced_tmp` `cp` failure path, remove both temps in the handler (e.g. `{ rm -f "$probe_tmp" "$fenced_tmp"; return 1; }`), matching the `cp "$fenced_tmp" "$probe_tmp"` branch at line 162; optionally add a single `rm -f "$fenced_tmp"` immediately before that `return 1` so every exit from the fenced branch clears `fenced_tmp`.

### FINDING_18: `allowedTools` is Read-only; plan mentioned Read/Grep/Glob
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Scout cannot Grep/Glob staged trees if needed; minor mismatch vs plan wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update plan text or expand allowlist if required.

### FINDING_19: dispatch-panel dynamic tests invoke real Codex `launch-review.sh` when only Claude is stubbed
- **Reviewer(s)**: dyn-harness-codex-stub-gap-output.txt
- **Severity**: latent
- **Concern**: `dynamic4`, `dynamic8`, `dynamic-empty`, and `oversized-diff` use `--codex-available true` with only `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` stubbed; real Codex tier runs (preflight, lock, retries, 180s) before Claude stub wins—CI latency/flakiness risk and weak offline guard for large-diff panel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-codex-stub-gap-output.txt: Reuse the lightweight `codex_tier_stub` pattern from `scripts/test-scout-dynamic-archetypes.sh:532-563` and export `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` on these cases (and in `scout_wrapper` for `dynamic4`), matching the plan’s “stubbed launchers; no real Codex” testing strategy and `test-scout` waterfall cases at `565-627`.
  - From dyn-harness-codex-stub-gap-output.txt: Either set `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` to the shared `codex_tier_stub`, or use `--codex-available false` here so the case tests panel dispatch + large-diff staging without running the Codex waterfall.

### OOS_1: [OUT_OF_SCOPE] Scout acceptance lists Cursor tier; documentation-only mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Waterfall is Codex→Claude only while issue acceptance mentions Cursor; not a harness gap in changed files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update acceptance or issue close note to match scout vs panel behavior.

### OOS_2: [OUT_OF_SCOPE] Harness missing waterfall cases (3) and (4)
- **Reviewer(s)**: dyn-waterfall-state-machine-output.txt
- **Severity**: nit
- **Concern**: No harness asserts Codex launch-fail + Claude probe-miss → `empty`, or both launch-fail → `claude-failed`; logic matches contract but coverage thinner than cases (1)–(2).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] `last_scout_status` initialized to `claude-failed` before tiers (amplifies empty-raw gap)
- **Reviewer(s)**: dyn-waterfall-state-machine-output.txt
- **Severity**: nit
- **Concern**: Combined with exit-0 empty-raw handling (FINDING_9), all-empty multi-tier path can report `claude-failed` without any launcher failure.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] No harness for Codex + staged description ~128 KiB–1 MiB / E2BIG argv
- **Reviewer(s)**: dyn-argv-materialization-output.txt
- **Severity**: nit
- **Concern**: Test gap for `--codex-present true` with large staged description to catch `E2BIG` or assert argv omits bulk `--description-text`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Staged-context and launch-env artifact lifecycle (intentional retention)
- **Reviewer(s)**: dyn-temp-file-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `STAGED_DIR` not removed per scout; launch env files truncated not deleted; `cleanup_temps` covers only fenced/validated temps—acceptable except fenced-probe leak (FINDING_17).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Plan allows panel PATH `codex` fallthrough vs fully stubbed launchers
- **Reviewer(s)**: dyn-harness-codex-stub-gap-output.txt
- **Severity**: nit
- **Concern**: Plan “ok-path” note documents tradeoff; conflicts with testing strategy calling for stubbed launchers—panel tests remain weak link (see FINDING_19).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-codex-stub-gap-output.txt: The implementation plan explicitly allows `dynamic4` / `dynamic8` / `dynamic-empty` to keep `--codex-available true` with PATH `codex` fallthrough (plan “ok-path” note). That documents the tradeoff but still conflicts with the same plan’s testing strategy calling for fully stubbed launchers and with FINDING_7’s split override variables; panel tests remain the weak link.
