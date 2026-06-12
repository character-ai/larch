# Review Round 2

- Mode: `diff`
- 10 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: OOS repo resolution can split GitHub context across steps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-skill-workflow-state-output.txt, dyn-py-robustness-output.txt
- **Severity**: important
- **Concern**: OOS resolves `$REPO` once, but several GitHub-touching verbs omit `--repo "$REPO"`. `apply_main` and `close_sources_main` also use weaker repo resolution than newer dependency verbs. Runs can fail or target different repos across fetch, list, apply, audit, and close steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-skill-workflow-state-output.txt: Address the concern above.
  - From dyn-py-robustness-output.txt: Address the concern above.


### FINDING_11: plan-audit can skip approved edges after failed writes
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan_audit_main` suppresses approved decided edges even when they are absent from existing edges. If a write fails, a recovery rerun can skip the approved edge instead of writing it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Comment API failures are treated as empty comments
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Nonzero comment reads can be silently treated as no comments. Dependencies that appear only in comments can be missed while prose audit still reports success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: oos-6c exception approval gate is underspecified
- **Reviewer(s)**: dyn-skill-workflow-state-output.txt
- **Severity**: important
- **Concern**: oos-6c says to surface newly classified exception edges for approval, but does not bind that gate to the oos-6b schema, phases, shared write-results file, or cancellation-as-unresolved behavior. Reclassified exceptions can remain undecided while later closure still runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-workflow-state-output.txt: Address the concern above.


### FINDING_2: Singular source-to-combined mapping loses split-source dependencies
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A one-to-one `source_to_combined` mapping cannot represent one source issue contributing to multiple combined issues. Inherited dependencies from that source can attach to only one combined host and leave the others missing blockers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: close-sources can report success after partial close failures
- **Reviewer(s)**: dyn-py-robustness-output.txt
- **Severity**: important
- **Concern**: `close_sources_main` can return 0 when individual closes fail or sources are skipped. The skill may continue and report success from partial stdout while eligible sources remain open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py-robustness-output.txt: Address the concern above.


### FINDING_3: Prose audit can write edges for closed or unproven-open issues
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prose audit trusts stale or incomplete open-issue metadata. It can treat missing combined issues as open, or keep using an issue that closed after `list-open`, then emit or auto-write dependency edges against closed endpoints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Prose audit parser can treat negated or example text as blockers
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `prose_audit_main` sends raw prose through a parser that can match negated text, examples, comments, and fenced code as real `Blocked by` dependencies. That can create safe Tier-1 candidates and auto-write false native blocker edges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: OOS dependency phase does not hard-stop on failed prerequisites
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-skill-workflow-state-output.txt, dyn-py-robustness-output.txt
- **Severity**: important
- **Concern**: The skill redirects `list-open` and chains dependency commands without reliable exit-code or `status=ok` gates. Failed `fetch-deps` or `list-open` can feed empty or stale inputs into planners, producing misleading unknown classifications instead of an operator-visible abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-skill-workflow-state-output.txt: Address the concern above.
  - From dyn-py-robustness-output.txt: Address the concern above.


### FINDING_7: Required empty workflow JSON files are not consistently materialized
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-skill-workflow-state-output.txt
- **Severity**: latent
- **Concern**: The skill omits required empty JSON initialization for files such as write results, exception decisions, blocked sources, and Tier-2 candidates. First-run or no-op paths can fail on missing files instead of proceeding with empty schemas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-skill-workflow-state-output.txt: Address the concern above.


