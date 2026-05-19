### FINDING_1: **Important** correctness [scripts/scout-dynamic-archetypes.sh:267](<OPERATOR_REPO_PATH>/scripts/scout-dynamic-archetypes.sh:267) — The new fence-stripping path can make the scout exit nonzero before it reaches the `json_parse` failure emitter. Concrete scenario: a launcher exits `0` but fails to create `$raw_output`; line 262 enters the recovery branch because `jq` cannot read it, then line 267 runs `awk` on the missing file under `set -e`, aborting the script. `dispatch-panel.sh:313-315` then reports `SCOUT_STATUS=validation-failed`, so there is no `SCOUT_FAIL_REASON=json_parse` and no parse-failure execution-issues warning. Guard the `awk` extraction with a readable-file check or tolerate `awk` failure, then let the existing `jq` gate at lines 275-277 emit the normal `json_parse` result.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness [scripts/scout-dynamic-archetypes.sh:267](<OPERATOR_REPO_PATH>/scripts/scout-dynamic-archetypes.sh:267) — The new fence-stripping path can make the scout exit nonzero before it reaches the `json_parse` failure emitter. Concrete scenario: a launcher exits `0` but fails to create `$raw_output`; line 262 enters the recovery branch because `jq` cannot read it, then line 267 runs `awk` on the missing file under `set -e`, aborting the script. `dispatch-panel.sh:313-315` then reports `SCOUT_STATUS=validation-failed`, so there is no `SCOUT_FAIL_REASON=json_parse` and no parse-failure execution-issues warning. Guard the `awk` extraction with a readable-file check or tolerate `awk` failure, then let the existing `jq` gate at lines 275-277 emit the normal `json_parse` result.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/scout-dynamic-archetypes.sh:262-272
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fence stripper concatenates multiple fenced regions Multiple ``` blocks can merge into invalid JSON and surface as json_parse instead of a clearer failure Pick first jq-valid fenced block or strip a single best block
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/scout-dynamic-archetypes.sh:262-276
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fence-strip path runs under set -e; awk/mv failure exits non-zero so dispatch maps scout to validation-failed instead of parse-failed/SCOUT_FAIL_REASON. Disk full or permission error during mv after successful fenced JSON extraction: scout exits before emit_parse_failed_result; dispatch shows validation-failed and loses telemetry semantics. Wrap fence extraction in set +e (or explicit || true) and convert I/O failures into emit_parse_failed_result with a dedicated reason without non-zero exit.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review/scripts/dispatch-panel.sh:337-345;skills/review/scripts/test-dispatch-panel.sh:294-312
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reused status sidecar can carry SCOUT_STATUS=parse-failed without SCOUT_FAIL_REASON; stdout omits the key and execution-issues use reason=unknown. reuse-empty-with-status fixture: parse-failed with no fail-reason line for downstream parsers expecting SCOUT_FAIL_REASON whenever SCOUT_STATUS=parse-failed. Default SCOUT_FAIL_REASON when sidecar says parse-failed but the key is missing (e.g. cached_parse_failed).
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/scout-dynamic-archetypes.sh:262-276
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Fence strip concatenates all fenced regions Multiple markdown code blocks can concatenate into invalid or wrong JSON reintroducing parse-failed in production Add multi-block regression test or change extraction to select the valid JSON block e.g last fenced segment or first jq-valid slice
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/review/scripts/test-dispatch-panel.sh:294-312
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale sidecar parse-failed without SCOUT_FAIL_REASON untested SCOUT_FAIL_REASON omitted on stdout and execution log uses unknown without assertion drift could hide regressions Add grep for SCOUT_FAIL_REASON absence or expected unknown and optional execution-issues.md check under REVIEW_TMPDIR
- **Suggested revision**: Address the concern above.


