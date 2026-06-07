### FINDING_17: [OUT_OF_SCOPE] `launch-claude-ci.sh` exits 0 regardless of `LAUNCHER_EXIT`
- **Reviewer(s)**: dyn-cli-envelope-output.txt
- **Severity**: latent
- **Concern**: The CI launcher always exits `0`, requiring callers to parse `LAUNCHER_EXIT=` from stdout instead of relying on process exit status. The reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-envelope-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] cache 5m/1h collapse is an accepted v1 trade-off
- **Reviewer(s)**: dyn-cli-envelope-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that collapsing cache 5m/1h into a single `cache_create` bucket is documented as an accepted v1 trade-off, not a new regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-envelope-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] append-token-record rewrites CI Claude token-records to unknown
- **Reviewer(s)**: dyn-cost-pipeline-output.txt
- **Severity**: latent
- **Concern**: The new CI launcher writes `TOOL=claude` into `.token-record`, but `append-token-record.sh` only accepts `codex|cursor` and rewrites other tools to `unknown`, weakening the NDJSON audit fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cost-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] token-ledger still permits reserved `claude` vendor writes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `record-vendor` still accepts arbitrary vendor names, including `claude`, which could collide with transcript-derived `claude` totals. The reviewer marked this as pre-existing; the new code uses `claude_sub`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] fourth-lane final-summary/Python/callsite integration tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-schema-compat-output.txt
- **Severity**: important
- **Concern**: Several integration test surfaces do not pin non-zero `claude_sub` behavior, including final-summary fixtures, render-run-summary callsite argv wiring, Python token-cost/KV parsing, scan parsing, and four-lane final cost-line shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] per-bucket `claude_sub` cost harness coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cost-pipeline-output.txt
- **Severity**: important
- **Concern**: The dedicated per-bucket harness was not updated for `claude_sub`, leaving subprocess per-bucket rate arithmetic and environment-precedence behavior unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-cost-pipeline-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_26: [OUT_OF_SCOPE] historical-log backward compatibility appears handled
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that historical logs without `BUCKETS_claude_sub` / `.claude_sub` are handled with `// 0` defaults and defaulted Python fields, so old runs should render zero subprocess spend instead of failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-schema-compat-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] CI fixer prompt still inlines plan file without hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `launch-claude-ci.sh` still inlines `$(cat "$PLAN_FILE")` into the CI-fixer prompt without symlink canonicalization or broader content redaction. The reviewer marked this prompt-injection surface as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] report-tokens/topology docs still describe the old lane model
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cost-pipeline-output.txt, dyn-schema-compat-output.txt
- **Severity**: nit
- **Concern**: Plan-listed documentation surfaces such as `skills/report-tokens/SKILL.md` and `skills/shared/topology.tsv` were not updated, leaving operator-facing docs with the old three-lane story.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-cost-pipeline-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] JSON parsing and numeric validation appear hardened
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that JSON parsing uses `jq --arg` and digit-only validation before ledger writes, avoiding shell interpolation of untrusted JSON fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] subprocess token capture is gated on exit 0 and stale sidecars are cleared
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that `launch-claude-subprocess.sh` gates token capture on subprocess exit `0` and clears stale JSON sidecars before copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] `TOKEN_RAW` provenance is constrained by timing-kind case mapping
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that `TOKEN_RAW` provenance is derived from a fixed `case` on `--timing-task-kind`, not caller-supplied free text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] `claude_sub` naming avoids transcript-`claude` collision in the reviewed diff
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-cli-envelope-output.txt, dyn-schema-compat-output.txt
- **Severity**: nit
- **Concern**: Multiple reviewers observed that the new subprocess lane uses `claude_sub`, preserving separation from transcript-derived `claude` accounting and avoiding the known merge collision in the reviewed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-cli-envelope-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

