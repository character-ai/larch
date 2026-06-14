### FINDING_1: Dirty-tree contract gap between `--mode collect` and brainstorm recovery prose
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-brainstorm-flow
- **Severity**: important
- **Concern**: Moving the dirty-tree checkpoint into `design-step1d5.sh --mode collect` breaks or contradicts the brainstorm dirty-tree contract. Either collect omits `${OUTPUT}.dirty-tree` sidecar consult and drops `STAGE=brainstorm-collection`, `RECOVERY_REQUIRED=true`, and the `.dirty-tree-prompted-brainstorm-collection` AskUserQuestion gate, so launcher-detected pollution can be missed and `/design` may continue without the non-skippable recovery flow; or collect is warn-only while `brainstorm.md` still mandates operator recovery, leaving conflicting orchestrator prose and duplicate or skipped prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In collect, scan each argv output path for a .dirty-tree sidecar before checkpoint; on dirty/unknown write dirty-tree-detected.env with STAGE=brainstorm-collection and RECOVERY_REQUIRED=true and emit WARN=. Keep orchestrator recovery in brainstorm.md after collect (consult sidecars, AskUserQuestion once via .dirty-tree-prompted-brainstorm-collection), mirroring plan-review SKILL.md sidecar plus prompt pattern
  - From Cursor-Innovation: In collect, scan each supplied output path for a readable `${path}.dirty-tree` sidecar (same contract as plan-review collection), merge dirty/unknown into `dirty-tree-detected.env` with `STAGE=brainstorm-collection` and `RECOVERY_REQUIRED=true`, and keep `brainstorm.md` operator recovery prose keyed on `.dirty-tree-prompted-brainstorm-collection`
  - From Cursor-Pragmatic: In `design-step1d5.sh --mode collect`, preserve today's brainstorm contract (sidecar consult if still required, full checkpoint stdout to `dirty-tree-detected.env`, `STAGE=brainstorm-collection`, `RECOVERY_REQUIRED=true`, idempotent prompt sentinel). Keep plan-review warn-only alignment out of this path unless the issue explicitly retires operator recovery
  - From Codex-Requirements: Revise the brainstorm.md plan to branch after --mode collect on dirty-tree-detected.env with RECOVERY_REQUIRED=true and run the existing once-per-boundary recovery prompt before synthesis or Step 1d.7, or document an equivalent wrapper output contract that forces the same stop.
  - From Cursor-dyn-brainstorm-flow: Replace lines 105-113 with prose stating dirty-tree is owned by design-step1d5.sh --mode collect (write dirty-tree-detected.env plus WARN only); delete RECOVERY_REQUIRED and .dirty-tree-prompted-brainstorm-collection instructions


### FINDING_2: Collector per-slot `STATUS!=OK` failures not logged when collect exits 0
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-brainstorm-flow
- **Severity**: important
- **Concern**: Planned `--mode collect` failure logging keys only on non-zero `collect-agent-results.sh` exit. That script can exit 0 while emitting per-reviewer records with `STATUS` values such as `TIMED_OUT`, `FAILED`, `EMPTY_OUTPUT`, `SENTINEL_TIMEOUT`, `NOT_SUBSTANTIVE`, or `cap_hit`, so a failed brainstorm external may never reach `execution-issues.md` even though collection "succeeded."
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: After collection, parse result blocks and append one External Reviewer Issues entry for each STATUS not OK, preferably using the existing agent compose-collector-failure-log helper and per-record idempotency sentinels
  - From Codex-Innovation: After capturing collector stdout, scan its KEY=value result blocks for STATUS values other than OK and append a run-log failure for those records; keep the existing non-zero-rc logging for argument or wait-reviewers failures
  - From Codex-Pragmatic: Parse collector stdout after every collect run and append one External Reviewer Issues entry for each STATUS other than OK. Keep stdout visible and continue synthesis from readable outputs.
  - From Codex-dyn-brainstorm-flow: In --mode collect, parse collector stdout records after every run and append a warning for each STATUS other than OK or cap_hit using REVIEWER_FILE, TOOL, EXIT_CODE, and FAILURE_REASON; keep rc handling for collector invocation failures


### FINDING_4: Step 2b.5 SKILL.md retained procedure still documents pre-wrapper capture and rc branching
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-design-fence-lint
- **Severity**: important
- **Concern**: The plan folds rc=2 capture-then-append into `design-step2b5.sh` with `PLAN_SIZE_RC` / `PLAN_SIZE_HANDLED`, but `skills/design/SKILL.md` Step 2b.5 items 2–3 still describe inline subshell capture, `_plan_size_rc` / `$?` branching, direct `python/cli.py plan check-size` invocation, and raw `run-log append-failure` bullets. Retained callers may keep prompt-side append prose or misread handled wrapper failures as success, letting hard/partition/drift branches fire incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Rewrite Step 2b.5 items 2–3: step 2 invokes only `design-step2b5.sh` and parses wrapper stdout for check-size KVs plus `PLAN_SIZE_RC`/`PLAN_SIZE_HANDLED`; step 3 deletes rc=2/other-non-zero append bullets and branches on `PLAN_SIZE_HANDLED=true` before threshold logic
  - From Cursor-dyn-design-fence-lint: In the plan’s `skills/design/SKILL.md` section, explicitly replace step 2 with “invoke `design-step2b5.sh`, capture full stdout”, replace step 3 with “parse `PLAN_SIZE_HANDLED=true` first (return immediately), else parse `PLAN_SIZE_RC=` before any `SIZE_TRIGGER_FIRED` logic”, delete the raw `run-log append-failure` bullets, and remove the “or `python/cli.py plan check-size` directly” retained-path wording at line 521


### FINDING_6: Collect scans canonical launch failure logs that launches do not create
- **Reviewer(s)**: Codex-dyn-brainstorm-flow
- **Severity**: important
- **Concern**: `design-step1d5.sh --mode collect` is planned to scan `$DESIGN_TMPDIR/*-brainstorm-launch.failure.log`, but brainstorm launch fences remain plain `launch-review.sh` calls without `--stderr-sink` (or equivalent) to write those canonical files. A Cursor or Codex brainstorm launch that fails before usable output is collected leaves nothing for collect to append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-brainstorm-flow: Update the brainstorm launch examples or prose to write the exact canonical failure files with existing launcher support, such as --stderr-sink "$DESIGN_TMPDIR/cursor-brainstorm-launch.failure.log" and the Codex equivalent, or make collect consume the launcher sidecars it actually writes

---

**Merge summary**: 14 inputs → 6 findings. Dirty-tree items (1, 4, 6, 9, 12) merged despite conflicting resolution directions (preserve recovery vs. warn-only prose). Collector-logging items (2, 5, 7, 14) merged. Step 2b.5 SKILL items (8, 10) merged. Items 3, 11, and 13 kept separate (distinct surfaces/fixes).



### FINDING_3: Launch-failure logging split between prompt-side prose and `--mode collect`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `brainstorm.md` still directs prompt-side `run-log append-failure` during external launches while the plan assigns launch-log ingestion to `--mode collect` via canonical `*-brainstorm-launch.failure.log` files with once-only sentinels. An orchestrator following the launch prose can append before collect runs, then collect appends again from the same logs, duplicating `execution-issues.md` entries despite wrapper sentinels covering only the collect path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Remove or demote the prompt-side `run-log append-failure` instruction in the External launches section; state that launch stderr sinks plus `--mode collect` own launch and collector failure logging
  - From Cursor-Requirements: Drop the append-failure directive; say launches must use the documented --stderr-sink paths and that design-step1d5.sh --mode collect ingests those logs


### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.md:1-75
- **Concern**: [SCOPE-REDUCTION] Plan updates the top-level test-design-structure sibling doc despite an explicit non-goal excluding scripts/*.md docs. Scenario: This adds documentation-only churn outside the approved orchestrator-facing surfaces; the feature still ships with the shell lint and wrapper changes without this file
- **Proposed resolution**: Remove the scripts/test-design-structure.md update from the plan and keep the structural lint contract in scripts/test-design-structure.sh only




### FINDING_1: `--mode collect` needs `set +e` around collector and checkpoint
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed `--mode collect` path in `design-step1d5.sh` runs `collect-agent-results.sh` and `dirty-tree checkpoint` under `set -euo pipefail` without `set +e` guards. A non-zero collector exit or checkpoint failure aborts the wrapper before failure logging, `dirty-tree-detected.env` merge, and the planned exit-0 degrade path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap `collect-agent-results.sh`, per-slot append helpers, and `dirty-tree checkpoint` in `set +e`/`set -e` (match `plan-review-loop.sh` `checkpoint || true` pattern) and document in `design-step1d5.md`


### FINDING_2: Step 2b.5 must bind `_plan_size_rc` from wrapper stdout, not Bash tool exit code
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The retained Step 2b.5 procedure in `SKILL.md` does not state that `_plan_size_rc` must come from the `PLAN_SIZE_RC=` row in captured wrapper stdout. If `design-step2b5.sh` exits 0 with `PLAN_SIZE_HANDLED=true` on rc 2/3/other failures, using the Bash tool exit code sets `_plan_size_rc=0` and threshold branches (Split/Cancel) can fire on a failed `plan check-size`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In Step 2b.5 item 3, state explicitly: parse `PLAN_SIZE_HANDLED` first; else set `_plan_size_rc` only from the `PLAN_SIZE_RC=` row in captured wrapper stdout; never from the Bash tool rc


### FINDING_4: Active brainstorm path omits pause check in proposed `--mode entry`
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The proposed `--mode entry` refactor preserves pause checks only for brainstorm-off and already-done exits. On the active brainstorm path, a pause requested before launches or collection is ignored until after those steps, unlike the current wrapper which pause-checks after step-1c/step-1d repairs and before the brainstorm timing mark.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add an explicit active-path pause check after skip branches and before the timing mark/prompt body, while keeping skip-path step-1d.5 repair before their pause check


### FINDING_5: Structural lint will not catch reintroduced brainstorm dirty-tree checkpoint fence
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned `assert_references_bash_fences_are_scripts` check only validates that bash fences start with `${CLAUDE_PLUGIN_ROOT}` or the session launcher. Because `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` satisfies that allowlist, the direct dirty-tree checkpoint fence in `brainstorm.md` (lines 105–111) could be reintroduced while the new lint still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add a targeted absence pin for the brainstorm.md direct dirty-tree checkpoint fence, or otherwise require that checkpoint handling appears only through design-step1d5.sh --mode collect



### FINDING_1: `--record-override` omits site, log path, and redaction inputs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed `--record-override` contract does not carry the Override append inputs the current SKILL path requires (`--site`, evidence log path, `--redact`). Today Override logging uses `run-log append-failure` with site-specific `--site "<SITE>"`, `--output-file "$DESIGN_TMPDIR/validate-plan-commands.log"`, and `--redact`. The plan only says append Warnings with tool `validate-plan-commands` and exit 0, so a wrapper-only Override call can drop site attribution and evidence, breaking execution-issues parity across Step 2b / Gate B / discussion-round2 / Step 5c.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify `--record-override` as a standalone launcher call that requires `--site` (same tokens as today), reads `$DESIGN_TMPDIR/validate-plan-commands.log` or forwarded `--validate-log-file`, and mirrors the current Override append flags; update SKILL Override prose to invoke that exact argv.


### FINDING_3: Brainstorm launch failure logging depends on sinks `launch-review` does not write
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Brainstorm launch failure logging depends on canonical `--stderr-sink` files that `launch-review` does not write. After prompt-side `run-log append-failure` is removed, a Cursor or Codex launch failure can leave no `$DESIGN_TMPDIR/*-brainstorm-launch.failure.log` for `design-step1d5.sh --mode collect` to ingest, so wrapper-owned launch failure logging is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Revise the plan to either make launch-review write the requested failure-only sink, or have collect ingest the existing output-side failure artifacts generated by launch-review before removing prompt-side launch append




### FINDING_1: Brainstorm `--stderr-sink` contract gaps and duplicate launch-failure logging
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: Brainstorm launches are planned to pass `--stderr-sink` into `launch-review.sh` / `run-external-agent`, but the launcher still records failures via `SIDECAR` / `append_launch_failure` without reliably writing the canonical sink files that `design-step1d5.sh --mode collect` will scan. Failures can remain in `.sidecar` / `.failure-diag` while collect ingestion is a no-op. When `DESIGN_TMPDIR` is set, `append_launch_failure` still appends to `execution-issues.md`, so the same failed brainstorm launch can produce two External Reviewer Issues rows (launcher append plus collect sentinel ingestion), breaking once-only / resume idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When `STDERR_SINK` is set, skip `append_launch_failure` (or gate it off for brainstorm timing kinds) and let `design-step1d5.sh --mode collect` own the single run-log append from the sink file.
  - From Cursor-Pragmatic: In `launch-review.sh`, when `--stderr-sink` is set: `rm -f` the sink before launch; on non-zero exit copy the resolved failure carrier (`resolve_failure_diagnostic_source` / existing `write_failure_diag` output) into the sink; on success leave the sink absent; mirror the `launch-codex-implement` stderr-sink contract in the plan's testing section
  - From Cursor-Requirements: Add explicit `launch-review.sh` contract: on launch start remove stale sink; on failure write resolved diagnostics to `--stderr-sink`; when sink is set for brainstorm, skip `append_launch_failure` and let collect own once-only ingestion via its sentinels
  - From Codex-Generic: Require --stderr-sink brainstorm launches to write the sink but skip append_launch_failure, or otherwise mark the sink path as caller-owned logging while preserving no-sink behavior


### FINDING_3: Collect mode may ingest stale launch-failure logs for vendors not launched this wave
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: If `--mode collect` always scans both fixed launch-failure log paths whenever present, a stale `codex-brainstorm-launch.failure.log` (or Cursor twin) from an earlier attempt in the same `$DESIGN_TMPDIR` can be ingested after pause/resume or a partial wave where only one vendor launched, producing a false launch-failure warning and masking real state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Derive launch-failure log ingestion from the supplied collect paths only (`cursor-brainstorm-output.txt` → `cursor-brainstorm-launch.failure.log`, `codex-brainstorm-output.txt` → `codex-brainstorm-launch.failure.log`); document that rule in `design-step1d5.md` and add a resume harness case


### FINDING_4: `design-step2b5.sh` stub lacks the planned stdout / rc handoff contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `design-step2b5.sh` currently runs `plan check-size`, captures output, and exits without printing stdout, `PLAN_SIZE_RC=`, or `PLAN_SIZE_HANDLED=`. Retained Step 2b.5 callers that switch to capturing wrapper stdout per the plan will get empty `_plan_size_out`, trip wrapper-drift failure modes, or mis-bind `_plan_size_rc` from Bash exit code 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Implement the full stdout contract from the plan (`Always print original stdout`, append `PLAN_SIZE_RC=`, rc 2/other logging + `PLAN_SIZE_HANDLED=true` + exit 0) before rewiring SKILL.md parsing; extend `test-design-pause-resume.sh` / structure pins if needed


### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/run_logs.py:2694; skills/design/scripts/design-step-validator-autofix.sh (proposed --record-override)
- **Concern**: [SCOPE-REDUCTION] Proposed repeated --redact <value> passthrough adds a wrapper surface that run-log append-failure does not support. Scenario: If a call site forwards a redact value, append-failure rejects the argv and the override warning can be silently lost behind degraded error handling
- **Proposed resolution**: Keep the minimum change: do not add valued redact args. Pass the existing boolean --redact only



