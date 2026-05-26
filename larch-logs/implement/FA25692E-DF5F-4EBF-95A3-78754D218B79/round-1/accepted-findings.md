### FINDING_11: risk-integration: scripts/test-parse-codex-usage.sh:117-120
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required checked-in real Codex CLI JSONL smoke fixture is absent; harness uses inline synthetic token_usage JSON only. A future Codex CLI rename or move of usage fields will not fail CI until production runs; fail-closed then drops Codex cost lines silently (plan failure mode #1). Check in anonymized scripts/fixtures/parse-codex-usage/*.jsonl from codex exec --json and assert parse-codex-usage.sh output in test-parse-codex-usage.sh; fix test-parse-codex-usage.md wording.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-launch-review.sh:782-817
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SL-transient-retry-codex-7 lacks plan-specified assertion that events/ledger usage is parsed exactly once after retry. Stale or duplicated events across retries could double-count tokens without detection; rm -f is present in launcher but untested. After successful retry assert single-line events sidecar and expected per-bucket codex_review ledger row (or helper KV output).
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/parse-codex-usage.sh:36-49
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parser omits .msg.input_tokens-style coalesce paths. Codex emits TokenUsage fields under msg without a usage wrapper; parser returns 1 and launchers skip ledger rows on successful runs. Add .msg.input_tokens // … to each field probe; add a harness fixture for that shape.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/launch-review.sh:561
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Launchers redirect parse-codex-usage stderr to /dev/null. JSONL parse fail-closed after a long run shows zero Codex cost with no warning in sidecar or final-summary. Forward parser stderr to SIDECAR or emit one breadcrumb when events file is non-empty but parse returns empty.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/test-parse-codex-usage.sh:117-120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Codex CLI smoke uses inline heredoc, not a checked-in real capture. Installed CLI event shape changes may pass CI but fail in production until a manual run. Add anonymized checked-in fixture from real codex exec --json output.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan-required dedicated stderr-only Codex auth classification test is missing; only SL-transient-vs-auth-precedence covers stderr auth indirectly. Auth-on-stderr regression in launch-review could slip through while CI harness still passes. Add a stub case like test-launch-codex-ci.sh:177-194: stderr auth text, no JSONL, assert classification without successful retry.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/test-parse-codex-usage.sh:117-120
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan-required checked-in real Codex CLI JSONL smoke fixture is missing; only a synthetic inline heredoc is used. A future Codex CLI rename of event fields would not be caught by a fixture representing the real 0.125+ stream; fail-closed behavior hides cost silently in production while unit tests stay green. Add scripts/fixtures/codex-events-0.125.jsonl (anonymized real capture) and load it from test-parse-codex-usage.sh.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan-required dedicated stderr-routed Codex auth-failure classification test is absent; only auth-vs-transient precedence retry is covered. test-launch-codex-ci.sh pins stderr auth classification; launch-review has no parallel case, so a regression merging stdout into SIDECAR or breaking stderr-only auth detection in review could ship undetected. Add a codex review stub that writes auth text only to stderr with no JSONL and assert auth classification/failure recording without a successful usage path.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/test-launch-review.sh:782-817
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] SL-transient-retry Codex case omits the plan-mandated assertion that events.jsonl records usage exactly once after retry. A bug that accumulates stale usage across transient retries (missing rm -f or double-append) would not be caught; cost could be doubled while retry count assertions still pass. After successful retry assert single-line events sidecar and one per-bucket codex_review ledger row.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/test-parse-codex-usage.md:5
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Documentation claims a checked-in Codex CLI fixture that is not present as a separate file. Contributors may believe CLI drift is already pinned when only synthetic data is tested. Add the fixture file or correct the doc to match the harness.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/test-parse-codex-usage.sh:117-120
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] codex-cli-fixture is synthetic JSONL, not a real anonymized codex exec --json capture per plan. Codex CLI event shape drift may not fail CI until production runs. Check in a real anonymized fixture or document fixture as schema-only in test-parse-codex-usage.md.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing fail-closed harness: no codex stub with empty/missing JSONL asserting no vendor ledger row. Regression in launch-review token capture could reintroduce aggregate or zero rows without this test firing. Add stub with transcript-only stdout and assert no codex vendor row in ledger.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/test-parse-codex-usage.sh:117-120
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan asked for checked-in real Codex CLI JSONL; only inline synthetic fixture is used. Future CLI shape drift may pass tests but fail closed in production. Check in anonymized real codex exec --json output as a fixture file.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: scripts/launch-codex-implement.sh:308-309
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment still describes combined stdout/stderr sidecar redirect. Future edit may restore 2>&1 merge and break stderr auth plus JSONL capture. Update comment to document events.jsonl vs SIDECAR_LOG split.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: skills/implement/scripts/test-codex-implementer.sh:646
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment still references awk sidecar scrape. Misleading for maintainers only. Replace with parse-codex-usage.sh wording.
- **Suggested revision**: Address the concern above.


