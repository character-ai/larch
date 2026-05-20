### FINDING_1: [OUT_OF_SCOPE] docs, `docs/voting-process.md:30`: Pre-existing stale wording says dispatch degraded-panel warnings include missing slots and the active tier, but `scripts/dispatch-code-voters.sh` emits only an effective-judge count; tier wording is written later by `skills/review/scripts/tally-code-votes.sh`. Suggested fix: split dispatch warning behavior from tally-file warning behavior so operators know where to look.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. docs, `docs/voting-process.md:30`: Pre-existing stale wording says dispatch degraded-panel warnings include missing slots and the active tier, but `scripts/dispatch-code-voters.sh` emits only an effective-judge count; tier wording is written later by `skills/review/scripts/tally-code-votes.sh`. Suggested fix: split dispatch warning behavior from tally-file warning behavior so operators know where to look.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] 2-judge fallback wording near designed 2-judge round 2+ section. Round 1 degradation misread as intentional 2-judge mode. Prefer degraded two remaining judges for round 1 vs intentional round 2+ panel.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Ambiguous stdout refers to Claude vs launcher. Reader looks at wrong stream for JSON error body. State JSON is written to the voter output file (claude primary stream), not unqualified stdout.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] JSON error described as on stdout. Readers may look at the wrong artifact; technically stdout is redirected to the voter output path. Say the JSON appears in the voter output file (CLI stdout as captured).
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] voter1_rc=2 described only as inside launch-claude-review.sh. Subprocess fail() also yields exit 2 before a successful Claude run. Widen wording to launch stack (launch-claude-review and launch-claude-subprocess validation).
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] rc=2 described only as validation inside launch-claude-review.sh Maintainers grep launch-claude-review.sh only and miss launch-claude-subprocess.sh fail() guards that also yield voter1_rc=2 and stderr via relay. Describe rc=2 as validation in launch-claude-review.sh or launch-claude-subprocess.sh preflight; point to subprocess fail() per line 43.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Heuristic framed as definitive API diagnosis with fixed exit 1 and JSON stdout Future CLI behavior or other faults could match the signature and mis-triage transient vs other failures. Frame as pattern from #2433 / commonly matches; avoid absolute “indicates” unless invariant is guaranteed.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] “Accepted recovery” without DISPATCH_OK / warning context Operators still see DISPATCH_OK=false and may treat it as hard failure. Note DISPATCH_OK stays false and degraded warning may appear while 2-judge path is expected.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Accepted recovery prose omits DISPATCH_OK and degraded warning behavior. voter1 failure still sets DISPATCH_OK false and can emit DEGRADED_PANEL_WARNING on round 1; consumer treats dispatch as hard-failed despite no manual fix needed. Clarify that DISPATCH_OK may still be false and warnings may still fire; accepted means triage stance not green status.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Doc ties voter1_rc=2 only to validation inside launch-claude-review.sh before CLI returns. Subprocess launch-claude-subprocess.sh fail() also exits 2 and propagates through launch-claude-review.sh; reader misattributes a 1 MB context failure to the wrong script layer. Describe rc=2 as validation failures from launch-claude-review.sh and/or launch-claude-subprocess.sh (wrapper chain), not only launch-claude-review.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Heuristic rc=1 + output + empty launcher-stderr described as indicating API-class errors. Other failure modes could match the same observable pattern in theory; doc reads as definitive diagnosis. Soften to correlates with / typical of or narrow to #2433-characterized cases.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Recovery prose names “Voters 2 and 3” for all rounds after Voter 1 fails. On round 2+ Codex is omitted; only the Cursor slot is dispatched, so the doc overstates how many judges remain. Qualify by round: round 1 → Codex + Cursor may continue; round 2+ → Cursor waterfall only (Codex still skipped).
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] `voter1_rc=2` is described only as `launch-claude-review.sh` validation before the CLI returns. `launch-claude-subprocess.sh` also exits 2 via `fail()` for pre-invocation checks; same file’s next paragraph documents subprocess `fail()` on stderr, so readers get conflicting attribution. Describe rc=2 as validation across `launch-claude-review.sh` and `launch-claude-subprocess.sh` (or “launch stack”), not a single wrapper.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Heuristic for `voter1_rc=1` + bytes + empty stderr is stated as definitive (“indicates”). Future edge cases could share the surface signature; operators might skip verifying output/diag. Use hedged language (“typically”) and explicitly tell readers to confirm via voter output / diag excerpt.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] voter1_rc=2 attributed only to launch-claude-review.sh validation Operators or triage docs treat exit 2 as outer-wrapper-only; subprocess guard failures (roots, 1MB cap, invalid paths) are misclassified and debugging looks at the wrong script layer Describe rc=2 as validation failures in launch-claude-review.sh or launch-claude-subprocess.sh before CLI success, with stderr usually populated via re-emitted subprocess diagnostics
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] CLI JSON error described as on stdout Readers may conflate wrapper stdout (/dev/null) with where the JSON actually lands Clarify JSON lands in the voter output file (captured CLI stdout)
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New recovery prose implies only operational continuation; it omits that DISPATCH_OK becomes false when Voter 1 fails. Operator assumes DISPATCH_OK stays true or that downstream should not treat the run as failed when only Voter 1 hits a transient API error. Clarify that DISPATCH_OK is still false and degraded-panel signaling still applies; separate human triage from dispatch_ok semantics.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Heuristic signature stated in definitive tone. Future CLI or wrapper behavior could diverge; doc read as a contract. Mark as heuristic or typical pattern and avoid implying exhaustive classification.
- **Suggested revision**: Address the concern above.

### FINDING_19: docs, `scripts/dispatch-code-voters.md:32`: The new paragraph says a Voter 1 API-style failure falls back to a “2-judge fallback (Voters 2 and 3 continuing without Voter 1)” without limiting that statement to round 1. In round 2+, Voter 2 is intentionally skipped, so a Voter 1 failure leaves only Voter 3 and the tally becomes single-judge if Voter 3 succeeds. Suggested fix: qualify the sentence as round-1 behavior, and add the round-2+ behavior explicitly.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. docs, `scripts/dispatch-code-voters.md:32`: The new paragraph says a Voter 1 API-style failure falls back to a “2-judge fallback (Voters 2 and 3 continuing without Voter 1)” without limiting that statement to round 1. In round 2+, Voter 2 is intentionally skipped, so a Voter 1 failure leaves only Voter 3 and the tally becomes single-judge if Voter 3 succeeds. Suggested fix: qualify the sentence as round-1 behavior, and add the round-2+ behavior explicitly.
- **Suggested revision**: Address the concern above.

