### FINDING_1: Final summary vs Split-path contract contradiction in design SKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Final summary block and `SUMMARY_OUTCOME` contract still imply Split-path never runs it and omit partition/cancel outcomes, while Split-path bullets now require invoking it for partition/cancel terminals. The orchestrator can see incompatible “do not invoke” vs “must invoke” guidance for the same exits; `render-final-summary` / terminal path alignment is implicated across docs and scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_15: `^###` lines inside embedded piece bodies can split generic batch items
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Panel piece bodies are embedded verbatim into generic `/larch:issue` batch input; inner Markdown lines matching `^###` can split items so intra-batch dependency indices misalign, filing wrong or extra issues from an otherwise valid partition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Normalize or escape ^### lines inside generated bodies, or switch to an OOS-shaped batch format; add regression coverage.


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


### FINDING_2: `panel-failed` vs non-zero waterfall RC when usable proposals exist
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Non-zero waterfall wrapper exit forces `panel-failed` even when parseable/usabled proposals exist, conflicting with `decompose-panel.md`’s notion of panel failure as zero usable output. Stubbed or partial external-tool failure can mislabel a recoverable degraded panel as total failure and skew Retry/Cancel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Only set panel-failed when usable==0; use degraded otherwise if _wf_rc!=0.


### FINDING_20: NDJSON manifest rows embed unescaped paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unusual tmpdir paths with quotes could break JSON line consumption downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Build manifest rows with jq string escaping.

---


### FINDING_3: Resume sentinel written on partial `/larch:issue` batch (`ISSUES_FAILED>0`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `annotate` writes the filing/resume sentinel even when `ISSUES_FAILED>0`, so §0 / resume-close can skip re-filing while children are still missing; operator may need manual sentinel removal and this conflicts with documented partial filing / resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Guard sentinel on ISSUES_FAILED==0 and fix resume-close prose for partial states
  - From cursor-specialist-correctness-output.txt: Only write the resume sentinel when ISSUES_FAILED=0 (and URLs are complete); keep partial diagnostics in partition-filed.md without arming skip-re-file
  - From cursor-specialist-plan-fidelity-output.txt: Only write filing sentinel when ISSUES_FAILED==0; define partial-state handling per decompose-panel.md


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


