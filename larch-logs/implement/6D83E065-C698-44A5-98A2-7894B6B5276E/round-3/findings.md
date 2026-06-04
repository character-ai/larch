### FINDING_1: Security-routed manifest OOS can clear `OOS_PENDING` without a durable private disposition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Manifest-only security OOS are written to `security-oos-observations.md` and set `OOS_PENDING=true`, but the canonical Step 9a.1 flow reads only accepted `### OOS_` markdown. With zero non-security accepted blocks, the pipeline can take the no-input/all-clear path and clear `OOS_PENDING` without SECURITY.md private-disclosure handling, NDJSON evidence, or a documented disposition for the security sidecar. The sidecar is also not clearly documented as a private, never-filed surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt: Address the concern above.

### FINDING_2: Manifest security routing predicate diverges from the gate and contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-manifest-materializer-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` security-routes observations on title-prefix and/or JSON `focus_area`, while the documented Step 9a.1/gate-aligned rule focuses on dedicated `- **focus-area**:` lines. A non-security item titled like “Security …” can be diverted to the private sidecar and never filed publicly, while docs/tests/contracts describe a different predicate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-manifest-materializer-output.txt, dyn-log-evidence-output.txt, dyn-public-redaction-output.txt: Address the concern above.

### FINDING_3: Design OOS path resolution is triplicated across bash, Python, and docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The design OOS accepted-file resolver appears independently in bash, Python, and prose. A future resolver change could fix one path while leaving another stale, recreating the class of regression under review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Manifest OOS count logic is duplicated at multiple hook sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Identical jq-based manifest OOS counting is duplicated in multiple runtime paths. Future policy changes could require coordinated edits in several places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Python tool-failure appending can diverge from the shell helper and drop repeated failures
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `_append_execution_tool_failure` duplicates `append-tool-failure.sh` behavior and deduplicates weakly by tool name, so repeated failures at different sites can be skipped or logged inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Manifest public-text sanitization is duplicated and incomplete for public-boundary data
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: `sanitize_public_text` duplicates redaction rules instead of using a shared outbound sanitizer, and its internal URL/token coverage is narrower than the public-boundary risk. Manifest-derived title/body text can reach accepted OOS markdown, public issues, or logs with missed internal hosts or secret-like values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-public-redaction-output.txt: Address the concern above.

### FINDING_7: Structure tests rely on brittle line-window scanners for mandatory OOS-pipeline loads
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: New structure assertions use fixed awk line windows. Prompt refactors that move load directives outside the window could fail CI without semantic regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] OOS grouping reference lacks executable Rule B / criteria detail
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The expanded OOS reference lacks detailed combine mechanics for Rule B and criteria 1–4, leaving operators to rely on LLM judgment beyond Rule A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] DESIGN_TMPDIR prose omits the file-exists guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 1 prose says to use `$DESIGN_TMPDIR/oos-accepted-design.md` when `$DESIGN_TMPDIR` is set, but runtime resolvers fall through unless that file exists. Prompt-side readers could choose the wrong empty path and miss `design-export/` OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Python NDJSON discovery diverges from checkpoint/run-id resolution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: important
- **Concern**: Python `_oos_gate` uses a different NDJSON discovery order than the checkpoint path. It can fall back to foreign NDJSON when a keyed batch is missing, or miss the session-id keyed batch when `RUN_ID` is unset, producing bash/Python disposition divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.

### FINDING_11: Python accepted-OOS flow can bypass mandatory Step 9a.1 handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-state-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: important
- **Concern**: The Python ship path goes from materialization to `disposition_ok()` without mirroring bash’s non-empty accepted-OOS size gate. Non-empty main/design/review accepted OOS can proceed to PR creation when disposition evidence appears sufficient, bypassing the orchestrator Step 9a.1 handoff and related NDJSON/checkpoint work. Tests also miss a negative design-export-only blocking case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-state-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] pr-prep disposition gate omits strict filed-URL input
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt
- **Severity**: latent
- **Concern**: The internal pr-prep disposition gate omits `--filed-urls-strict-file` used by the checkpoint/Python paths, so rare all-empty accepted-OOS cases may count filed URL evidence differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-python-bash-parity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Security predicate/docs/test pins are inconsistent around materializer routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash-state-output.txt, dyn-manifest-materializer-output.txt
- **Severity**: latent
- **Concern**: Out-of-scope reviewers also noted that the materializer’s broader security predicate is not consistently documented or pinned by structure tests, increasing drift risk after the policy is resolved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-bash-state-output.txt, dyn-manifest-materializer-output.txt: Address the concern above.

### FINDING_14: Materializer failure with non-empty manifest can leave no accepted OOS to file
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: If `materialize-manifest-oos.sh` fails while manifest `oos_observations[]` is non-empty, the flow can set `OOS_PENDING=true` but produce no accepted markdown. Step 9a.1 may then treat the batch as no-input and clear disposition without ever filing the manifest OOS. The test harness does not assert this fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-bash-state-output.txt: Address the concern above.

### FINDING_15: `has_title` passes untrusted titles through `awk -v`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest titles are passed into awk via `-v wanted="$key"` without escaping. Quotes or metacharacters in untrusted manifest input can break deduplication or cause incorrect skip/merge behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Materialization has no upper bound on manifest OOS array size
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `materialize-manifest-oos.sh` processes `oos_observations[]` without a count/size cap, allowing large manifests to exhaust disk or CPU before later issue-cap logic runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Public issue/redaction stack has pre-existing coverage gaps
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Pre-existing `/issue` and redaction boundaries still trust incomplete sanitization coverage for secrets, opaque tokens, internal URLs, and other sensitive text that may flow through public OOS paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-public-redaction-output.txt: Address the concern above.

### FINDING_18: Non-array `oos_observations` is silently treated as empty
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `oos_observations` exists but is not a JSON array, the helper can compute length zero and exit successfully, causing manifest OOS content to be dropped instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Resume directly to `pr-create` skips re-materialization
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: `--resume-phase pr-create` jumps past `run_pr_prep_phase` and does not rerun manifest materialization. If `OOS_PENDING` was falsely cleared after a materializer failure, resume can open the PR without ever regenerating accepted OOS markdown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.

### FINDING_20: Step 2 manifest sanitization drops structured `focus_area`
- **Reviewer(s)**: dyn-manifest-materializer-output.txt
- **Severity**: important
- **Concern**: Step 2 rebuilds manifest OOS entries with only title, description, and phase before materialization, dropping `focus_area` / `focus-area`. Security-only structured JSON markers can be lost, causing security observations to be materialized as non-security public OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-materializer-output.txt: Address the concern above.

### FINDING_21: Duplicate normalized titles can silently drop distinct manifest OOS
- **Reviewer(s)**: dyn-manifest-materializer-output.txt
- **Severity**: latent
- **Concern**: Idempotency skips observations whose normalized title already exists in accepted markdown. Distinct entries with colliding titles/descriptions are silently dropped without warnings or tool-failure evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-materializer-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Python reimplements the OOS disposition gate
- **Reviewer(s)**: dyn-python-bash-parity-output.txt
- **Severity**: latent
- **Concern**: `python/oos.py` duplicates gate behavior instead of invoking the shell gate, creating long-term drift risk outside the immediate branch regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-bash-parity-output.txt: Address the concern above.

### FINDING_23: Sentinel-recovery NDJSON writing ownership is duplicated
- **Reviewer(s)**: dyn-log-evidence-output.txt
- **Severity**: latent
- **Concern**: `oos-pipeline.md` assigns sentinel-recovery NDJSON append responsibility in both step 3 and step 6. An orchestrator following both can append duplicate evidence rows and skew run-log statistics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-evidence-output.txt: Address the concern above.

### FINDING_24: All-already-filed path can pass without committed NDJSON evidence
- **Reviewer(s)**: dyn-log-evidence-output.txt
- **Severity**: important
- **Concern**: The documented all-already-filed branch requires step 6 NDJSON evidence, but the mechanical gate can pass on strict filed URL lines alone. An orchestrator can skip NDJSON materialization and still clear `OOS_PENDING`, breaking the larch-log evidence contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-evidence-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Disjunctive gate pass can mask per-block disposition gaps
- **Reviewer(s)**: dyn-log-evidence-output.txt
- **Severity**: latent
- **Concern**: Pre-existing gate logic can pass when `filed_urls > 0` even if not every non-security OOS block has coverage. This is not introduced by the branch but interacts with all-already-filed evidence handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-evidence-output.txt: Address the concern above.

### FINDING_26: Security-relevant manifest prose without a field marker can enter public OOS
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: Manifest descriptions that discuss a real security issue but lack the exact dedicated focus-area field line can be written to `oos-accepted-main-agent.md` and become eligible for public filing, despite schema expectations that manifest OOS excludes security findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

### FINDING_27: Prompt-side sanitize requirements lack mechanical enforcement before combine/issue
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: important
- **Concern**: OOS pipeline steps require prompt-side sanitization before composing combined/grouping files and issue bodies, but no script enforces it at those boundaries. Manifest-derived session text can propagate to public issues or committed logs if the orchestrator misses the manual sanitize step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

### FINDING_28: Ship-pr structure guard can pass on path assignment without materializer invocation
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: latent
- **Concern**: The ordering guard matches the `materialize-manifest-oos.sh` path assignment rather than the actual `bash "$materialize_oos"` invocation. Deleting the call while leaving the assignment/comment could still satisfy CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.

### FINDING_29: Step 2 structure guard does not prove materialization runs on the complete path
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: latent
- **Concern**: The structure test only checks that `step2-implement.sh` mentions the materializer, not that it runs inside the `STATUS=complete` branch and before final completion emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.

### FINDING_30: Partial-failure negative check uses a narrow line window
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: latent
- **Concern**: The assertion around `ISSUES_FAILED>0` scans only a small window, so later prose could reintroduce forbidden accepted-disposition appends outside that window without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.

### FINDING_31: Global OOS-pipeline load count is an imprecise wiring signal
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: nit
- **Concern**: `load_count >= 3` counts any `oos-pipeline.md` mention, including cross-references, rather than only mandatory Step 9a.1 entry-point directives. It can give false confidence if scoped guards are weakened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Exact run-statistics command pin is brittle
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: nit
- **Concern**: The structure harness pins one long exact `larch-log.sh write … --batch run-statistics` string, so harmless flag reordering could fail CI without changing the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Makefile harness registration appears consistent
- **Reviewer(s)**: dyn-grep-guards-output.txt
- **Severity**: nit
- **Concern**: The reviewer noted `test-materialize-manifest-oos` registration looked consistent with existing Makefile shard patterns and did not appear to be registration drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-guards-output.txt: Address the concern above.
