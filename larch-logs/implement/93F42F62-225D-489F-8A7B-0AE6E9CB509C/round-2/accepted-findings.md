### FINDING_1: code-quality: scripts/design-pause-load.md:60-69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] MARKER_CLEARED=true|false is emitted on the success path but omitted from the documented loader output contract. A test or operator script that validates stdout against design-pause-load.md will not expect MARKER_CLEARED and may fail or ignore post-success marker-delete state. Document MARKER_CLEARED in design-pause-load.md Output Contract (and SECURITY.md if operator-facing) or remove the KV if it is test-only.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/design/scripts/test-design-pause-resume.md:33-34
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness contract says deleted-subtree failures use missing-restored-artifact but implementation and tests now use snapshot-not-found for empty ls-tree enumeration. A maintainer reading the .md sibling could reintroduce the wrong ERROR expectation or miss a regression that restores missing-restored-artifact for empty enumeration. Update the coverage note to snapshot-not-found for empty enumeration/deleted subtree; document missing-restored-artifact only for post-extraction artifact gaps.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/design-pause-load.sh:235-237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Empty ls-tree enumeration returns snapshot-not-found before artifact checks, but design-pause-load.md only describes missing-restored-artifact after extraction. A deleted or never-published snapshot subtree yields ERROR=snapshot-not-found while docs imply missing-restored-artifact, confusing runbooks and plan-aligned fixtures. Document the ! -s enum_tmp early-exit in design-pause-load.md with clear token semantics for empty vs partial snapshots.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/design-pause-load.sh:235-237
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Empty ls-tree enumeration exits early with ERROR=snapshot-not-found instead of falling through to required-artifact checks. After rm -rf of larch-logs/design/<RUN_ID>/ in the snapshot stub, load reports snapshot-not-found; the plan and fixture (a) require missing-restored-artifact so operators/automation cannot distinguish empty subtree from missing ref using the planned ERROR token. Remove the ! -s enum_tmp early exit (reserve snapshot-not-found for pre-enumeration ref/fetch failures) and restore missing-restored-artifact for empty enumeration; align deleted-subtree test and test-design-pause-resume.md.
- **Suggested revision**: Address the concern above.


### FINDING_25: architecture: python/ship.py
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] python/ship.py and python/test_ship.py were modified in round-1 review but are not in the plan file list for pause/resume WI1-WI3. The branch bundles unrelated ship-pr resume/OOS-gate logic with the pause/resume fix, breaking plan-to-diff traceability and review scope. Split ship.py changes to a separate PR or extend the plan and acceptance criteria to cover them explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/design-pause-load.sh:323-328
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] MARKER_CLEARED KV was added without updating design-pause-load.md or SECURITY.md output contracts. Downstream parsers/docs only know about WARN=marker-delete-failed per plan; MARKER_CLEARED is test-only surface with no contract doc. Document MARKER_CLEARED in design-pause-load.md and SECURITY.md, or remove it and keep WARN-only signaling per plan.
- **Suggested revision**: Address the concern above.


### FINDING_27: architecture: scripts/design-pause-load.sh:311
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Load clears restored .pause-requested after install but plan and design-pause-load.md omit this. Future readers may reintroduce immediate re-pause loops or omit harness coverage for restored pause-requested state. Add a contract bullet that successful load removes $DESIGN_TMPDIR/.pause-requested (separate from issue-body marker deletion).
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: skills/design/scripts/test-design-pause-resume.md:33-34
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test harness doc says deleted-subtree missing-restored-artifact but test expects snapshot-not-found. Readers following the .md contract will misdiagnose failures or file wrong bug reports. Update the .md to snapshot-not-found or revert code/tests to missing-restored-artifact per plan.
- **Suggested revision**: Address the concern above.


### FINDING_29: **correctness** `scripts/design-pause-load.sh:235-236` — After a successful `git ls-tree` (exit 0, ref already resolved at lines 206–228), an empty `enum_tmp` short-circuits to `ERROR=snapshot-not-found` instead of continuing to the required-artifact checks that emit `ERROR=missing-restored-artifact` (lines 262–266). That reuses the same token as genuine ref-resolution failures (`fetch` / `show-ref` at lines 209–226), so operators and automation cannot tell “git ref missing” from “ref OK but `larch-logs/design/<RUN_ID>/` has no blobs” (deleted subtree, wrong `RUN_ID`, never-published snapshot). The plan’s edge cases and `design-pause-load.md` describe empty-subtree / missing-content as `missing-restored-artifact`; round 1 added this early exit and the harness at `skills/design/scripts/test-design-pause-resume.sh:870` now expects `snapshot-not-found`, but `skills/design/scripts/test-design-pause-resume.md:33-34` still documents deleted-subtree coverage as `missing-restored-artifact`. **Suggested fix:** Drop the `if [[ ! -s "$enum_tmp" ]]` block and let an empty enumeration fall through to the existing `manifest.json` / `run-params.json` / `pause-state.txt` checks (emitting `missing-restored-artifact`), reserving `snapshot-not-found` for fetch/show-ref failures only; align the test and `.md` sibling with that contract.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - **correctness** `scripts/design-pause-load.sh:235-236` — After a successful `git ls-tree` (exit 0, ref already resolved at lines 206–228), an empty `enum_tmp` short-circuits to `ERROR=snapshot-not-found` instead of continuing to the required-artifact checks that emit `ERROR=missing-restored-artifact` (lines 262–266). That reuses the same token as genuine ref-resolution failures (`fetch` / `show-ref` at lines 209–226), so operators and automation cannot tell “git ref missing” from “ref OK but `larch-logs/design/<RUN_ID>/` has no blobs” (deleted subtree, wrong `RUN_ID`, never-published snapshot). The plan’s edge cases and `design-pause-load.md` describe empty-subtree / missing-content as `missing-restored-artifact`; round 1 added this early exit and the harness at `skills/design/scripts/test-design-pause-resume.sh:870` now expects `snapshot-not-found`, but `skills/design/scripts/test-design-pause-resume.md:33-34` still documents deleted-subtree coverage as `missing-restored-artifact`. **Suggested fix:** Drop the `if [[ ! -s "$enum_tmp" ]]` block and let an empty enumeration fall through to the existing `manifest.json` / `run-params.json` / `pause-state.txt` checks (emitting `missing-restored-artifact`), reserving `snapshot-not-found` for fetch/show-ref failures only; align the test and `.md` sibling with that contract.
- **Suggested revision**: Address the concern above.


### FINDING_35: **risk-integration** `scripts/design-pause-load.sh:235-237` — After a ref resolves successfully, an empty `ls-tree` enumeration now emits `ERROR=snapshot-not-found`, collapsing three previously distinct failure shapes into one token: fetch/show-ref failure, wrong/missing ref, and “ref OK but snapshot subtree empty/corrupt.” Before this branch, an empty `git archive | tar` install fell through to `missing-restored-artifact`, so operators and harnesses could tell “remote resolved, content missing” apart from “could not find snapshot ref.” The regression harness at `skills/design/scripts/test-design-pause-resume.sh:862-871` was updated to expect `snapshot-not-found`, but the plan acceptance still called for `missing-restored-artifact` on the deleted-subtree fixture. **Suggested fix:** Reserve `snapshot-not-found` for fetch/show-ref failures only; when `ls-tree` succeeds but the buffer is empty (or required root artifacts are absent after extraction), emit `missing-restored-artifact` so retryable content gaps stay distinguishable from ref-resolution failures.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:235-237` — After a ref resolves successfully, an empty `ls-tree` enumeration now emits `ERROR=snapshot-not-found`, collapsing three previously distinct failure shapes into one token: fetch/show-ref failure, wrong/missing ref, and “ref OK but snapshot subtree empty/corrupt.” Before this branch, an empty `git archive | tar` install fell through to `missing-restored-artifact`, so operators and harnesses could tell “remote resolved, content missing” apart from “could not find snapshot ref.” The regression harness at `skills/design/scripts/test-design-pause-resume.sh:862-871` was updated to expect `snapshot-not-found`, but the plan acceptance still called for `missing-restored-artifact` on the deleted-subtree fixture. **Suggested fix:** Reserve `snapshot-not-found` for fetch/show-ref failures only; when `ls-tree` succeeds but the buffer is empty (or required root artifacts are absent after extraction), emit `missing-restored-artifact` so retryable content gaps stay distinguishable from ref-resolution failures.
- **Suggested revision**: Address the concern above.


### FINDING_43: **architecture** `scripts/design-pause-load.sh:235-237` vs `scripts/design-pause-load.sh:262-267` — Empty `ls-tree` enumeration (deleted `larch-logs/design/<RUN_ID>/` subtree) now short-circuits to `ERROR=snapshot-not-found`, while a non-empty enumeration that lacks `manifest.json` / `run-params.json` / `pause-state.txt` still yields `ERROR=missing-restored-artifact`. The plan and edge-case prose treated an empty subtree as `missing-restored-artifact`; the harness at `skills/design/scripts/test-design-pause-resume.sh:862-870` codifies `snapshot-not-found` instead. Marker retention is the same, but operators and automation lose a distinct “snapshot published but incomplete/corrupt” signal. **Suggested fix:** Drop the `! -s "$enum_tmp"` early exit and let the existing required-artifact loop emit `missing-restored-artifact` for empty enumeration; or document `snapshot-not-found` as the canonical empty-subtree token everywhere (contract + tests + SECURITY.md).
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - **architecture** `scripts/design-pause-load.sh:235-237` vs `scripts/design-pause-load.sh:262-267` — Empty `ls-tree` enumeration (deleted `larch-logs/design/<RUN_ID>/` subtree) now short-circuits to `ERROR=snapshot-not-found`, while a non-empty enumeration that lacks `manifest.json` / `run-params.json` / `pause-state.txt` still yields `ERROR=missing-restored-artifact`. The plan and edge-case prose treated an empty subtree as `missing-restored-artifact`; the harness at `skills/design/scripts/test-design-pause-resume.sh:862-870` codifies `snapshot-not-found` instead. Marker retention is the same, but operators and automation lose a distinct “snapshot published but incomplete/corrupt” signal. **Suggested fix:** Drop the `! -s "$enum_tmp"` early exit and let the existing required-artifact loop emit `missing-restored-artifact` for empty enumeration; or document `snapshot-not-found` as the canonical empty-subtree token everywhere (contract + tests + SECURITY.md).
- **Suggested revision**: Address the concern above.


### FINDING_44: **architecture** `scripts/design-pause-load.sh:323-328` and `scripts/design-pause-load.md:60-64` — Round 1 added `MARKER_CLEARED=true|false` on the success path, but the contract doc still lists only `WARN=body-drift` / `WARN=marker-delete-failed`. `design-route.sh:300-312` also does not parse or relay `MARKER_CLEARED`, so integrated `/design` runs only see `WARN=marker-delete-failed` while direct loader callers can see both. That splits the lifecycle contract across call paths. **Suggested fix:** Either document `MARKER_CLEARED` in `design-pause-load.md` (and parse/relay it in `design-route.sh`’s pause-load KV loop), or drop `MARKER_CLEARED` and rely solely on `WARN=marker-delete-failed` for a single cross-boundary signal.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - **architecture** `scripts/design-pause-load.sh:323-328` and `scripts/design-pause-load.md:60-64` — Round 1 added `MARKER_CLEARED=true|false` on the success path, but the contract doc still lists only `WARN=body-drift` / `WARN=marker-delete-failed`. `design-route.sh:300-312` also does not parse or relay `MARKER_CLEARED`, so integrated `/design` runs only see `WARN=marker-delete-failed` while direct loader callers can see both. That splits the lifecycle contract across call paths. **Suggested fix:** Either document `MARKER_CLEARED` in `design-pause-load.md` (and parse/relay it in `design-route.sh`’s pause-load KV loop), or drop `MARKER_CLEARED` and rely solely on `WARN=marker-delete-failed` for a single cross-boundary signal.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/design-pause-load.sh:311
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Success path clears .pause-requested without contract documentation. Operators debugging a resumed session may not know the loader clears pause-requested state, leading to confusion about why a mid-run pause flag vanished. Mention .pause-requested removal in the success-path section of design-pause-load.md.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/design-pause-load.sh:235-237
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Empty ls-tree enumeration exits with snapshot-not-found before artifact checks, contradicting plan/acceptance that require missing-restored-artifact for deleted/missing snapshot subtrees. After rm -rf of larch-logs/design/RUN_ID/ on the selected ref, loader emits ERROR=snapshot-not-found; operators and acceptance text expect missing-restored-artifact for this shape. Remove the ! -s enum_tmp early exit and rely on missing-restored-artifact checks, or update plan acceptance and operator docs to standardize on snapshot-not-found for empty enumeration.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/design-pause-load.md:33-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Contract omits the empty-enumeration error branch present in the shell implementation. Maintainer reads design-pause-load.md only and misexpects missing-restored-artifact when ls-tree returns zero paths. Document which ERROR token empty enumeration produces and how it differs from snapshot-extract-failed and missing-restored-artifact.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/scripts/test-design-pause-resume.md:33-35
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness doc says deleted-subtree uses missing-restored-artifact but the test asserts snapshot-not-found. Doc-driven debugging contradicts test expectations. Align the markdown coverage note with the test and chosen error token.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/design/scripts/test-design-pause-resume.sh:875-881
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No fixture exercises GIT_STUB_SHOW_FAIL for per-path git show failures. A bug in the git show guard could ship while ls-tree-only failure remains green. Add a GIT_STUB_SHOW_FAIL=1 case expecting snapshot-extract-failed and marker retention.
- **Suggested revision**: Address the concern above.


