### FINDING_6: Extractor misses markdown-bulleted Location and Concern forms
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: blocking
- **Concern**: Extractors miss the repo's common markdown-bulleted `- **Location**:` and `- **Concern**:` forms (including directory-only or bare repo paths). Without normalizing those shapes, `file_path` or `concern` go empty or carry markdown, collapsing unrelated findings under one hash and breaking dedup/ledger backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Strip the bullet and bold prefix before matching `Location` and `Concern`, and accept plain repo-relative paths without a `:line` suffix
  - From Codex-Innovation: Teach the extractor to parse the bulletized `- **Concern**:` and `- **Location**:` / `- **File**:` shapes already present in committed logs, or reuse the same parser that normalizes existing review artifacts before hashing.


### FINDING_7: Hash path selection depends on mutable repo file existence
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: `extract_target_path` prefers the first normalized path that exists under `repo_root`, so the same finding can hash differently after an unrelated merge creates or removes a candidate path. That defeats the ledger backstop and allows duplicates or re-filing on rerun.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Choose the hash path from stable text order or a frozen TSV field only, and reserve repo-root existence checks for stale/verifier binding, not for the hash key
  - From Codex-Innovation: Make path selection depend only on a stable textual rule, or persist the chosen file path from prepare; do not consult live file existence when computing the hash key.
  - From Codex-Pragmatic: Make path selection stable from the finding text alone. Use repo existence only after hashing, for stale or verification decisions.


### FINDING_8: Launch-failed and parse-failed verdicts lack durable per-candidate staging
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: A transient launcher outage, parse failure, or location mismatch leaves no durable per-candidate status. The plan records only aggregate `LAUNCH_FAILURES` and no launch-failed stub, so `finalize` cannot distinguish retryable failures from successful launches that never ingested and may permanently ledger a retryable failure or misledger stranded candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Persist a status row for every candidate on every ingest outcome, not just dirty-tree and confirmed verdicts, and have finalize read that durable status file instead of inferring missing rows as verification-failed.
  - From Codex-Pragmatic: Persist a per-candidate launch-failed status row or sidecar, and have finalize and record exclude those hashes from the missing-ingest fallback.


