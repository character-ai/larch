### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/check-reviewers.sh:196-202
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Codex probe silently continues with empty model args when agent-model-args.sh fails Step 0 can mark CODEX_PRESENT=true on default-model probe while reviewers hit quota on gpt-5.5 with effort reproducing silent 2-judge degradation Treat agent-model-args failure as probe failure or log a visible warning; document fail-open behavior in check-reviewers.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: **risk-integration** `skills/design/scripts/plan-review-loop.sh:1045` — Pretty-printed sentinels where the first line is only `{` and `"no_issues_found": true` appears on a later line will not match the regex, so operators can still see the false WARN on an otherwise valid no-findings response. Prompts ask for a single-line literal, but launch-review already treats trailing-note and multi-line shapes as valid in some paths. **Suggested fix:** Either document single-line-only suppression in `plan-review-loop.md`, or scan the file the way `validate-research-output.sh` does (first line, then full trimmed body) before suppressing.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-loop.sh:1045` — Pretty-printed sentinels where the first line is only `{` and `"no_issues_found": true` appears on a later line will not match the regex, so operators can still see the false WARN on an otherwise valid no-findings response. Prompts ask for a single-line literal, but launch-review already treats trailing-note and multi-line shapes as valid in some paths. **Suggested fix:** Either document single-line-only suppression in `plan-review-loop.md`, or scan the file the way `validate-research-output.sh` does (first line, then full trimmed body) before suppressing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: **architecture** `scripts/check-reviewers.sh:196-209` — When `agent-model-args.sh --tool codex --with-effort` fails, the probe continues with no `-m`/effort (stderr discarded), while `launch-review.sh` fails closed and aborts the Codex slot. With a bad `LARCH_CODEX_MODEL` (or similar), the probe can succeed on Codex’s default model and set `CODEX_PRESENT=true`, while every real review launch fails at model-args preflight — the same class of “probe healthy, panel dead” confusion, now with mismatched failure modes. This mirrors the Cursor probe pattern but is more likely to bite Codex because production launches always require model args. **Suggested fix:** On `agent-model-args.sh` failure, either fail the Codex probe (align with launch) or log a loud `Warnings` breadcrumb and force `CODEX_PRESENT=false`; add a `test-check-reviewers.sh` case with an invalid `LARCH_CODEX_MODEL`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **architecture** `scripts/check-reviewers.sh:196-209` — When `agent-model-args.sh --tool codex --with-effort` fails, the probe continues with no `-m`/effort (stderr discarded), while `launch-review.sh` fails closed and aborts the Codex slot. With a bad `LARCH_CODEX_MODEL` (or similar), the probe can succeed on Codex’s default model and set `CODEX_PRESENT=true`, while every real review launch fails at model-args preflight — the same class of “probe healthy, panel dead” confusion, now with mismatched failure modes. This mirrors the Cursor probe pattern but is more likely to bite Codex because production launches always require model args. **Suggested fix:** On `agent-model-args.sh` failure, either fail the Codex probe (align with launch) or log a loud `Warnings` breadcrumb and force `CODEX_PRESENT=false`; add a `test-check-reviewers.sh` case with an invalid `LARCH_CODEX_MODEL`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: **risk-integration** `scripts/check-reviewers.sh:207-209` vs `scripts/launch-review.sh:555-562` — Even with matching model args, the probe still omits production-only argv (`--add-dir`, `-c` trust config, `--json`, full review prompt). Failures tied to sandbox dir, trust config, or prompt/load can still yield `CODEX_PRESENT=true` and silent mid-run degradation (plan defers circuit-breaker). **Suggested fix:** Accept as documented residual risk, or extend the probe with the smallest additional argv that reproduces #3248-class failures without a full review prompt.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **risk-integration** `scripts/check-reviewers.sh:207-209` vs `scripts/launch-review.sh:555-562` — Even with matching model args, the probe still omits production-only argv (`--add-dir`, `-c` trust config, `--json`, full review prompt). Failures tied to sandbox dir, trust config, or prompt/load can still yield `CODEX_PRESENT=true` and silent mid-run degradation (plan defers circuit-breaker). **Suggested fix:** Accept as documented residual risk, or extend the probe with the smallest additional argv that reproduces #3248-class failures without a full review prompt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: **correctness** `skills/design/scripts/plan-review-loop.sh:1045` — Only the JSON sentinel is recognized; legacy `NO_ISSUES_FOUND` (still whitelisted in `launch-review.sh` and prompts) does not suppress the WARN. Reviewers emitting the legacy token with `STATUS=OK` and an empty TSV fragment will keep getting the false empty-rows WARN. **Suggested fix:** If legacy output is still in the wild, extend the guard with the same `NO_ISSUES_FOUND` checks used upstream; otherwise document JSON-only suppression and steer prompts/tests to JSON only.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:1045` — Only the JSON sentinel is recognized; legacy `NO_ISSUES_FOUND` (still whitelisted in `launch-review.sh` and prompts) does not suppress the WARN. Reviewers emitting the legacy token with `STATUS=OK` and an empty TSV fragment will keep getting the false empty-rows WARN. **Suggested fix:** If legacy output is still in the wild, extend the guard with the same `NO_ISSUES_FOUND` checks used upstream; otherwise document JSON-only suppression and steer prompts/tests to JSON only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: `4a85030f4` — Fix misleading /design review panel Codex probe and empty-rows WARN (#3402)
- **Reviewer**: dyn-probe-launch-parity-output.txt
- **Concern**: - `4a85030f4` — Fix misleading /design review panel Codex probe and empty-rows WARN (#3402)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: correctness: scripts/check-reviewers.sh:196-209
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Codex probe silently omits model args when agent-model-args.sh fails but launch-review fails closed on the same failure Step 0 probe succeeds with default model; panel provisions Codex; every real review exits 7 like issue #3402 Fail probe or set CODEX_PRESENT=false when model-args preflight fails; or document fail-open and add a test
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: `d69a6ab82` — chore(larch-logs): flush implement run (orthogonal)
- **Reviewer**: dyn-probe-launch-parity-output.txt
- **Concern**: - `d69a6ab82` — chore(larch-logs): flush implement run (orthogonal)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: **architecture** `scripts/check-reviewers.sh:207-209` vs `scripts/launch-review.sh:555-560` — Production Codex reviewer launches place `agent-model-args.sh` tokens **before** `-c "$TRUST_CONFIG_ARG"`, `--output-last-message`, and `--json`, but the strengthened probe inserts `${_probe_model_args[@]}` **after** `--output-last-message "$probe_out"`. Both sides are still “before `--`”, but the relative position of model/effort flags differs from `launch-review.sh`. If `codex exec` applies model/quota binding in argv order (or documents order-sensitive flags), the probe can still exercise a different invocation shape than the calls that failed with `exit 7` in #3248. **Suggested fix:** Reorder the probe to match the reviewer spine: `codex exec --sandbox read-only -C "$PWD" ${_probe_model_args[@]+"${_probe_model_args[@]}"} … --output-last-message "$probe_out" … -- "Respond with OK"` (add the minimal trust `-c` only if production requires it for parity), and extend `scripts/test-check-reviewers.sh` to assert token order (e.g. `-m` appears before `--output-last-message` in the argv log), not only that `sentinel-model` appears somewhere.
- **Reviewer**: dyn-probe-launch-parity-output.txt
- **Concern**: - **architecture** `scripts/check-reviewers.sh:207-209` vs `scripts/launch-review.sh:555-560` — Production Codex reviewer launches place `agent-model-args.sh` tokens **before** `-c "$TRUST_CONFIG_ARG"`, `--output-last-message`, and `--json`, but the strengthened probe inserts `${_probe_model_args[@]}` **after** `--output-last-message "$probe_out"`. Both sides are still “before `--`”, but the relative position of model/effort flags differs from `launch-review.sh`. If `codex exec` applies model/quota binding in argv order (or documents order-sensitive flags), the probe can still exercise a different invocation shape than the calls that failed with `exit 7` in #3248. **Suggested fix:** Reorder the probe to match the reviewer spine: `codex exec --sandbox read-only -C "$PWD" ${_probe_model_args[@]+"${_probe_model_args[@]}"} … --output-last-message "$probe_out" … -- "Respond with OK"` (add the minimal trust `-c` only if production requires it for parity), and extend `scripts/test-check-reviewers.sh` to assert token order (e.g. `-m` appears before `--output-last-message` in the argv log), not only that `sentinel-model` appears somewhere.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: **risk-integration** `scripts/check-reviewers.sh:207-209` vs `scripts/launch-review.sh:555-561` — Reviewer launches always pass `--json` and route usage-limit/quota signals through `${OUTPUT}.events.jsonl` (see `launch-review.sh:584-587`), while the Codex probe omits `--json` entirely. Model alignment fixes the “default model vs `gpt-5.5`” gap from the plan, but quota/limit failures that only surface on the JSON event stream can still leave `CODEX_PRESENT=true` at Step 0 and fail every real `--json` review call later—the exact silent-degradation shape the issue describes, via a different mechanism. **Suggested fix:** Either add a minimal `--json` + discarded events file to the probe (still with the trivial prompt), or document this as an accepted asymmetry in `scripts/check-reviewers.md` and add a follow-up for quota-shaped probes; do not claim full “mirrors production” parity without one of those.
- **Reviewer**: dyn-probe-launch-parity-output.txt
- **Concern**: - **risk-integration** `scripts/check-reviewers.sh:207-209` vs `scripts/launch-review.sh:555-561` — Reviewer launches always pass `--json` and route usage-limit/quota signals through `${OUTPUT}.events.jsonl` (see `launch-review.sh:584-587`), while the Codex probe omits `--json` entirely. Model alignment fixes the “default model vs `gpt-5.5`” gap from the plan, but quota/limit failures that only surface on the JSON event stream can still leave `CODEX_PRESENT=true` at Step 0 and fail every real `--json` review call later—the exact silent-degradation shape the issue describes, via a different mechanism. **Suggested fix:** Either add a minimal `--json` + discarded events file to the probe (still with the trivial prompt), or document this as an accepted asymmetry in `scripts/check-reviewers.md` and add a follow-up for quota-shaped probes; do not claim full “mirrors production” parity without one of those.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: **risk-integration** `scripts/check-reviewers.sh:196-201` vs `scripts/launch-review.sh:489-516` — On `agent-model-args.sh` failure the probe swallows stderr and runs `codex exec` with **no** model args (`2>/dev/null`, empty `_probe_model_args`), while `launch-review.sh` fails closed before spawn. That recreates the pre-fix failure mode (trivial/default-model probe passes, `gpt-5.5` reviewer calls fail) whenever model-arg resolution fails transiently at probe time. The Cursor probe already used this pattern; this branch copies it onto Codex as part of the fix. **Suggested fix:** Treat `agent-model-args.sh` non-zero exit as probe failure (`return 1` / `CODEX_PRESENT=false`) or retry once, matching launch preflight semantics; add a harness case where the stub `agent-model-args.sh` exits non-zero and asserts `CODEX_PRESENT=false`.
- **Reviewer**: dyn-probe-launch-parity-output.txt
- **Concern**: - **risk-integration** `scripts/check-reviewers.sh:196-201` vs `scripts/launch-review.sh:489-516` — On `agent-model-args.sh` failure the probe swallows stderr and runs `codex exec` with **no** model args (`2>/dev/null`, empty `_probe_model_args`), while `launch-review.sh` fails closed before spawn. That recreates the pre-fix failure mode (trivial/default-model probe passes, `gpt-5.5` reviewer calls fail) whenever model-arg resolution fails transiently at probe time. The Cursor probe already used this pattern; this branch copies it onto Codex as part of the fix. **Suggested fix:** Treat `agent-model-args.sh` non-zero exit as probe failure (`return 1` / `CODEX_PRESENT=false`) or retry once, matching launch preflight semantics; add a harness case where the stub `agent-model-args.sh` exits non-zero and asserts `CODEX_PRESENT=false`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: **architecture** `scripts/test-check-reviewers.sh:161` — The new test only checks `grep -Fq 'sentinel-model'` in the logged argv. That is usually sufficient because `agent-model-args.sh` emits `-m` and `sentinel-model` on separate lines (`scripts/agent-model-args.sh:158-159`), but it does not prove parity with `launch-review.sh` (no assertion on `-c model_reasoning_effort=…`, flag order, or absence of `--json`). A regression that dropped `--with-effort` but kept a coincidental `sentinel-model` elsewhere could still pass. **Suggested fix:** Assert the log contains a line exactly `sentinel-model` immediately after `-m`, and optionally that `--with-effort` produced a separate `-c` line—tightening the test into a structural parity check, not a substring check.
- **Reviewer**: dyn-probe-launch-parity-output.txt
- **Concern**: - **architecture** `scripts/test-check-reviewers.sh:161` — The new test only checks `grep -Fq 'sentinel-model'` in the logged argv. That is usually sufficient because `agent-model-args.sh` emits `-m` and `sentinel-model` on separate lines (`scripts/agent-model-args.sh:158-159`), but it does not prove parity with `launch-review.sh` (no assertion on `-c model_reasoning_effort=…`, flag order, or absence of `--json`). A regression that dropped `--with-effort` but kept a coincidental `sentinel-model` elsewhere could still pass. **Suggested fix:** Assert the log contains a line exactly `sentinel-model` immediately after `-m`, and optionally that `--with-effort` produced a separate `-c` line—tightening the test into a structural parity check, not a substring check.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: `4a85030f4` — Fix misleading /design review panel Codex probe and empty-rows WARN (#3402)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `4a85030f4` — Fix misleading /design review panel Codex probe and empty-rows WARN (#3402)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: `d69a6ab82` — chore(larch-logs): flush implement run (run-log artifact; not part of the functional diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `d69a6ab82` — chore(larch-logs): flush implement run (run-log artifact; not part of the functional diff) ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: **`scripts/check-reviewers.sh` (Codex probe)** — Model args are built via the existing `agent-model-args.sh` → temp file → bash array → `${_probe_model_args[@]+"${_probe_model_args[@]}"}` path, matching the Cursor probe and production `launch-review.sh` invocation. Tokens are validated for control characters and passed as separate argv elements to `codex exec`, not interpolated into a shell string, so there is no new command-injection surface. Env-sourced model names go through the same validation as production launches.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **`scripts/check-reviewers.sh` (Codex probe)** — Model args are built via the existing `agent-model-args.sh` → temp file → bash array → `${_probe_model_args[@]+"${_probe_model_args[@]}"}` path, matching the Cursor probe and production `launch-review.sh` invocation. Tokens are validated for control characters and passed as separate argv elements to `codex exec`, not interpolated into a shell string, so there is no new command-injection surface. Env-sourced model names go through the same validation as production launches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: **`skills/design/scripts/plan-review-loop.sh` (sentinel suppression)** — The change only gates emission of a diagnostic `WARN=` line. Finding extraction still runs from the structured TSV sidecar; an empty fragment still contributes zero findings. `STATUS=OK` is required before the branch runs, and `_rf` is a session-scoped collector path under `$DESIGN_TMPDIR`, not arbitrary user input. Suppressing the false-positive WARN does not weaken authn/authz, secret handling, or trust-boundary enforcement elsewhere in the pipeline.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **`skills/design/scripts/plan-review-loop.sh` (sentinel suppression)** — The change only gates emission of a diagnostic `WARN=` line. Finding extraction still runs from the structured TSV sidecar; an empty fragment still contributes zero findings. `STATUS=OK` is required before the branch runs, and `_rf` is a session-scoped collector path under `$DESIGN_TMPDIR`, not arbitrary user input. Suppressing the false-positive WARN does not weaken authn/authz, secret handling, or trust-boundary enforcement elsewhere in the pipeline.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: **Tests** — Stub codex uses `"$@"` append to a test-controlled log path; test-only, no production trust-boundary change.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Tests** — Stub codex uses `"$@"` append to a test-controlled log path; test-only, no production trust-boundary change. No injection, secret leakage, auth bypass, unsafe deserialization, path traversal, or other security regressions were identified in the functional commit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: **risk-integration** `skills/design/scripts/plan-review-loop.sh:1045` — Sentinel suppression uses a line-anchored grep (`^[[:space:]]*\{"no_issues_found`) and does not require `"no_issues_found": true` or parse JSON. A line like `{"no_issues_found": false}` or `{"no_issues_found": null}` still suppresses the WARN while producing zero TSV rows, so a malformed or non-committal reviewer response can look like a healthy zero-findings slot. Elsewhere the repo tends to validate with `jq` (e.g. `validate-research-output.sh`). **Suggested fix:** Tighten the guard (e.g. `jq -e '.no_issues_found == true'` on the first JSON object line, or match the full literal `{"no_issues_found": true}`) and add a harness case for `false` / pretty-printed multi-line JSON so suppression tracks real zero-findings semantics.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-loop.sh:1045` — Sentinel suppression uses a line-anchored grep (`^[[:space:]]*\{"no_issues_found`) and does not require `"no_issues_found": true` or parse JSON. A line like `{"no_issues_found": false}` or `{"no_issues_found": null}` still suppresses the WARN while producing zero TSV rows, so a malformed or non-committal reviewer response can look like a healthy zero-findings slot. Elsewhere the repo tends to validate with `jq` (e.g. `validate-research-output.sh`). **Suggested fix:** Tighten the guard (e.g. `jq -e '.no_issues_found == true'` on the first JSON object line, or match the full literal `{"no_issues_found": true}`) and add a harness case for `false` / pretty-printed multi-line JSON so suppression tracks real zero-findings semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

