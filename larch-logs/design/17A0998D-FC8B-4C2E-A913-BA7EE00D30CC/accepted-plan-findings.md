### FINDING_1: progress-reporting negative grep conflicts with retained breadcrumb rules
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan pairs a whole-file ban on `STEP_NUM_PREFIX`, `STEP_PATH_PREFIX`, and `PARENT_SKILL_PATH` in `skills/shared/progress-reporting.md` with instructions to keep common breadcrumb rules unchanged and only remove the `## --step-prefix Encoding` block. Current Breadcrumb Format prose (e.g. line 15) legitimately references `STEP_PATH_PREFIX`. A faithful split either fails the negative grep or violates the keep-breadcrumb instruction. Standalone readers also still need a concise nested-breadcrumb contract without re-loading the full encoding block, and the plan does not say how to document that without tripping the grep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the progress-reporting edit bullets: rewrite Breadcrumb Format and Step Start Formatting references to generic nested-prefix prose plus a one-line pointer to `skills/shared/step-prefix-encoding.md`, without the three exact token names; or narrow the negative grep to the removed `## --step-prefix Encoding` block only (line-range or section-scoped pattern).
  - From Cursor-Arch: Specify the retained nested breadcrumb contract in one or two lines (e.g., "when nested, prepend the parent text segment from `--step-prefix`; see `step-prefix-encoding.md`") and align the negative grep with that retained surface.
  - From Cursor-Requirements: Narrow the negative check to the moved encoding section only (for example grep for `## --step-prefix Encoding` / `### Parsing in child skills` must be absent, or scope the token grep to lines after the encoding heading) instead of banning `STEP_NUM_PREFIX|STEP_PATH_PREFIX|PARENT_SKILL_PATH` repo-wide in that file.


### FINDING_2: dialectic-protocol active-file negative grep uses HTML entities instead of literal angle-bracket tags
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The testing strategy's second negative grep for `skills/shared/dialectic-protocol.md` lists `&lt;steelman&gt;`, `&lt;claim&gt;`, and `&lt;evidence&gt;` instead of literal `<steelman>`, `<claim>`, and `<evidence>`. Copied verbatim, `rg` will not match real six-tag debater template residue still present in kept Ballot Format prose, so CI can pass while stale debater markup (~40 lines of retired ballot assembly prose) remains in the always-loaded active file. The intended trim of `<steelman>` / `<claim>` / `<evidence>` / `<strongest_concession>` / `<counter_to_opposition>` / `<risk_if_wrong>` template text is therefore unverifiable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace entities with literal patterns (`<steelman>`, `<claim>`, `<evidence>`) in the documented `rg` command, or add an explicit note that implementers must unescape before running the check.
  - From Codex-Arch: Search for the raw tokens directly, or add a separate raw-tag grep that fails if any of the six defense markers remain
  - From Cursor-Innovation: In the testing strategy, use literal rg patterns `<steelman>`, `<claim>`, and `<evidence>` (shell-quoted), not HTML entities
  - From Cursor-Pragmatic: Use literal patterns `<steelman>`, `<claim>`, and `<evidence>` in the rg command (or document that entities must be decoded before running)


### FINDING_3: dialectic-protocol negative greps omit intro and Caller-Binding legacy phrases
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan rewrites the intro and Caller Binding sections but the expanded negative grep set never forbids legacy phrases such as `judge presence check`, `replacement-first` (including `replacement-first 3-judge panel`), `external waterfall`, `per-decision judge panels`, or `cursor-judge-output` / `codex-judge-output`. An implementer can drop named legacy sections yet leave retired choreography in the always-loaded header (e.g. line 5 callout and line 17 judge output paths), and validation still passes while the active Gate C file advertises external judge choreography.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add those tokens to the second active-file negative grep (or a dedicated intro/Caller-Binding grep) so partial trims fail closed
  - From Codex-Requirements: Add a targeted negative grep for the intro callout phrases the plan says to remove, for example judge presence check|replacement-first 3-judge panel|external waterfall|per-decision judge panels, against skills/shared/dialectic-protocol.md.


### FINDING_4: disposition rewrite text conflicts with active-file `Step 3.5` negative grep
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The UPDATED disposition section mandates active prose naming `Step 2b` and `Step 3.5` in a non-binding clarifier sentence (`None of ... bind plan.txt, Step 2b, or Step 3.5`). The second negative grep at plan line 188 forbids any `Step 3.5` match in the active file. An implementer cannot satisfy both the rewrite bullets and the validation greps without dropping required clarifier-only semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Align wording and greps: either allow negation-only `Step 3.5` matches (tighten the grep to binding phrases like `Step 3\.5 treats|still-contested`) or rewrite the disposition/scope bullets to state advisory-only semantics without the literal `Step 3.5` token (for example "later design discussion gates").


### FINDING_5: dialectic-legacy.md validation does not prove preserved parked blocks
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan requires `skills/design/references/dialectic-legacy.md` to retain retired choreography, disposition meanings, Consumer Contract text, and Step 3.5 schema, but the legacy-file checks only look for a few section-title markers. Sections such as Collecting Judge Results, Tally and Resolution, or disposition rows could be dropped and the test suite would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Expand the legacy-file grep set to cover the preserved moved sections, not just Judge Panel Composition and Launching Judges, or add a stronger block-level assertion that the full legacy schema was copied over.


### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/dialectic-protocol.md:63
- **Concern**: [SCOPE-REDUCTION] Ballot Format rewrite omits Write-tool/heredoc assembly guidance.. Scenario: The clarifier path writes `dialectic-ballot.txt` from Python (`python/design_dialectic.py` `_atomic_write_text`); Gate C does not use orchestrator Write-tool ballot assembly. The plan rewrites defense sources and paths but never drops the active-file "written via the Write tool (not heredoc/cat)" rule, so a literal trim can preserve retired orchestrator assembly choreography in the always-loaded clarifier reference.
- **Proposed resolution**: Add an explicit Ballot Format bullet: drop Write-tool/heredoc/cat assembly instructions; state that clarifier ballot text is assembled by `python/design_dialectic.py` into `$DESIGN_TMPDIR/dialectic-ballot.txt`. Optionally add `Write tool` or `heredoc` to the second dialectic negative grep.


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md:151-172
- **Concern**: [SCOPE-REDUCTION] Voter removal scope ends before the interstitial availability/dispatch paragraphs. Scenario: The four named deletes span 120-183, but the plan never says to drop the `Cursor voter availability`, `Codex voter availability`, and `Claude voter dispatch` paragraphs between the argv fences; a surgical delete can leave ~15 lines that repeat `Voter Panel Composition` / `Launching Voters` dispatcher ownership and blunt the ~50-line voting read reduction
- **Proposed resolution**: Replace the contiguous 120-183 block with one ownership note, or explicitly list those three paragraphs for removal in the voting-protocol section


### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/progress-reporting.md:15
- **Concern**: [SCOPE-REDUCTION] Step-prefix split omits rewrite of Breadcrumb Format prose that still names `STEP_PATH_PREFIX` while file-wide negative grep forbids that token. Scenario: The plan moves only `## --step-prefix Encoding` but line 15 still contains `STEP_PATH_PREFIX`; the negative grep at plan.txt:215 fails unless that earlier bullet is generalized, yet the Files section does not instruct that rewrite
- **Proposed resolution**: Add an explicit bullet under `skills/shared/progress-reporting.md` to replace line 15 with generic nested-breadcrumb wording (no `STEP_NUM_PREFIX` / `STEP_PATH_PREFIX` / `PARENT_SKILL_PATH` literals) and point readers to `skills/shared/step-prefix-encoding.md`


### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:183-189
- **Concern**: [SCOPE-REDUCTION] Active dialectic negative greps omit legacy path-placeholder tokens (`$DIALECTIC_TMPDIR`, `cursor-judge-output`, `codex-judge-output`). Scenario: Prior kept-section legacy markers are covered, but an implementer can drop section titles yet leave Caller Binding or ballot examples using `$DIALECTIC_TMPDIR` and external judge output paths; greps pass while Gate C clarifier readers still load retired path choreography
- **Proposed resolution**: Extend the active-file negative grep list with `$DIALECTIC_TMPDIR`, `cursor-judge-output`, and `codex-judge-output`, and state in the dialectic rewrite that clarifier-only paths use `$DESIGN_TMPDIR/dialectic-ballot.txt` exclusively


