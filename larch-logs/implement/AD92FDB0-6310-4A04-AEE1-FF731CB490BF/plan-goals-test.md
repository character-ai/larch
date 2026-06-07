## Goal
Implement issue #3649: [IMPLEMENTING] PR3: Necessity-gated review — rubric + YES/NO judge bar + reviewer self-filter\n\n# PR3 — Necessity-gated review: rubric + YES/NO judge bar + reviewer self-filter.

## Implementation Plan
# PR3 — Necessity-gated review: rubric + YES/NO judge bar + reviewer self-filter

**Part of a 3-PR split of #3644.** **Blocked by #3647 (EXONERATE → YES/NO) and #3648 (assessor removal).** Implement this PR **after both are merged**, and rebase on them — by then the judge/voter is already YES/NO with simplified scoring (#3647), and `skills/design/SKILL.md` / `scripts/test-design-structure.sh` are already free of the assessor (#3648). This PR adds the **acceptance criteria** (it does not re-touch EXONERATE, scoring, or the assessor). Implementer: Sonnet.

Read `AGENTS.md`, `KARPATHY_CLAUDE.md`, `BASH_AUTHORING.md`, `skills/shared/reviewer-templates.md`, `skills/shared/voting-protocol.md`, and `.claude/rules/reviewer-archetype-generation.md` before starting.

## Context

larch review accepts too many findings, bloating plans/diffs round over round. #3647 made voting binary (YES/NO) but left the **criteria** unchanged — the judge still accepts anything "correct / important / worth implementing," which admits any plausible-sounding improvement. This PR replaces that preference test with a **necessity gate** at both the judge (filter) and the reviewer (supply), and makes Out-of-Scope the rewarded home for real-but-non-essential findings, so conservatism *defers* good ideas rather than discarding them.

This is the additive half of the overhaul. The structural half (YES/NO, scoring) already shipped in #3647.

---

## A. Canonical necessity rubric (new shared source of truth)

Create `skills/shared/review-acceptance-rubric.md`. This is the single source both the judge prompt and the reviewer prompts embed. Mirror the existing OOS-rubric sync convention: a test greps a shared sentence across every surface that embeds it (see `scripts/test-render-voter-prompt.sh` for the pattern).

**Verbatim content of the rubric body** (the text reviewers and judges must see):

```
# Review Acceptance Rubric (Necessity Gate)

A proposed change is **in-scope-acceptable only if the feature would be incomplete, broken,
unverifiable, or regressed without it.** If a finding is real, or even valuable, but the feature
ships correctly without it, it is **not in-scope** — route it to Out-of-Scope (file a tracked
issue). To be accepted in-scope, a finding must clear at least one of these gates:

1. Completeness — the change is a required part of the specified feature; without it,
   functionality the issue explicitly asked for is missing or only partially delivered.
2. Correctness — as written, the plan or implementation would fail to deliver the feature as
   specified: a real defect on the feature's own execution path (wrong behavior, inverted logic,
   a missing case the spec requires).
3. Introduced regression or harm — the change itself introduces a security vulnerability, a
   data-loss or data-corruption path, or a breaking change to an existing caller, contract, or
   CLI/wire surface — even if the new feature works. (You do not ship a regression and file an
   issue about it.)
4. Necessary test — the change adds a test for behavior THIS feature introduces that is not
   covered by any existing or planned test, AND the test is proportionate to the behavior's risk
   and size. A test that merely could exist, restates coverage already present, or is
   red-green-TDD-that-should-have-happened does NOT qualify — that is a Nit, and Nits never clear
   this gate.
5. Unblock a pre-existing condition — a pre-existing defect that actively blocks completing,
   building, or verifying the feature (overlaps 1-2; the test is "the feature cannot be finished
   or shipped until this is fixed").

Default-deny. If you are unsure whether a finding clears a gate, it does not. Unsure => Out-of-Scope
or reject => never an in-scope accept.

Out-of-Scope signals, NOT acceptance signals (real, possibly worth a future issue — never an
in-scope change here): "cleaner," "more robust," "more idiomatic," "more consistent," "more
flexible / future-proof," "best practice," "while we're here," "defensive in case," refactors,
renames-for-clarity, added configurability, and broadened error handling for inputs the feature
cannot produce.

Out-of-Scope is the safe harbor, not the trash. A real finding that fails the necessity gate
belongs on the Out-of-Scope list, where it can still be accepted as a tracked GitHub issue.
Deferring a good idea is the correct outcome, not a loss.

Severity interaction. A Nit can never clear the necessity gate (a Nit is by definition optional).
After the first review round, a finding that no prior round raised is suspect: if it were
necessary, the plan or code would not have passed the earlier round — hold it to gate 2 or 3
(Correctness or Introduced-regression) only.

Anchor. Judge necessity against the spec, not against the finding text. For /design plan review,
the spec is the originating issue scope (the staged scope anchor / feature description). For
/implement and /review code review, the spec is the implementation plan (plan fidelity).
```

Keep the file's prose free of hardcoded counts / line numbers per `.claude/rules/drift-prone-prose-in-docs.md`. Add an "Update triggers" footer listing every surface that embeds the rubric (judge renderer, reviewer template, generated agents, external-reviewer renderers, competition notice) so future edits stay in sync.

---

## B. Judge / voter — add the necessity criteria

The judge is already YES/NO (from #3647). This PR adds the necessity bar.

### B1. `scripts/render-voter-prompt.sh`

After the `You are a %s.` line, insert this **verbatim** block (keep the existing `Do NOT vote NO solely because you dislike or distrust the proposed fix …` line that #3647 left in place):

```
You vote YES or NO on each in-scope finding. Vote YES only if the finding is NECESSARY for the feature under the Review Acceptance Rubric below: the feature would be incomplete, broken, unverifiable, or regressed without it. Otherwise vote NO.
Default-deny: if you are unsure whether a finding clears a necessity gate, vote NO. "Legitimate but not necessary" is a NO — such findings belong on the Out-of-Scope list, not in this change.
Do NOT vote YES because the change would be cleaner, more robust, more consistent, more flexible, more idiomatic, or "best practice" — those are Out-of-Scope signals, not acceptance signals.
When the CORRECTNESS axis is recorded on a NO vote, use false-positive only when the problem is not real; use true or partially-true when the problem is real but does not clear a necessity gate.
```

Then emit the rubric body from `skills/shared/review-acceptance-rubric.md` (cat the file, or inline a copy kept in sync by the grep test). Leave the YES/NO output grammar from #3647 unchanged.

### B2. `skills/shared/voting-protocol.md`

Tighten the YES definition in the voter prompt template from "correct, important, and worth implementing" to the necessity bar, and reference the Review Acceptance Rubric. Keep the YES/NO shape from #3647.

### B3. `skills/design/references/plan-review.md`

Update the inline Voter-1 instruction string and the Codex/Cursor voter instruction string to the necessity framing (YES only if the finding is necessary per the rubric; default-deny; cleaner/robust/etc. are Out-of-Scope signals).

### B4. Rubric-sync test

Extend `scripts/test-render-voter-prompt.sh` (or add a sibling) to grep a shared rubric sentence across `skills/shared/review-acceptance-rubric.md`, `scripts/render-voter-prompt.sh`, `skills/shared/reviewer-templates.md`, and the external-reviewer renderers, so the embedded copies cannot drift.

---

## C. Reviewer — same rubric, self-filter, scored by it

### C1. `skills/shared/reviewer-templates.md` — add to the "Quality gate" section

Insert this **verbatim** subsection (applies to the canonical Code Reviewer archetype and all generated specialists):

```
## Necessity gate (in-scope findings)

Before you place ANY finding under In-Scope Findings, it must clear the Review Acceptance Rubric:
the feature must be incomplete, broken, unverifiable, or regressed without it. If the feature ships
correctly without your finding — however real or valuable — it is NOT in-scope. Put it under
Out-of-Scope Observations instead.

"Cleaner," "more robust," "more consistent," "more idiomatic," "more flexible," "best practice,"
"while we're here," refactors, renames, added configurability, and defensive handling for inputs
the feature cannot produce are Out-of-Scope signals — never In-Scope.

You are scored against this same rubric. Putting a finding In-Scope that the panel does not accept
forfeits the point: you earn 0 if at least one judge found it credible and -1 if none did. The safe
home for a real-but-non-essential finding is Out-of-Scope, where panel acceptance still earns +1.
Win points by putting necessary findings In-Scope and real-but-not-necessary findings
Out-of-Scope — not by maximizing In-Scope volume.
```

Then **regenerate** the four generated agents (CI `agent-sync` enforces this; see `.claude/rules/reviewer-archetype-generation.md`):

- `bash scripts/generate-code-reviewer-agent.sh`
- `bash scripts/generate-reviewer-plan-fidelity-agent.sh`
- `bash scripts/generate-reviewer-code-robustness-agent.sh`
- `bash scripts/generate-reviewer-security-structure-tests-agent.sh`

### C2. Hand-maintained specialist variants

Add the same Necessity-gate subsection directly to `agents/reviewer-edge-cases.md` and `agents/reviewer-testing.md` (they carry the "specialist variant, hand-maintained" header), then run `bash scripts/generate-pre-rendered-reviewer-prompts.sh` so `agents/pre-rendered/` stays in sync.

### C3. External-reviewer prompt renderers

Add the rubric + scoring-awareness to the external (Codex/Cursor) reviewer prompts:

- `skills/design/scripts/render-plan-review-prompt.sh` (the 5 static plan-review archetypes + dynamic tail).
- `scripts/render-specialist-prompt.sh` (the `/review` code-review specialists).

### C4. Competition notice

Add a necessity-awareness paragraph to the Competition notice blockquote in `skills/design/references/plan-review.md` (and any sibling copies the grep surfaces): voting is YES/NO against the Review Acceptance Rubric; real-but-not-necessary findings belong in Out-of-Scope; the scoring (already in place from #3647) rewards correctly-routed findings, not In-Scope volume. Do **not** restate or alter the scoring table itself — #3647 owns it.

---

## Boundary with the other PRs

- **Do NOT** re-touch EXONERATE, the YES/NO grammar, or the scoring table — #3647 owns all of it. This PR only adds necessity *criteria* and *reviewer self-filtering*.
- **Do NOT** touch the plan-quality assessor — #3648 removed it.
- The judge anchors necessity on the issue scope for `/design` and on the plan for `/implement` / `/review` (already plumbed: design voters receive `--scope-anchor-file`; code review has the plan-fidelity reviewer).

## Definition of done

1. `skills/shared/review-acceptance-rubric.md` exists; a sync test greps a shared rubric sentence across the judge renderer, reviewer template, generated agents, and external renderers.
2. A voter prompt rendered by `scripts/render-voter-prompt.sh` embeds the rubric and the default-deny line; the YES definition is necessity-based.
3. The Code Reviewer archetype and all generated / hand-maintained agents contain the Necessity-gate subsection; `scripts/check-generators.sh` passes (no agent-sync drift); `agents/pre-rendered/` regenerated.
4. External-reviewer renderers and the Competition notice carry the rubric + scoring-awareness.
5. `bash scripts/relevant-checks.sh` and `make lint` pass; `scripts/test-render-voter-prompt.sh`, the design/review test suites, and the agent-sync check pass; `make lint-bash32` and `make lint-bare-grep-probe` clean.
6. `docs/topology.md` regenerated if any topology count changed; the sibling `.md` of every edited script updated in the same PR.
7. `SECURITY.md` reviewed for any security-relevant behavior change (OOS security-tag handling is unchanged by this PR — confirm).

## Test plan
(no test plan section in plan-file)
