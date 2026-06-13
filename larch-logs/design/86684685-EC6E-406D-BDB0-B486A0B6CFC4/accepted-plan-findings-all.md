### FINDING_1: Validation ingestion misses retry/REVIEWER_FILE sidecar paths
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-token-env, Codex-dyn-token-env, Cursor-dyn-prompt-harness, Codex-dyn-prompt-harness
- **Severity**: important
- **Concern**: The planned validation-phase ingestion loop only walks fixed `COLLECT_ARGS` paths (`cursor-validation-output.txt`, `codex-validation-output.txt`) and does not mirror research-phase candidate-path expansion. After `collect-agent-results.sh` runs (including with `--substantive-validation`), successful or retried lanes can publish prose to the fixed stems while billable `.token-record` sidecars sit beside `REVIEWER_FILE` or derived `*-retry.txt` / `*-ns-retry.txt` outputs. Ingesting only the original `COLLECT_ARGS` paths drops validation Codex/Cursor usage from NDJSON and the active ledger, defeating Item 5 parity with research-phase ingestion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After parsing collect-agent-results.sh stdout map each COLLECT_ARGS slot in order to its fixed validation output path then for each slot dedupe candidate paths in research order REVIEWER_FILE fixed path ${fixed%.txt}-retry.txt ${fixed%.txt}-ns-retry.txt ingest each existing non-empty SIDECAR with the same append-record and env-cleaned record-vendor-sidecar block as research-phase.md
  - From Codex-Arch: Reuse the research-phase candidate-path logic: include REVIEWER_FILE, fixed output, retry, and ns-retry paths, then dedupe before ingestion
  - From Cursor-Innovation: Mirror the research-phase candidate-path table (fixed path, `-retry.txt`, `-ns-retry.txt`, and collector REVIEWER_FILE when available), dedupe, then ingest; or move ingestion to immediately after collector output parse so REVIEWER_FILE is known
  - From Codex-Innovation: Mirror the research-phase candidate-path logic: include REVIEWER_FILE, the fixed output, retry, and ns-retry candidates, then dedupe before ingestion.
  - From Cursor-Pragmatic: Mirror research-phase.md candidate-path selection: map collector rows to validation stems, dedupe REVIEWER_FILE plus fixed path plus -retry and -ns-retry variants before append-record and record-vendor-sidecar; extend test-research-structure.sh pins if needed
  - From Codex-Pragmatic: Mirror the research-phase candidate-path logic for validation: after collection, include collector REVIEWER_FILE plus the original output and its -retry and -ns-retry variants, dedupe paths, then ingest each non-empty .token-record with the planned clean RESEARCH_TMPDIR env
  - From Cursor-Requirements: Mirror research-phase candidate expansion: for each COLLECT_ARGS path dedupe and ingest `${OUTPUT}`, `${OUTPUT%.txt}-retry.txt`, and `${OUTPUT%.txt}-ns-retry.txt` when sidecars exist; state ingestion is independent of collector STATUS; extend scripts/test-research-structure.sh pins to require those retry suffix tokens in validation-phase.md
  - From Cursor-dyn-token-env: Reorder validation ingestion to after parsing collector `REVIEWER_FILE` rows (mirror skills/research/references/research-phase.md:186-215): for each validation lane build deduped candidate paths from `REVIEWER_FILE`, the fixed `COLLECT_ARGS` path, `${path%.txt}-retry.txt`, and `${path%.txt}-ns-retry.txt`, then run append-record and env-cleaned record-vendor-sidecar per existing sidecar
  - From Codex-dyn-token-env: Mirror research-phase candidate enumeration: collector REVIEWER_FILE, original path, *-retry.txt, and *-ns-retry.txt, deduped before append-record and record-vendor-sidecar
  - From Cursor-dyn-prompt-harness: collect-agent-results.sh uses the same retry machinery for --validation-mode (scripts/collect-agent-results.sh:1001-1156) and can set REVIEWER_FILE to cursor-validation-output-retry.txt or codex-validation-output-ns-retry.txt; token sidecars sit next to the actual output file, so COLLECT_ARGS-only ingestion drops usage on validation retry paths Add validation candidate-path resolution adapted from research-phase.md:188-188 (REVIEWER_FILE first, fixed COLLECT_ARGS path, ${fixed%.txt}-retry.txt, ${fixed%.txt}-ns-retry.txt; dedupe) for cursor-validation-output.txt and codex-validation-output.txt
  - From Codex-dyn-prompt-harness: Parse collector output enough to build the same candidate set as research-phase: REVIEWER_FILE first, fixed output, derived -retry.txt, and derived -ns-retry.txt, deduped. Keep ingestion after collect settles and before runtime fallback handling. Add structural pins for those candidate tokens, not unrelated prose.


### FINDING_2: Ship-pr test harness env-prefixed python3 bypasses shell-function stubs
- **Reviewer(s)**: Codex-Arch, Codex-dyn-token-env
- **Severity**: important
- **Concern**: The planned change to `ship_pr_ingest_token_record_once` uses `env -u ... python3`, which executes a PATH binary rather than a Bash `python3()` shell function. The updated `scripts/test-ship-pr-rebase.sh` harness relies on function-only stubs to assert env cleanup; after the change the harness may invoke real `python3`, miss env assertions, or fail unpredictably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Replace the function-only stubs with a temporary PATH python3 executable stub, then assert env cleanup from that stub
  - From Codex-dyn-token-env: Use a PATH-front executable python3 stub, or otherwise intercept env-executed python3, and log the record-vendor-sidecar environment there


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ci_monitor.py:1062-1070; python/agents.py:2470-2501
- **Concern**: [SCOPE-REDUCTION] Output-path fallback would ingest Claude CI sidecars on the Python ship path. Scenario: ci_monitor calls ingest_launcher_token_sidecar for every tier. Claude writes ${output}.token-record and already records active ledger usage, but emits no TOKEN_RECORD. The proposed fallback would ingest Claude again and double-count active-ledger usage.
- **Proposed resolution**: Gate the fallback or call site to codex and cursor only, matching scripts/ship-pr.sh. Do not fallback-ingest TOOL=claude sidecars unless a separate feature asks for it.


### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:2857-2895; python/ci_monitor.py:1062-1070; python/agents.py:2470-2501
- **Concern**: [SCOPE-REDUCTION] The proposed ${output}.token-record fallback is not limited to the Codex/Cursor recovery sidecars in scope. Scenario: ci_monitor invokes ingest_launcher_token_sidecar for codex, cursor, and claude tiers; launch_claude_ci writes a .token-record without TOKEN_RECORD stdout and _record_claude_ci_usage already records claude_sub directly, so the new fallback would ingest Claude too and double-count active ledger rows
- **Proposed resolution**: Gate the fallback by tier/tool or parse the sidecar and skip TOOL=claude for fallback discovery; keep stdout TOKEN_RECORD handling unchanged and cover the skip in python/test_agents.py or the ci_monitor harness


### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:1062-1069; python/agents.py:2483-2502
- **Concern**: [SCOPE-REDUCTION] Python ship fallback is not tier-gated. Scenario: ci_monitor calls ingest_launcher_token_sidecar for every tier. The planned ${output}.token-record fallback would also ingest Claude CI sidecars, but launch_claude_ci_main already records Claude active-ledger usage. A Claude winning tier can be double-counted and the plan exceeds Bash parity, which only ingests Codex/Cursor sidecars.
- **Proposed resolution**: Gate CI fallback ingestion to codex/cursor in ci_monitor, or make the helper tier-aware and skip fallback ingestion for claude. Add a focused test that a Claude .token-record without TOKEN_RECORD stdout is not ingested.


### FINDING_10:
- **Reviewer(s)**: Codex-dyn-ship-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:1040-1069; python/agents.py:2857-2894; scripts/ship-pr.sh:1686-1725; python/config.py:112-113
- **Concern**: [SCOPE-REDUCTION] Planned fallback sidecar discovery is too broad and can ingest stale sidecars. Scenario: Python uses stable ci-fix-{tier}.out paths and calls ingestion for every tier, including claude, while Bash uses a timestamped base and only ingests codex/cursor; a prior ${output}.token-record can be picked up when the current launcher emitted no TOKEN_RECORD and produced no fresh sidecar
- **Proposed resolution**: Before launching, remove the expected fallback sidecar or otherwise prove freshness, and gate fallback to codex/cursor or an explicit allow_output_fallback flag at the ci_monitor call site



