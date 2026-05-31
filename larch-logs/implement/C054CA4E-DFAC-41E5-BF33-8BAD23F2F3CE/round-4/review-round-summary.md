# Review Round 4

- Mode: `diff`
- 6 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Rename failure — contract drift and hard abort vs best-effort
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-rename-fail-behavior-output.txt
- **Severity**: important
- **Concern**: `design-init-runparams.sh` treats rename failure as a hard stop (`INIT_STATUS=rename-failed`, exit 1) before `write-run-params.sh`, while `design-init-runparams.md` still documents rename failure as `WARN=` and continue, omits `rename-failed` from the allowlist/exit table, and the #3245 plan / pre-refactor Step 0b expected best-effort rename (log warning, continue with `run-params.json`). `SKILL.md` matches the driver’s abort path, so orchestrator and script agree with each other but not with the sibling contract or prior observable behavior; transient `gh`/API rename failures can abort all of Step 0b without `run-params.json` where the old path continued with a warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rename-fail-behavior-output.txt: Align with the plan: on rename failure, `add_warn` (and optionally `append-tool-failure.sh` to `execution-issues.md` like old 5.5), keep `INIT_STATUS=ok`, emit `RENAMED=false` if unknown, and proceed to run-params; reserve exit **1** only for `env-refresh-failed` / `contract-drift`. If hard abort is intentional, update the plan, `design-init-runparams.md`, and acceptance text so they match the implementation.
  - From dyn-rename-fail-behavior-output.txt: If rename stays best-effort, drop the `rename-failed` branch and log driver `WARN=` breadcrumbs after `_init_rc=0`; if rename stays fatal, document that explicitly in Step 0b prose and drop “best-effort” wording elsewhere (e.g. clarify sub-step 5 still says best-effort for a different rename callsite).
  - From dyn-rename-fail-behavior-output.txt: Either update the `.md` to document `rename-failed` + abort semantics and drop the `WARN=` rename line, or change the script to match the current `.md` (WARN + continue, no `rename-failed`).


### FINDING_2: Partial state when rename succeeds but run-params write fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Rename runs before `write-run-params.sh`. If rename succeeds and `write-run-params` fails with `contract-drift`, the issue may already show `[DESIGNING]` without a fresh `run-params.json`. Retries can hit wrong tier/flag routing or inconsistent clarify/plan gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document the partial-state retry contract in the `.md` sibling and SKILL banner, or reorder so rename is best-effort only after run-params is written if policy allows.


### FINDING_3: Step 0b router harness does not exercise production driver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-step0b-router-flag-recovery.sh` duplicates jq-merge logic instead of invoking `design-init-runparams.sh` while `relevant-checks` maps driver edits to this test. Driver-only changes (e.g. `append-tool-failure` on jq failure, jq-unavailable warnings) can pass all replica cases while production merge/logging diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend the existing harness with stubbed dependencies and invoke `design-init-runparams.sh`; add cases for jq failure logging and jq-unavailable warnings.


### FINDING_4: WARN/ERROR substring dedup can suppress distinct messages
- **Reviewer(s)**: dyn-kv-parse-safety-output.txt
- **Severity**: important
- **Concern**: In `skills/design/SKILL.md`, WARN/ERROR de-duplication uses a space-padded substring test on joined prior messages (`[[ " ${_route_warn_lines[*]} " != *" $_value "* ]]`). A later message that is a proper substring of an earlier one (e.g. `invalid-step` after `pause-load-invalid-step`) is dropped even when strings differ. Operators can miss real breadcrumbs on `LOAD_OK=false` fallthrough and other file-first + stdout merge paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-parse-safety-output.txt: De-dupe with exact membership only (e.g. loop `"${_route_warn_lines[@]}"` and `[[ "$_w" == "$_value" ]]`, or an associative array keyed by the full message). Keep `=${_line#*=}` splitting so values may contain `=`; do not use substring globbing on joined text.


### FINDING_6: Re-entry guard failures lack operator-visible diagnostic
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Re-entry guard helper return 2 no longer surfaces a diagnostic WARN breadcrumb (old inline Step 0b 2.6 printed helper KV). Invalid-input reentry guard failures can fall through silently to clarify/plan routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit helper stdout as WARN on non-zero rc (especially rc 2) into route result env or orchestrator breadcrumbs.


### FINDING_8: Pause-marker pre-check stricter than pause loader
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` uses `grep -Fq` on a literal substring for pause pre-check while `design-pause-load.sh` uses a strict line regex. A body with a valid pause block using non-canonical whitespace may load in pause-load but be skipped by route, so `/design` runs fresh routing while the pause marker remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse the loader's marker regex or a shared helper for the route driver's resume gate.


