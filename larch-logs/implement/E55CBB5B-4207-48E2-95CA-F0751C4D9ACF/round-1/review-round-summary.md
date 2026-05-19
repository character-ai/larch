# Review Round 1

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 3
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `correctness` `scripts/larch-log.sh:92`, `scripts/scout-dynamic-archetypes.sh:290` — The newly committed `.raw` scout sidecar is not always the raw Claude output. If Claude returns prose-wrapped fenced JSON, `scout-dynamic-archetypes.sh` calls `extract_valid_fenced_json "$raw_output" "$raw_output"`, which overwrites `${OUTPUT}.raw` with the extracted JSON before `write-round` commits it. Concrete scenario: Claude outputs `Here is the JSON:\n```json\n{...}\n````; the committed `scout-roundN-manifest.json.raw` loses the prose and fences, so the sidecar no longer supports debugging the actual model response. Write the fenced/normalized JSON to a separate temp file for parsing and leave `${OUTPUT}.raw` untouched; add a regression assertion for the existing `fence-with-prose` case.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/larch-log.sh:92`, `scripts/scout-dynamic-archetypes.sh:290` — The newly committed `.raw` scout sidecar is not always the raw Claude output. If Claude returns prose-wrapped fenced JSON, `scout-dynamic-archetypes.sh` calls `extract_valid_fenced_json "$raw_output" "$raw_output"`, which overwrites `${OUTPUT}.raw` with the extracted JSON before `write-round` commits it. Concrete scenario: Claude outputs `Here is the JSON:\n```json\n{...}\n````; the committed `scout-roundN-manifest.json.raw` loses the prose and fences, so the sidecar no longer supports debugging the actual model response. Write the fenced/normalized JSON to a separate temp file for parsing and leave `${OUTPUT}.raw` untouched; add a regression assertion for the existing `fence-with-prose` case.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/test-scout-dynamic-archetypes.sh:93-253
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] `assert_raw_matches` is not used for fence-wrapped scout cases where `.raw` content intentionally diverges from the stub fixture file. After doc fixes, fence regressions could slip without a test that pins the post-extraction `.raw` shape. Add expectations for stripped-json bytes (or document explicitly that only non-fence paths are cmp-stable).
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/scout-dynamic-archetypes.md (new ${OUTPUT}.raw invariant)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] New doc claims .raw is always subprocess-verbatim for every outcome. When Claude returns fence-wrapped JSON, scout replaces ${OUTPUT}.raw with extracted JSON (mv in extract_valid_fenced_json), so committed scout-roundN-manifest.json.raw can differ from true subprocess output; readers trust the wrong invariant. Align wording with actual behavior (verbatim only until fence normalization) or add a separate immutable raw artifact if verbatim is required.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/scout-dynamic-archetypes.md (new invariant bullet)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Doc claims scout `${OUTPUT}.raw` is committed verbatim via `larch-log.sh write-round`. Investigators comparing committed `round-N/scout-round*-manifest.json.raw` to the session tmpfile may believe redaction or staging failed because bytes differ after `larch_log_redact_file`. Clarify: on-disk sidecar next to OUTPUT is verbatim; committed copy is staged through the same tmpdir/secret redaction as other round artifacts (see `stage_round_artifact` + `larch_log_redact_file`).
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/scout-dynamic-archetypes.md:22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New invariant claims scout `${OUTPUT}.raw` is verbatim for every Claude outcome and is committed unchanged by write-round. An operator diffs round-N `scout-round*-manifest.json.raw` against the live subprocess transcript after a fenced-json scout success, or audits secrets, and assumes byte identity with launcher stdout; committed files are redacted (`larch_log_redact_file`), fence success rewrites `.raw` to extracted JSON, and `--max-archetypes 0` never creates `.raw`. Reword to separate launcher capture, optional in-place fence extraction, redaction on `write-round`, and the max-archetypes-zero no-launch path.
- **Suggested revision**: Address the concern above.


