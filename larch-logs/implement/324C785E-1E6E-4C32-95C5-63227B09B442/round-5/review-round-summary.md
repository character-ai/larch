# Review Round 5

- Mode: `diff`
- 19 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Post-success add-dir serialization destroys successful Codex output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: After a successful Codex run, `launch-codex-exec.sh` can fail while serializing `--add-dir` metadata (e.g. tab/newline in a path with `LARCH_TEST_FORCE_NO_JQ=1`). The failure path reuses `write_preflight_bundle`, which truncates successful `OUTPUT`, overwrites retry metadata, and forces `LAUNCHER_EXIT=1`. Collectors then see failed/empty output despite a valid transcript. This also conflicts with `launch-codex-exec.md`, which documents a workdir-only retry-metadata fallback on serialization failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: On post-run serialization failure append workdir-only OUTER_LAUNCHER_ADD_DIRS_JSON preserve real LAUNCHER_EXIT and promote inner.done; reserve write_preflight_bundle for pre-dispatch failures only.
  - From cursor-specialist-correctness-output.txt: Use a post-success metadata-only failure path: warn fall back to workdir-only OUTER_LAUNCHER_ADD_DIRS_JSON preserve OUTPUT and real LAUNCHER_EXIT.
  - From cursor-specialist-correctness-output.txt: Update .md to match fail-closed behavior or restore workdir-only fallback in code.
  - From cursor-specialist-edge-cases-output.txt: Serialize add-dir metadata before dispatch; on post-exec serialization failure, log and record workdir-only outer meta without truncating ${OUTPUT}.
  - From cursor-specialist-edge-cases-output.txt: Align code with the documented workdir-only fallback (preferably pre-exec), or update the contract to match intentional destructive failure.
  - From cursor-specialist-plan-fidelity-output.txt: Implement workdir-only fallback per doc, or update doc and move serialization before dispatch if post-success failure is wrong.


### FINDING_10: Login-mode launcher tests omit auth.json/config-stripping assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-launch-codex-exec.sh` login-mode tests omit `auth.json` symlink and config-stripping assertions present in the negotiation harness. Launcher login fallback could stop symlinking `~/.codex/auth.json` while negotiation still passes CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mirror test-run-negotiation-round.sh login assertions (auth link target, stripped config) in test-launch-codex-exec.sh.


### FINDING_11: Negotiation harness lacks ephemeral CODEX_HOME leak checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The negotiation harness lacks temp `CODEX_HOME` leak checks on default success and `codex exec` failure paths. Broken cleanup on common paths can leak ephemeral auth state under `/tmp` without failing `make test-run-negotiation-round`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add CODEX_STUB_HOME_LOG or find-based leak assertions to success and CODEX_STUB_RC failure cases.


### FINDING_12: Unsafe absolute `--output` rejection is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `validate_meta_scalar_path` unsafe `--output` rejection is untested beyond relative paths. An absolute output with disallowed bytes could write sidecars before rejection or behave differently than the contract exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert_fails case with unsafe absolute --output and assert no sidecar files created.


### FINDING_13: No collector retry harness for malformed `OUTER_LAUNCHER_ADD_DIRS_JSON`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Malformed `OUTER_LAUNCHER_ADD_DIRS_JSON` with `jq` present has no collector retry harness. The collector may fall through or mis-retry when add-dir JSON is corrupt but `jq` is available.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-collect-agent-retry fixture expecting OUTER_LAUNCHER_ADD_DIRS_JSON malformed fail-closed.


### FINDING_14: `external_launcher_append_codex_exec_outer_meta` lacks direct unit coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The new codex-exec outer-meta helper in `lib-external-launcher-common.sh` lacks direct unit coverage. Metadata field drift can break collector retry routing and be discovered only in integration runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-lib-external-launcher-common case for external_launcher_append_codex_exec_outer_meta output keys.


### FINDING_15: Linter harness never fixtures `.claude/rules/*.md` scope
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `lint-codex-exec-auth.sh` scans `.claude/rules/*.md`, but the harness never fixtures that scope. A regression in rules-path scanning could leave raw `codex exec` in `.claude/rules` undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add .claude/rules/*.md violation fixture to test-lint-codex-exec-auth.sh.


### FINDING_16: Updated research Codex telemetry prose is not pinned by structure tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Updated Codex telemetry prose in `research-phase.md` is not pinned by research structure tests. Stale unmeasurable-Codex wording can return without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep-pin best-effort usage records (and ban obsolete unmeasurable prose if desired).


### FINDING_2: Transient-network retry still hand-parses TIMEOUT metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The transient-network retry branch in `collect-agent-results.sh` still hand-parses `TIMEOUT`, while the empty-output retry path uses the new `parse_retry_meta` helpers. Future outer-meta field changes may be updated in one retry path but not the other, causing inconsistent retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reuse parse_retry_meta and validate_retry_timeout_or_mark in the transient-network branch.


### FINDING_21: Linter pragma suppression is bypassable and under-specified
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: `lint-codex-exec-auth.sh` pragma suppression can pass unwired `codex exec` without mechanical auth proof. `has_trailing_pragma()` matches `# lint-codex-exec-auth: ok` anywhere on the line, so a same-line string such as `dummy=" # lint-codex-exec-auth: ok"; codex exec …` satisfies the regex and suppresses detection. The harness only covers embedded pragmas where `#` is not preceded by whitespace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Tighten pragma contract (allowlisted reasons or nearby external_prepare_codex_auth requirement).
  - From dyn-linter-bypass-output.txt: Anchor suppression to a real trailing comment (e.g. require the match at `$` or after `;`/command terminators), or strip quoted strings before pragma detection; add a harness case for `VAR=" # lint-codex-exec-auth: ok"; codex exec …` that must fail.


### FINDING_25: `lint-fix-loop.md` still claims `run_codex()` acquires serial lock
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `lint-fix-loop.md` still claims `run_codex()` acquires the serial lock before `run-external-agent.sh`. That contradicts the plan requirement to drop local Codex serial lock from `run_codex()` and misleads maintainers about dispatch layering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Rewrite §5: serial-lock prose for run_cursor() only; document that launch-codex-exec.sh owns Codex lock + dispatch.


### FINDING_26: `LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH` override missing from contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-required `LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH` test override is implemented in code/harness but absent from `lint-fix-loop.md`. Harness authors must read source/tests to discover the override env var the plan promised in the sibling `.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add a Test override subsection naming LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH and its default/harness usage.


### FINDING_29: Negotiation omits `external_launcher_mirror_quota_from_events` on Codex failure
- **Reviewer(s)**: dyn-auth-parity-output.txt
- **Severity**: important
- **Concern**: The inline Codex branch in `run-negotiation-round.sh` captures `--json` events and stderr to sidecar files, but on non-zero `codex_rc` it never calls `external_launcher_mirror_quota_from_events`. Quota/usage-limit signals live on the events stream, not the stderr sidecar (#3390), so negotiation failures that are really quota limits still surface as undifferentiated exit 2 and leave the sidecar without the mirrored marker that other `--json` launchers rely on for correct failure classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-parity-output.txt: After the `codex exec` line when `codex_rc != 0`, call `external_launcher_mirror_quota_from_events "$codex_events" "$codex_sidecar"` before usage recording and exit, matching the other `--json` launchers.


### FINDING_30: Negotiation silently ignores `config.toml` copy failure
- **Reviewer(s)**: dyn-auth-parity-output.txt
- **Severity**: important
- **Concern**: The new `cp ~/.codex/config.toml "$codex_home/config.toml"` block in negotiation runs under `set -uo pipefail` without `set -e`, so copy failure is silently ignored and `external_prepare_codex_auth` may proceed without the stripped temp config that `check-reviewers.sh` guarantees via fail-closed `cp … || return 1`. That weakens the shared contract that stripping runs on copied config before env-key argv or login `auth.json` symlink setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-parity-output.txt: Either add `set -e` to the Codex branch (with explicit `||` handlers where soft-fail is intended) or mirror the probe pattern: `cp … || { _negotiation_codex_cleanup; emit_kv RESPONSE_FILE "$OUTPUT_FILE"; exit 2; }`.


### FINDING_32: Quoted or escaped `codex exec` evades linter detection
- **Reviewer(s)**: dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: `lint-codex-exec-auth.sh` detection is limited to the literal token sequence `codex[[:space:]]+exec`. Quoted or escaped command names such as `"codex" exec …`, `'codex' exec …`, and `\codex exec …` evade detection while remaining valid shell. None of these appear in `test-lint-codex-exec-auth.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-bypass-output.txt: After env-prefix stripping, also flag lines matching `[\"'\\]?codex[\"'\\]?[[:space:]]+exec`, or normalize/remove quoted/\\-prefixed command tokens before matching; add harness fixtures for each evasion shape.


### FINDING_33: Markdown fence opener is case-sensitive and too strict
- **Reviewer(s)**: dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: Markdown scanning only enters a fence when the opener matches `^[[:space:]]*```[[:space:]]*(bash|sh|shell)[[:space:]]*$` case-sensitively with nothing after the info string. Fences like ` ```Bash` / ` ```SH` are ignored, so raw `codex exec` inside them is never scanned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-bypass-output.txt: Case-fold the info string (e.g. `tolower()` on the capture) and/or accept common variants; add harness cases for ` ```Bash` and trailing-info openers.


### FINDING_34: `scripts/*` basename allowlist can exempt misplaced copies
- **Reviewer(s)**: dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: `review-and-fix.sh` is allowlisted by full path under `skills/review-and-fix/scripts/`, but every other `scripts/*.sh` file is exempted by basename alone. A new `scripts/review-and-fix.sh` or other allowlisted basename copied into `scripts/` would skip the entire file scan, not just the canonical launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-bypass-output.txt: For `scripts/*`, allowlist only the known canonical paths (mirror the full-path rule used for `skills/review-and-fix/scripts/review-and-fix.sh`) instead of bare basenames; document the closed path set in `lint-codex-exec-auth.md`.

### FINDING_6: Collector cannot replay multi add-dir metadata without jq
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Outer retry for `launch-codex-exec` cannot replay multi `--add-dir` metadata without `jq`, even though the launcher records it without `jq`. On jq-less hosts, `EMPTY_OUTPUT` retry for lint-fix or research multi add-dir launches is rejected as invalid metadata instead of re-invoking the launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Expand OUTER_LAUNCHER_ADD_DIRS_JSON in the no-jq branch via json_array_from_args or require jq for codex-exec retries.


### FINDING_9: No test enforces identical Codex auth inventory across four docs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires an identical canonical merged Codex auth inventory in `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `SECURITY.md`, and `scripts/lib-external-launcher-common.md`, but no test enforces it. A future edit can remove a swept surface from one doc only while operators still trust stale guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a structural harness that byte-compares the inventory list across all four files.


