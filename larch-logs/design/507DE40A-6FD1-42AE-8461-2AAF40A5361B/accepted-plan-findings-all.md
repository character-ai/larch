### FINDING_1: Missing security gate before triage mutation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Triage can investigate or publicly mutate security-sensitive issues without the fail-closed handling used by `/bug`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a /bug-style security triage step before any mutation: abort with SECURITY.md responsible-disclosure guidance when the issue content is security-sensitive; allow --report-only analysis only
  - From Codex-Arch: Reuse the /bug security recheck and abort mutation when the issue is security-sensitive or uncertain
  - From Cursor-Innovation: Port /bug Step 1 and Step 5 security triage: abort before fetch/mutation, disarm the Write hook, and point operators to SECURITY.md private disclosure; never post public verification text for security issues
  - From Cursor-Pragmatic: Mirror /bug: mandatory security triage after fetch and again immediately before mutation; on security-sensitive or uncertain reports abort with the existing SECURITY.md responsible-disclosure message, emit TRIAGE_VERDICT failure rows with ISSUE_UPDATED=false, and never call the mutation helper
  - From Cursor-Requirements: Mirror /bug Step 1: hard-abort before scratch allocation when the report is security-sensitive or uncertain; route to private SECURITY.md disclosure with no /issue or triage mutation
  - From Cursor-dyn-Triage Boundary Auditor: Add Step-1 and pre-mutation security re-check gates mirroring /bug; abort with SECURITY.md responsible-disclosure text and emit ISSUE_UPDATED=false without gh mutation


### FINDING_3: Define per-mutation snapshot freshness
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: The concurrent-update contract does not specify the timestamp field, comparison behavior, or protection across multiple mutations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Fetch updatedAt in the initial issue pull, pass it to the mutation helper, refuse when the pre-mutation re-read differs, and document the exact stdout keys and exit code
  - From Codex-Innovation: Perform compare-and-swap validation immediately before every mutation, refresh the expected version after each successful mutation, and fail closed on any mismatch
  - From Cursor-Pragmatic: Pin gh issue view --json updatedAt (plus number/state/title/body) in the fetch step, persist EXPECTED_UPDATED_AT in the scratch artifact, and have triage.py re-read and compare before any edit/comment/close; add mismatch tests in python/tests/issue/test_triage.py
  - From Codex-dyn-Triage Boundary Auditor: Check the current update timestamp before each mutation, advance it from each verified read-back, and fail closed on any mismatch


### FINDING_4: Exclude the structural harness from agent lint
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The new structural harness may be treated as a dead script by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: agent-lint.toml with the same exclude entry and comment pattern as the other *-structure harnesses


### FINDING_5: Bound foreign-repository verification
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: A `--repo` target differing from the checkout can cause code verification against the wrong repository and produce false verdicts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When --repo differs from the checkout, forbid main-resolution claims, cap local code reads to the current repo, and require explicit missing-evidence language for foreign-repo code checks
  - From Cursor-Innovation: When --repo differs from the session checkout, forbid local main/symbol verification, label code claims as unverified or GitHub-only, and restrict repro to issue-linked evidence plus read-only `git fetch`/`git show` of cited refs only
  - From Cursor-Pragmatic: Adopt the /deps pattern: resolve origin slug, set a REGULAR_REFRESH_ALLOWED-style flag false when checkout origin != --repo, and block code/log-based verdicts (report-only or invalid with missing-evidence language) while still allowing comment-only close paths that need no local tree
  - From Codex-Requirements: Fail before investigation or mutation unless the checkout is verified as the target repository, or inspect a verified temporary checkout


### FINDING_7: Fail closed on dependency postcondition mismatch
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Dependency mutation can report success without verifying that the required blocked-by edge exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make postcondition mismatch fail closed, or add a strict triage path that independently verifies each dependency before continuing
  - From Codex-Pragmatic: Re-read the blocked-by relation after each mutation and treat an absent or unverifiable edge as a triage failure without a success summary
  - From Codex-dyn-Triage Boundary Auditor: Treat missing or malformed relationship data as failure and perform a fail-closed read-back of the exact dependency


### FINDING_8: Neutralize larch control markers in outbound text
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Copied issue, evidence, or comment text can inject machine-parsed larch plan or pause markers into published triage content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Neutralize control markers in untrusted sections before writing, while preserving only separately validated system-owned blocks
  - From Codex-Innovation: Neutralize larch marker syntax in every copied untrusted section, preserve or reject existing machine blocks, and test both injection and preservation
  - From Cursor-Requirements: Require the same rule as `/deps`: strip or neutralize all `<!-- larch:` control markers from outbound rewrite/comment text before redaction; add regression coverage in `python/tests/issue/test_triage.py`
  - From Codex-Requirements: Neutralize user-sourced larch markers before egress, allow only helper-synthesized triage markers, and test the rejection or escaping path
  - From Codex-dyn-Triage Boundary Auditor: Neutralize `<!-- larch:` markers in every user-controlled section and strip pre-existing plan blocks before redaction and publication


### FINDING_9: Protect existing plans and lifecycle state
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: A valid-verdict rewrite can destroy active design, implement, clarify, pause, or plan state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Reject issues with active plan or pause blocks, or preserve and validate those blocks byte-for-byte during the rewrite
  - From Codex-Innovation: Reject triage when protected machine blocks exist, or preserve them byte-for-byte outside the rewritten triage content, with regression tests
  - From Cursor-Pragmatic: Before any mutation, call python/cli.py issue title-eligibility on the fetched title and refuse when LIFECYCLE_REJECT=true; also refuse valid body rewrites when the fetched body contains an intact larch:plan block (reuse issue_wire plan-block validation). Pin refusal in skills/triage/SKILL.md, python/larch/issue/triage.py, scripts/test-triage-structure.sh, and python/tests/issue/test_triage.py
  - From Cursor-Requirements: Refuse mutation (report-only OK) when title matches lifecycle reject markers, clarify label is present, or a `larch:plan` named block exists; document the refusal in stdout and `--report-only` output


### FINDING_11: Require explicit operator authorization
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: The CLI and follow-up invocations do not pin the `--operator-invoked` boundary, risking unauthorized direct mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and pin Skill invocations as `/issue ... --operator-invoked` (plus existing dedup/sentinel rules) in `skills/triage/SKILL.md` and `scripts/test-triage-structure.sh`
  - From Cursor-Requirements: Register `("triage", "apply")` (or `fetch`+`apply` if split), accept `--operator-invoked` at the CLI boundary, map it to `check_live_mutation_auth(..., operator_mode=True)`, and document the invocation in `skills/triage/SKILL.md`
  - From Cursor-dyn-Triage Boundary Auditor: Add --operator-invoked to the triage apply verb; SKILL passes it to apply and to /issue; use operator_mode=bool(operator_invoked); test auth refusal with zero gh calls when the flag is absent


### FINDING_13: Constrain issue-derived refs and paths
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Unvalidated issue-supplied refs or paths can cause option injection, traversal, unintended fetches, or secret-file disclosure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use a deterministic helper with fixed remotes, validated commit or PR refs, argument-based execution, and no raw issue text in shell commands
  - From Codex-dyn-Triage Boundary Auditor: Allow only validated repo-relative code paths and canonical larch-log paths; reject absolute paths, traversal, symlinks, and other files


### FINDING_14: Make multi-step mutations compare-and-swap safe
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: A single initial freshness check cannot protect later mutations in a multi-step verdict sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Perform compare-and-swap validation immediately before every mutation, refresh the expected version after each successful mutation, and fail closed on any mismatch
  - From Codex-dyn-Triage Boundary Auditor: Check the current update timestamp before each mutation, advance it from each verified read-back, and fail closed on any mismatch


### FINDING_15: Add an inconclusive no-mutation verdict
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Missing evidence or repository mismatch currently forces an unjustified verdict or an inappropriate issue close.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add an explicit inconclusive or insufficient-evidence terminal result with `ISSUE_UPDATED=false`, no mutation, and matching docs and tests


### FINDING_16: Prevent unsafe reproduction commands
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Prompt-only reproduction rules can execute issue-supplied shell expansion, destructive actions, secret exfiltration, or externally mutating requests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Never execute issue-supplied commands verbatim; reconstruct validated argv, reject shell expansion and arbitrary destinations, and require approval for authenticated or networked probes
  - From Codex-dyn-Triage Boundary Auditor: Add a deterministic safe-probe runner or strict command allowlist with isolated credentials and fail-closed rejection


### FINDING_17: Forward `--repo` to dependency wiring
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: Dependency application may target the checkout default instead of the repository selected for triage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Pass the same `--repo OWNER/REPO` slug through every `/block-issue` Skill invocation and pin it in `scripts/test-triage-structure.sh`


### FINDING_19: Render full report-only analysis
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: `--report-only` may emit only terminal verdict keys instead of the requested evidence, diagnosis, and fix analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Require rendered evidence, diagnosis, verdict, and fix outline before the terminal KVs; pin this in the structural harness


### FINDING_20: Apply complete outbound redaction
- **Reviewer(s)**: Cursor-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Token-only sanitization can publish secrets, internal URLs, PII, temporary paths, or control markers from evidence and repro output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Triage Boundary Auditor: Mirror deps_audit _sanitize_outbound_body in triage.py; add bug-style compose-time sanitization (secrets, internal URLs, PII, larch-marker neutralization) before body-file writes; fail closed on redaction errors


### FINDING_23: Wrap all evidence as untrusted content
- **Reviewer(s)**: Codex-dyn-Triage Boundary Auditor
- **Severity**: major
- **Concern**: Logs, git output, code excerpts, and reproduction output are not consistently isolated from instructions embedded in untrusted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Triage Boundary Auditor: Wrap every content-bearing artifact and command output as untrusted escaped evidence before model inspection


### FINDING_4: Wire triage into the anti-halt contract
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: Triage can halt after child skills return, skipping dependency read-back, follow-up verification, cleanup, and terminal machine keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the orchestrator banner and continuation reminders, and register `skills/triage/SKILL.md` in the shared scope list and harness 1. **[security] Dependency authorization is incomplete.** The plan authorizes `triage apply` and `/issue`, but `/block-issue` remains a separate mutation path without `--operator-invoked` enforcement. 2. **[architecture] Add the required anti-halt wiring.** `/triage` performs work after child skill calls, so it must follow the repository’s orchestrator banner, reminder, scope-list, and harness contracts.
  - From Codex-Requirements: Add canonical anti-halt reminders, verify `/issue` through counters and a sentinel, and register triage in `skills/shared/subskill-invocation.md` and `scripts/test-anti-halt-banners.sh`.


### FINDING_6: Inspect code from an immutable main snapshot
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Investigation may inspect a feature branch or dirty worktree instead of main, producing false fixed or root-cause conclusions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Resolve and record a main commit before investigation, read cited files and symbols through that commit, and fail closed if the exact main ref cannot be verified


### FINDING_7: Provide a validated evidence-inspection CLI
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The required fetch-and-show workflow for unmerged branch evidence has no reachable, validated CLI surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a triage inspect (or equivalent) entry point in triage.py, register it in cli.py, validate refs/paths and fixed-remote fetch/show there, record missing refs as evidence gaps, and pin the helper in skills/triage/SKILL.md and scripts/test-triage-structure.sh.
  - From Codex-Pragmatic: Add a triage evidence verb that validates refs and paths, uses the fixed remote with argument-vector execution, and has focused tests.
  - From Cursor-Requirements: Add a deterministic triage read-ref (or equivalent) verb in python/larch/issue/triage.py, register it in python/larch/cli.py, call it from skills/triage/SKILL.md for validated commit SHAs or refs/pull/N/head, and cover fetch-show success, rejection, and caps in python/tests/issue/test_triage.py and scripts/test-triage-structure.sh


### FINDING_8: Recheck freshness before dependency writes
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Dependency application can use stale analysis after an intervening issue edit or lifecycle transition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Pass the verified timestamp into a triage-controlled dependency mutation that rechecks freshness and protected state immediately before applying and reading back the edge.
  - From Codex-Requirements: Thread the latest verified `updatedAt` into dependency application and make `issue_block.py` compare it immediately before mutation. Test that mismatch prevents the GraphQL mutation.


### FINDING_9: Preserve title restoration on close verdicts
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Rejecting lifecycle-prefixed titles before verdict routing makes required title restoration unreachable for already-fixed or duplicate issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reject active lifecycle state, but allow close verdicts to restore a stale prefix when no protected block or label remains. Test both paths.


### FINDING_10: Permit narrowly scoped external-tool reproduction
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: A blanket ban on networked or authenticated probes prevents the specified safe external-tool reproduction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Allow narrowly named, fixed-destination, read-only external probes through existing credential-safe launch paths. Keep arbitrary commands, arguments, and destinations forbidden.


