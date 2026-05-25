Here is the normalized aggregator output. Multiple slots repeated the same behavioral risk; those are merged with combined attribution. Verbatim suggested revisions are taken from each slot’s **Suggested revision** line (generic “Address the concern above.” lines from different slots that are **literally identical** are merged into one bullet with comma-separated `From` slots).

---

### FINDING_1: Final summary vs Split-path contract contradiction in design SKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Final summary block and `SUMMARY_OUTCOME` contract still imply Split-path never runs it and omit partition/cancel outcomes, while Split-path bullets now require invoking it for partition/cancel terminals. The orchestrator can see incompatible “do not invoke” vs “must invoke” guidance for the same exits; `render-final-summary` / terminal path alignment is implicated across docs and scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: `panel-failed` vs non-zero waterfall RC when usable proposals exist
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Non-zero waterfall wrapper exit forces `panel-failed` even when parseable/usabled proposals exist, conflicting with `decompose-panel.md`’s notion of panel failure as zero usable output. Stubbed or partial external-tool failure can mislabel a recoverable degraded panel as total failure and skew Retry/Cancel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Only set panel-failed when usable==0; use degraded otherwise if _wf_rc!=0.

### FINDING_3: Resume sentinel written on partial `/larch:issue` batch (`ISSUES_FAILED>0`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `annotate` writes the filing/resume sentinel even when `ISSUES_FAILED>0`, so §0 / resume-close can skip re-filing while children are still missing; operator may need manual sentinel removal and this conflicts with documented partial filing / resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Guard sentinel on ISSUES_FAILED==0 and fix resume-close prose for partial states
  - From cursor-specialist-correctness-output.txt: Only write the resume sentinel when ISSUES_FAILED=0 (and URLs are complete); keep partial diagnostics in partition-filed.md without arming skip-re-file
  - From cursor-specialist-plan-fidelity-output.txt: Only write filing sentinel when ISSUES_FAILED==0; define partial-state handling per decompose-panel.md

### FINDING_4: `/larch:block-issue` vs intra-batch deps / top-level requirements drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Reference / requirements still imply `/larch:block-issue` while the flow may rely on intra-batch deps only, so extra dependency edges outside the batch TSV might never get filed unless documented or an explicit step exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document subsume-by-intra-batch or add explicit block-issue step

### FINDING_5: `aggregate-findings` reuse vs waterfall-only aggregator
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan / acceptance language pointed at `aggregate-findings` reuse but implementation is waterfall-only; mismatch risks silent loss of an intended merge path and weak CI signal for concatenation/order bugs at full panel width.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Maintain as KISS or add optional probe per original plan
  - From cursor-specialist-testing-output.txt: Reconcile docs/plan with code or implement the optional aggregate-findings path plus tests

### FINDING_6: `close-original` comment body is grep-thin vs #2644 narrative
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Closing comment is minimal for grepping/audit compared to the richer narrative expected for partition closes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Compose structured close body from parsed partition metadata

### FINDING_7: Stale `partition-input.txt` / `partition-deps.tsv` after non-ok prepare (incl. cycle-detected)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A successful prepare writes batch artifacts; a later prepare that fails (e.g. cycle-detected) can leave prior batch files on disk while emitting non-ok status, risking stale `/larch:issue --input-file` if callers trust paths without checking partition status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: rm -f or overwrite batch artifacts atomically at prepare start; on non-ok status unlink stale outputs
  - From cursor-specialist-edge-cases-output.txt: Truncate or delete batch artifacts on every non-ok prepare path (including cycle-detected).

### FINDING_8: Cycle witness promised in reference but not produced by prepare
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Reference tells the operator to expect a cycle witness / edge detail; prepare only signals cycle-detected without a compact edge list, slowing correction without re-reading the partition artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit a compact edge list or piece index witness from Python on cycle-detected or drop witness wording from the reference
  - From cursor-specialist-edge-cases-output.txt: Emit a witness from Python or remove the witness wording from the reference.

### FINDING_9: Omitted `--issue-number` yields placeholder parent reference in partition bodies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Prepare falls back to a placeholder original issue reference when `--issue-number` is omitted, weakening traceability and confusing partition issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require --issue-number for prepare or read ISSUE_NUMBER from a session env file.

### FINDING_10: `close-original` test may not use `gh` stub (env/PATH not applied)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Env vars for the `gh` stub apply only around a `set +e` region, not necessarily the `close-original` invocation, so tests may hit system `gh` and become non-deterministic or vacuous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Prefix the same PATH/env onto the `"$DFI" close-original` invocation or wrap in a subshell so the stub always runs

### FINDING_11: No harness for partial `annotate` (`ISSUES_FAILED>0`) vs sentinel / markdown contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance / plan called for partial filing behavior to be tested; without a fixture asserting markdown + sentinel behavior, regressions in partial batches can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stdout fixture with ISSUES_FAILED>1 and assert markdown + sentinel expectations match the orchestration contract
  - From cursor-specialist-plan-fidelity-output.txt: Add fixture with ISSUES_FAILED>0 and assert sentinel behavior after annotate fix

### FINDING_12: Aggregator harness uses 2-row panel NDJSON instead of full eight-slot panel
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Concatenation / ordering bugs across a full panel surface may not be exercised in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add eight minimal panel output files and assert merge prompt contains eight panel sections

### FINDING_13: No assertion for feature-only discussion substitution on success path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Discussion block wiring in feature-only success mode is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed feature-only run and grep rendered prompt for discussion artifact text

### FINDING_14: No test for `FALLBACK_COUNT`-only degradation path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Threshold regression for degraded vs ok could flip without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub FALLBACK_COUNT=5 with STATIC_DISPATCH_OK=true and assert degraded panel flags

### FINDING_15: `^###` lines inside embedded piece bodies can split generic batch items
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Panel piece bodies are embedded verbatim into generic `/larch:issue` batch input; inner Markdown lines matching `^###` can split items so intra-batch dependency indices misalign, filing wrong or extra issues from an otherwise valid partition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Normalize or escape ^### lines inside generated bodies, or switch to an OOS-shaped batch format; add regression coverage.

### FINDING_16: `DECOMPOSE_REDACT_SH` can override close-comment redactor
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Hostile or mistaken env could disable redaction while still posting via `gh issue comment --body-file`; trust boundary for tests vs production should be explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Limit override to harness runs or ignore env outside tests; document trust boundary.

### FINDING_17: `render-final-summary` rejects new Split-path outcomes (`approved-partition`, `cancelled-decompose`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Outcome enum / case list omits new Split-path terminal outcomes, so the script can exit 2 and abort the documented terminal path when those outcomes are set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Extend the allowed outcome case list (and tests) to include approved-partition and cancelled-decompose; align any summary bullets and design-log publish expectations.
  - From cursor-specialist-plan-fidelity-output.txt: Whitelist and handle approved-partition and cancelled-decompose; sync docs/tests

### FINDING_18: `close-original` can duplicate partition comment and under-log close failures on retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After a successful `gh issue comment`, `gh issue close` may fail; retry can re-post the partition comment and close failures may skip `append-tool-failure.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a comment-posted sentinel to skip duplicate comments on retry; append-tool-failure on gh issue close failures.

### FINDING_19: Annotate idempotency: `ISSUES_CREATED` vs parsed URL count / malformed stdout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sentinel and filed record can desync from real GitHub filing if stdout is malformed; interacts with partial-batch semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add stricter stdout validation before sentinel write; document partial ISSUES_FAILED handling.

### FINDING_20: NDJSON manifest rows embed unescaped paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unusual tmpdir paths with quotes could break JSON line consumption downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Build manifest rows with jq string escaping.

---

### OOS_1: [OUT_OF_SCOPE] Large design / run-log commits inflate diff noise for reviewers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Flushed `larch-logs/**` (including design sessions) add paging overhead and diff surface unrelated to decomposition script logic; policy/chore rather than a functional defect in the decomposition code path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Keep log flushes in separate commits (already mostly true) or trim unrelated sessions from the feature branch
  - From cursor-specialist-security-output.txt: None (policy-driven content).

### OOS_2: [OUT_OF_SCOPE] Three-stage AskUserQuestion UX vs older single-step side-by-side copy
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Legacy UX/feature description text does not match shipped orchestration contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Follow the implementation plan as source of truth or update the feature spec if UX must change

### OOS_3: [OUT_OF_SCOPE] `skills/issue/scripts/create-one.sh` batch redaction (pre-existing interaction)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Bodies are redacted at `gh issue create`; this does not fix generic `###` splitting in prepare output; interaction is broader than this PR slice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: None for this PR beyond documenting interaction with prepare output.

### OOS_4: [OUT_OF_SCOPE] `dispatch-with-waterfall.sh` exit code vs `DISPATCH_OK` behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing waterfall often exits 0 while `DISPATCH_OK` is false; relevant mainly as context for classifying panel health vs raw RC.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer interpreting DISPATCH_OK and usable counts over raw exit codes when classifying panel health.

### OOS_5: [OUT_OF_SCOPE] Product brief vs implementation plan on `/larch:block-issue`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Feature description still mentions `/larch:block-issue` while Round 1 Decision 2 favors intra-batch deps; spec vs plan authority is a product/process question outside the narrow decomposition script fix list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: None if implementation plan is authoritative; otherwise reopen Decision 2

---

Because this output contains one or more `### FINDING_N:` blocks, the file must **not** include `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` (and none appears above).
