### [Plan Review] FINDING_10

### FINDING_10: Three near-identical PROMPT splice blocks
- **Concern**: Each of the three CI launchers will have its own copy of the fragment-load + PROMPT-splice block. This invites drift over time, even with the launcher-parity rule. There's already a `scripts/lib-cursor-launcher-common.sh` that provides shared helpers across cursor launchers; nothing similar spans cursor+codex+claude today, but a small helper here would prevent future drift.
- **Proposed resolution**: Extract the fragment-load logic into a new helper `scripts/lib-ci-fix-fragment.sh` (or extend an existing common library) with a function like `ci_fix_load_patterns_fragment` that the three launchers call. Each launcher then reduces to one line: `LARCH_PATTERNS=$(ci_fix_load_patterns_fragment)` followed by the existing PROMPT splice. This is a nit (the launcher-parity rule + sentinel-substring tests already catch drift), but it'd remove a class of recurring parity bugs.
- **Reviewers**: Cursor-Innovation (1 reviewer)
- **Severity**: Nit


### [Plan Review] FINDING_2

### FINDING_2: Missing regression test for the real ci-decide producer
- **Concern**: The existing exit-3 stub test (`test-ship-pr.sh:1042-1047`) injects `STUB_BAIL_REASON=fix-attempts-exhausted` directly, bypassing `ci-decide.sh` entirely. The plan changes the only real producer (`ci-decide.sh`'s `FIX_ATTEMPTS >= 10` branch) but adds NO test that exercises `ci-decide.sh` itself emitting the new exact-match token. If a future edit reverts the prose-vs-token change, no test catches it.
- **Proposed resolution**: Extend `scripts/test-ci-decide.sh` (existing file) with a test that runs `ci-decide.sh` with `FIX_ATTEMPTS=10` (other inputs in any valid state) and asserts the stdout envelope contains exactly `ACTION=bail` and `BAIL_REASON=fix-attempts-exhausted` (no surrounding prose). Add an acceptance criterion noting this.
- **Reviewers**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-exit-contract (6 reviewers)
- **Severity**: Important


### [Plan Review] FINDING_3

### FINDING_3: New batch slug not reflected in canonical run-log docs
- **Concern**: Plan registers `final-bail-reason` in `scripts/larch-log-batches.sh` and updates the sibling `.md`'s prose list, but does NOT update `docs/run-logs.md` (canonical run-log layout doc enumerated in AGENTS.md) or the required-file enumeration in `scripts/verify-run-log-completeness.sh`. Downstream verifier may either (a) miss the batch in the inventory or (b) reject runs where the file is absent (most bail paths won't write it).
- **Proposed resolution**: Add `docs/run-logs.md` and `scripts/verify-run-log-completeness.sh` to the files-to-modify list. In the verifier, classify `final-bail-reason` as optional (not required) since it only exists on bail/stall paths. In `docs/run-logs.md` add a one-line entry under the existing batch enumeration noting it captures `BAIL_REASON` for bail/stall outcomes.
- **Reviewers**: Cursor-Innovation, Cursor-Pragmatic, Codex-Arch, Codex-Innovation, Codex-Requirements (5 reviewers)
- **Severity**: Important


### [Plan Review] FINDING_9

### FINDING_9: Conflated exit-4 STALL_STEP semantics
- **Concern**: Plan §"Failure modes" #2 doesn't disambiguate between the two distinct `STALL_STEP="10-max-retries"` callsites: (a) `run_evaluate_failure` vendor-loop exhaustion at ship-pr.sh:1503, vs (b) `run_rebase_rebump`'s rebase storm cap (uses different STALL_STEP tokens but operators reading bail logs may confuse them). The plan's test stubs evaluate_failure but the prose risks future regressions where rebase code reuses the token.
- **Proposed resolution**: Add a one-line note to the failure-modes section: "Vendor-loop exhaustion sets `STALL_STEP=10-max-retries` (ci-initial) / `STALL_STEP=12-max-retries` (ci-merge); these are emitted ONLY from `run_evaluate_failure`. Do not reuse these tokens in unrelated cap paths." No code change needed unless an audit finds reuse.
- **Reviewers**: Cursor-Edge (1 reviewer)
- **Severity**: Latent


