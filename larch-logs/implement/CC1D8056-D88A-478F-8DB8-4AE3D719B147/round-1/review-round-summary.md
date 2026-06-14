# Review Round 1

- Mode: `diff`
- 16 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Citation budget does not stop in-flight HTTP/DNS work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: Global `--budget-seconds` expiry only cancels pending `ThreadPoolExecutor` futures; in-flight `fetch_url()` HTTP/DNS work keeps running until per-fetch timeouts. `ThreadPoolExecutor` shutdown waits on running workers, so validation can block past the budget and leave orphan network work after `SUMMARY` is emitted. This violates the migrated zero-orphan-worker / kill-in-flight contract from the retired bash harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Use killable worker/subprocess handles (as the plan specifies), or another mechanism that can interrupt blocking stdlib HTTP/DNS work on budget expiry; add the budget-harness Tests 20/21 coverage that was planned for `python/test_research.py`.
  - From codex-specialist-correctness-output.txt: Use killable subprocess workers or a non-waiting shutdown path, terminate exposed workers, and backfill UNKNOWN(timeout).
  - From cursor-specialist-edge-cases-output.txt: Use killable subprocess fetchers or shutdown(wait=False cancel_futures=True) with explicit cleanup; port budget/orphan pytest coverage.


### FINDING_10: Unreadable inputs crash instead of documented fail-soft paths
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `read_text` is used outside an `OSError` guard in `python/research.py` and `python/research_eval.py`. Permission-denied or otherwise unreadable report/validator inputs can crash instead of producing the documented degraded sidecar or exit `4`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Catch OSError around reads or check readability, then preserve the documented fail-soft outputs.


### FINDING_13: Missing budget-exhaustion / orphan-worker pytest coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Plan-required citation budget Tests 20/21 were not ported after deleting `test-validate-citations-budget.sh`. `make test-validate-citations-budget` can pass while budget kill semantics, `UNKNOWN(timeout)` backfill, fail-soft exit `0`, and zero-surviving-work behavior regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add pytest equivalents of old Tests 20/21 with injected clock/fetcher/worker seams.
  - From cursor-specialist-testing-output.txt: Add injected clock/fetcher/worker tests for parallel fetch, budget backfill as UNKNOWN(timeout), and zero surviving work after exit; align with ThreadPoolExecutor or subprocess kill semantics.
  - From dyn-test-replacement-output.txt: Add pytest cases with injected clock/fetcher/sleeper seams that mirror Tests 20/21: global budget expiry, sidecar timeout rows, exit `0`, and no surviving in-flight work; keep them runnable under the `test-validate-citations-budget` alias.


### FINDING_14: Research pytest matrix is far below retired harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: `python/test_research.py` omits large parts of the plan-mandated pytest matrix: HTTP reason-token cases, proxy bypass, quiet fd-3 routing for all four KV verbs, `BANNER_TEMPLATE` doc drift pin, findings-batch fixture matrix / `issue parse-input` round-trip, and full file-line failure-mode assertions. Regressions in rendering, validation, or contract streams can pass `make py-test` and migrated harness aliases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port bash-harness high-risk cases: BANNER_TEMPLATE drift, issue parse-input round-trip, file-line/git-root matrix, HTTP 403/405/501/redirect cases, per-verb quiet fd-3 tests.
  - From dyn-test-replacement-output.txt: Extend `test_fetch_url_reason_matrix_and_ssrf` (or split focused tests) with connector/resolver injection for each token, plus a CLI test that asserts `SUMMARY=...` is the last stdout/fd-3 line after validation.
  - From dyn-test-replacement-output.txt: Reuse the fd-3 wrapper for all four verbs with `LARCH_QUIET_DISABLE` unset and `IMPLEMENT_TMPDIR` set; assert contract bytes on fd 3 (or the preserved pipe), not incidental parent stdout.
  - From dyn-test-replacement-output.txt: Add a test that extracts the banner literal from `research-phase.md` §1.5 and asserts byte equality with `research.BANNER_TEMPLATE`, matching the old `test-research-banner.sh` contract.
  - From dyn-test-replacement-output.txt: Port the old harness fixture matrix into parametrized pytest cases, including a round-trip through `issue_create.parse_input_main` on rendered batch output.
  - From dyn-test-replacement-output.txt: Add explicit sidecar row assertions for each file-line failure mode from the old harness.


### FINDING_15: Eval pytest coverage missing plan-required negative and CLI paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: `python/test_research_eval.py` lacks plan-required eval tests: git show `--baseline` success, `--id` no-match exit `0`, validation-mode `--min-words` override, direct `CURSOR_EMPTY_RESPONSE`, inline TSV validation-mode acceptance, eval-set failure matrix, unreadable input exit `4`, usage exit `1`, and quiet routing for KV-emitting eval verbs such as `eval research`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed git runner baseline test, no-match --id test, and explicit --min-words validation-mode CLI tests.
  - From dyn-test-replacement-output.txt: Add pure-function tests for `validate_research_output(..., validation_mode=True)` with and without `min_words`, plus CLI tests for `--validation-mode --min-words N`.
  - From dyn-test-replacement-output.txt: Add validation-mode fixtures for inline TSV and a direct `CURSOR_EMPTY_RESPONSE` sentinel.
  - From dyn-test-replacement-output.txt: Port the old `test-eval-set-structure.sh` and `test-eval-research-baseline-flag.sh` failure matrix into parametrized pytest cases with monkeypatched `git`/`parse_eval_set` inputs.
  - From dyn-test-replacement-output.txt: Add an fd-3 quiet subprocess test for `eval research --smoke-test` (and optionally other KV emitters) with `LARCH_QUIET_DISABLE` unset.


### FINDING_16: `test-research-structure.sh` missing Python CLI call-site pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: The plan-required structural pins for `python/cli.py research run-planner`, `research validate-citations`, `research banner`, and `research render-findings-batch` were not added. Doc/call-site drift back to deleted `.sh` paths is not caught by `make test-research-structure`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-cutover-output.txt: Add Check N pins mirroring the updated `scripts/test-research-structure.md` contract: assert `python/cli.py research run-planner` in `research-phase.md` (both §1.1.b and §1.1.c), `research validate-citations` in `citation-validation-phase.md` / `SKILL.md`, and `research banner` / `render-findings-batch` in the Step 1.5 / Step 3 surfaces.


### FINDING_18: Missing static pin for collector §3.7 `VALIDATOR_CMD` cutover
- **Reviewer(s)**: dyn-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: `scripts/test-collect-agent-bash32.sh` pins the primary validator loop but not structured-reviewer NS-retry paths in collector §3.7. Those call sites are cut over in code, yet no grep pin ensures they keep `VALIDATOR_CMD=(python3 "$SCRIPT_DIR/../python/cli.py" eval validate-research-output)` and do not regress to a scalar `$VALIDATOR` or deleted `.sh` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-cutover-output.txt: Extend Case 1 (or add Case 7) to grep §3.7 for `VALIDATOR_CMD` + `eval validate-research-output` on both structured and substantive NS-retry branches, and assert no `validate-research-output.sh` literal remains in `collect-agent-results.sh`.


### FINDING_19: Research citation-validation docs still describe retired curl / broken paths
- **Reviewer(s)**: dyn-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: Operator docs are stale after the Python port. `docs/skills.md` cites a non-existent mashed path and curl contract; `citation-validation-phase.md` still documents curl-era fetch semantics in its Contract paragraph; and it still points at deleted `validate-citations.md` for reason-token vocabulary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-cutover-output.txt: Replace the citation with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" research validate-citations` and rewrite the SSRF paragraph to match `citation-validation-phase.md` / `python/research.py` (stdlib HTTPS, no proxy env, no normal URL redirects, DNS pinning, budget cancellation).
  - From dyn-callsite-cutover-output.txt: Rewrite line 5 to describe the Python validator behavior only, matching the invocation block at lines 29–38 and `python/research.py`; drop curl flag vocabulary from the Contract paragraph.
  - From dyn-callsite-cutover-output.txt: Retarget both references to `python/research.py` (or inline the reason vocabulary in this file) so Step 2.5 does not cite a retired sibling contract.


### FINDING_2: SSRF check misses RFC6598 100.64.0.0/10 carrier-grade NAT
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_private_hostname()` / `_is_private_ip()` do not treat `100.64.0.0/10` as private. Literal hosts such as `https://100.64.0.1/` can pass the private-host block because Python `ipaddress` does not mark that range private or reserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Add explicit 100.64.0.0/10 checks in `_is_private_ip()` for literal hosts and resolved IPs.


### FINDING_3: DNS failures emit `dns-error` instead of legacy `network-error`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: DNS-resolution failures now produce `UNKNOWN(dns-error)` instead of the preserved `UNKNOWN(network-error)` token. Sidecar consumers and tests pinned to the existing vocabulary can misclassify DNS/network failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Map socket.gaierror and DNS-resolution failures back to network-error unless intentionally bumping the contract.
  - From codex-specialist-edge-cases-output.txt: Map socket.gaierror paths to network-error or intentionally bump the contract with docs and tests.
  - From codex-specialist-testing-output.txt: Map socket.gaierror and no-resolution fetch failures to the preserved network-error token, or intentionally bump docs and tests.


### FINDING_4: Parallel DNS races on process-global `socket.setdefaulttimeout`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: `_resolve_public_ips()` mutates the process-global default socket timeout via `socket.setdefaulttimeout()` inside thread-pool workers while URL/DOI fetches run concurrently. Parallel citation validation can race on the global timeout and cause mis-timed or hung DNS/connect behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Avoid setdefaulttimeout in parallel workers; use per-call timeout boundaries or isolated resolver subprocesses.
  - From dyn-research-parity-output.txt: Avoid global socket timeout mutation; pass per-call timeouts into `socket.create_connection()` / resolver helpers, or isolate DNS resolution outside the shared global default.


### FINDING_5: Eval harness does not run the LLM judge
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: Ported `eval_research()` stubs judge execution. `judge_timeout` is discarded, `judge.txt` / `judge.stderr` are empty placeholders, and `row.json` / summary output omit `judge_total`, `judge_status`, and related legacy judge fields. Full eval runs no longer produce rubric judge scores.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Port `run_judge`, the rubric prompt, staged terminate/kill via `_run_with_timeout`, fail-closed `parse_judge_output`, and wire judge fields back into `row.json`, the summary table, and baseline export.
  - From cursor-specialist-edge-cases-output.txt: Port run_judge rubric subprocess, fail-closed parser, and --judge-timeout kill behavior from eval-research.sh.
  - From codex-specialist-edge-cases-output.txt: Port judge execution, fail-closed judge parsing, URL reputability counts, status mapping, markdown columns, and the previous baseline JSON schema.


### FINDING_6: `--write-baseline` emits wrong baseline schema (v1 flat rows)
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: `--write-baseline` writes `{"version": 1, "entries": [...]}` with flat scorer keys instead of the committed version-2 envelope with `harness_commit`, `generated_at`, nested `provenance`, judge fields, `wall_clock_seconds`, and `research_status`. Baseline/compare workflows become non-comparable with the retired harness and committed `eval-baseline.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Match the v2 envelope and per-entry field names from the retired `scripts/eval-research.sh`, and tighten `validate_baseline_json()` to require `version == 2` and the nested entry shape.
  - From codex-specialist-testing-output.txt: Port the judge subprocess, fail-closed parser, summary columns, and version-2 baseline JSON shape.


### FINDING_7: Research subprocess timeouts not mapped to legacy `research_status="timeout"`
- **Reviewer(s)**: dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: Research subprocess timeouts are reported as `status="exit-124"` instead of the legacy `research_status="timeout"` derived from `TIMED_OUT_AFTER=` in `research.stderr`. Downstream consumers keyed on the old status vocabulary will misclassify timed-out runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Map rc `124` (and/or `TIMED_OUT_AFTER` in stderr) to `research_status="timeout"` in `row.json` and the summary table, preserving the old token.


### FINDING_8: External-comparison path stubs `url-reputability.txt`
- **Reviewer(s)**: dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: For `external-comparison` entries, `url-reputability.txt` is created with `touch()` instead of running URL classification. The retired harness wrote `URL_HIGH` / `URL_LOW` / `URL_UNKNOWN` counts from `classify_url_reputability()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Port `classify_url_reputability()` and write the same KV sidecar content on the external-comparison path.


### FINDING_9: `validate_eval_set()` weakens retired structural checks
- **Reviewer(s)**: dyn-research-parity-output.txt
- **Severity**: important
- **Concern**: `validate_eval_set()` no longer enforces the Anthropic source literal pin and weakens adversarial-note checks to two `ADVERSARIAL` notes plus global substrings `fictitious` and `data` anywhere in the file, instead of the per-entry fictitious-mechanism and data-absence shapes from the old Check 6/8 semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-research-parity-output.txt: Restore the old Check 6/8 semantics: grep `research_eval.py` (or eval-set) for the Anthropic URL literal, and require one adversarial entry whose notes document fictitious/fabricated mechanism and one whose notes document data absence.


