Here is the normalized structured finding list. Same behavioral risks are merged; `[OUT_OF_SCOPE]` is preserved where any merged source carried it; suggested revisions are quoted verbatim (identical wording merged into one bullet per the rules).

---

### FINDING_1: BASH_AUTHORING §4 title and depth vs acceptance / plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The normative section around [BASH_AUTHORING.md](BASH_AUTHORING.md) (e.g. §4 near line 50) does not align with the acceptance/plan title “Foreground Default for Blocking Script Calls” (wording such as “Default” vs “markers”), so searches and checklists can miss the canonical section; plan-fidelity also flags missing or insufficient worked / before-after fenced examples relative to the agreed deliverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Unrelated work bundled on one branch / PR
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The branch mixes foreground-marker work with unrelated items (OOS disposition gate, design OOS scripts, run logs, version bump, changelog, etc.), which complicates bisect, revert, and review unless explicitly bundled and documented; reviewers note partitioning cost and skewed “foreground-only” reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: None for foreground plan closure; split PRs or narrow review scope if separation is required.

### FINDING_3: Duplicate foreground banner before ship-pr fence in implement skill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [skills/implement/SKILL.md](skills/implement/SKILL.md) (around 1563–1568) repeats the canonical foreground banner and a long bespoke warning back-to-back, diluting the single contract line operators should see before the fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Strict fence-opener regex may skip valid fences
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) (around 301–302) uses a strict trailing-token regex on the fence line so some Family B fence shapes are never scanned, yielding false green CI vs acceptance intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Family A harness relies on weak grep count invariants
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/test-lint-foreground-markers.sh](scripts/test-lint-foreground-markers.sh) (and related lines cited) use whole-file or minimum grep counts for `run_in_background` (and similar), so counts can stay stable while a launch site loses backgrounding, or duplicate lines inflate counts, producing false passes or false failures; reviewers want basename pairing, anchored manifests, golden excerpts, and/or stronger structural or exact-count checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] collect-agent-results only in prose in voting-protocol
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [skills/shared/voting-protocol.md](skills/shared/voting-protocol.md) (around 182): `collect-agent-results` appears only in prose, not as a fenced invocation; out of scope for the narrow acceptance unless fenced examples are added later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: None unless fenced examples are added later.

### FINDING_7: Plain-URL OOS recovery pairs sentinels to blocks by document order, not id
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [skills/design/scripts/file-design-oos.sh](skills/design/scripts/file-design-oos.sh) (7095–7177 per input): recovery pairs plain URLs to the first unfiled OOS blocks in order without OOS id matching, so filing two issues in reverse order can swap **Filed URL** lines while still exiting 0; need `OOS_FILE_MAP` whenever multiple URLs/blocks or match URLs to OOS ids.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Banner lint accepts substring anywhere in window, not leading callout semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) treats the canonical banner as a substring within a line/window, so a long preface can embed the banner mid-sentence and still pass, undermining a visible foreground warning before the fence; optional stricter line-equality after blockquote strip was suggested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: `git ls-files` scope skips untracked markdown locally
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) (62–69): enumeration via `git ls-files` omits untracked files, so new fences in unstaged skills can yield false green local `make lint-foreground-markers` until `git add`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: `filed_urls` diagnostic may double-count the same URL across surfaces
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [skills/implement/scripts/oos-disposition-gate.sh](skills/implement/scripts/oos-disposition-gate.sh): loose plus strict URL counts are summed without cross-dedup in the logged `filed_urls` scalar, so the log can show `filed_urls=2` for one unique GitHub URL filed via two surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: S3 scenario title claims dual-channel union but assertions are too weak
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: [skills/implement/scripts/test-oos-disposition-gate.sh](skills/implement/scripts/test-oos-disposition-gate.sh) (8355–8380 per input): scenario text claims strict+loose union coverage for two OOS blocks but only checks exit 0; one counting path could be dropped while `filed>0` still holds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Python `gh_url` regex in file-design-oos is incorrect / dead for normal URLs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [skills/design/scripts/file-design-oos.sh](skills/design/scripts/file-design-oos.sh) (375–388): bracket class in the Python URL regex is wrong for CPython, so normal GitHub URLs never match and `url_tokens` dedupe lines may never emit; primary recovery may mask this but future consumers of plain URL lines are misled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Strict “Filed URL” counter brittle to line shape / trailing noise
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/oos-disposition-shared.inc.bash](scripts/oos-disposition-shared.inc.bash) (40–51): strict counter expects an exact single-line markdown shape ending with the URL only; trailing text/whitespace or heading variants drop strict counts and can false-fail the gate despite visible filings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Single-level blockquote strip misses nested `> >` banners
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) (83–95): only one level of blockquote prefix is stripped, so nested blockquote banners can fail lint or be mis-detected; alternatively document forbidding nesting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Symlinked SKILL/rule Markdown skipped by lint traversal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) (285–287): symlink indirection bypasses enforcement for in-scope paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Fixture inventory doc disagrees with harness case numbering/count
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/test-lint-foreground-markers.md](scripts/test-lint-foreground-markers.md) (74–99) vs [scripts/test-lint-foreground-markers.sh](scripts/test-lint-foreground-markers.sh): sibling doc inventory does not match implemented scenarios, confusing triage after failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: `.pre-commit-config.yaml` header contradicts `make lint-only` vs `make lint` story
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [.pre-commit-config.yaml](.pre-commit-config.yaml) top-of-file comment still implies CI runs `make lint` while docs/plan call for reconciling to `make lint-only` for the CI job and local extras as appropriate (plan OOS_4 / reconciliation task).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Lint stderr message shape vs acceptance needle tokens
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [scripts/lint-foreground-markers.sh](scripts/lint-foreground-markers.sh) stderr messages differ from acceptance wording (e.g. missing unified `<banner|comment> for <BASENAME>` pattern), so runbooks or harnesses matching acceptance regex literally may not match actual output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: AGENTS.md Family B cross-reference folded into ScheduleWakeup bullet
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [AGENTS.md](AGENTS.md) (line 56 area): Family B pointer is embedded in a long ScheduleWakeup bullet rather than a standalone conventions line, slightly weakening discoverability vs plan editorial instruction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: Version bump rationale vs mixed-branch change set
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [.claude-plugin/plugin.json](.claude-plugin/plugin.json): semver bump may not be explained in the foreground-only plan manifest when other commits drive the bump on the same branch; confirm Step 8 bump policy for mixed PRs or split releases so rationale matches what merged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge map (for traceability):**  
FINDING_1 ← input 1, 10, 22 · FINDING_2 ← 2, 12, 27 `[OUT_OF_SCOPE]` · FINDING_3 ← 3 · FINDING_4 ← 4 · FINDING_5 ← 5, 14, 20 · FINDING_6 ← 6 · FINDING_7 ← 7 · FINDING_8 ← 8, 15 · FINDING_9 ← 9 · FINDING_10 ← 11 · FINDING_11 ← 13 · FINDING_12 ← 16 · FINDING_13 ← 17 · FINDING_14 ← 18 · FINDING_15 ← 19 · FINDING_16 ← 21 · FINDING_17 ← 23 · FINDING_18 ← 24 · FINDING_19 ← 25 · FINDING_20 ← 26  

Input 24 was kept separate from FINDING_8 (stderr shape vs banner position). FINDING_7 (positional URL recovery) and FINDING_12 (broken `gh_url` regex) stay separate (different failure modes and fixes).  

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in the file.
