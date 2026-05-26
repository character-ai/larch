### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/scripts/decompose-prompts/_common-tail.txt:27,skills/design/scripts/decompose-aggregator.sh:95
- **Concern**: Partition prompt templates still teach only singular blocked-by Piece N. Scenario: Models may keep emitting single-blocker lines or non-standard prose; multi-blocker comma lists stay undocumented at the producer layer despite parser support
- **Proposed resolution**: Extend the plan to update both templates to blocked-by Piece N[, Piece M ...] (and keep none); mirror the new edge-extraction bullet in decompose-file-issues.md

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/decompose-prompts/_common-tail.txt:25-28; skills/design/scripts/decompose-aggregator.sh:86-96
- **Concern**: The plan updates the parser contract but leaves the producer schemas advertising only `blocked-by Piece N`.. Scenario: The accepted partition grammar would be split across parser docs and prompt schemas, so future prompt/output changes can treat multi-blocker dependencies as non-contractual or invalid despite the parser now depending on them.
- **Proposed resolution**: Update the panel and aggregator required-output schemas to document the same multi-blocker form, for example `none | blocked-by Piece N[, Piece M...]`, while preserving the deferred exclusion of `Pieces 1, 2, 3`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:97-104 (proposed)
- **Concern**: Anchor remainder treats every `Piece N` after `blocked-by` as a blocker. Scenario: `- Dependencies: blocked-by Piece 1 (see also Piece 2 for context)` or similar prose emits a spurious `1→i` / `2→i` edge or a false `bad-dependency-ref` when Piece 2 is narrative-only
- **Proposed resolution**: Split on comma/`and` first and parse only the dependency clause, or stop `findall` at the first parenthetical/`:` boundary; add a harness case with trailing prose

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:97-104
- **Concern**: Proposed parser accepts blocked-by lines with zero parsed blockers as no dependencies. Scenario: A reviewer emits blocked-by Pieces 1, 2, 3 or another malformed blocked-by declaration; prepare returns ok and files issues without dependency edges, silently corrupting the blocker graph
- **Proposed resolution**: After m_anchor, if blockers is empty, abort with an explicit invalid dependency status or bad-dependency-ref before serialization

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/decompose-prompts/_common-tail.txt:25-28; skills/design/scripts/decompose-aggregator.sh:93-96
- **Concern**: Producer prompts still advertise only the singular dependency grammar. Scenario: Panel reviewers and the aggregator remain instructed to output none | blocked-by Piece N, so multi-blocker output is unsupported by the normative generation schema even though the parser and docs now accept it
- **Proposed resolution**: Update both schemas to describe the accepted repeated Piece N form, while explicitly rejecting the deferred plural-no-repeat shape

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:97-104
- **Concern**: Anchor-to-EOL findall treats any trailing Piece N as a blocker. Scenario: Dependencies like blocked-by Piece 1 (see Piece 2) or blocked-by Piece 1, notes about Piece 99 emit spurious edges or bad-dependency-ref when incidental Piece numbers appear in prose after the first token
- **Proposed resolution**: Replace tail findall with comma/and segment parsing: split m_anchor.group(1) on ,\s* or \band\b, require each segment to match ^Piece\s+(\d+)\s*$ (re.I), then dedupe; keeps multi-blocker lists while ignoring parenthetical or narrative Piece mentions

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:97-104
- **Concern**: Proposed findall parser accepts every Piece N token after blocked-by, not just comma or and separated blockers. Scenario: A dependency line like blocked-by Piece 1 unless Piece 2 changes silently creates an unintended 2 to current edge, which can impose false blockers or cycles
- **Proposed resolution**: Parse the dependency value with an explicit grammar for blocked-by Piece N followed only by comma or and plus Piece N tokens, and reject or status-fail malformed blocked-by text

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/decompose-prompts/_common-tail.txt:25-28; skills/design/scripts/decompose-aggregator.sh:91-96
- **Concern**: Producer prompts still advertise only the singular blocked-by Piece N schema while the proposed consumer/documentation contract supports multi-blockers. Scenario: Panel or aggregator outputs will continue to be steered toward a narrower or inconsistent dependency grammar, so the new parser contract is not end-to-end
- **Proposed resolution**: Update the prompt schemas to show the multi-blocker form, for example none | blocked-by Piece N[, Piece M...] and mention and-separated Piece N tokens if supported

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-decompose-file-issues.sh:65-92
- **Concern**: The plan documents and implements and-separated blockers and duplicate dedupe, but adds regression coverage only for comma lists and bad refs. Scenario: A later change can break blocked-by Piece 1 and Piece 2 or reintroduce duplicate edges without the harness failing
- **Proposed resolution**: Add focused fixtures for blocked-by Piece 1 and Piece 2 and blocked-by Piece 1, Piece 1, asserting two edges and one deduped edge respectively

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:97-104
- **Concern**: `re.findall(r"Piece\s+(\d+)", …)` scans the entire post-`blocked-by` remainder. Scenario: Dependencies like `blocked-by Piece 1 (see also Piece 2)` or `blocked-by Piece 1, Piece 2 for context` can emit a spurious 1→N edge for an incidental `Piece 2` token, over-serializing the batch via `partition-deps.tsv`
- **Proposed resolution**: Restrict extraction to delimiter-bounded segments (comma/`and`-separated list after the first `Piece N`) or document that the remainder must contain only blocker tokens; add a harness fixture with parenthetical `Piece N` that must not become an edge

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:97-104
- **Concern**: Proposed findall extracts every Piece N mention after blocked-by, not just comma/and-separated dependency tokens. Scenario: A dependencies line like blocked-by Piece 1 (not Piece 2) or blocked-by Piece 1; Piece 2 is independent would incorrectly add a 2 to current edge, causing unnecessary serialization or a false cycle
- **Proposed resolution**: Constrain extraction to the declared list grammar: parse only Piece N tokens separated by comma or and, and add a negative fixture with extra prose mentioning another Piece N

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-file-issues.sh:91-92
- **Concern**: Testing strategy adds only a comma-separated multi-blocker fixture; acceptance and Round-1 Decision 6 require `and`-separated lists (`blocked-by Piece 1 and Piece 2`) to parse to multiple edges. Scenario: A regression that breaks `and` parsing while leaving comma lists intact would still pass `make test-decompose-file-issues` and `make lint`
- **Proposed resolution**: Add a third harness section (or extend p2c) with `Dependencies: blocked-by Piece 1 and Piece 2` on a 3-piece partition and assert both `1\t3` and `2\t3` in `partition-deps.tsv`

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-file-issues.sh:65-91
- **Concern**: Bad-ref multi-list test does not assert exit 2. Scenario: The proposed _out2d=$(... 2>/dev/null || true) masks the helper exit status, so an implementation that prints DECOMPOSE_PARTITION_STATUS=bad-dependency-ref but exits 0 would pass despite the acceptance criterion requiring exit 2
- **Proposed resolution**: Capture the return code with set +e around the prepare invocation, then assert $_rc -eq 2 in the bad-ref inside multi list fixture

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-file-issues.sh:65-91
- **Concern**: Duplicate-blocker acceptance lacks required validation. Scenario: The feature explicitly requires blocked-by Piece 1, Piece 1 to be idempotent, but the plan marks a duplicate fixture optional and the canonical multi-blocker test cannot catch dedupe removal because it has no duplicate blocker
- **Proposed resolution**: Add a required third fixture or extend the multi-blocker fixture with a duplicate dependency line and assert exactly one emitted edge for the duplicated blocker

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-fixture-interface
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-file-issues.sh (proposed p2c; plan Failure modes ~159-160)
- **Concern**: Plan claims the multi-blocker fixture catches dedupe regression (5 edges vs 4) on the canonical comma-list shape. Scenario: The proposed fixture uses four distinct blockers (Pieces 1–4); if per-line dedupe breaks, that input still emits exactly four edges and all greps/wc assertions pass
- **Proposed resolution**: Revise the failure-modes text; add a small fixture (e.g. Piece 5 blocked by `blocked-by Piece 1, Piece 1`) asserting one edge and `wc -l == 1`, or drop the false mitigation claim

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-fixture-interface
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-file-issues.sh:87-90
- **Concern**: Proposed p2d masks the bad-ref exit code while claiming it exercises exit-2 propagation. Scenario: The prepare wrapper currently propagates non-zero Python exits after emitting status from prepare-python.log; with _out2d=$(... || true), a regression that emits DECOMPOSE_PARTITION_STATUS=bad-dependency-ref but exits 0 would still pass
- **Proposed resolution**: Add set +e around the p2d invocation, capture _rc2d=$?, restore set -e, and assert [[ "$_rc2d" -eq 2 ]] before the status and artifact-absence checks

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-fixture-interface
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:83-85,158-160
- **Concern**: Proposed p2c fixture cannot verify partition-deps.tsv column semantics because raw piece numbers equal 1-based batch positions. Scenario: The script sorts by raw Piece N, then writes TSV columns as a+1 and b+1 batch positions; a future implementation that incorrectly writes raw piece numbers would still pass the proposed 1..5 fixture
- **Proposed resolution**: Use non-contiguous or out-of-order piece numbers in p2c, for example Pieces 10, 20, 30, 40, 50 with Piece 50 blocked by the first four, and keep expected rows 1 5 through 4 5 to pin position-based TSV semantics
