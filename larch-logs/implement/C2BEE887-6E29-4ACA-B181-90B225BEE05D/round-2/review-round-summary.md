# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_5: `_accepted_reviewers_from_classification` does not split comma-separated TSV reviewer cells
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_accepted_reviewers_from_classification` (`python/progress_report.py:689-691`) treats `finding_reviewers` as one reviewer string, but real TSV rows contain comma-separated reviewer names. A row like `Cursor-Arch, Codex-Innovation` is counted as one combined label, so the `/design` Top reviewers fallback reports wrong names and counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Split the reviewer cell on commas, strip each name, drop empties, and append each reviewer separately.


### FINDING_6: `_design_collector_field` can copy stale failed records when `failure_count` is zero
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_design_collector_field` (`python/progress_report.py:1803-1814`) reads the design-root `collector-results.env` even when `failure_count` is zero. If a later pruned or empty round has no fresh collector file, stale failed records from an earlier round can be copied into the new round meta and render false reviewer failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Return `""` immediately when `failure_count <= 0`, or only use the root collector file when it is known to belong to the current round.


### FINDING_7: `resolve_collector_stderr_tail_file` omits `ns-retry` stderr-tail probe
- **Reviewer(s)**: codex-generic-output.txt, dyn-diagnostics-parity-output.txt
- **Severity**: important
- **Concern**: `resolve_collector_stderr_tail_file` (`python/collect_results.py:756-775`) checks only `{base}-retry.txt.stderr-tail` before phase fallbacks and never probes `{base}-ns-retry.txt.stderr-tail`. The deleted `scripts/lib-failed-agent-stderr-tail.sh` and the G10 plan required ordering `retry → ns-retry → launch-stderr → .stderr-tail`. After this branch deletes that Bash library, a reviewer slot with only an ns-retry stderr-tail sidecar (no retry tail) skips ns-retry and falls through to launch-stderr or the primary `.stderr-tail`, so collector chat tails and dedupe signatures can show the wrong failure or nothing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Check `f"{base}-ns-retry.txt.stderr-tail"` immediately after the regular retry tail and before launch-stderr / `.stderr-tail` fallbacks.
  - From dyn-diagnostics-parity-output.txt: After the retry-tail check, add the same ns-retry probe Bash used (`{base}-ns-retry.txt.stderr-tail` when non-empty), then keep the existing phase/launch-stderr loop; add a pytest case with only an ns-retry tail present.


