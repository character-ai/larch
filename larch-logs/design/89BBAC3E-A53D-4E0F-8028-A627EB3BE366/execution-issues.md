### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt)

Searching the repo for the dependency-edge plan and related implementation references.
The plan is in the design session cache; reading it now.
**Verdict:** The flip rule and plan-time in-flight client ban are directionally sound, but the plan has gaps on apply-time edge revalidation, busy-prefix classification breadth, and cycle/duplicate normalization that can still write blocked-by edges onto in-flight issues or miss unsafe graphs.

---

## Supporting plan sections (correct)

**REGULAR vs in-flight + flip** — Plan lines 26–39 and anti-pattern line 103:

```26:39:<TMPDIR>/plan.txt
Default issue groups:

- **DESIGNING**: title starts with `[DESIGNING]`
- **DESIGNED**: title starts with `[DESIGNED]`
- **IMPLEMENTING**: title starts with `[IMPLEMENTING]`
- **REGULAR**: every other open issue

For a desired edge `X blocked by Y`:

- If `X` is REGULAR, plan `X blocked by Y`.
- If `X` is in-flight and `Y` is REGULAR, flip to `Y blocked by X`.
- If both are in-flight, write no edge and emit a loud warning.
- Skip duplicates, self-edges, and edges that would create a dependency cycle.
- Revalidate titles at apply time before writing.
```

This keeps in-flight issues off the **client** side when the blocker is REGULAR (flip records the edge on the REGULAR issue). `REGULAR` blocked by in-flight `Y` is allowed and does not violate line 103.

**Plan-time guards** — Lines 132–135 require rewrite/close targets to be REGULAR and normalize edges through the flip rule before `edges_to_write` is frozen.

**Write path** — Line 41 and lines 153–154 route writes through `block-issue add-blocked-by`, matching `skills/block-issue/SKILL.md` (ISSUE_A = client, ISSUE_B = blocker).

---

## Findings


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt)

Reviewing the public skill integration surface: searching the repo for `${CLAUDE_PLUGIN_ROOT}`, skill frontmatter, docs registration, topology, and plugin manifest patterns.
**Verdict:** The shipped runtime surface is largely wired (`skills/`, hooks, `${CLAUDE_PLUGIN_ROOT}` in fences), but consumer docs and strict-permissions registration lag the live `/bug` contract and several other public skills.

---

## Summary

| Area | Status |
|------|--------|
| `${CLAUDE_PLUGIN_ROOT}` in shipped skill fences/hooks | **Good** |
| Skill frontmatter (name, description, hooks) | **Good** with minor gaps |
| README + `docs/skills.md` catalog completeness | **Listed**, but **stale** on `/bug` argv |
| Topology regeneration | **Good** (no `/bug` row expected) |
| Plugin manifest | **Present**; marketplace wording diverges |
| Strict-permissions copy-paste snippet | **Incomplete** vs shipped public skills |
| Missing shipped-runtime / generated-doc steps | **Yes** — see findings 1–3 |

---

## Findings


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt)

Found **2 integration-surface issues**.

### FINDING_1: `/bug --urgent` is missing from public docs

- **Severity:** Medium
- **Issue:** `skills/bug/SKILL.md` now advertises and implements `--urgent`, but the public catalogs still say `/bug` has no flags.
- **Current stale docs:**
  - `README.md:68-71` lists `/bug` as only `<bug description>`.
  - `docs/skills.md:53-59` lists only `<bug description>` and says the skill “takes no flags.”
- **Contradicting shipped runtime:**
  - `skills/bug/SKILL.md:1-4` has `argument-hint: "[--urgent] <bug description>"`.
  - `skills/bug/SKILL.md:23-28` defines `--urgent` and `[BUG] (URGENT)`.
- **Plan support:**
  - `larch-logs/design/6489D890-4C0B-4C37-9FEB-CB7734CE2DA3/plan.txt:109-126` explicitly adds `/bug --urgent`.
  - `larch-logs/design/6489D890-4C0B-4C37-9FEB-CB7734CE2DA3/plan.txt:128-153` adds only a SKILL.md structural harness, so the public catalog step was missed.
  - `larch-logs/design/074668FC-3A89-432E-9668-44BC978C0A67/plan.txt:438-457` establishes README and `docs/skills.md` as the consumer `/bug` registration surfaces.
- **Fix:** Update `README.md` and `docs/skills.md` to show `[--urgent] <bug description>` and explain `[BUG]` vs `[BUG] (URGENT)`.

### FINDING_2: Marketplace wording implies `/bug` uses collaborative reviewers

- **Severity:** Low
- **Issue:** `.claude-plugin/marketplace.json` says `/bug` issue-report filing is “with collaborative reviewers (Claude subagents + Codex + Cursor),” but `/bug` is explicitly inline and does not dispatch external agents.
- **Current misleading wording:**
  - `.claude-plugin/marketplace.json:9-12`
- **Contradicting runtime and plan:**
  - `skills/bug/SKILL.md:29-31` says to use only read-only inline tools and not external agents.
  - `larch-logs/design/48393744-074E-49D7-AFDA-8681B996C37A/plan.txt:12-16` says investigate inline and do not dispatch external agents.
- **Plan support for manifest wording:** `larch-logs/design/074668FC-3A89-432E-9668-44BC978C0A67/plan.txt:467-480` calls for plugin and marketplace descriptions with a short `/bug` mention, not a reviewer claim.
- **Fix:** Reword marketplace text so collaborative reviewers describe design/review/implementation, while `/bug` is described as a read-only issue-filing helper.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-public-skill-surface.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 2271 bytes)
  ```
### FINDING_1: `/bug` catalog docs stale after `--urgent` shipped-runtime change

- **Severity:** important
- **Plan:** `larch-logs/design/6489D890-4C0B-4C37-9FEB-CB7734CE2DA3/plan.txt` § `UPDATED: skills/bug/SKILL.md` (lines 109–126); harness scope in § `NEW: scripts/test-bug-structure.sh` (lines 128–139). Plan updates SKILL + harness only; it does **not** list README/`docs/skills.md`, so doc sync is an integration gap the harness does not close.
- **Concern:** Shipped `skills/bug/SKILL.md` documents `[--urgent]` and pins it via `scripts/test-bug-structure.sh`, but the public catalogs still describe a no-flag skill.
- **Evidence:**

```4:4:skills/bug/SKILL.md
argument-hint: "[--urgent] <bug description>"
```

```23:25:skills/bug/SKILL.md
- `--urgent` is the only flag.
- Remove one or more leading `--urgent` tokens from the description before validation.
```

```55:59:docs/skills.md
**Arguments**: `<bug description>`
...
The whole `$ARGUMENTS` string is the bug description; the skill takes no flags.
```

```68:70:README.md
      <td><a href="docs/skills.md#bug"><code>/bug</code></a></td>
      <td><code>&lt;bug description&gt;</code></td>
```

- **Missing step:** Update `docs/skills.md` § `/bug` and README public-skills table argv column; add a mechanical doc-sync check (similar to `scripts/test-quick-mode-docs-sync.sh` for `/implement`) or extend `scripts/test-bug-structure.sh` to grep the catalogs.

---

### FINDING_2: `SECURITY.md` omits `/bug` deny-edit-write consumer contract

- **Severity:** important
- **Plan:** `larch-logs/design/48393744-074E-49D7-AFDA-8681B996C37A/plan.txt` § `NEW: skills/bug/SKILL.md` (lines 45–50) requires skill-scoped `deny-edit-write.sh` on `Write`.
- **Concern:** `/research` is documented at length; `/bug` ships the same hook pattern but has no parallel SECURITY section. Strict-permissions / read-only consumers auditing hooks will miss it.
- **Evidence:**

```6:12:skills/bug/SKILL.md
hooks:
  PreToolUse:
    - matcher: "Write"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh"
```

`SECURITY.md` documents `/research` hook behavior at lines 241–255; **no `/bug` mention** in that file (grep returns no matches).
- **Missing step:** Add a `/bug` subsection mirroring `/research` (hook matcher scope, `/tmp`-only `Write`, `Bash` residual risk, child-skill hook non-propagation).

---

### FINDING_3: Strict-permissions snippet incomplete for several shipped public skills

- **Severity:** important
- **Plan:** `docs/configuration-and-permissions.md` § “Copy-paste settings.allow snippet” (lines 11–37) claims to cover invoked larch skills; `skills/upgrade-larch/SKILL.md` § “Edit-in-sync” (line 25) lists `docs/skills.md` as a manual sync surface.
- **Concern:** The copy-paste `Skill(...)` block omits multiple user-invocable public skills. Dev `.claude/settings.json` is also incomplete for some of them.
- **Evidence — missing from docs snippet** (`docs/configuration-and-permissions.md` lines 14–37): `pause`, `fluff-analysis`, `gc-run-logs`, `status`, `upgrade-larch` (and qualified `larch:` forms).
- **Evidence — dev settings gap** (`.claude/settings.json` lines 145–174): has `upgrade-larch` but **not** `pause`, `fluff-analysis`, `gc-run-logs`, or `status`.
- **Missing step:** Extend the docs snippet and `.claude/settings.json` with bare + `larch:` pairs for every shipped `skills/*/SKILL.md` users can invoke directly.

---

### FINDING_4: `docs/skills.md` `/status` drops `${CLAUDE_PLUGIN_ROOT}` convention

- **Severity:** nit
- **Plan:** `skills/shared/skill-design-principles.md` § III-A (line 39): plugin paths via `${CLAUDE_PLUGIN_ROOT}`; shipped `skills/status/SKILL.md` follows this.
- **Concern:** Consumer catalog shows a bare `python3 python/cli.py` invocation, unlike the shipped skill fence.
- **Evidence:**

```13:14:skills/status/SKILL.md
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" status check
```

```179:179:docs/skills.md
... then `python3 python/cli.py agent degraded-tools-gate` to classify each vendor ...
```

- **Missing step:** Align catalog prose with the shipped fence (or cite the launcher indirection explicitly).

---

### FINDING_5: `/pause` shipped-runtime block `source`s session env

- **Severity:** latent
- **Plan:** `skills/shared/subskill-invocation.md` § “Security — never `source` a session-env file” (lines 179–183); pause plan finding 21 (`larch-logs/design/707E97A2-.../accepted-plan-findings.md` lines 202–207) required catalog registration (now done) but not this parse pattern.
- **Concern:** Inline `source "$ENV_FILE"` in shipped `skills/pause/SKILL.md` contradicts the repo-wide safe-parse rule for cross-boundary env files.
- **Evidence:**

```29:30:skills/pause/SKILL.md
# shellcheck disable=SC1090
source "$ENV_FILE" || true
```

vs.

```179:183:skills/shared/subskill-invocation.md
**Do NOT `source` `session-env.sh`.** Parse it line-by-line with `KEY=VALUE` matching.
```

- **Note:** Later lines 37–44 correctly use `${CLAUDE_PLUGIN_ROOT}` for CLI calls.

---

### FINDING_6: Plugin manifest wording diverges between `plugin.json` and `marketplace.json`

- **Severity:** nit
- **Plan:** Public integration surface includes both `.claude-plugin/plugin.json` (consumer version/semver) and `.claude-plugin/marketplace.json` (marketplace listing).
- **Concern:** Descriptions are not aligned; marketplace text is shorter and emphasizes `/bug` + reviewers differently from `plugin.json`.
- **Evidence:**

```5:5:.claude-plugin/plugin.json
  "description": "Multi-agent workflow automation for Claude Code: issue-anchored `/design` ... `/bug` (consumer issue-filing helper), and `/implement` ...
```

```11:11:.claude-plugin/marketplace.json
      "description": "Multi-agent workflow automation for Claude Code: design, code review, implementation, and PR automation, and `/bug` issue-report filing with collaborative reviewers (Claude subagents + Codex + Cursor).",
```

- **Missing step:** Edit-in-sync pass when either manifest changes (no mechanical harness today).

---

### FINDING_7: Minor frontmatter gaps on no/low-argv skills

- **Severity:** nit
- **Plan:** `skills/shared/skill-design-principles.md` § V (lines 53–68): `argument-hint` helps activation; not all skills need it.
- **Concern:** `upgrade-larch` documents `--run-id` in body (lines 9–11) but omits `argument-hint`; `pause` omits `allowed-tools: Bash` despite a Bash-only fence.
- **Evidence:** `skills/upgrade-larch/SKILL.md` lines 1–11; `skills/pause/SKILL.md` lines 1–4 vs. Bash block at lines 20–50.

---

## Passing checks

### `${CLAUDE_PLUGIN_ROOT}`

- Shipped public skills use `${CLAUDE_PLUGIN_ROOT}` in executable fences and hook commands (`skills/bug/SKILL.md` lines 11, 53; `skills/status/SKILL.md` line 14; `hooks/hooks.json` throughout).
- `skills/shared/subskill-invocation.md` and `skills/shared/skill-design-principles.md` § III-A codify the convention.
- `scripts/test-bug-structure.sh` pins `/bug` contract but does **not** cover docs (by design per plan 6489D890).

### Skill frontmatter

- All 17 public `skills/*/SKILL.md` files have `name` + `description`.
- Orchestrators (`implement`, `review`, `alias`, `research`, `bug`) carry anti-halt banners per `skills/shared/subskill-invocation.md` § Scope list (lines 123–129), enforced by `scripts/test-anti-halt-banners.sh` (`Makefile` `test-anti-halt` target).
- Read-only filing skills (`bug`, `research`) ship skill-scoped `deny-edit-write.sh` hooks in frontmatter.

### README + `docs/skills.md` registration

- All public skills including `/pause` appear in both `README.md` § Public skills (lines 36–144) and `docs/skills.md` § Public skills (lines 11–29).
- `/im` alias registered in README § Aliases (lines 217–223) and `docs/skills.md` § Aliases (lines 189–199).
- Pause catalog gap from plan finding 21 appears **resolved**.

### Topology regeneration

- Authority: `skills/shared/topology.tsv`.
- Generated doc: `docs/topology.md` lines 1–4 AUTO-GENERATED header + `python3 python/cli.py generate topology-docs`.
- Rule: `.claude/rules/topology-generation.md` lines 26–28.
- Harness: `make test-check-topology-rule-paths`, `scripts/check-topology-rule-paths.py` (`agent-lint.toml` lines 539–548).
- No topology row is required for `/bug` (topology covers design/implement/research panel shapes only).

### Plugin manifest + shipped runtime

- Version `51.1.9` in `.claude-plugin/plugin.json` line 3.
- Sparse shipped dirs: `scripts/lib-sparse-dirs.sh` line 9 (`skills` included).
- `skills/upgrade-larch/SKILL.md` line 25 documents manual edit-in-sync surfaces when sparse allowlist changes.

---

## Recommended fix order (guidance only; Ask mode)

1. Sync `/bug` argv in `docs/skills.md` + `README.md`; add a harness assertion.
2. Document `/bug` in `SECURITY.md` next to `/research`.
3. Complete strict-permissions snippet + `.claude/settings.json` for `pause`, `fluff-analysis`, `gc-run-logs`, `status`, `upgrade-larch`.
4. Align `plugin.json` / `marketplace.json` descriptions.
5. Refactor `/pause` env load to safe KV parse (or route through `session setup --caller-env`).

I can draft exact doc/manifest diffs in Agent mode if you want these applied.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-public-skill-surface.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 10825 bytes)
  ```
### FINDING_1: Apply does not re-run flip/in-flight guards on edges (only on rewrites/closes)

- **Severity:** Important  
- **Focus area:** correctness  
- **Plan section:** `python/deps_audit.py` `apply` (plan lines 145–156)  
- **Code:** `python/issue_block.py` lines 38–122  

**Concern:** `apply` re-fetches metadata and skips rewrites/closes that are “no longer REGULAR and open” (lines 149–150), but it does not say to re-classify **edge endpoints**, re-run flip normalization, or reject any `edges_to_write` row whose **client** is DESIGNING/DESIGNED/IMPLEMENTING. It only says to write edges from the plan file (lines 153–154). `issue_block.py` performs no title checks, so a stale plan can still POST `addBlockedBy` with an in-flight client if a title changed after `plan`.

**Scenario:** At plan time `#10` is REGULAR; desired edge `10 blocked by 5` is approved. Before apply, `#10` is renamed to `[DESIGNING] …`. Apply writes the frozen edge unless it explicitly re-validates clients.

**Plan fix:** In `apply`, re-fetch titles for every edge endpoint; re-run `_plan_edge` / flip logic; skip (and warn) if the normalized client is in-flight or not open; do not trust frozen `edges_to_write` alone.

---

### FINDING_2: “REGULAR” swallows other managed/busy prefixes

- **Severity:** Important  
- **Focus area:** correctness  
- **Plan section:** Grouping rules (plan lines 26–31); anti-pattern line 103  
- **Code:** `python/combine_issues.py` line 23; `python/admission.py` lines 49–54; `.claude/skills/combine-issues/SKILL.md` line 425  

**Concern:** Only `[DESIGNING]`, `[DESIGNED]`, and `[IMPLEMENTING]` are in-flight. Titles like `[STALLED]`, `[DONE]`, `[PLANNED]`, `[IN PROGRESS]`, and `[LOCKED]` fall into **REGULAR**. For those issues the plan allows body rewrites, stale closes, and new blocked-by edges as **client**. Elsewhere, combine-issues treats several of these as busy and refuses to combine them (`_BUSY_RE` at `python/combine_issues.py:23`; anti-pattern at `.claude/skills/combine-issues/SKILL.md:425`). Admission treats `[DESIGNING]`, `[IMPLEMENTING]`, `[STALLED]`, etc. as managed (`python/admission.py:49–50`) but **not** `[DESIGNED]`.

**Scenario:** `#42 [STALLED] …` is classified REGULAR → `/deps` can add a new blocked-by edge **to** `#42`, contradicting the review goal for workflow-active issues.

**Plan fix:** Either expand in-flight groups to match `_BUSY_RE` / admission managed prefixes (excluding `[DESIGNED]` if that remains deliberate), or document why STALLED/DONE/LOCKED are intentionally mutable and accept the risk.

---

### FINDING_3: Prefix matching is underspecified vs existing title guards

- **Severity:** Important  
- **Focus area:** correctness  
- **Plan section:** `_group_for_title` (plan lines 160–161); grouping lines 28–30  
- **Code:** `python/admission.py` lines 49–54; `python/combine_issues.py` line 23  

**Concern:** Plan says “title starts with `[DESIGNING]`” without requiring the canonical `"[DESIGNING] "` trailing space. Admission uses `startswith("[DESIGNING] ")` (`python/admission.py:50`). `_BUSY_RE` uses `\[DESIGNING\]\s` (`python/combine_issues.py:23`). A title `[DESIGNING]foo` (no space) could classify as REGULAR and receive a new blocked-by edge.

**Plan fix:** Pin `_group_for_title` to the same prefix rules as `admission._has_managed_prefix` / `_has_designed_prefix`, with tests for boundary titles.

---

### FINDING_4: Cycle prevention and duplicate normalization are not fully specified

- **Severity:** Important  
- **Focus area:** correctness  
- **Plan section:** Flip/cycle lines 37–38; `plan` verb lines 133–135; helpers lines 163–164  

**Concern:** The plan names `_edge_would_cycle` but does not state:
1. Whether cycle checks run on **post-flip** `(client, blocker)` tuples.  
2. Whether existing `blocking` edges are normalized to `(client, blocker)` before dedupe (line 124 reads both directions but does not define merge semantics).  
3. Whether transitive cycles through existing native edges are considered (compare `/issue` SCC loop in `skills/issue/SKILL.md` around Step 5 validation).

Pre-flip cycle checks on `DESIGNING blocked by REGULAR` could differ from post-flip `REGULAR blocked by DESIGNING`.

**Plan fix:** Specify: normalize all existing edges to directed `(client, blocker)`; apply flip before dedupe and cycle detection; document algorithm (DFS or SCC, same as `/issue`); add tests for “flip introduces cycle with existing edge.”

---

### FINDING_5: Apply-time revalidation for edge blockers is incomplete

- **Severity:** Moderate  
- **Focus area:** edge cases  
- **Plan section:** `apply` (lines 149–156); edge cases (lines 261–263)  

**Concern:** Edge case line 261 (“Issue changes group after fetch”) is not explicitly tied to **edge writes**. There is no requirement that blockers remain open at apply time. A `REGULAR blocked by DESIGNING` edge could be applied after the DESIGNING issue closed, leaving a questionable dependency.

**Plan fix:** At apply, skip edges whose client or blocker is not open; optionally reclassify satisfied/closed blockers like `combine_issues._classify_edge` “satisfied” handling (`python/combine_issues.py:395–396`).

---

### FINDING_6: Step 6 trusts frozen plan without optional re-`plan` pass

- **Severity:** Moderate  
- **Focus area:** risk-integration  
- **Plan section:** Steps 4–6 (lines 82–98); `apply` (lines 145–156)  

**Concern:** Approval covers a plan JSON snapshot. Long gaps between approval and `deps apply` rely entirely on apply-side checks; those checks are spelled out for rewrites/closes but not for edges (Finding 1). Safer pattern (used in combine-issues oos-6c): refresh metadata and re-run planner before mutation.

**Plan fix:** Either re-invoke `deps plan` inside `apply` with the approved proposals file plus fresh fetch, or duplicate the full normalization pipeline in `apply` before any `block-issue` call.

---

## Checklist vs review prompt

| Criterion | Plan coverage | Gap |
|-----------|---------------|-----|
| REGULAR vs in-flight classification | Lines 26–31, 160–161 | STALLED/DONE/LOCKED/PLANNED/IN PROGRESS treated as REGULAR (Finding 2); prefix spacing (Finding 3) |
| Flip behavior | Lines 35–36, 133 | Sound if applied post-fetch and **again** at apply (Finding 1) |
| Cycle prevention | Lines 37–38, 163–164 | Underspecified; flip order unclear (Finding 4) |
| Duplicate handling | Lines 38, 134 | Direction normalization not pinned (Finding 4) |
| Apply-time revalidation | Lines 39, 149–150 | Edges not re-normalized; blockers not checked (Findings 1, 5) |
| No new blocked-by on DESIGNING/DESIGNED/IMPLEMENTING | Lines 103, 35–37, 132 | Holds at plan time; **not enforced at apply** without Finding 1 fix; busy non-DESIGNING prefixes exposed (Finding 2) |

---

## Tests the plan should add (beyond lines 184–195)

- Apply skips edge when client title changed from REGULAR → `[DESIGNING]` after plan.  
- `[STALLED]` / `[LOCKED]` classification: in-flight vs REGULAR per chosen policy.  
- Prefix boundary: `[DESIGNING]foo` vs `[DESIGNING] foo`.  
- Post-flip cycle: existing `B blocked by A` + proposed `A blocked by B` (REGULAR/in-flight flip).  
- `blocking` API rows normalize to the same duplicate key as `blocked_by` rows.

---

**Bottom line:** Plan-time flip + “never client on in-flight” is the right model, but **`apply` must re-validate and re-normalize every edge** because `issue_block.py` will write whatever numbers it receives. Until then, rename races and incomplete in-flight prefix coverage are realistic paths to new blocked-by edges on workflow-active issues.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-deps-guardrails.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
✓ cursor agent: completed (exit code 0, output 9935 bytes)
  ```
