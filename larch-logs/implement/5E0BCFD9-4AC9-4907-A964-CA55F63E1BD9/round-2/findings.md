```text
### FINDING_1: PR scope vs acceptance (non-Makefile / non-scripts-only churn)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The branch appears to change more than a “Makefile-only” / “new scripts only” / “no edits to existing shipped skills” surface (notably `AGENTS.md`, `skills/implement/SKILL.md`, `docs/issue-anchored-plan.md`, `agent-lint.toml`, and potentially other coordinated files). That creates merge/review risk: acceptance checklists or release gates that treat those boundaries as hard requirements may reject the PR unless the issue/PR text is amended or changes are split/followed up.
- **Suggested revision**: Either narrow the diff to the originally advertised touch surface, or explicitly widen/amend issue acceptance and PR description so coordinated doc, lint metadata, and skill catalog updates are intentional and reviewable as one delivery.

### FINDING_2: Normative doc churn vs helper landing (STATE / wire-format clarity)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: Large edits to `docs/issue-anchored-plan.md` alongside new helpers can blur whether runtime behavior vs documentation semantics changed, increasing operator misreads and review friction.
- **Suggested revision**: Split doc changes, or clearly annotate what is normative vs editorial; align doc claims with what the scripts actually enforce.

### FINDING_3: `plan-block-write.sh` temp lifecycle / EXIT trap ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The EXIT cleanup trap may be registered only after temp allocation/composition steps; failures or interrupts in the earlier window can leak `mktemp` artifacts (especially under flaky automation).
- **Suggested revision**: Register EXIT cleanup immediately after temp dirs/files are created (or consolidate to one guarded temp directory with a single lifecycle owner).

### FINDING_4: Duplicated `resolve_repo` / stderr redaction helpers across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Near-identical copies across multiple scripts make stderr/repo-resolution policy fixes error-prone (multi-way edits).
- **Suggested revision**: Extract a tiny shared sourced helper (when repo policy allows touching shared script libs), or otherwise centralize the contract once.

### FINDING_5: `clarify-state.sh` GitHub pagination merge shape vs tests (`gh --paginate --slurp` + `jq`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: `gh --slurp` pagination can yield nested page arrays; merging/indexing as if it were a flat comment list risks `jq` failures or wrong ordering/state for large threads (e.g., >100 comments). Related: the offline harness may not mirror the real nested-slurp shape, so CI can miss the production failure mode.
- **Suggested revision**: Flatten pages to a single comment array before marker parsing; extend fixtures/tests to cover the nested-slurp JSON shape and assert final derived state.

### FINDING_6: Marker id=0 parsing inconsistency between `clarify-state.sh` and `clarify-comment-post.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `clarify-state` may accept/propagate `id=0` via regex while posting tooling rejects `id=0`, yielding inconsistent automation state for hand-crafted markers.
- **Suggested revision**: Align rules (reject/ignore `id=0`, or treat as ambiguous) and add a regression test.

### FINDING_7: [OUT_OF_SCOPE] Committed implement run logs under `larch-logs/implement/...`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Source flagged this as potential scope drift, but also notes it is consistent with committed run-log policy (`docs/run-logs.md`).
- **Suggested revision**: No change required for scope on this basis; keep any run-log policy rationale in the PR/issue if reviewers ask.

### FINDING_8: `test-clarify-comment.sh` success-path assertions are too shallow vs contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-coverage-output.txt
- **Concern**: Harness checks can pass on marker/first-line behavior while failing to prove the full success envelope (e.g., `POSTED`, `COMMENT_ID`, `COMMENT_URL`) or the full composed post body after the marker line—so regressions in `gh` output parsing, composition, or emitted KV keys may slip through.
- **Suggested revision**: Assert the full documented success outputs for both request/response paths, and compare captured post bodies beyond the first line.

### FINDING_9: `plan-block-read.sh` combines `gh` fetch failures with `jq` parse failures in one pipeline
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: A `gh | jq` pipeline can make `jq`/install issues look like GitHub/API failures in operator-facing `ERROR=` messaging (still fail-closed, but misleading).
- **Suggested revision**: Optionally split fetch vs parse stages (or distinct error tokens) to improve diagnosability.

### FINDING_10: [OUT_OF_SCOPE] `agent-lint.toml` commentary about `SKILL.md` reachability
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Comment drift risk if G004/suppression rules change; not treated as a functional defect for this PR.
- **Suggested revision**: None required unless you want to reduce future desync by linking commentary to a single authoritative note elsewhere.

### FINDING_11: Unvalidated `--repo` / owner slug used inside double-quoted `gh api` paths (`clarify-state.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Treating `REPO` as trusted without slug validation can be unsafe if callers pass attacker-controlled values (metacharacters / command-substitution-like patterns) and the value participates in shell word expansion before `gh` runs.
- **Suggested revision**: Validate `OWNER/REPO` against a strict slug allowlist; reject metacharacters and unexpected patterns; prefer structured args where possible.

### FINDING_12: `plan-block-read.sh` `--output` path trust model (symlink / sensitive targets)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Writing/truncating an arbitrary `--output` without symlink hardening can cause unintended overwrite/data loss if orchestration passes an unsafe path.
- **Suggested revision**: Constrain outputs to a trusted temp location + atomic rename, and document the trust model for callers.

### FINDING_13: `SECURITY.md` not updated for new GitHub write surfaces
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `AGENTS.md` calls for `SECURITY.md` updates when security-relevant behavior changes; new `gh` write helpers may lack a consolidated statement of trust assumptions (repo validation, redaction, tokens, output paths).
- **Suggested revision**: Add/adjust a `SECURITY.md` subsection describing assumptions and non-goals for these helpers.

### FINDING_14: [OUT_OF_SCOPE] `scripts/tracking-issue-write.sh` pre-existing `--repo` validation gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Similar unvalidated `--repo` patterns may predate this PR; not uniquely introduced here, but any repo-wide hardening should likely be shared.
- **Suggested revision**: If adopting validation, implement via a shared helper and apply consistently (outside this PR’s required scope if unchanged).

### FINDING_15: [OUT_OF_SCOPE] `eval` in offline `gh` stub (`scripts/test-plan-block.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Harness-only pattern; not a production attack surface under normal lint runs.
- **Suggested revision**: Optional hardening: parse argv without `eval`.

### FINDING_16: `clarify-state.sh` only inspects the first line of each comment for markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Markers appearing after a heading/quote line on line 2+ can be ignored, producing false “clean” states or wrong phase relative to visible thread content.
- **Suggested revision**: Scan a bounded leading window, or fail closed if markers appear off the mandated first line; add regression tests.

### FINDING_17: Clarification comment id sequencing gaps vs documentation (`clarify-state.sh` + `docs/issue-anchored-plan.md`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Possible ambiguity when ids don’t start at 1 or have gaps (e.g., posting `id=2` first): script behavior vs documented “successive ids” expectations may diverge.
- **Suggested revision**: Make the normative rule explicit in docs and enforce it in code (with tests) if gaps/non-1 starts are disallowed—or explicitly define supported partial states.

### FINDING_18: `clarify-comment-post.sh` relies on URL substring parsing for `COMMENT_ID`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: If `gh` output shape changes, automation might record success (`POSTED=true`) but lose a numeric id needed for later edits/dedupe.
- **Suggested revision**: Prefer structured `gh` JSON for ids; or treat missing id as failure under strict contracts.

### FINDING_19: Exit-code taxonomy differs across helpers (`clarify-comment-post.sh` vs `plan-block-write.sh`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Shared exit code values meaning different failure classes can cause orchestrators that key only on exit codes to misclassify redaction vs network vs auth failures.
- **Suggested revision**: Align exit codes across helpers or publish a single matrix and ensure callers use the right discriminator(s).

### FINDING_20: `clarify-comment-post` contract vs implementation for `POSTED=false`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Contract text may imply `POSTED=true|false` always appears, while failure paths might omit `POSTED=false`, confusing strict parsers.
- **Suggested revision**: Align documentation with actual stdout, or emit `POSTED=false` consistently on failure paths.

### FINDING_21: `test-plan-block.sh` missing coverage for empty inner block between markers
- **Reviewer(s)**: dyn-harness-coverage-output.txt
- **Concern**: Read-path tests may never assert the “markers present but extracted region is zero bytes” edge case implied by `plan-block-read.sh` behavior.
- **Suggested revision**: Add a fixture with consecutive start/end markers (or explicit blank-inner semantics) and assert `BLOCK_PRESENT=true` with an empty output file.

### FINDING_22: [OUT_OF_SCOPE] `run_case_dual` exercises real `jq -s` merge path in `clarify-state` tests
- **Reviewer(s)**: dyn-harness-coverage-output.txt
- **Concern**: Source frames this as intentional coverage (stub substitutes `gh api`, pipeline remains real), not a harness shortcut defect.
- **Suggested revision**: None unless you want additional fixtures beyond this mechanism.

### FINDING_23: [OUT_OF_SCOPE] JSON-significant characters in plan-block bodies beyond newline coverage
- **Reviewer(s)**: dyn-harness-coverage-output.txt
- **Concern**: Multiline bodies are partially covered; stronger round-trip assurance for JSON-significant characters would be incremental hardening, not a reported defect.
- **Suggested revision**: Optional future fixture if you want stronger stub/JSON edge guarantees.
```
