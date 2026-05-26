### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: Proposed canonical dedup uses a colon-delimited string and case pattern matching for full file paths. Scenario: Pathnames may legally contain ':' or glob metacharacters, producing false duplicate hits or missed duplicates; extending this pattern from directories to operator-supplied files increases a brittle parsing surface
- **Proposed resolution**: Use a Bash 3.2-compatible array loop comparing strings with [[ "$seen" == "$canonical" ]] instead of delimiter-based pattern matching for seen_canonical_paths


### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: Colon-delimited seen_canonical_paths can false-match valid paths containing colon. Scenario: After seeing a path like /tmp/a:b, a later /tmp/a can be treated as already seen because the filename colon is indistinguishable from the delimiter, silently dropping context
- **Proposed resolution**: Use a Bash 3.2-compatible array plus linear equality loop for seen canonical paths and allow-roots


### [Plan Review] FINDING_16

### FINDING_16:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/launch-claude-review.sh:92-108
- **Concern**: Colon-delimited seen_canonical_paths is a brittle dedup structure for filesystem paths. Scenario: A valid path component containing colon can make the case-pattern dedup logic misclassify paths, silently dropping context or forwarding duplicates
- **Proposed resolution**: Use Bash 3.2-compatible indexed arrays with a small linear equality loop for seen canonical paths and allow roots instead of delimiter-packed strings


### [Plan Review] FINDING_19

### FINDING_19:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: allow-root dirname source ambiguous vs dedup key. Scenario: Plan says add the canonical dir to allow_root_args but does not pin whether dir is dirname("$path") or dirname("$canonical"); mismatch could leave duplicate --allow-root entries or diverge from subprocess pwd -P roots
- **Proposed resolution**: Spell out allow_root dir="$(dirname "$canonical")" (or document intentional use of operator path dirname) in the append_context_file bullet


### [Plan Review] FINDING_20

### FINDING_20:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:18-20
- **Concern**: strict second arg default only in Failure modes. Scenario: Implementation bullets require strict at all call sites but only Failure modes #1 mentions local strict="${2:-0}"; a partial refactor breaks implicit-flag call sites before tests run
- **Proposed resolution**: Add local strict="${2:-0}" to the proposed append_context_file signature in the main script section, not only in Failure modes


### [Plan Review] FINDING_30

### FINDING_30:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:95-103
- **Concern**: Colon-delimited dedup keys are ambiguous for valid path names. Scenario: The plan requires canonical-path dedup but stores seen paths in a colon-separated string; a valid path containing ':' can false-match another path and silently drop context
- **Proposed resolution**: Use a Bash-3.2-compatible indexed array plus exact string comparison loop for seen canonical paths and allow roots instead of delimiter-packed strings


### [Plan Review] FINDING_34

### FINDING_34:
- **Reviewer(s)**: Cursor-dyn-caller-resolution-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-plan-voters.sh:71-78
- **Concern**: Plan adds launcher --context-files (option a) but states No new callers added; Voter 1 launch still passes only --prompt-file with no --context-files "$BALLOT_FILE". Scenario: Parent R4/FINDING_1 requires launch-claude-review.sh --context-files ballot so the subprocess receives the ballot as a context file; render-voter-prompt.sh:66 only embeds the ballot path in prose, so merging this plan alone leaves plan Voter 1 unable to mechanically read the ballot the way the multi-round spec assumes
- **Proposed resolution**: Add an Approach/Edge-cases bullet naming resolution option (a) at the launcher and explicitly deferring caller wiring; record the required follow-up: append --context-files "$BALLOT_FILE" to the launch-claude-review.sh invocation at dispatch-plan-voters.sh:71-78 in a named partition piece (not implied by No new callers alone)


### [Plan Review] FINDING_35

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-caller-resolution-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-plan-voters.sh:71-78, scripts/dispatch-code-voters.sh:103-110
- **Concern**: The plan implements the new launcher flag but explicitly leaves callers unchanged, so it does not actually apply R4/FINDING_1 option (a) to Voter 1 ballot delivery.. Scenario: After the PR, dispatch-plan-voters.sh still launches Claude Voter 1 with only --prompt-file and no --context-files, while dispatch-code-voters.sh forwards only diff/plan ctx_args and not the ballot file. The prompt renderer tells Voter 1 to read the ballot path, but the selected option (a) requires callers to pass that file as context; the ballot-context failure remains unless a later piece is explicitly documented.
- **Proposed resolution**: Revise the plan to either update both Voter 1 launcher calls to pass --context-files "$BALLOT_FILE" with matching dispatch tests, or explicitly mark this PR as launcher-only prerequisite work that does not resolve R4/FINDING_1 and name the later caller-wiring piece.


