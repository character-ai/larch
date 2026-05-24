### FINDING_10: Step 5d automation and cache sentinel lack documented security posture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The branch adds Step 5d `gh issue comment` plus a HOME cache sentinel while `SECURITY.md` is unchanged relative to policy in `AGENTS.md`, leaving undocumented threat model, data classification, operator expectations, non-fatal failure behavior, token scope assumptions, and the requirement for a pinned static comment body so agents do not assemble `gh --body` from `plan.txt` or other dynamic content that could leak secrets into a public upstream issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_13: Plan-size capture example vs prose mismatch on stdout vs stderr
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Prose says capture stdout only while an example uses `2>&1`, which can confuse implementers about which FDs populate `_plan_size_out` for KV parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

There is at least one `### FINDING_N:` block, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** in this output.

### FINDING_4: Step 5d `gh issue comment` lacks a hard upstream-repo guard before posting
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 5d can post a tracking comment toward upstream issue 2672 when the operator’s `ISSUE_NUMBER` is 2670 and the sentinel is absent, without an explicit guard that `gh` is always invoked with `--repo character-ai/larch` (or an equivalent argv-anchored upstream resolution). A forked or non-default-`gh` session working on a local issue #2670 could still emit a comment on the upstream repo. Separately, maintainers editing Step 5d might assume two numbered guards are sufficient and omit a literal `--repo` requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: `check-plan-size` vs `emit-plan.sh` trailer grammar can disagree on hand-edited trailers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Documentation claims trailer grammar matches `emit-plan.sh` so validators never disagree, but `check-plan-size` accepts some final `diff_lines` trailers (for example multiple spaces or tab after the colon) that `emit-plan.sh` rejects as missing-diff-lines, so a hand-edited `plan.txt` can pass `check-plan-size` yet fail `emit-plan.sh`, contradicting the “never disagree” claim unless the relationship is documented as superset/subset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Partition intent can be lost when `run-params.json` is missing or `jq` merge fails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After a failed first `write-run-params`, there may be no JSON while argv carried `-p/--partition`, so the merge path that only updates an existing `run-params.json` never records `partition_requested` and Step 2b.5 can treat partition as false. Separately, best-effort `jq` merge can hide failures when existing JSON is corrupt, swallowing diagnostics so `partition_requested` never persists and later subshells miss `--partition`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Scout harness lacks a negative fixture for malformed `###NEW:` headings after regex tightening
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Scout heading regex was tightened to require whitespace after `###`, but the scout harness has no negative fixture for malformed `###NEW:` headings, so future regex edits could desynchronize scout scope extraction from `check-plan-size` / documented plan format without CI failing (contrast `test-check-plan-size.sh` case 16).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


