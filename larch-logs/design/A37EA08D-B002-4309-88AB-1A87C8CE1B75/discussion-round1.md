## Decision 1: Switch-to-discussion fallback in auto-apply mode
- **Question**: How should the user retain access to discussion mode when auto-apply is the default?
- **Resolution**: Gate C only. Auto-apply silently applies all accepted findings; the user still picks "Discuss further" at Gate C's final-approval prompt. Re-running /design with --manual restores the per-iteration Gate B prompt.
- **Source**: user

## Decision 2: Severity gating for auto-apply
- **Question**: Should auto-apply respect severity (e.g., always prompt on Critical)?
- **Resolution**: No gating — auto-apply applies every accepted finding regardless of severity. Matches the literal feature description ("auto-apply all approved suggestions").
- **Source**: user

## Decision 3: Apply visibility on auto-apply path
- **Question**: Should the auto-apply path still print the list of findings being applied?
- **Resolution**: Print findings list + breadcrumb. Auto-apply prints "🔶 /design 3.5: gate B (auto-apply N findings)" plus a compact list (severity + reviewer + concern excerpt) before revising plan.txt.
- **Source**: user

## Decision 4: Scope of the --manual flag
- **Question**: Should the default also apply to Gate A "Discuss more" plan revisions, or only Gate B?
- **Resolution**: Gate B only. Gate A discussion sub-rounds and Gate C final approval are unchanged. --manual restores today's per-iteration Gate B prompt only.
- **Source**: user

## Decision 5: Manual-mode shape
- **Question**: Should --manual reproduce today's Gate B verbatim or add reminder text?
- **Resolution**: Exact current behavior. --manual is a pure default-flip — no new prompt text, no "auto-apply is default" reminder, no other Gate B changes.
- **Source**: user

## Decision 6: Flag persistence across re-entries
- **Question**: Does the flag persist for the full /design run or could it toggle mid-run?
- **Resolution**: Whole-run sticky. Flag is parsed once at argv, persisted to $DESIGN_TMPDIR/run-params.json, and consulted on every Gate B entry (including Step 3 re-entries from Gate C(c) "Re-run review panel"). No mid-run toggle.
- **Source**: user

## Decision 7: Coordination with issue #2667
- **Question**: Does this need to coordinate with #2667 (Gate B multi-round presentation + docs reconciliation)?
- **Resolution**: This issue (#2930) ships first; #2667 is marked blocked-by #2930 (native GitHub blocker dependency). #2667's multi-round Gate B docs rebase on top of the new auto-apply default after this lands. The plan should explicitly call out State Invariant #4 update so #2667's later edit knows the new contract.
- **Source**: user

## Hard constraints (derived from codebase scan)
- Cross-tier uniformity: --manual applies across --trivial/--simple/--hard (--trivial's quick self-review also produces accepted-plan-findings.md → Gate B path).
- Gate C unchanged: still the only human-final-approval gate; "Discuss further" and "Re-run review panel" options preserved.
- Gate A unchanged: Discussion sub-rounds (Round 1 + Round 2) unaffected.
- Zero-findings short-circuit at Gate B remains intact (no prompt regardless of flag setting).
- No mutation to plan-review machinery (Step 3 voting, tally script, aggregator) — only the Gate B prompt branch changes.
- approval-gates.md State Invariant #4 ("No-auto-apply contract") needs revision: the new contract is "auto-apply by default; --manual restores per-iteration approval".
- run-params.json key name follows existing convention (partition_requested / brainstorm_requested) — propose `manual_gate_b` (boolean, default false).

## Non-goals (out of scope for this change)
- Multi-round Gate B (issue #2667) — independent feature; just coordinate via blocker.
- Severity-based partial auto-apply (e.g., Critical always prompts) — declined per Decision 2.
- Mid-run mode toggle UI (extra Gate B option to re-enable prompts) — declined per Decision 6.
- /implement integration: this flag is /design-only; no argv forwarding from /implement (which doesn't invoke /design internally).
