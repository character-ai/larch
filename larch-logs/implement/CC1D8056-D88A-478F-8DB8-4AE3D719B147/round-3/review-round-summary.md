# Review Round 3

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Citation sidecar omits domain-credibility advisory block
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The Python citation-validation sidecar no longer renders the per-domain allow/unknown credibility block (`<details>` table). Synthesis reports citing HTTPS URLs get only the claims ledger, so operators lose tier visibility, sidecars no longer match the documented schema in `skills/research/references/citation-validation-phase.md`, and behavior diverges from bash byte-identical reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port host tier classification and append the documented `<details>` credibility table in `_sidecar()`; add pytest coverage
  - From codex-generic-output.txt: Restore the allow/unknown domain credibility table in `_sidecar()` for URL and DOI hosts, or deliberately remove the documented contract and tests if the advisory is being dropped.


### FINDING_12: DNS timeout can block until global citation budget
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_resolve_public_ips()` returns `UNKNOWN(timeout)` after `future.result(timeout=...)`, but the underlying `getaddrinfo` thread is not killable, and the parent fetch loop in `python/research.py:293-323` only kills the subprocess at `budget_seconds`. A slow DNS lookup with `--per-fetch-timeout 1 --budget-seconds 300` can hang for about 300 seconds instead of one per-fetch timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Enforce a per-process deadline in `_parallel_fetch_results`, killing each fetch subprocess after `per_fetch_timeout` as well as at the global budget, or move DNS into a worker process that the child exits with `os._exit` after timeout.


### FINDING_6: `fetch_url` ignores non-default HTTPS port
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `fetch_url` and `_PinnedHTTPSConnection` always connect to port 443 and ignore `urlparse(url).port`. A synthesis citing `https://example.com:8443/doc` performs HEAD against port 443 while the Host header says `:8443`, so the ledger can PASS or FAIL the wrong endpoint and mislead `/research` citation validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pass `parsed.port` or 443 into `HTTPSConnection` and the connector seam; add a pytest for a non-default HTTPS port.


### FINDING_7: Case 5b retry-success degraded fails in `test-collect-agent-bash32.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retry output is not emitted as `REVIEWER_FILE=*-retry.txt` with `STATUS=CURSOR_EMPTY_RESPONSE`. `make lint` → `test-harnesses-12` → `test-collect-agent-bash32` exits 1 despite green pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Debug retry artifacts and stdout; check `META_TIMEOUT=1` retry timeout vs `_classify_sentinel_status` on `*-retry.txt`; stabilize fixture or fix collector retry degraded mapping.


